#!/usr/bin/env python3
"""Build the subdomain landings from the start landing.

public/index.html is the template (start.unitty.io). Every landings/<name>.json describes only
what differs for that landing: texts (KA/EN/RU) and optionally an extra HTML block. The script writes
public/<name>/index.html, so a design or tracking change made once on the start page reaches every
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

    # texts
    m = I18N_RE.search(s)
    assert m, "I18N dictionary not found"
    d = json.loads(m.group(1))
    for key, vals in cfg.get("i18n", {}).items():
        for lang in ("ka", "en", "ru"):
            d[lang][key] = vals[lang]
    s = s[:m.start(1)] + json.dumps(d, ensure_ascii=False) + s[m.end(1):]
    log(f"--- {len(cfg.get('i18n', {}))} text keys overridden")

    # optional extra block
    if cfg.get("insert_file"):
        extra = (LANDINGS / cfg["insert_file"]).read_text(encoding="utf-8")
        marker = cfg["insert_before"]
        assert s.count(marker) == 1, f"marker not found once: {marker}"
        s = s.replace(marker, extra + marker)
        log(f"--- inserted {cfg['insert_file']} ({len(extra)} chars)")

    out = ROOT / "public" / name / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(s, encoding="utf-8")
    log(f"<<< wrote {out.relative_to(ROOT)} ({len(s)} chars)")


def main():
    base = TEMPLATE.read_text(encoding="utf-8")
    for cfg_path in sorted(LANDINGS.glob("*.json")):
        build(json.loads(cfg_path.read_text(encoding="utf-8")), base)
    log("*** done")


if __name__ == "__main__":
    main()
