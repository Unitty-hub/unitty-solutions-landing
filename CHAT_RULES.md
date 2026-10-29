# Unitty landings: one chat per landing + one shared chat

Updated 2026-10-29 (after the v61-v63 round). The project file `Landing Pages/chat-rules.md` is a copy of this file.

All landing chats live in the project **Unitty Sales Funnel** (folder "Landing Pages").
Each chat starts by reading this file and `claude/landings-and-funnel-dashboards-handover.md`.

## Where the work happens (read first)

- **Files are written only from Claude Desktop (Cowork / Claude Code)**, which works directly in the Mac clone
  `~/Documents/GitHub/unitty-solutions-landing`. Giorgi pushes with GitHub Desktop.
- **claude.ai web chats have no access to the Mac.** Use them for planning, design review, copy and dashboards.
  If a claude.ai chat must change the repo, it commits through the browser on github.com, and every Mac chat
  must Fetch + Pull before its next write.
- Never ship changes as a ZIP to be unpacked over the repo, and never drag `public/` or `landings/` folders in
  Finder with "Replace" (that deleted 53 files on 2026-10-29). Write files individually.
- Never commit helper files such as `FILES-*.txt`.

## Who may change what

| Chat | May change | Must ask first |
|---|---|---|
| **start.unitty.io** | `landings/start.json`, start-only insert files, `public/index.html` *only via the build* | anything else |
| **crm.unitty.io** | `landings/crm.*` (crm.json, **crm.page.html**, crm.page.i18n.py, crm.process.html, crm.packages.*, crm.extra.html), CRM cards in `landings/pains.html` (crm* cards only), `public/crm/` | anything else |
| **ai.unitty.io** | `landings/ai.json`, ai-only insert files, `public/ai/` | anything else |
| **banks.unitty.io** | `landings/banks.json`, banks-only insert files, `public/banks/` | anything else |
| **solutions.unitty.io** | `landings/solutions.json`, `landings/solutions.extra.html`, `public/solutions/` | anything else |
| **Shared (all landings)** | template `public/index.html` (header, footer, shared sections), `public/unitty-v2.css`, `tools/*`, `public/tracking.js`, `functions/*`, `public/thank-you/`, shared pain cards, fonts/logos, this file | — |

Rule: a request made in a landing chat changes **only that landing**. A change to a shared file happens only in the
shared chat, or after Giorgi explicitly says "all landings" in a landing chat.
Landing-only variants of a shared section go into the landing's own file via `"inserts"` or `"replace"` in its JSON
(example: CRM's own process section = `landings/crm.process.html`).

Note: `public/index.html` is both the template and the start landing. The start chat changes start through
`landings/start.json`; the template's shared parts belong to the shared chat.

**CRM is a standalone designer page** (`landings/crm.page.html`, `"standalone"` in crm.json since crm-v63). It does not
use the template and does not load `public/unitty-v2.css`. A shared change (header, footer, style, CTA, tracking)
reaches CRM only if the CRM chat ports it, or the shared chat edits `crm.page.html` after Giorgi says "all landings".

## Design standard (since v61, Giorgi 2026-10-29)

- The designer system in `public/unitty-v2.css` is the standard for every landing, the thank-you page and any new design:
  navy background (#060616), surfaces #12121F/#1A1A29, hairlines rgba(255,255,255,.08), lime #C1FD3A, pill buttons,
  card radius 20px, JetBrains Mono (self-hosted) for labels/kickers/numbers, uppercase TBC Contractica headings, SVG logo,
  nav = logo + phone + "უფასო ზარი", CTA wording "მოითხოვე უფასო ზარი", designer font sizes (the old 14px floor is dropped),
  stats as a hairline band (not glass tiles).
- **Georgian only (v62):** no language switcher on any page; the pages force `ka` and clear the old `unitty-lang`
  value. EN/RU strings stay in the files, unused, in case languages come back. Georgian copy uses informal "შენ".
- Landing-only CSS uses the same tokens (`var(--surface)`, `var(--line)`, `var(--lime)`, `var(--r-card)`, `var(--font-mono)`)
  instead of new colours. Mobile first (390px), then desktop.
- When `unitty-v2.css` changes, bump its `?v=` in the template and the thank-you page.
- Changes to the shared style layer go through the shared chat; if a landing chat finds that the shared rules need a
  correction, it proposes it to Giorgi and, once he agrees, the change is made in `unitty-v2.css` for everyone.

## Thank-you page

- Zoho Bookings embed is Giorgi's snippet 1:1 (v63): `bookings.nimbuspop.com/assets/embed.js` +
  `Bookings.inlineEmbed` with `meet.unitty.io/portal-embed#/251936000000059094`, height 600px, no UTM parameters.
  Do not change it without asking (bookings currently carry no source/UTM).

## Build

- One landing: `python3 tools/build_landings.py --only crm` (template CRM parts also: `python3 tools/build_crm_packages.py` first).
- All landings (shared chat only): `python3 tools/build_landings.py`.
- The translations workbook (`tools/build_translations.py`) is not needed while the site is Georgian only.

## Versions

- Each landing has its own `"version"` in `landings/<name>.json` (e.g. `"v62-2026-10-29"`), written into
  `<meta name="unitty-version">` and sent to Zoho as `Landing_Version` = `crm-v74-2026-10-29`.
- A landing chat bumps only its own landing's version. `BUILD` in `public/tracking.js` is the shared fallback,
  bumped only by the shared chat.

## Session start / end (prevents chats overwriting each other)

1. Start: GitHub Desktop → **Fetch → Pull**. Then the clone must be clean and level with GitHub
   (`git status -sb` shows `## main...origin/main` with nothing else). If another chat left uncommitted work, stop and tell Giorgi.
2. Work only in your files, build only your landing, test mobile first (390px), then desktop.
3. End: write files to the Mac, verify sizes, ask Giorgi to Commit + Push in GitHub Desktop.
4. Only one chat writes at a time. Switch chats only after the previous Push.
