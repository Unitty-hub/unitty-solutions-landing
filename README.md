# Unitty Solutions Landing

Production landing + thank-you page hub for [unitty.io/solutions](https://solutions.unitty.io).

- **Hosting:** Cloudflare Pages (auto-deploy from `main`)
- **Form backend:** Cloudflare Pages Function (`/functions/api/lead.js`) → Zoho CRM Leads API
- **Analytics:** Microsoft Clarity + Cloudflare Web Analytics
- **Version tracking:** `LANDING_VERSION` constant inside `public/index.html`, bumped per deploy
- **Languages:** English, Georgian, Russian (i18n inline JS, viewer-switchable, localStorage-persisted)

## Repo structure

```
.
├── public/
│   ├── index.html              Landing page (main)
│   ├── thank-you/index.html    Post-form confirmation + resources
│   ├── fonts/                  Self-hosted brand fonts (LGV Big Noodle)
│   ├── assets/                 Images (logo, Giorgi photo, client photos)
│   ├── pdf/                    Static downloads (Solutions Catalog PDF)
│   ├── _headers                Cloudflare Pages response headers (CSP, caching)
│   └── _redirects              Cloudflare Pages redirects
└── functions/
    └── api/
        └── lead.js             POST handler → Zoho CRM Leads API
```

## Deployment

1. Push to `main` → Cloudflare Pages builds + deploys automatically (~60 seconds)
2. Preview URL for every PR (Cloudflare branch deploy)
3. Rollback: Cloudflare dashboard → Deployments → previous build → "Rollback"

## Bumping the landing version (for sequential A/B)

Before deploying a design change you want to measure separately:

1. Edit `public/index.html` → find `const LANDING_VERSION = "..."`;
2. Bump to new identifier, e.g. `v23-2026-10-30`
3. Commit, push → auto-deploy
4. Every lead captured after deploy is tagged with the new version
5. Compare versions in **Zoho Analytics** (group by `Landing_Version`) and **Clarity** (custom tag `landing_version`)

## Environment variables (Cloudflare Pages → Settings → Env)

| Name | Value | Required |
|---|---|---|
| `ZOHO_CLIENT_ID` | from Zoho API Console | yes |
| `ZOHO_CLIENT_SECRET` | from Zoho API Console | yes |
| `ZOHO_REFRESH_TOKEN` | one-time generated | yes |
| `ZOHO_API_DOMAIN` | e.g. `https://www.zohoapis.com` | yes |

See `/functions/api/lead.js` for the exact token refresh flow.

## Local development

```
# Install Wrangler (Cloudflare CLI)
npm i -g wrangler

# Serve locally (functions + static)
wrangler pages dev public --compatibility-date=2024-01-01

# Deploy manually (not needed if GitHub auto-deploy is on)
wrangler pages deploy public
```

## Contact

- Owner: Giorgi Kordzakhia (digital@unitty.io)
- Phone: +995 32 2 05 50 60
