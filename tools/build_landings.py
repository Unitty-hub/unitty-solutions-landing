#!/usr/bin/env python3
"""Build the subdomain landings from the start landing.

public/index.html is the template (start.unitty.io). Every landings/<name>.json describes only
what differs for that landing: texts (KA/EN/RU), its "Sound familiar?" pain cards (landings/pains.html)
and optionally an extra HTML block. The script writes public/<name>/index.html (start.json writes
public/index.html itself), so a design or tracking change made once on the start page reaches every
landing by re-running:

    python3 tools/build_landings.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "public" / "index.html"
LANDINGS = ROOT / "landings"
I18N_RE = re.compile(r"const I18N = (\{.*?\});\n")
PAINS_RE = re.compile(r"<!--PAINS-->.*?<!--/PAINS-->\n?", re.S)
PAINS_BEFORE = "<!-- ============ PROCESS (3 steps) ============ -->"
CARD_RE = re.compile(r"<!--card:([\w-]+)-->\n(.*?)<!--/card-->", re.S)



BA_SWITCH = """    <div class="ba-bar">
      <div class="ba-switch" role="group" aria-label="Before / After">
        <button type="button" class="ba-btn" data-ba-go="before" aria-pressed="true"><i></i><span data-i18n="pain.ba.before">Before</span></button>
        <button type="button" class="ba-btn ba-to-after" data-ba-go="after" aria-pressed="false"><i></i><span data-i18n="pain.ba.after">After</span></button>
      </div>
    </div>
    <script>
    (function () {
      var sec = document.getElementById('pains'); if (!sec) return;
      var seen = false;
      function go(state) {
        sec.setAttribute('data-ba', state);
        sec.querySelectorAll('.ba-btn').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-ba-go') === state ? 'true' : 'false'); });
        if (state === 'after' && !seen) { seen = true; try { window.clarity && window.clarity('event', 'pains_after'); } catch (e) {} }
      }
      sec.addEventListener('click', function (e) { var b = e.target.closest('[data-ba-go]'); if (b) go(b.getAttribute('data-ba-go')); });
    })();
    </script>
"""

def log(msg):
    print(msg, flush=True)


# ---------------- SEO (v40) ----------------
SEO_RE = re.compile(r"<!--SEO-->.*?<!--/SEO-->\n?", re.S)
ORG = {
    "@type": "Organization", "@id": "https://unitty.io/#org", "name": "Unitty", "legalName": "Unity LLC",
    "url": "https://unitty.io", "logo": "https://start.unitty.io/unitty-logo.png",
    "email": "digital@unitty.io", "telephone": "+995322055060",
    "address": {"@type": "PostalAddress", "addressLocality": "Tbilisi", "addressCountry": "GE"},
    "sameAs": ["https://www.unitty.io", "https://www.instagram.com/unitty.io/"],
}
TAG_RE = re.compile(r"<[^>]+>")


def prerender(s, ka):
    """Write the Georgian texts into the HTML, so crawlers and link previews see real content without JS."""
    def txt(m):
        val = ka.get(m.group(3))
        return m.group(0) if val is None else m.group(1) + html.escape(val, quote=False) + m.group(5)
    s, n1 = re.subn(r'(<(\w+)\b[^>]*\sdata-i18n="([^"]+)"[^>]*>)([^<]*)(</\2>)', txt, s)
    def rich(m):
        key = m.group(3)
        val = ka.get(key) if key != "hero.sub.html" else ka.get("hero.sub")
        return m.group(0) if val is None else m.group(1) + val + m.group(5)
    s, n2 = re.subn(r'(<(\w+)\b[^>]*\sdata-i18n-html="([^"]+)"[^>]*>)(.*?)(</\2>)', rich, s, flags=re.S)
    log(f"--- prerendered {n1} text + {n2} html elements in Georgian")
    return s


def seo_block(cfg, ka):
    seo = cfg["seo"]
    url = f"https://{seo['host']}/"
    title, desc = seo["title"]["ka"], seo["description"]["ka"]
    og_img = f"https://{seo['host']}/og/{cfg['name']}.jpg"
    faq = []
    for i in range(1, 21):
        q, a = ka.get(f"faq.q{i}"), ka.get(f"faq.a{i}")
        if q and a:
            faq.append({"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": TAG_RE.sub("", a)}})
    graph = [ORG,
             {"@type": "WebSite", "@id": "https://unitty.io/#website", "url": "https://unitty.io", "name": "Unitty",
              "inLanguage": ["ka", "en", "ru"], "publisher": {"@id": "https://unitty.io/#org"}},
             {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": title, "description": desc,
              "inLanguage": "ka", "isPartOf": {"@id": "https://unitty.io/#website"},
              "about": {"@id": url + "#service"}, "primaryImageOfPage": og_img},
             {"@type": "Service", "@id": url + "#service", "name": seo["service"], "serviceType": seo["service"],
              "provider": {"@id": "https://unitty.io/#org"}, "areaServed": {"@type": "Country", "name": "Georgia"},
              "url": url}]
    if cfg.get("offers"):
        graph[-1]["offers"] = cfg["offers"]
    if faq:
        graph.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": faq})
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")
    e = lambda v: html.escape(v, quote=True)
    return (f'''<!--SEO-->
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#0A0A0A">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Unitty">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="ka_GE">
<meta property="og:locale:alternate" content="en_US">
<meta property="og:locale:alternate" content="ru_RU">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{og_img}">
<script type="application/ld+json">{ld}</script>
<!--/SEO-->
'''), len(faq)


def apply_seo(s, cfg, ka):
    if not cfg.get("seo"):
        return s
    s = SEO_RE.sub("", s)
    s, n = re.subn(r"<title[^>]*>.*?</title>", '<title data-i18n="seo.title">' + html.escape(cfg["seo"]["title"]["ka"], quote=False) + "</title>", s, count=1, flags=re.S)
    assert n == 1, "title tag missing"
    block, nfaq = seo_block(cfg, ka)
    anchor = '<meta name="viewport"'
    assert s.count(anchor) == 1, "viewport meta missing"
    s = s.replace(anchor, block + anchor)
    log(f"--- SEO: title, canonical {cfg['seo']['host']}, OG, JSON-LD (FAQ {nfaq})")
    return prerender(s, ka)


def build(cfg, base):
    name = cfg["name"]
    s = base
    log(f">>> building {name}")

    # landing identity (tracking.js reads it -> Landing_Version "crm-v27-...")
    s, n = re.subn(r'<meta name="unitty-landing" content="[^"]*">', f'<meta name="unitty-landing" content="{name}">', s, count=1)
    assert n == 1, "unitty-landing meta missing in template"

    if cfg.get("description"):
        s, n = re.subn(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % cfg["description"].replace('"', "&quot;"), s, count=1)
        assert n == 1, "description meta missing"

    # texts: shared keys (pain cards, hero variants) first, then this landing's own overrides
    m = I18N_RE.search(s)
    assert m, "I18N dictionary not found"
    d = json.loads(m.group(1))
    shared = json.loads((LANDINGS / "pains.i18n.json").read_text(encoding="utf-8"))
    for key, vals in list(shared.items()) + list(cfg.get("i18n", {}).items()):
        for lang in ("ka", "en", "ru"):
            d[lang][key] = vals[lang]
    s = s[:m.start(1)] + json.dumps(d, ensure_ascii=False) + s[m.end(1):]
    log(f"--- {len(cfg.get('i18n', {}))} text keys overridden")

    # "Sound familiar?" pain cards (landings/pains.html), only the ones this landing lists
    pains = cfg.get("pains") or []
    if pains:
        src = (LANDINGS / "pains.html").read_text(encoding="utf-8")
        cards = dict(CARD_RE.findall(src))
        section = CARD_RE.sub("", src).rstrip() + "\n"
        missing = [p for p in pains if p not in cards]
        assert not missing, f"unknown pain cards: {missing}"
        section = section.replace("{{COUNT}}", str(len(pains))).replace("{{CARDS}}", "".join(cards[p] for p in pains).rstrip())
        # optional Before / After switch ("pains_ba": true): one toggle for all cards, CRM mock-ups on the "after" side
        if cfg.get("pains_ba"):
            section = section.replace("{{BA_CLASS}}", " has-ba").replace("{{BA_ATTR}}", ' data-ba="before"').replace("{{BA_SWITCH}}", BA_SWITCH)
        else:
            section = section.replace("{{BA_CLASS}}", "").replace("{{BA_ATTR}}", "").replace("{{BA_SWITCH}}", "")
        assert s.count(PAINS_BEFORE) == 1, "PROCESS marker missing"
        s = s.replace(PAINS_BEFORE, "<!--PAINS-->\n" + section + "<!--/PAINS-->\n" + PAINS_BEFORE)
        log(f"--- pain cards: {', '.join(pains)}")

    # optional extra blocks (after the pain cards, so a block placed before CHAOS vs CLARITY follows them).
    # "inserts": [{"file": ..., "before": ...}] or the older single "insert_file" + "insert_before".
    inserts = list(cfg.get("inserts", []))
    if cfg.get("insert_file"):
        inserts.append({"file": cfg["insert_file"], "before": cfg["insert_before"]})
    for ins in inserts:
        extra = (LANDINGS / ins["file"]).read_text(encoding="utf-8")
        marker = ins["before"]
        assert s.count(marker) == 1, f"marker not found once: {marker}"
        s = s.replace(marker, extra + marker)
        log(f"--- inserted {ins['file']} ({len(extra)} chars)")

    # per-landing hero video (YouTube Short id) and its poster image
    hv = cfg.get("hero_video")
    if hv:
        s, n1 = re.subn(r'(class="giorgi-card yt-card" data-yt-id=")[^"]+(")', r"\g<1>" + hv["id"] + r"\g<2>", s, count=1)
        s, n2 = re.subn(r'(<img class="yt-poster-img" src=")[^"]+(")', r"\g<1>" + hv["poster"] + r"\g<2>", s, count=1)
        assert n1 == 1 and n2 == 1, "hero video markup not found"
        if hv.get("position"):
            s = s.replace('<img class="yt-poster-img" src="' + hv["poster"] + '"', '<img class="yt-poster-img" style="object-position:' + hv["position"] + '" src="' + hv["poster"] + '"', 1)
        if hv.get("brightness"):
            # the YouTube file itself can't be edited, so the video and its poster are dimmed with a CSS filter
            css = f'<style>.giorgi-card .yt-frame iframe, .giorgi-card .yt-poster-img {{ filter: brightness({hv["brightness"]}); }}</style>\n'
            assert s.count("</head>") == 1, "head end missing"
            s = s.replace("</head>", css + "</head>")
        log(f"--- hero video {hv['id']} + poster {hv['poster']}")

    final = json.loads(I18N_RE.search(s).group(1))["ka"]
    s = apply_seo(s, cfg, final)

    out = ROOT / cfg.get("output", f"public/{name}/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(s, encoding="utf-8")
    log(f"<<< wrote {out.relative_to(ROOT)} ({len(s)} chars)")


def main():
    # the start page is the template; its own pain block is removed first and re-added from start.json
    base = PAINS_RE.sub("", TEMPLATE.read_text(encoding="utf-8"))
    for cfg_path in sorted(p for p in LANDINGS.glob("*.json") if not p.name.endswith((".i18n.json", ".data.json"))):
        build(json.loads(cfg_path.read_text(encoding="utf-8")), base)
    log("*** done")


if __name__ == "__main__":
    main()
