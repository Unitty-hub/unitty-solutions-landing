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
//
// v64 (2026-10-29, shared chat):
//   - Service (multi-select) from the landing: crm -> CRM, ai -> AI, banks/solutions -> Process Automation,
//     start -> Consulting.
//   - City / Country from Cloudflare geo (request.cf), Country as an English name ("Georgia").
//   - Lead_Source mapped to the Zoho picklist spelling (LinkedIn -> Linkedin, YouTube -> Youtube, ...).
//     "Email" is not in the Zoho picklist yet: it is sent as "Email" and, if Zoho rejects it, retried as "Other".
//   - Mobile normalised to +995XXXXXXXXX (international numbers kept as +<digits>).
//   - If Zoho rejects one field (INVALID_DATA), the lead is retried without that field (max 3 retries),
//     so one bad value never loses the whole lead. Dropped fields are listed in the Description.

const ZOHO_API_VERSION = "v6";
const META_GRAPH_VERSION = "v21.0";
const LEAD_JS_VERSION = "v64-2026-10-29";
const MAX_FIELD_RETRIES = 3;

// landing -> Zoho Leads.Service (multi-select picklist values, confirmed 2026-10-29)
const SERVICE_BY_LANDING = {
  crm: "CRM",
  ai: "AI",
  banks: "Process Automation",
  solutions: "Process Automation",
  start: "Consulting",
};

// form "heardFrom" value -> Zoho Leads.Lead_Source picklist value (exact Zoho spelling)
const LEAD_SOURCE_MAP = {
  linkedin: "Linkedin",
  facebook: "Facebook",
  instagram: "Instagram",
  youtube: "Youtube",
  google: "Google",
  ai: "AI",
  email: "Email",            // not in the Zoho picklist yet -> falls back to "Other" on rejection
  recommendation: "Recommendation",
  tiktok: "Tiktok",
  other: "Other",
};
const LEAD_SOURCE_FALLBACK = "Other";
// never dropped on retry (Zoho mandatory / identity fields)
const PROTECTED_FIELDS = ["Last_Name", "Email", "Mobile"];

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
  const landing = detectLanding(body, attr);
  const service = SERVICE_BY_LANDING[landing] || SERVICE_BY_LANDING.start;
  const leadSource = mapLeadSource(body.heardFrom);
  const mobile = normalizeMobile(body.phone);
  console.log(">>> lead received", JSON.stringify({
    lead_js: LEAD_JS_VERSION, landing, service, version: attr.landing_version, utm,
    heardFrom: body.heardFrom, leadSource, fbclid: !!attr.fbclid, eid: body.event_id,
    geo: `${server.country}/${server.city}`,
  }));

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
    Mobile: mobile,
    Company: body.company,
    Lead_Source: leadSource,                  // the "where did you hear about us" answer, Zoho spelling
    Service: [service],                       // multi-select picklist -> array
    City: clip(server.city, 100),
    Country: clip(countryName(server.country), 100),
    Description: buildDescription(body, attr, server, { landing, service, leadSource }),

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

  // 4. POST to Zoho - on a single rejected field, retry without it (or with the fallback value)
  let zohoRes, zohoBody;
  const dropped = [];
  const baseDescription = lead.Description || "";
  for (let attempt = 0; attempt <= MAX_FIELD_RETRIES; attempt++) {
    zohoRes = await postZohoLead(env, accessToken, lead);
    zohoBody = await zohoRes.json().catch(() => ({}));
    const rec = zohoBody?.data?.[0] || {};
    if (zohoRes.ok && rec.status === "success") break;

    const field = rec?.details?.api_name;
    console.log("--- zoho rejected", JSON.stringify({ attempt, code: rec.code, field, message: rec.message }));
    if (attempt === MAX_FIELD_RETRIES || !field || !(field in lead)) break;

    if (field === "Lead_Source" && lead.Lead_Source !== LEAD_SOURCE_FALLBACK) {
      dropped.push(`Lead_Source=${lead.Lead_Source} -> ${LEAD_SOURCE_FALLBACK}`);
      lead.Lead_Source = LEAD_SOURCE_FALLBACK;
    } else if (PROTECTED_FIELDS.includes(field)) {
      break;                                   // cannot create a useful lead without it
    } else {
      dropped.push(`${field}=${clip(JSON.stringify(lead[field]), 120)}`);
      delete lead[field];
    }
    lead.Description = baseDescription + `\n\n— ZOHO RETRY —\nRejected and adjusted: ${dropped.join("; ")}`;
    console.log("*** retrying lead", JSON.stringify({ attempt: attempt + 1, dropped }));
  }

  if (!zohoRes.ok || zohoBody?.data?.[0]?.status !== "success") {
    console.error("*** Zoho error:", JSON.stringify(zohoBody));
    return json({
      ok: false,
      error: "Zoho rejected the lead",
      zoho: zohoBody,
    }, 502);
  }

  const leadId = zohoBody.data[0].details.id;
  console.log("+++ zoho lead created", leadId, dropped.length ? JSON.stringify({ dropped }) : "");

  // 5. Meta Conversions API - runs after the response, never blocks or fails the lead
  if (env.META_CAPI_TOKEN && body.event_id) {
    context.waitUntil(
      sendMetaLead(env, body, attr, server, leadId, leadSource).catch((e) => console.log("*** meta capi failed", e.message))
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

async function postZohoLead(env, accessToken, lead) {
  return fetch(`${env.ZOHO_API_DOMAIN}/crm/${ZOHO_API_VERSION}/Leads`, {
    method: "POST",
    headers: {
      Authorization: `Zoho-oauthtoken ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      data: [lead],
      trigger: ["approval", "workflow", "blueprint"],
    }),
  });
}

// Which landing sent the lead: "crm-v75-2026-10-29" -> crm; else the host (crm.unitty.io) or path (/crm/).
function detectLanding(body, attr) {
  const known = Object.keys(SERVICE_BY_LANDING);
  const fromVersion = String(attr.landing_version || "").toLowerCase().split("-v")[0];
  if (known.includes(fromVersion)) return fromVersion;
  const fromBody = String(body.landing || "").toLowerCase();
  if (known.includes(fromBody)) return fromBody;
  try {
    const u = new URL(attr.submission_url || attr.landing_url || "");
    const sub = u.hostname.split(".")[0];
    if (known.includes(sub)) return sub;
    const seg = u.pathname.split("/").filter(Boolean)[0];
    if (known.includes(seg)) return seg;
  } catch (e) {}
  return "start";
}

function mapLeadSource(heardFrom) {
  const key = String(heardFrom || "").trim().toLowerCase();
  if (!key) return "";
  return LEAD_SOURCE_MAP[key] || LEAD_SOURCE_FALLBACK;
}

// Zoho Mobile: +995XXXXXXXXX for Georgian numbers, +<digits> for international ones.
function normalizeMobile(phone) {
  const raw = String(phone || "").trim();
  let d = raw.replace(/\D/g, "");
  if (!d) return raw;
  if (d.startsWith("00")) d = d.slice(2);
  if (d.length === 9 && /^[235]/.test(d)) return "+995" + d;   // 5XX XXX XXX mobile, 32/2X landline
  if (d.length === 12 && d.startsWith("995")) return "+" + d;
  return "+" + d;
}

// "GE" -> "Georgia" (falls back to the code if Intl.DisplayNames is unavailable)
function countryName(code) {
  if (!code || code === "XX" || code === "T1") return "";
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) || code;
  } catch (e) {
    return code;
  }
}

async function sendMetaLead(env, body, attr, server, leadId, leadSource) {
  const pixelId = env.META_PIXEL_ID || "1468998947504136";
  const { firstName, lastName } = splitFullName(body.fullName);
  const userData = {
    em: [await sha256(String(body.email || "").trim().toLowerCase())],
    ph: [await sha256(normalizePhone(body.phone))],
    fn: firstName ? [await sha256(firstName.trim().toLowerCase())] : undefined,
    ln: lastName ? [await sha256(lastName.trim().toLowerCase())] : undefined,
    country: server.country ? [await sha256(server.country.toLowerCase())] : undefined,
    ct: server.city ? [await sha256(server.city.toLowerCase().replace(/[^a-z]/g, ""))] : undefined,
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
      lead_source: leadSource || body.heardFrom || undefined,
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

function buildDescription(body, attr, server, meta = {}) {
  const utm = attr.utm || {};
  const fu = attr.first_utm || {};
  const first = attr.first_touch || {};
  const lines = [
    `Landing: ${meta.landing || "?"} | Service: ${meta.service || "?"} | lead.js ${LEAD_JS_VERSION}`,
    `Landing version: ${attr.landing_version || "?"}`,
    `Language: ${body.lang || "?"}`,
    `Hero headline: ${body.hero_variant || "default"}`,
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
    `Heard from (self-reported): ${body.heardFrom || "-"} -> Lead_Source ${meta.leadSource || "-"}`,
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
