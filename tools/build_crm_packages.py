#!/usr/bin/env python3
"""Build the CRM packages + add-ons section (crm.unitty.io only).

Source of truth: landings/crm.packages.data.json (prices in EUR, days, KA/EN/RU texts, taken from
"Unitty Offer Template v3" on Drive). This script writes:
  - landings/crm.packages.html   static, crawlable markup with data-i18n keys + the interactive script
  - the "pk.*" / "ao.*" / "sum.*" text keys into landings/crm.json -> i18n
Run it before tools/build_landings.py whenever the packages data changes.

v37 design (simplified on request): mobile first; one package visible at a time on phones (tabs),
three columns on desktop; each card = who it is for, price, 3 highlights, one button, full list folded
away; add-ons folded into one "Extra features" panel (7 popular first, the rest by category, each
category folded); EUR/GEL switch (GEL = EUR x 3); a small live total bar.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "landings" / "crm.packages.data.json"
OUT = ROOT / "landings" / "crm.packages.html"
CFG = ROOT / "landings" / "crm.json"
GEL_RATE = 3   # GEL price = EUR price x 3 (set by Giorgi, 2026-10-28)


def log(msg):
    print(msg, flush=True)


def T(ka, en, ru):
    return {"ka": ka, "en": en, "ru": ru}


UI = {
    "pk.title": T("აირჩიე, საიდან დაიწყო", "Choose where to start", "Выберите, с чего начать"),
    "pk.sub": T("ფიქსირებული ფასი და მკაფიო ვადები. დაიწყე მცირე პაკეტით, დანარჩენს მოგვიანებით დაამატებ.",
                "Fixed price, fixed timeline. Start small and add the rest later.",
                "Фиксированная цена и срок. Начните с малого, остальное добавите потом."),
    "pk.popular": T("ყველაზე ხშირად ირჩევენ", "Most popular", "Выбирают чаще всего"),
    "pk.deal": T("ფასდაკლება მოქმედებს ოფერის გაგზავნიდან 1 კვირის განმავლობაში.",
                  "Discount valid for 1 week from the day the offer is sent.",
                  "Скидка действует 1 неделю с момента отправки предложения."),
    "pk.once": T("ერთჯერადად", "one-time", "разово"),
    "pk.days": T("სამუშაო დღე", "working days", "рабочих дней"),
    "pk.full": T("სრული ჩამონათვალი", "Everything included", "Всё, что входит"),
    "pk.choose": T("ამ პაკეტის არჩევა", "Choose this package", "Выбрать этот пакет"),
    "pk.chosen": T("არჩეულია", "Selected", "Выбран"),
    "pk.note": T("ფასს ემატება დღგ (18%). CRM-ის ლიცენზიას ცალკე, პირდაპირ მწარმოებელს უხდი.",
                 "VAT (18%) is added. The CRM licence is paid separately, directly to the vendor.",
                 "Добавляется НДС (18%). Лицензия CRM оплачивается отдельно, напрямую производителю."),
    "pk.cur": T("ვალუტა", "Currency", "Валюта"),
    "ao.title": T("დამატებითი ფუნქციები", "Extra features", "Дополнительные функции"),
    "ao.sub": T("არასავალდებულოა. დაამატე მხოლოდ საჭიროებისამებრ", "Optional. Add only if you need them", "Необязательно. Добавьте, если нужно"),
    "ao.popular": T("ხშირად ამატებენ", "Often added", "Часто добавляют"),
    "ao.more": T("ყველა დამატებითი ფუნქცია კატეგორიების მიხედვით", "All add-ons by category", "Все дополнения по категориям"),
    "ao.catalog": T("სრულ კატალოგს (75+ გადაწყვეტა) ზარზე გაჩვენებთ.", "We show the full catalog (75+ solutions) on the call.", "Полный каталог (75+ решений) покажем на звонке."),
    "sum.empty": T("აირჩიე პაკეტი", "Choose a package", "Выберите пакет"),
    "sum.addons": T("ფუნქცია", "features", "функц."),
    "sum.vat": T("+ დღგ", "+ VAT", "+ НДС"),
    "sum.cta": T("მოითხოვე ზარი", "Request a call", "Запросить звонок"),
    "sum.picked": T("შენი არჩევანი:", "Your selection:", "Ваш выбор:"),
}


def esc(s):
    return html.escape(s, quote=True)


def price_span(eur, cls=""):
    """Price shown in EUR by default; the script swaps it to GEL (x3) when the visitor switches."""
    c = f' class="{cls}"' if cls else ""
    return f'<span{c} data-eur="{eur}">€{eur:,}</span>'


def was_html(p):
    """Old price struck through + the discount chip, only for a package with "was" (e.g. Essentials 2499 -> 1999 = -20%)."""
    if not p.get("was"):
        return ""
    off = round((1 - p["price"] / p["was"]) * 100)
    return f'<span class="pk-was-row"><s class="pk-was" data-eur="{p["was"]}">€{p["was"]:,}</s><span class="pk-off">-{off}%</span></span>'


def deal_html(p):
    return '\n        <p class="pk-deal" data-i18n="pk.deal">Discount valid for 1 week from the day the offer is sent.</p>' if p.get("was") else ""


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    keys = dict(UI)
    log(f">>> {len(d['packages'])} packages, {len(d['addons'])} add-ons, GEL rate x{GEL_RATE}")

    # ---------- package cards ----------
    tabs, cards = [], []
    for p in d["packages"]:
        pid = p["id"]
        keys[f"pk.{pid}.name"] = p["name"]
        keys[f"pk.{pid}.short"] = p["short"]
        if "base" in p:
            keys[f"pk.{pid}.base"] = p["base"]
        keys[f"pk.{pid}.out"] = p["outcome"]
        hl = []
        for i, h in enumerate(p["highlights"], 1):
            keys[f"pk.{pid}.h{i}"] = h
            hl.append(f'<li data-i18n="pk.{pid}.h{i}">{esc(h["en"])}</li>')
        full = []
        if "base" in p:
            full.append(f'<li class="pk-base" data-i18n="pk.{pid}.base">{esc(p["base"]["en"])}</li>')
        full += hl
        for i, it in enumerate(p["items"], 1):
            keys[f"pk.{pid}.i{i}"] = it
            full.append(f'<li data-i18n="pk.{pid}.i{i}">{esc(it["en"])}</li>')
        pop = " is-popular" if p.get("popular") else ""
        badge = '<span class="pk-badge" data-i18n="pk.popular">Most popular</span>' if p.get("popular") else ""
        tabs.append(f'<button type="button" class="pk-tab" role="tab" data-pk="{pid}" aria-selected="false" aria-controls="pk-{pid}">'
                    f'<span data-i18n="pk.{pid}.name">{esc(p["name"]["en"])}</span>{price_span(p["price"], "pk-tab-price")}</button>')
        cards.append(f'''      <article class="pk-card{pop}" id="pk-{pid}" role="tabpanel" data-pk="{pid}" data-price="{p["price"]}"{(' data-was="%d"' % p["was"]) if p.get("was") else ""} data-days="{p["days"]}">
        {badge}
        <h3 class="pk-name" data-i18n="pk.{pid}.name">{esc(p["name"]["en"])}</h3>
        <p class="pk-for" data-i18n="pk.{pid}.short">{esc(p["short"]["en"])}</p>
        <p class="pk-price">{was_html(p)}{price_span(p["price"], "pk-amount")}<span class="pk-once" data-i18n="pk.once">one-time</span></p>{deal_html(p)}
        <p class="pk-time"><b>{p["days"]}</b> <span data-i18n="pk.days">working days</span></p>
        <p class="pk-out" data-i18n="pk.{pid}.out">{esc(p["outcome"]["en"])}</p>
        <button type="button" class="btn pk-choose" data-pk="{pid}" aria-pressed="false"><span class="pk-choose-off" data-i18n="pk.choose">Choose this package</span><span class="pk-choose-on" data-i18n="pk.chosen">Selected</span></button>
        <details class="pk-full">
          <summary data-i18n="pk.full">Everything included</summary>
          <ul>{"".join(full)}</ul>
        </details>
      </article>''')

    # ---------- add-ons: popular first, then each category folded ----------
    def row(n, a):
        cat, price, days, rec, ka, en, ru = a
        keys[f"ao.{n}"] = T(ka, en, ru)
        return (f'<li><label class="ao-row"><input type="checkbox" class="ao-cb" value="{n}" data-price="{price}" data-days="{days}" data-en="{esc(en)}">'
                f'<span class="ao-name" data-i18n="ao.{n}">{esc(en)}</span>{price_span(price, "ao-price")}<span class="ao-box" aria-hidden="true"></span></label></li>')

    popular = [row(n, a) for n, a in enumerate(d["addons"], 1) if a[3]]
    groups = []
    for c in d["categories"]:
        keys[f"ao.cat.{c['id']}"] = c["name"]
        rows = [row(n, a) for n, a in enumerate(d["addons"], 1) if a[0] == c["id"] and not a[3]]
        if not rows:
            continue
        groups.append(f'<details class="ao-cat"><summary><span data-i18n="ao.cat.{c["id"]}">{esc(c["name"]["en"])}</span> <small>{len(rows)}</small></summary><ul class="ao-list">{"".join(rows)}</ul></details>')

    names_en = {p["id"]: p["name"]["en"] for p in d["packages"]}

    section = f'''<!-- ============ CRM PACKAGES + ADD-ONS (crm.unitty.io only) ============ -->
<!-- Built by tools/build_crm_packages.py from landings/crm.packages.data.json (Unitty Offer Template v3).
     Mobile first: base CSS = phone; min-width queries add desktop. The choice goes into the lead's
     "selected solutions" (Zoho CRM lead description). GEL = EUR x {GEL_RATE}. -->
<style>
  .pk-top {{ display: flex; flex-direction: column; gap: 16px; }}
  .pk-cur {{ display: inline-flex; align-self: flex-start; padding: 4px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); }}
  .pk-cur button {{ appearance: none; border: 0; background: none; min-width: 64px; min-height: 40px; padding: 0 14px; border-radius: 999px;
    font: inherit; font-size: 14px; font-weight: 700; color: var(--fg-dim); cursor: pointer; }}
  .pk-cur button[aria-pressed="true"] {{ background: var(--fg); color: var(--bg); }}
  .pk-tabs {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding: 4px; margin-top: 20px;
    background: var(--surface); border: 1px solid var(--border); border-radius: 14px; }}
  .pk-tab {{ appearance: none; border: 0; background: transparent; color: var(--fg-dim); border-radius: 10px; min-height: 56px; padding: 6px 4px;
    font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; }}
  .pk-tab-price {{ font-size: 14px; font-weight: 500; color: var(--fg-mute); }}
  .pk-tab[aria-selected="true"] {{ background: var(--surface-2); color: var(--fg); box-shadow: inset 0 0 0 1px var(--border-2); }}
  .pk-tab[aria-selected="true"] .pk-tab-price {{ color: var(--accent); }}
  .pk-cards {{ margin-top: 12px; }}
  .pk-card {{ display: none; flex-direction: column; gap: 10px; padding: 24px 20px; border-radius: 20px; background: var(--surface); border: 1px solid var(--border); }}
  .pk-card.is-shown {{ display: flex; }}
  .pk-card.is-popular {{ border-color: color-mix(in srgb, var(--accent) 45%, transparent); }}
  .pk-card.is-chosen {{ border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }}
  .pk-badge {{ align-self: flex-start; font-size: 14px; line-height: 1; padding: 7px 10px; border-radius: 999px; color: var(--accent-ink); background: var(--accent); font-weight: 600; }}
  .pk-name {{ margin: 0; font-family: var(--font-head); font-weight: 900; font-size: 26px; line-height: 1.1; color: var(--fg); }}
  .pk-for {{ margin: 0; font-size: 15px; line-height: 1.45; color: var(--fg-dim); }}
  .pk-price {{ margin: 6px 0 0; display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 10px; }}
  .pk-amount {{ font-weight: 700; font-size: 42px; line-height: 1; letter-spacing: -0.02em; color: var(--fg); }}
  .pk-once {{ font-size: 14px; color: var(--fg-dim); }}
  .pk-was-row {{ flex-basis: 100%; display: flex; align-items: center; gap: 10px; }}
  .pk-was {{ font-size: 18px; color: var(--fg-mute); text-decoration-thickness: 2px; text-decoration-color: color-mix(in srgb, var(--fg) 55%, transparent); }}
  .pk-off {{ font-size: 14px; font-weight: 700; line-height: 1; padding: 5px 8px; border-radius: 6px; color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent); }}
  .pk-deal {{ margin: -2px 0 0; font-size: 14px; line-height: 1.45; color: var(--fg-dim); }}
  .pk-time {{ margin: 0; font-size: 15px; color: var(--fg-dim); }}
  .pk-out {{ margin: 4px 0 2px; font-size: 16px; line-height: 1.5; color: var(--fg); }}
  .pk-time b {{ color: var(--accent); }}
  .pk-hl {{ list-style: none; margin: 6px 0 4px; padding: 0; display: grid; gap: 10px; }}
  .pk-hl li, .pk-full li {{ position: relative; padding-left: 26px; font-size: 15px; line-height: 1.45; color: var(--fg); }}
  .pk-hl li::before, .pk-full li::before {{ content: ""; position: absolute; left: 2px; top: 5px; width: 12px; height: 7px;
    border-left: 2px solid var(--accent); border-bottom: 2px solid var(--accent); transform: rotate(-45deg); }}
  .pk-choose {{ width: 100%; justify-content: center; min-height: 52px; margin-top: 6px; background: var(--accent); color: var(--accent-ink); }}
  .pk-choose-on, .pk-choose[aria-pressed="true"] .pk-choose-off {{ display: none; }}
  .pk-choose[aria-pressed="true"] .pk-choose-on {{ display: inline; }}
  .pk-choose[aria-pressed="true"] {{ background: transparent; color: var(--accent); border-color: var(--accent); }}
  .pk-full summary {{ list-style: none; cursor: pointer; min-height: 44px; display: flex; align-items: center; justify-content: center; gap: 8px;
    font-size: 14px; font-weight: 600; color: var(--fg-dim); }}
  .pk-full summary::-webkit-details-marker {{ display: none; }}
  .pk-full summary::after {{ content: ""; width: 7px; height: 7px; border-right: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(45deg) translateY(-2px); transition: transform .2s ease; }}
  .pk-full[open] summary::after {{ transform: rotate(-135deg) translateY(-2px); }}
  .pk-full ul {{ list-style: none; margin: 4px 0 0; padding: 0; display: grid; gap: 10px; }}
  .pk-full li.pk-base {{ padding-left: 0; color: var(--fg-dim); font-weight: 600; }}
  .pk-full li.pk-base::before {{ display: none; }}
  .pk-note {{ margin: 18px auto 0; max-width: 640px; text-align: center; font-size: 14px; line-height: 1.5; color: var(--fg-dim); }}

  .ao {{ margin-top: 24px; border-radius: 20px; background: var(--surface); border: 1px solid var(--border); }}
  .ao > summary {{ list-style: none; cursor: pointer; display: grid; grid-template-columns: 1fr 32px; align-items: center; gap: 4px 12px; padding: 18px 20px; min-height: 64px; }}
  .ao > summary::-webkit-details-marker {{ display: none; }}
  .ao-title {{ font-weight: 700; font-size: 17px; color: var(--fg); }}
  .ao-sub {{ grid-column: 1; font-size: 14px; color: var(--fg-dim); }}
  .ao-plus {{ grid-column: 2; grid-row: 1 / span 2; width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; background: var(--surface-2); border: 1px solid var(--border-2); position: relative; }}
  .ao-plus::before, .ao-plus::after {{ content: ""; position: absolute; width: 12px; height: 2px; background: var(--fg); border-radius: 2px; transition: transform .2s ease; }}
  .ao-plus::after {{ transform: rotate(90deg); }}
  .ao[open] .ao-plus::after {{ transform: rotate(0deg); }}
  .ao-body {{ padding: 0 20px 18px; }}
  .ao-head {{ margin: 4px 0 4px; font-size: 14px; font-weight: 700; color: var(--fg-dim); }}
  .ao-list {{ list-style: none; margin: 0; padding: 0; }}
  .ao-row {{ display: grid; grid-template-columns: 1fr auto 26px; align-items: center; gap: 12px; min-height: 56px; padding: 10px 0; border-bottom: 1px solid var(--border); cursor: pointer; }}
  .ao-cb {{ position: absolute; opacity: 0; width: 1px; height: 1px; }}
  .ao-name {{ font-size: 15px; line-height: 1.4; color: var(--fg); }}
  .ao-price {{ font-size: 15px; font-weight: 700; color: var(--fg); white-space: nowrap; }}
  .ao-box {{ width: 26px; height: 26px; border-radius: 8px; border: 2px solid var(--border-2); position: relative; transition: background .15s ease, border-color .15s ease; }}
  .ao-cb:checked ~ .ao-box {{ background: var(--accent); border-color: var(--accent); }}
  .ao-cb:checked ~ .ao-box::after {{ content: ""; position: absolute; left: 7px; top: 3px; width: 7px; height: 12px; border-right: 2.5px solid var(--accent-ink); border-bottom: 2.5px solid var(--accent-ink); transform: rotate(45deg); }}
  .ao-cb:focus-visible ~ .ao-box {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  .ao-cb:checked ~ .ao-name {{ font-weight: 600; }}
  .ao-cat {{ border-bottom: 1px solid var(--border); }}
  .ao-cat summary {{ list-style: none; cursor: pointer; min-height: 52px; display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 15px; font-weight: 600; color: var(--fg); }}
  .ao-cat summary::-webkit-details-marker {{ display: none; }}
  .ao-cat summary small {{ margin-left: auto; font-size: 14px; font-weight: 500; color: var(--fg-mute); }}
  .ao-cat summary::after {{ content: ""; width: 7px; height: 7px; border-right: 2px solid var(--fg-dim); border-bottom: 2px solid var(--fg-dim); transform: rotate(45deg); transition: transform .2s ease; }}
  .ao-cat[open] summary::after {{ transform: rotate(-135deg); }}
  .ao-cat .ao-row:last-child {{ border-bottom: 0; }}
  .ao-more {{ margin: 20px 0 4px; font-size: 14px; font-weight: 700; color: var(--fg-dim); }}
  .ao-catalog {{ margin: 12px 0 0; font-size: 14px; color: var(--fg-dim); }}

  .pk {{ padding-bottom: 110px; }}
  .pk-bar {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: 60; transform: translateY(110%); transition: transform .25s ease;
    padding: 10px 16px calc(10px + env(safe-area-inset-bottom)); background: color-mix(in srgb, var(--bg) 90%, transparent);
    -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px); border-top: 1px solid var(--border-2); }}
  .pk-bar.is-visible {{ transform: none; }}
  .pk-bar-in {{ max-width: 1180px; margin: 0 auto; display: flex; align-items: center; gap: 12px; }}
  .pk-bar-sum {{ flex: 1; min-width: 0; }}
  .pk-bar-what {{ display: block; font-size: 14px; color: var(--fg-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .pk-bar-total {{ display: block; font-size: 20px; font-weight: 700; color: var(--fg); line-height: 1.25; }}
  .pk-bar-total small {{ font-size: 14px; font-weight: 500; color: var(--fg-dim); }}
  .pk-bar .btn {{ flex: none; min-height: 48px; padding: 12px 16px; }}
  .pk-picked {{ margin: 0 auto 20px; max-width: 640px; padding: 12px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5; color: var(--fg);
    background: color-mix(in srgb, var(--accent) 8%, var(--surface)); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); }}
  .pk-picked b {{ color: var(--accent); }}
  @media (prefers-reduced-motion: reduce) {{ .pk-bar {{ transition: none; }} }}

  @media (min-width: 980px) {{
    .pk-top {{ flex-direction: row; align-items: flex-end; justify-content: space-between; }}
    .pk-top .section-sub {{ margin-bottom: 0; }}
    .pk-cur {{ align-self: auto; flex: none; }}
    .pk-tabs {{ display: none; }}
    .pk-cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 32px; align-items: start; }}
    .pk-card {{ display: flex; padding: 28px 24px; }}
    .pk-card:not(.is-popular) .pk-choose:not([aria-pressed="true"]) {{ background: var(--surface-2); color: var(--fg); border-color: var(--border-2); }}
    .ao > summary {{ padding: 20px 28px; }}
    .ao-body {{ padding: 0 28px 24px; }}
    .ao-body > .ao-list, .ao-cats {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 40px; align-items: start; }}
  }}
</style>
<section class="section pk" id="packages">
  <div class="wrap">
    <div class="pk-top">
      <div>
        <h2 class="section-title" data-i18n="pk.title">Choose where to start</h2>
        <p class="section-sub" data-i18n="pk.sub"></p>
      </div>
      <div class="pk-cur" role="group" data-i18n-attr="aria-label:pk.cur" aria-label="Currency">
        <button type="button" data-cur="eur" aria-pressed="true">EUR €</button>
        <button type="button" data-cur="gel" aria-pressed="false">GEL ₾</button>
      </div>
    </div>
    <div class="pk-tabs" role="tablist">{"".join(tabs)}</div>
    <div class="pk-cards">
{chr(10).join(cards)}
    </div>
    <p class="pk-note" data-i18n="pk.note"></p>

  </div>
</section>
<script>
  // CRM packages: one package + optional add-ons, EUR/GEL switch, live total, sent with the lead.
  (function () {{
    var NAMES_EN = {json.dumps(names_en)};
    var GEL_RATE = {GEL_RATE};
    var sec = document.getElementById('packages');
    if (!sec) return;
    var chosen = null;
    var cur = 'eur';
    try {{ cur = localStorage.getItem('unitty-cur') === 'gel' ? 'gel' : 'eur'; }} catch (e) {{}}
    function log(m, x) {{ try {{ console.info('[packages] ' + m, x === undefined ? '' : x); }} catch (e) {{}} }}
    function tr(key, fb) {{ try {{ var v = (typeof t === 'function') ? t(key) : null; return (v && v !== key) ? v : fb; }} catch (e) {{ return fb; }} }}
    function money(eur) {{ return cur === 'gel' ? (eur * GEL_RATE).toLocaleString('en-US') + ' ₾' : '€' + eur.toLocaleString('en-US'); }}
    function track(name, data) {{ try {{ if (window.UnittyTracking) window.UnittyTracking.event(name, data); }} catch (e) {{}} }}
    var cards = [].slice.call(sec.querySelectorAll('.pk-card'));
    var tabs = [].slice.call(sec.querySelectorAll('.pk-tab'));

    // phones: one card at a time, switched by the tabs (desktop shows all three, tabs hidden)
    function show(id) {{
      tabs.forEach(function (b) {{ b.setAttribute('aria-selected', b.dataset.pk === id ? 'true' : 'false'); }});
      cards.forEach(function (c) {{ c.classList.toggle('is-shown', c.dataset.pk === id); }});
    }}
    tabs.forEach(function (b) {{ b.addEventListener('click', function () {{ show(b.dataset.pk); }}); }});
    var pop = sec.querySelector('.pk-card.is-popular');
    show(pop ? pop.dataset.pk : cards[0].dataset.pk);

    sec.querySelectorAll('.pk-choose').forEach(function (b) {{
      b.addEventListener('click', function () {{
        chosen = (chosen === b.dataset.pk) ? null : b.dataset.pk;
        log('>>> package', chosen);
        if (chosen) track('package_selected', {{ package: chosen }});
        render();
      }});
    }});
    sec.querySelectorAll('.pk-cur button').forEach(function (b) {{
      b.addEventListener('click', function () {{
        cur = b.dataset.cur;
        try {{ localStorage.setItem('unitty-cur', cur); }} catch (e) {{}}
        log('--- currency', cur);
        track('currency_switched', {{ currency: cur }});
        render();
      }});
    }});

    function whatText() {{ return chosen ? tr('pk.' + chosen + '.name', NAMES_EN[chosen]) : ''; }}
    function price() {{ var c = chosen && document.getElementById('pk-' + chosen); return c ? +c.dataset.price : 0; }}
    function syncLead() {{
      // the template's "selected solutions" set is sent to /api/lead and lands in the Zoho lead description
      try {{
        if (typeof state === 'undefined' || !state.selected) return;
        Array.from(state.selected).forEach(function (k) {{ if (/^(Package|Add-on): /.test(k)) state.selected.delete(k); }});
        if (chosen) {{ var cc = document.getElementById('pk-' + chosen); state.selected.add('Package: ' + NAMES_EN[chosen] + ' (€' + cc.dataset.price + (cc.dataset.was ? ', -20% from €' + cc.dataset.was + ', valid 1 week from offer' : '') + ')'); }}
      }} catch (e) {{ log('*** lead sync failed', e.message); }}
    }}
    function render() {{
      sec.querySelectorAll('[data-eur]').forEach(function (el) {{ el.textContent = money(+el.dataset.eur); }});
      sec.querySelectorAll('.pk-cur button').forEach(function (b) {{ b.setAttribute('aria-pressed', b.dataset.cur === cur ? 'true' : 'false'); }});
      cards.forEach(function (c) {{
        var on = c.dataset.pk === chosen;
        c.classList.toggle('is-chosen', on);
        c.querySelector('.pk-choose').setAttribute('aria-pressed', on ? 'true' : 'false');
      }});
      var any = !!chosen;
      syncLead();
      var fin = document.getElementById('final'), box = document.getElementById('pkPicked');
      if (fin && any) {{
        if (!box) {{ box = document.createElement('p'); box.id = 'pkPicked'; box.className = 'pk-picked'; var form = fin.querySelector('form'); (form || fin).parentNode.insertBefore(box, form || fin.firstChild); }}
        box.innerHTML = tr('sum.picked', 'Your selection:') + ' <b>' + whatText() + '</b> · ' + money(price()) + ' ' + tr('sum.vat', '+ VAT');
      }} else if (box) box.remove();
    }}

    document.addEventListener('click', function (e) {{ if (e.target.closest && e.target.closest('.lang-btn')) setTimeout(render, 0); }});
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render); else setTimeout(render, 0);
  }})();
</script>

'''
    OUT.write_text(section, encoding="utf-8")
    log(f"+++ wrote {OUT.relative_to(ROOT)} ({len(section)} chars)")

    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    for k in [k for k in cfg["i18n"] if k.startswith(("pk.", "ao.", "sum."))]:
        del cfg["i18n"][k]
    cfg["i18n"].update(keys)
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"+++ {len(keys)} text keys written to {CFG.relative_to(ROOT)}")
    log("<<< done")


if __name__ == "__main__":
    main()
