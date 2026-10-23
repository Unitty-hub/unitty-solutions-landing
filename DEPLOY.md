# Deploy Playbook — Unitty Solutions Landing

Step-by-step first-time deployment. Keep this open in a browser tab as you go.

---

## Phase 1 — GitHub (5 minutes)

1. Go to **https://github.com/signup**
2. Email: `digital@unitty.io` · strong password · verify email
3. Click avatar → **Your organizations** → **New organization** → **Free** plan
4. Organization name: `unitty-io` (or `unitty` if available)
5. Contact email: `digital@unitty.io`
6. Click **Create organization**

### Create the repo

1. On github.com → `+` → **New repository**
2. Owner: `unitty-io` · Name: `solutions-landing` · **Private**
3. Do NOT initialize with README (we have one)
4. **Create repository**
5. Copy the repo URL (e.g. `git@github.com:unitty-io/solutions-landing.git`)

### Push the code

```bash
cd /path/to/local/copy
git init -b main
git remote add origin git@github.com:unitty-io/solutions-landing.git
git add .
git commit -m "Initial commit: landing V22 + Cloudflare Pages setup"
git push -u origin main
```

(You can also upload via the GitHub web UI if git CLI is not set up.)

---

## Phase 2 — Cloudflare (5 minutes)

1. Go to **https://dash.cloudflare.com/sign-up**
2. Email: `digital@unitty.io` · verify
3. Dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
4. Authorize GitHub for `unitty-io/solutions-landing`
5. Project name: `unitty-solutions-landing`
6. Production branch: `main`
7. Build settings:
   - Framework preset: **None**
   - Build command: *(leave empty)*
   - Build output directory: `public`
8. Click **Save and Deploy**
9. First build runs → `unitty-solutions-landing.pages.dev` live in ~60 seconds

---

## Phase 3 — Zoho CRM API (10 minutes)

### A. Register a Zoho API client

1. **https://api-console.zoho.com** → login as digital@unitty.io
2. **Add Client** → Server-based Applications
3. Client Name: `Unitty Solutions Landing`
4. Homepage URL: `https://solutions.unitty.io`
5. Authorized Redirect URIs: `https://solutions.unitty.io/api/zoho/callback`
6. **Create** → copy **Client ID** and **Client Secret**

### B. Generate a refresh token (one-time)

In a browser (replace `CLIENT_ID`):

```
https://accounts.zoho.com/oauth/v2/auth?scope=ZohoCRM.modules.leads.CREATE&client_id=CLIENT_ID&response_type=code&access_type=offline&redirect_uri=https://solutions.unitty.io/api/zoho/callback
```

Approve → you'll be redirected with `?code=XXX` in the URL. Copy `XXX`.

```bash
curl -X POST https://accounts.zoho.com/oauth/v2/token \
  -d code=XXX \
  -d client_id=CLIENT_ID \
  -d client_secret=CLIENT_SECRET \
  -d redirect_uri=https://solutions.unitty.io/api/zoho/callback \
  -d grant_type=authorization_code
```

Response has `refresh_token`. **Save it, it never expires.**

### C. Create Zoho CRM custom fields on the Leads module

Zoho CRM → Setup → Customization → Modules → **Leads** → **Fields** → add these (all **Single Line** unless noted):

| Field label | API name | Type | Required | Notes |
|---|---|---|---|---|
| Landing Version | `Landing_Version` | Single Line | No | e.g. "v22-2026-10-23" |
| Lang | `Lang` | Picklist | No | Options: en, ka, ru |
| Selected Solutions | `Selected_Solutions` | Multi Line | No | Pipe-separated solution names |
| UTM Source | `UTM_Source` | Single Line | No | last-touch |
| UTM Medium | `UTM_Medium` | Single Line | No | |
| UTM Campaign | `UTM_Campaign` | Single Line | No | |
| UTM Content | `UTM_Content` | Single Line | No | |
| UTM Term | `UTM_Term` | Single Line | No | |
| First UTM Source | `First_UTM_Source` | Single Line | No | first-touch |
| First UTM Campaign | `First_UTM_Campaign` | Single Line | No | |
| First Referrer | `First_Referrer` | Single Line | No | |
| First Touch Date | `First_Touch_Date` | DateTime | No | |
| Heard From | `Heard_From` | Single Line | No | Lead self-reported |
| Submission URL | `Submission_URL` | URL | No | |

### D. Add Cloudflare Pages env vars

Cloudflare dashboard → Pages → `unitty-solutions-landing` → Settings → Environment Variables:

| Variable | Value |
|---|---|
| `ZOHO_CLIENT_ID` | from step A |
| `ZOHO_CLIENT_SECRET` | from step A |
| `ZOHO_REFRESH_TOKEN` | from step B |
| `ZOHO_API_DOMAIN` | `https://www.zohoapis.com` (or EU: `.zohoapis.eu`) |
| `ZOHO_ACCOUNTS_DOMAIN` | `https://accounts.zoho.com` (or `.eu`) |

Mark the secrets as **Encrypted**. Redeploy once env vars are saved.

---

## Phase 4 — Custom domain (5 minutes)

### A. In Cloudflare Pages

1. Pages project → **Custom domains** → **Set up a custom domain**
2. Enter: `solutions.unitty.io` → **Continue**
3. Cloudflare gives you a CNAME target like `unitty-solutions-landing.pages.dev`

### B. In GoDaddy DNS

1. GoDaddy → `unitty.io` → DNS → **Add record**
2. Type: **CNAME** · Name: `solutions` · Value: `unitty-solutions-landing.pages.dev` · TTL: 1 hour
3. Save

Propagation 2-30 minutes. Cloudflare auto-issues SSL cert.

---

## Phase 5 — Clarity (3 minutes)

Already have Clarity account. Add the tracking script to the top of `public/index.html` and `public/thank-you/index.html`:

```html
<script>
  (function(c,l,a,r,i,t,y){
    c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
    t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
    y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
  })(window, document, "clarity", "script", "YOUR_CLARITY_PROJECT_ID");
</script>
```

Replace `YOUR_CLARITY_PROJECT_ID` with your actual Clarity project ID (Clarity dashboard → Settings → Setup).

Our landing already calls `window.clarity('set', 'landing_version', LANDING_VERSION)` after the snippet loads, so sessions are automatically tagged.

---

## Phase 6 — Zoho Analytics dashboard (30-60 minutes)

1. Zoho Analytics → **Connect** → Zoho CRM
2. Import the **Leads** and **Deals** modules
3. New Workspace: `Unitty Solutions Funnel`
4. Build the chart: **Horizontal Funnel** → Steps:
   - **Leads** (count by Lead Source + Landing Version)
   - **Qualified** (Lead Status = Qualified)
   - **Deal Created**
   - **Negotiating / Paying**
   - **Closed Won**
5. Filters: Date range, Lead Source, Landing Version, UTM Campaign
6. Share dashboard URL with team

---

## Smoke test (after everything is live)

1. Visit `https://solutions.unitty.io?utm_source=test&utm_campaign=smoketest` on your phone
2. Fill the form with your real email, submit
3. Within 30 seconds, a Lead should appear in Zoho CRM Leads
4. Verify fields: Landing_Version, UTM_Source, UTM_Campaign, First_Touch_Date all populated
5. Verify Clarity session: Settings → Project → see "landing_version" tag on the session

If anything fails: Cloudflare Pages → Deployments → latest → Function logs will show the error.
