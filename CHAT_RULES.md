# Unitty landings: one chat per landing + one shared chat

All chats live in the claude.ai project **Unitty Sales Funnel** (folder "Landing Pages").
Each chat starts by reading this file and `claude/landings-and-funnel-dashboards-handover.md`.

## Who may change what

| Chat | May change | Must ask first |
|---|---|---|
| **start.unitty.io** | `landings/start.json`, start-only insert files, `public/index.html` *only via the build* | anything else |
| **crm.unitty.io** | `landings/crm.*` (crm.json, crm.process.html, crm.packages.*, crm.extra.html), CRM cards in `landings/pains.html` (crm* cards only), `public/crm/` | anything else |
| **ai.unitty.io** | `landings/ai.json`, ai-only insert files, `public/ai/` | anything else |
| **banks.unitty.io** | `landings/banks.json`, banks-only insert files, `public/banks/` | anything else |
| **solutions.unitty.io** | `landings/solutions.json`, `landings/solutions.extra.html`, `public/solutions/` | anything else |
| **Shared (all landings)** | template `public/index.html` (header, footer, shared sections), `tools/*`, `public/tracking.js`, `functions/*`, `public/thank-you/`, shared pain cards, fonts/logos, translations workbook | — |

Rule: a request made in a landing chat changes **only that landing**. A change to a shared file happens only in the
shared chat, or after Giorgi explicitly says "all landings" in a landing chat.
Landing-only variants of a shared section go into the landing's own file via `"inserts"` or `"replace"` in its JSON
(example: CRM's own process section = `landings/crm.process.html`).

Note: `public/index.html` is both the template and the start landing. The start chat changes start through
`landings/start.json`; the template's shared parts belong to the shared chat.

## Build

- One landing: `python3 tools/build_landings.py --only crm` (CRM also: `python3 tools/build_crm_packages.py` first).
- All landings (shared chat only): `python3 tools/build_landings.py`.
- Translations workbook (shared chat, or a landing chat after a text change): `python3 tools/build_translations.py`.

## Versions

- Each landing has its own `"version"` in `landings/<name>.json` (e.g. `"v55-2026-10-29"`), written into
  `<meta name="unitty-version">` and sent to Zoho as `Landing_Version` = `crm-v55-2026-10-29`.
- A landing chat bumps only its own landing's version. `BUILD` in `public/tracking.js` is the shared fallback,
  bumped only by the shared chat.

## Session start / end (prevents chats overwriting each other)

1. Start: check the Mac clone is clean and pushed (GitHub Desktop shows no changes; HEAD = origin/main).
   If another chat left uncommitted work, stop and tell Giorgi.
2. Work only in your files, build only your landing, test mobile first (390px), then desktop.
3. End: write files to the Mac, verify sizes, ask Giorgi to Commit + Push in GitHub Desktop.
4. Only one chat writes to the Mac at a time. Switch chats after the previous Push.
