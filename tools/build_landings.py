#!/usr/bin/env python3
"""Build the subdomain landings from the start landing.

public/index.html is the template (start.unitty.io). Every landings/<name>.json describes only
what differs for that landing: texts (KA/EN/RU), its "Sound familiar?" pain cards (landings/pains.html)
and optionally an extra HTML block. The script writes public/<name>/index.html (start.json writes
public/index.html itself), so a design or tracking change made once on the start page reaches every
landing by re-running:

    python3 tools/build_landings.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "public" / "index.html"
LANDINGS = ROOT / "landings"
I18N_RE = re.compile(r"const I18N = (\{.*?\});\n")
PAINS_RE = re.compile(r"<!--PAINS-->.*?<!--/PAINS-->\n?", re.S)
PAINS_BEFORE = "<!-- ============ CHAOS vs CLARITY ============ -->"
CARD_RE = re.compile(r"<!--card:([\w-]+)-->\n(.*?)<!--/card-->", re.S)


def log(msg):
    print(msg, flush=True)


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
        assert s.count(PAINS_BEFORE) == 1, "CHAOS vs CLARITY marker missing"
        s = s.replace(PAINS_BEFORE, "<!--PAINS-->\n" + section + "<!--/PAINS-->\n" + PAINS_BEFORE)
        log(f"--- pain cards: {', '.join(pains)}")

    # optional extra block (after the pain cards, so a block placed before CHAOS vs CLARITY follows them)
    if cfg.get("insert_file"):
        extra = (LANDINGS / cfg["insert_file"]).read_text(encoding="utf-8")
        marker = cfg["insert_before"]
        assert s.count(marker) == 1, f"marker not found once: {marker}"
        s = s.replace(marker, extra + marker)
        log(f"--- inserted {cfg['insert_file']} ({len(extra)} chars)")

    out = ROOT / cfg.get("output", f"public/{name}/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(s, encoding="utf-8")
    log(f"<<< wrote {out.relative_to(ROOT)} ({len(s)} chars)")


def main():
    # the start page is the template; its own pain block is removed first and re-added from start.json
    base = PAINS_RE.sub("", TEMPLATE.read_text(encoding="utf-8"))
    for cfg_path in sorted(p for p in LANDINGS.glob("*.json") if not p.name.endswith(".i18n.json")):
        build(json.loads(cfg_path.read_text(encoding="utf-8")), base)
    log("*** done")


if __name__ == "__main__":
    main()
