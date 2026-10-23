# start.unitty.io — what still needs connecting
### 2026-10-23

---

# 0 · Already working — don't rebuild these

```
page live          https://unitty-solutions-landing.pages.dev/   149 KB, 200
_headers applied   HSTS + X-Frame-Options confirmed on the live response
_redirects applied Cloudflare Pages, so /thank-you /book /pricing work
/api/lead running  returns 400 "Missing required field", not 404
```

**UTM tracking is already built into the page.** It captures first-touch *and* last-touch
(`utm_source/medium/campaign/content/term`), the first referrer, the first landing URL and the
first-touch date, and persists them in `localStorage` so they survive across visits. Nothing to add.

**Clarity custom tags are already written** — the page calls `window.clarity('set', 'first_referrer', …)`
and similar in 21 places. They are no-ops today only because the Clarity loader script is missing.

**Everything is already dumped into the Lead's Description** by `buildDescription()` — landing
version, language, both UTM sets, referrer, first-touch date, selected solutions, user agent.

---

# 1 · 🔴 Zoho — CORRECTED. Which org, and which fields.

## The destination is the **Unitty** CRM

Leads from this page go to the **Unitty** Zoho org, not the Gegidze/info one. `DEPLOY.md`'s
instruction to register the API client as `digital@unitty.io` is right for that — just make sure the
console session really is the Unitty org when you create the client, because the refresh token is
bound to whichever org you authorise.

## ⚠️ My earlier field mapping was from the WRONG org — disregard it

I quoted `UTM_Source` / `LEADCF21`, `UTM_Medium` / `LEADCF20`, `Where_did_you_hear_about_us_dropdown`
and so on. **Those are Gegidze CRM fields**, built for the three Wix forms. They tell us nothing
about what exists on Unitty.

What our own notes actually say about Unitty:

```
2026-08-19  "Still parked: UTM attribution (separate job)" - the Webflow forms do NOT
            yet carry UTM data into Zoho. Only the form_submission EVENT was fixed.
2026-08-31  Footer code added the browser-side attribution script - it stores
            unitty_attr_last / unitty_attr_first in localStorage and knows the names
            utm_source utm_medium utm_campaign utm_term utm_content page_url
            first_touch language_version
2026-09-23  Bookings plan: "port the Gegidze Deluge function" for Lead Source
            -> implying Unitty did NOT have that function
2026-09-23  "my CRM connector lost API access" - still true today, getFields returns
            NO_PERMISSION, so I cannot read the Unitty Leads module myself
```

🔴 **So it is likely the Unitty CRM has no UTM fields at all yet.** I cannot confirm it from
here. You need to look.

## What to check (Unitty CRM → Setup → Modules → Leads → Fields)

```
is there any field holding utm_source / utm_medium / utm_campaign / utm_content / utm_term?
is there a "where did you hear about us" field?
is there a Lead Source assignment function or workflow?
```

Send me the API names of whatever exists and I will map `lead.js` onto them exactly.

## 🟢 If they do NOT exist — the opportunity

Create them **once, named to serve both sources**, so unitty.io's Webflow forms and
start.unitty.io write to the same fields. The browser-side script on unitty.io already uses these
names, so matching them means the Webflow side can be wired up later with no rework:

| Suggested label | API name | Type | Fed by |
|---|---|---|---|
| UTM Source | `UTM_Source` | Single Line | both |
| UTM Medium | `UTM_Medium` | Single Line | both |
| UTM Campaign | `UTM_Campaign` | Single Line | both |
| UTM Content | `UTM_Content` | Single Line | both |
| UTM Term | `UTM_Term` | Single Line | both |
| First Touch | `First_Touch` | DateTime | both |
| Page URL | `Page_URL` | URL | both |
| Language Version | `Language_Version` | Picklist | Webflow today, landing later |

🟡 Optional, landing-page specific and genuinely useful for reporting:
`Selected_Solutions` (Multi Line) and `Landing_Version` (Single Line).

⚠️ Everything else `lead.js` sends (first-touch UTMs, referrer, submission URL, user agent) is
already written into **Description** by `buildDescription()`. Leave it there unless you want to
filter on it.

🟢 **Doing this now is cheaper than doing it twice.** The Unitty UTM job has been parked since
August. This landing page forces the decision, and if the fields are created with these names the
parked Webflow job becomes "point the existing hidden inputs at them".

---

# 2 · 🔴 `lead.js` sets `Lead_Source` itself — decide who owns it

`lead.js` computes `Lead_Source` in `mapLeadSource()` and posts with
`trigger: ["approval","workflow","blueprint"]`, so **any workflow on the Unitty org also fires** on
these leads.

Two cases, and answer §7 question 2 to know which you are in:

## If Unitty HAS a Lead Source function/workflow

🟢 **Remove `Lead_Source` from the payload.** Let the CRM own it, exactly as it does for every
other lead. The UTMs are being sent, so the function has what it needs, and this page's leads get
classified the same way as all the others. Two writers on one field is how reporting quietly drifts.

## If Unitty does NOT have one (likely — our 2026-09-23 note says it would have to be ported)

🟡 Then `mapLeadSource()` is the only thing setting it, and it has to match **Unitty's** Lead
Source picklist — which I do not know.

🔴 **Check Unitty's Lead Source options before the first real submission.** `mapLeadSource()`
can return `Youtube`, `TikTok`, `crm.ge`, `unitty.io` and `Meta`. If any of those are not options on
the Unitty picklist, Zoho rejects the value or blanks the field, and the lead still saves — so it
fails silently and you only notice it in reporting weeks later.

Send me the picklist and I will rewrite the mapping to match it.

⚠️ The values I quoted earlier — Meta, AI, Direct, SEO, Linkedin, Recommendation … — are the
**Gegidze** picklist. Same mistake as the fields. Do not assume Unitty matches.

---

# 3 · Clarity — one script tag

The tagging code is already on the page. It needs the loader:

```
Clarity → Settings → Setup → copy the tracking code → paste into <head> of public/index.html
```

⚠️ The **tracking ID** is a short string (like `abc123xyz`). It is **not** the Data Export JWT your
coworker sent — that one is for the API/MCP connector and does nothing on a web page.

🟡 Use the **same Clarity project as unitty.io** if you want this landing page's sessions in the
same dashboard as the main site. A separate project if you want them reported apart. Your call —
the script is identical either way, only the ID differs.

---

# 4 · Domain — `start.unitty.io`, nothing else touched

```
Cloudflare → Pages → unitty-solutions-landing → Custom domains → Set up a custom domain
  enter:  start.unitty.io
```

Cloudflare then gives you a CNAME target. Add **one record** at GoDaddy:

```
Type   CNAME
Name   start                                  ← just the label
Value  unitty-solutions-landing.pages.dev
TTL    1 hour
```

🟢 **Nothing about Webflow changes.** The root `unitty.io A 198.202.211.1` and
`www.unitty.io CNAME cdn.webflow.com` stay exactly as they are. Webflow only serves hostnames
registered inside Webflow, so `start.unitty.io` is invisible to it. You are adding a record, not
editing one.

🟢 unitty.io stays on GoDaddy DNS (`ns53/ns54.domaincontrol.com`). No nameserver change, no
transfer. Cloudflare Pages issues the SSL certificate itself once the CNAME resolves.

⚠️ `DEPLOY.md` says `solutions.unitty.io` throughout — that was the generated assumption. Use
`start.unitty.io` and ignore that name wherever it appears, **including the Zoho redirect URI in
Phase 3** (see §5).

---

# 5 · Zoho API credentials (the real remaining work)

The function needs five environment variables in Cloudflare Pages → Settings → Environment
Variables, marked **Encrypted**:

```
ZOHO_CLIENT_ID          from api-console.zoho.com
ZOHO_CLIENT_SECRET      from api-console.zoho.com
ZOHO_REFRESH_TOKEN      one-time OAuth exchange, never expires
ZOHO_API_DOMAIN         https://www.zohoapis.com     (or .eu — must match your org's DC)
ZOHO_ACCOUNTS_DOMAIN    https://accounts.zoho.com    (or .eu)
```

🔴 **Check your data centre first.** If the Unitty CRM is on `.eu`, both domains must be `.eu` or
every call fails with an invalid-token error that looks like a credentials problem.

🔴 When registering the client, the **Authorized Redirect URI must use `start.unitty.io`**, not
`solutions.unitty.io`. It only matters for the one-time token generation, but a mismatch there
blocks the whole OAuth step.

Scope needed: `ZohoCRM.modules.leads.CREATE`.

---

# 6 · Order

```
1  fix lead.js      remove Lead_Source, rename Heard_From, drop UTM_Term if absent
2  Clarity          one script tag, needs the tracking ID
3  Zoho OAuth       client + refresh token, redirect URI on start.unitty.io
4  Cloudflare env   five variables, encrypted, then redeploy
5  test submit      on the pages.dev URL, confirm the Lead lands with UTMs attached
6  domain           Pages custom domain + one CNAME at GoDaddy
```

🟡 Do the domain **last**. Test everything on `unitty-solutions-landing.pages.dev` first — a broken
form on a public branded URL is worse than a delayed launch.

---

# 7 · What I need from you

```
1  🔴 Unitty CRM → Setup → Modules → Leads → Fields
   which UTM / "heard about us" fields already exist? send me the API names.
   (I cannot read it - the MCP connector has had no CRM permission since 2026-09-23)

2  is there already a Lead Source assignment function/workflow on the UNITTY org,
   or is it still only on Gegidze?

3  Clarity tracking ID - and: same project as unitty.io, or separate?

4  is the Unitty CRM on .com or .eu?

5  decision: create the shared UTM fields now (§1) so unitty.io and start.unitty.io
   write to the same place - my recommendation - or landing-page-only fields?
```

Answers to 1 and 2 decide how much of `lead.js` changes. Everything else is independent.
