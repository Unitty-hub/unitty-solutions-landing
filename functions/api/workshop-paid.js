// Cloudflare Pages Function: POST /api/workshop-paid  (v1, 2026-11-24)
//
// Called from workshop.unitty.io/workshop/pay/ when the visitor clicks "გადავიხადე" (I have paid).
// It does NOT mark the lead as paid - a bank transfer is only confirmed by the bank statement
// (bank integration or a person in Zoho). It only records the visitor's claim:
//   1. checks that the lead exists and its Description contains the same payment ref (WS-xxxxxx),
//      so a random lead id cannot be written to;
//   2. adds a Note to the Zoho Lead: "Workshop: visitor says payment was sent";
//   3. when env WORKSHOP_FIELDS = "1", sets Workshop_Payment_Status = "Claimed" (custom field).
//
// Env (same as lead.js): ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ZOHO_API_DOMAIN, ZOHO_ACCOUNTS_DOMAIN.

const ZOHO_API_VERSION = "v6";
const VERSION = "workshop-paid-v1-2026-11-24";

export async function onRequestPost(context) {
  const { request, env } = context;
  let body;
  try {
    body = await request.json();
  } catch (e) {
    return json({ ok: false, error: "Invalid JSON" }, 400);
  }
  const leadId = String(body.lead_id || "");
  const ref = String(body.ref || "");
  console.log(">>> workshop paid claim", JSON.stringify({ v: VERSION, leadId, ref }));
  if (!/^\d{6,25}$/.test(leadId) || !/^WS-\d{6}$/.test(ref)) {
    console.log("*** invalid input");
    return json({ ok: false, error: "Invalid lead_id or ref" }, 400);
  }

  let token;
  try {
    token = await refreshZohoToken(env);
  } catch (err) {
    console.log("*** zoho auth failed", err.message);
    return json({ ok: false, error: "Zoho auth failed" }, 500);
  }
  const base = `${env.ZOHO_API_DOMAIN}/crm/${ZOHO_API_VERSION}/Leads/${leadId}`;
  const headers = { Authorization: `Zoho-oauthtoken ${token}`, "Content-Type": "application/json" };

  // 1. the lead must exist and carry this ref
  const getRes = await fetch(`${base}?fields=Description`, { headers });
  const getBody = await getRes.json().catch(() => ({}));
  const desc = getBody?.data?.[0]?.Description || "";
  if (!getRes.ok || !desc.includes(`Payment ref: ${ref}`)) {
    console.log("*** lead/ref mismatch", JSON.stringify({ status: getRes.status, found: !!desc }));
    return json({ ok: false, error: "Lead not found for this ref" }, 404);
  }
  console.log("--- lead verified", leadId);

  // 2. note on the lead
  const when = new Date().toISOString();
  const ip = request.headers.get("CF-Connecting-IP") || "-";
  const country = (request.cf && request.cf.country) || "-";
  const noteRes = await fetch(`${base}/Notes`, {
    method: "POST",
    headers,
    body: JSON.stringify({ data: [{
      Note_Title: `Workshop: visitor says payment was sent (${ref})`,
      Note_Content: `The visitor clicked "გადავიხადე" on the payment page at ${when}.\nPayment ref: ${ref}\nNot confirmed yet - check the bank statement for this ref, then set the payment status.\nIP ${ip} (${country}) | ${VERSION}`,
    }] }),
  });
  const noteBody = await noteRes.json().catch(() => ({}));
  const noteOk = noteRes.ok && noteBody?.data?.[0]?.status === "success";
  console.log(noteOk ? "+++ note added" : "*** note failed", JSON.stringify(noteBody?.data?.[0] || noteBody));

  // 3. optional custom status field
  if (env.WORKSHOP_FIELDS === "1") {
    const upd = await fetch(base, { method: "PUT", headers, body: JSON.stringify({ data: [{ Workshop_Payment_Status: "Claimed" }], trigger: ["workflow"] }) });
    const updBody = await upd.json().catch(() => ({}));
    console.log("--- status Claimed", upd.status, JSON.stringify(updBody?.data?.[0]?.code || updBody));
  }

  console.log("<<< done", leadId, noteOk);
  return json({ ok: noteOk });
}

async function refreshZohoToken(env) {
  const url = new URL(`${env.ZOHO_ACCOUNTS_DOMAIN}/oauth/v2/token`);
  url.searchParams.set("refresh_token", env.ZOHO_REFRESH_TOKEN);
  url.searchParams.set("client_id", env.ZOHO_CLIENT_ID);
  url.searchParams.set("client_secret", env.ZOHO_CLIENT_SECRET);
  url.searchParams.set("grant_type", "refresh_token");
  const res = await fetch(url.toString(), { method: "POST" });
  if (!res.ok) throw new Error("Token refresh HTTP " + res.status);
  const data = await res.json();
  if (!data.access_token) throw new Error("No access_token");
  return data.access_token;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });
}
