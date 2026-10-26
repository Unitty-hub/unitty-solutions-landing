// Cloudflare Pages Function — POST /api/lead
// Receives the form submission from public/index.html, enriches it with server-side data
// (client IP, user agent, country), creates a Lead in Zoho CRM and - when configured -
// sends the same Lead event to the Meta Conversions API.
//
// Required Cloudflare Pages env vars (Settings → Variables and Secrets):
//   ZOHO_CLIENT_ID
//   ZOHO_CLIENT_SECRET
//   ZOHO_REFRESH_TOKEN      (one-time generated in Zoho API Console)
//   ZOHO_API_DOMAIN         "https://www.zohoapis.eu"   <- Unitty org is EU
//   ZOHO_ACCOUNTS_DOMAIN    "https://accounts.zoho.eu"  <- EU, not .com
//
// Optional (Meta Conversions API - leave unset to skip):
//   META_PIXEL_ID           "1468998947504136"
//   META_CAPI_TOKEN         access token from Events Manager → Settings → Conversions API
//   META_TEST_EVENT_CODE    e.g. "TEST12345" while testing in Events Manager, then remove
//
// The function:
//   1. Validates required fields.
//   2. Refreshes the Zoho access token via refresh_token (short-lived).
//   3. Maps the payload to the Unitty CRM Lead fields (attribution, Meta IDs, landing version).
//   4. POSTs to /crm/v6/Leads.
//   5. Sends a server-side "Lead" event to Meta with the same event_id as the browser Pixel
//      (Meta deduplicates the pair), without delaying the response.
//   6. Returns { ok: true, lead_id } or { ok: false, error }.

const ZOHO_API_VERSION = "v6";
const META_GRAPH_VERSION = "v21.0";

export async function onRequestPost(context) {
  const { request, env } = context;

  // 1. Parse + validate
  let body;
  try {
    body = await request.json();
  } catch (e) {
    return json({ ok: false, error: "Invalid JSON" }, 400);
  }

  const required = ["fullName", "email", "phone", "company"];
  for (const field of required) {
    if (!body[field] || String(body[field]).trim() === "") {
      return json({ ok: false, error: `Missing required field: ${field}` }, 400);
    }
  }

  const attr = body.attribution || {};
  const utm = attr.utm || {};
  const server = {
    ip: request.headers.get("CF-Connecting-IP") || "",
    userAgent: request.headers.get("User-Agent") || attr.user_agent || "",
    country: (request.cf && request.cf.country) || "",
    city: (request.cf && request.cf.city) || "",
  };
  console.log(">>> lead received", JSON.stringify({ version: attr.landing_version, utm, fbclid: !!attr.fbclid, eid: body.event_id }));

  // 2. Refresh Zoho access token
  let accessToken;
  try {
    accessToken = await refreshZohoToken(env);
  } catch (err) {
    console.log("*** zoho auth failed", err.message);
    return json({ ok: false, error: "Zoho auth failed: " + err.message }, 500);
  }

  // 3. Map payload -> Zoho Lead (Unitty CRM field API names, confirmed 2026-10-26)
  //
  // Empty values are stripped below rather than sent as "". Zoho rejects an
  // empty string on a picklist, and a rejected field can fail the whole record.
  // Single "Full Name" field: one word -> Last_Name only;
  // two or more words -> first word is First_Name, the rest is Last_Name.
  const { firstName, lastName } = splitFullName(body.fullName);

  const lead = {
    First_Name: firstName,
    Last_Name: lastName,
    Email: body.email,
    Mobile: body.phone,
    Company: body.company,
    Lead_Source: body.heardFrom,              // the "where did you hear about us" answer (self-reported)
    Description: buildDescription(body, attr, server),

    // attribution - last-touch campaign (lowercase API names, as created on the Unitty org)
    utm_source: utm.utm_source,
    utm_medium: utm.utm_medium,
    utm_campaign: utm.utm_campaign,
    utm_content: utm.utm_content,
    utm_term: utm.utm_term,
    page_url: clip(attr.submission_url, 450),
    language_version: mapLanguageVersion(body.lang),
    first_touch: clip(JSON.stringify(attr.first_touch || {}), 2000),

    // landing version + full landing URL (fields created 2026-10-26)
    Landing_Version: attr.landing_version,
    Landing_URL: clip(attr.landing_url, 2000),

    // click IDs + Meta matching keys, for Conversions API feedback from the CRM later
    fbclid: clip(attr.fbclid, 255),
    fbc: clip(attr.fbc || buildFbc(attr.fbclid), 2000),
    fbp: clip(attr.fbp, 255),
    Google_Click_ID: clip(attr.gclid, 255),
    Client_IP: clip(server.ip, 100),
    Client_User_Agent: clip(server.userAgent, 2000),
    Meta_Event_ID: clip(body.event_id, 100),
  };

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
    console.error("*** Zoho error:", JSON.stringify(zohoBody));
    return json({
      ok: false,
      error: "Zoho rejected the lead",
      zoho: zohoBody,
    }, 502);
  }

  const leadId = zohoBody.data[0].details.id;
  console.log("+++ zoho lead created", leadId);

  // 5. Meta Conversions API - runs after the response, never blocks or fails the lead
  if (env.META_CAPI_TOKEN && body.event_id) {
    context.waitUntil(
      sendMetaLead(env, body, attr, server, leadId).catch((e) => console.log("*** meta capi failed", e.message))
    );
  }

  console.log("<<< done", leadId);
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

async function sendMetaLead(env, body, attr, server, leadId) {
  const pixelId = env.META_PIXEL_ID || "1468998947504136";
  const { firstName, lastName } = splitFullName(body.fullName);
  const userData = {
    em: [await sha256(String(body.email || "").trim().toLowerCase())],
    ph: [await sha256(normalizePhone(body.phone))],
    fn: firstName ? [await sha256(firstName.trim().toLowerCase())] : undefined,
    ln: lastName ? [await sha256(lastName.trim().toLowerCase())] : undefined,
    country: server.country ? [await sha256(server.country.toLowerCase())] : undefined,
    external_id: [await sha256(String(leadId))],   // the Zoho Lead ID - lets later CRM events match this lead
    client_ip_address: server.ip || undefined,
    client_user_agent: server.userAgent || undefined,
    fbc: attr.fbc || buildFbc(attr.fbclid) || undefined,
    fbp: attr.fbp || undefined,
  };
  const event = {
    event_name: "Lead",
    event_time: Math.floor(Date.now() / 1000),
    event_id: body.event_id,                       // same as the browser Pixel event -> deduplicated
    action_source: "website",
    event_source_url: attr.submission_url || undefined,
    user_data: userData,
    custom_data: {
      lead_source: body.heardFrom || undefined,
      landing_version: attr.landing_version || undefined,
      utm_campaign: (attr.utm || {}).utm_campaign || undefined,
    },
  };
  const payload = { data: [event] };
  if (env.META_TEST_EVENT_CODE) payload.test_event_code = env.META_TEST_EVENT_CODE;

  const res = await fetch(
    `https://graph.facebook.com/${META_GRAPH_VERSION}/${pixelId}/events?access_token=${encodeURIComponent(env.META_CAPI_TOKEN)}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }
  );
  const out = await res.text();
  console.log(res.ok ? "+++ meta capi lead sent" : "*** meta capi error", res.status, out.slice(0, 300));
}

async function sha256(value) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Meta wants digits only, with country code. Georgian mobiles typed as 5XX XXX XXX get 995 in front.
function normalizePhone(phone) {
  let d = String(phone || "").replace(/\D/g, "");
  if (d.startsWith("00")) d = d.slice(2);
  if (d.length === 9 && d.startsWith("5")) d = "995" + d;
  return d;
}

function buildFbc(fbclid) {
  return fbclid ? `fb.1.${Date.now()}.${fbclid}` : "";
}

function clip(value, max) {
  if (value === undefined || value === null) return value;
  const s = String(value);
  return s.length > max ? s.slice(0, max) : s;
}

function splitFullName(fullName) {
  const parts = String(fullName || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length <= 1) {
    return { firstName: "", lastName: parts[0] || "" };
  }
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}

function mapLanguageVersion(lang) {
  // the page stores en/ka/ru; the Zoho picklist expects En/Ka/Ru
  const map = { en: "En", ka: "Ka", ru: "Ru" };
  return map[String(lang || "").toLowerCase()] || "";
}

function buildDescription(body, attr, server) {
  const utm = attr.utm || {};
  const fu = attr.first_utm || {};
  const first = attr.first_touch || {};
  const lines = [
    `Landing version: ${attr.landing_version || "?"}`,
    `Language: ${body.lang || "?"}`,
    `Submitted: ${attr.submitted_at || new Date().toISOString()}`,
    `From URL: ${attr.submission_url || "?"}`,
    "",
    "— TRACKING —",
    `First landing URL: ${attr.landing_url || "-"}`,
    `Last-touch URL: ${attr.last_touch_url || "-"}`,
    `Last-touch UTM: source=${utm.utm_source || "-"} medium=${utm.utm_medium || "-"} campaign=${utm.utm_campaign || "-"} content=${utm.utm_content || "-"} term=${utm.utm_term || "-"}`,
    `First-touch UTM: source=${fu.utm_source || "-"} medium=${fu.utm_medium || "-"} campaign=${fu.utm_campaign || "-"}`,
    `Click IDs: ${JSON.stringify(attr.click_ids || {})}`,
    `First referrer: ${attr.first_referrer || "-"} | Last referrer: ${attr.referrer || "-"}`,
    `First touch time: ${first.ts || "-"}`,
    `Heard from (self-reported): ${body.heardFrom || "-"}`,
    `Visitor: ${server.country || "-"} ${server.city || ""} | tz ${attr.tz || "-"} | screen ${attr.screen || "-"}`,
    `Meta event_id: ${body.event_id || "-"}`,
    "",
    "— SELECTED SOLUTIONS —",
    body.selected_solutions || "(none selected on landing)",
    "",
    "— USER AGENT —",
    server.userAgent || "-",
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
