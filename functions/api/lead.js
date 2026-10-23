// Cloudflare Pages Function — POST /api/lead
// Receives the form submission from public/index.html, enriches it,
// and creates a Lead in Zoho CRM via the official REST API.
//
// Required Cloudflare Pages env vars (Settings → Env):
//   ZOHO_CLIENT_ID
//   ZOHO_CLIENT_SECRET
//   ZOHO_REFRESH_TOKEN      (one-time generated in Zoho API Console)
//   ZOHO_API_DOMAIN         "https://www.zohoapis.eu"   <- Unitty org is EU
//   ZOHO_ACCOUNTS_DOMAIN    "https://accounts.zoho.eu"  <- EU, not .com
//
// The function:
//   1. Validates required fields.
//   2. Refreshes the Zoho access token via refresh_token (short-lived).
//   3. Maps the form payload to the Unitty CRM Lead fields (incl. lowercase utm_*).
//   4. POSTs to /crm/v6/Leads.
//   5. Returns { ok: true, lead_id } or { ok: false, error }.

const ZOHO_API_VERSION = "v6";

export async function onRequestPost(context) {
  const { request, env } = context;

  // 1. Parse + validate
  let body;
  try {
    body = await request.json();
  } catch (e) {
    return json({ ok: false, error: "Invalid JSON" }, 400);
  }

  const required = ["firstName", "email", "phone", "company"];
  for (const field of required) {
    if (!body[field] || String(body[field]).trim() === "") {
      return json({ ok: false, error: `Missing required field: ${field}` }, 400);
    }
  }

  // 2. Refresh Zoho access token
  let accessToken;
  try {
    accessToken = await refreshZohoToken(env);
  } catch (err) {
    return json({ ok: false, error: "Zoho auth failed: " + err.message }, 500);
  }

  // 3. Map payload -> Zoho Lead (Unitty CRM field API names, confirmed 2026-10-23)
  //
  // Empty values are stripped below rather than sent as "". Zoho rejects an
  // empty string on a picklist, and a rejected field can fail the whole record.
  const lead = {
    First_Name: body.firstName,
    Last_Name: body.lastName || "(not provided)",
    Email: body.email,
    Mobile: body.phone,
    Company: body.company,
    Industry: body.industry,
    Designation: body.jobTitle,               // "Designation" = job title in Zoho
    Lead_Source: body.heardFrom,              // the "where did you hear about us" answer
    Description: buildDescription(body),

    // attribution - lowercase API names, as created on the Unitty org
    utm_source: body.utm_source,
    utm_medium: body.utm_medium,
    utm_campaign: body.utm_campaign,
    utm_content: body.utm_content,
    utm_term: body.utm_term,
    page_url: body.submission_url,
    language_version: mapLanguageVersion(body.lang),
  };

  // first_touch is deliberately not sent yet - parked until it is implemented
  // the same way as on the other sites. Everything else stays in Description.

  for (const k of Object.keys(lead)) {
    if (lead[k] === undefined || lead[k] === null || String(lead[k]).trim() === "") {
      delete lead[k];
    }
  }

  // 4. POST to Zoho
  const zohoRes = await fetch(
    `${env.ZOHO_API_DOMAIN}/crm/${ZOHO_API_VERSION}/Leads`,
    {
      method: "POST",
      headers: {
        Authorization: `Zoho-oauthtoken ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data: [lead],
        trigger: ["approval", "workflow", "blueprint"],
      }),
    }
  );

  const zohoBody = await zohoRes.json().catch(() => ({}));

  if (!zohoRes.ok || zohoBody?.data?.[0]?.status !== "success") {
    console.error("Zoho error:", JSON.stringify(zohoBody));
    return json({
      ok: false,
      error: "Zoho rejected the lead",
      zoho: zohoBody,
    }, 502);
  }

  const leadId = zohoBody.data[0].details.id;

  return json({ ok: true, lead_id: leadId });
}

// ---------- Helpers ----------

async function refreshZohoToken(env) {
  const url = new URL(`${env.ZOHO_ACCOUNTS_DOMAIN}/oauth/v2/token`);
  url.searchParams.set("refresh_token", env.ZOHO_REFRESH_TOKEN);
  url.searchParams.set("client_id", env.ZOHO_CLIENT_ID);
  url.searchParams.set("client_secret", env.ZOHO_CLIENT_SECRET);
  url.searchParams.set("grant_type", "refresh_token");

  const res = await fetch(url.toString(), { method: "POST" });
  if (!res.ok) throw new Error("Token refresh HTTP " + res.status);
  const data = await res.json();
  if (!data.access_token) throw new Error("No access_token in response: " + JSON.stringify(data));
  return data.access_token;
}

function mapLanguageVersion(lang) {
  // the page stores en/ka/ru; the Zoho picklist expects En/Ka/Ru
  const map = { en: "En", ka: "Ka", ru: "Ru" };
  return map[String(lang || "").toLowerCase()] || "";
}

function buildDescription(body) {
  const lines = [
    `Landing version: ${body.landing_version || "?"}`,
    `Language: ${body.lang || "?"}`,
    `Submitted: ${body.submission_timestamp || new Date().toISOString()}`,
    `From URL: ${body.submission_url || "?"}`,
    "",
    "— TRACKING —",
    `Last-touch UTM: source=${body.utm_source || "-"} medium=${body.utm_medium || "-"} campaign=${body.utm_campaign || "-"} content=${body.utm_content || "-"}`,
    `First-touch UTM: source=${body.first_utm_source || "-"} campaign=${body.first_utm_campaign || "-"}`,
    `First referrer: ${body.first_referrer || "-"}`,
    `First landing: ${body.first_landing_url || "-"}`,
    `First touch date: ${body.first_touch_date || "-"}`,
    `Heard from (self-reported): ${body.heardFrom || "-"}`,
    "",
    "— SELECTED SOLUTIONS —",
    body.selected_solutions || "(none selected on landing)",
    "",
    "— USER AGENT —",
    body.submission_user_agent || "-",
  ];
  return lines.join("\n");
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

// CORS preflight
export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}
