#!/usr/bin/env python3
"""Build the CRM packages + add-ons section (crm.unitty.io only).

Source of truth: landings/crm.packages.data.json (prices, days, KA/EN/RU texts, taken from
"Unitty Offer Template v3" on Drive). This script writes:
  - landings/crm.packages.html   static, crawlable markup with data-i18n keys + the interactive script
  - the "pk.*" / "ao.*" / "sum.*" text keys into landings/crm.json -> i18n
Run it before tools/build_landings.py whenever the packages data changes.
Mobile first: base CSS is the phone layout, min-width queries add the desktop layout.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "landings" / "crm.packages.data.json"
OUT = ROOT / "landings" / "crm.packages.html"
CFG = ROOT / "landings" / "crm.json"


def log(msg):
    print(msg, flush=True)


def T(ka, en, ru):
    return {"ka": ka, "en": en, "ru": ru}


UI = {
    "pk.title": T("აირჩიე, საიდან დაიწყო", "Choose where to start", "Выберите, с чего начать"),
    "pk.sub": T("ფიქსირებული ფასი და ვადა. იწყებ პატარა პაკეტით და ამატებ მხოლოდ იმას, რაც ნამდვილად გჭირდება.",
                "Fixed price, fixed timeline. Start with a small package and add only what you actually need.",
                "Фиксированная цена и срок. Начинаете с небольшого пакета и добавляете только то, что действительно нужно."),
    "pk.popular": T("ყველაზე ხშირად ირჩევენ", "Most popular", "Выбирают чаще всего"),
    "pk.once": T("ერთჯერადად · ფიქსირებული ფასი", "One-time · fixed price", "Разово · фиксированная цена"),
    "pk.days": T("სამუშაო დღე", "working days", "рабочих дней"),
    "pk.more": T("ყველა პუნქტის ნახვა", "Show everything included", "Показать всё, что входит"),
    "pk.less": T("დაკეცვა", "Show less", "Свернуть"),
    "pk.choose": T("ამ პაკეტის არჩევა", "Choose this package", "Выбрать этот пакет"),
    "pk.chosen": T("არჩეულია", "Selected", "Выбран"),
    "pk.trust.1": T("ფასი ფიქსირებულია, დამატებითი ხარჯების გარეშე", "Fixed price, no change orders inside the scope", "Цена фиксирована, без доплат внутри объёма"),
    "pk.trust.2": T("3 დღე ჩასაბარებლად, ხარვეზებს უფასოდ ვასწორებთ", "3 days to review, defects fixed at no cost", "3 дня на приёмку, недочёты исправляем бесплатно"),
    "pk.trust.3": T("CRM, ანგარიში და მონაცემები შენია", "The CRM, the account and the data are yours", "CRM, аккаунт и данные принадлежат вам"),
    "pk.trust.4": T("ტრენინგი და დოკუმენტაცია ყველა პაკეტში", "Training and documentation in every package", "Обучение и документация в каждом пакете"),
    "pk.note": T("ფასები ევროშია, დღგ-ს (18%) და CRM-ის ლიცენზიის გარეშე. ლიცენზიას პირდაპირ მწარმოებელს უხდი.",
                 "Prices are in EUR, excluding 18% VAT and the CRM licence. You pay the licence directly to the vendor.",
                 "Цены в евро, без НДС (18%) и лицензии CRM. Лицензию вы оплачиваете напрямую производителю."),
    "ao.title": T("დამატებები", "Add-ons", "Дополнения"),
    "ao.sub": T("დაამატე ნებისმიერ პაკეტს ან შეუკვეთე ცალკე სპრინტად. თითოეულს ფიქსირებული ფასი და ვადა აქვს.",
                "Add to any package or order as a standalone sprint. Each has a fixed price and timeline.",
                "Добавьте к любому пакету или закажите отдельным спринтом. У каждого фиксированная цена и срок."),
    "ao.rec": T("რეკომენდებული", "Recommended", "Рекомендуем"),
    "ao.all": T("ყველა", "All", "Все"),
    "ao.days": T("დღე", "days", "дн."),
    "ao.add": T("დამატება", "Add", "Добавить"),
    "ao.remove": T("მოშორება", "Remove", "Убрать"),
    "ao.catalog": T("სრულ კატალოგს (75+ გადაწყვეტა) ზარზე გაჩვენებთ.", "We show the full catalog (75+ solutions) on the call.", "Полный каталог (75+ решений) покажем на звонке."),
    "sum.empty": T("აირჩიე პაკეტი ან დამატება", "Pick a package or an add-on", "Выберите пакет или дополнение"),
    "sum.addons": T("დამატება", "add-ons", "доп."),
    "sum.vat": T("+ დღგ", "+ VAT", "+ НДС"),
    "sum.days": T("დღე", "days", "дн."),
    "sum.from": T("პაკეტები €990-დან", "Packages from €990", "Пакеты от €990"),
    "sum.cta": T("მოითხოვე ზარი", "Request a call", "Запросить звонок"),
    "sum.clear": T("გასუფთავება", "Clear", "Сбросить"),
    "sum.picked": T("შენი არჩევანი:", "Your selection:", "Ваш выбор:"),
}


def esc(s):
    return html.escape(s, quote=True)


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    keys = dict(UI)
    log(f">>> {len(d['packages'])} packages, {len(d['addons'])} add-ons")

    # ---------- package cards ----------
    tabs, cards = [], []
    for p in d["packages"]:
        pid = p["id"]
        for f in ("name", "title", "for", "base"):
            if f in p:
                keys[f"pk.{pid}.{f}"] = p[f]
        items = []
        if "base" in p:
            items.append(f'<li class="pk-base" data-i18n="pk.{pid}.base">{esc(p["base"]["en"])}</li>')
        for i, it in enumerate(p["items"], 1):
            keys[f"pk.{pid}.i{i}"] = it
            items.append(f'<li data-i18n="pk.{pid}.i{i}">{esc(it["en"])}</li>')
        pop = ' is-popular' if p.get("popular") else ''
        badge = '<span class="pk-badge" data-i18n="pk.popular">Most popular</span>' if p.get("popular") else ''
        tabs.append(f'<button type="button" class="pk-tab" role="tab" data-pk="{pid}" aria-selected="false"><span data-i18n="pk.{pid}.name">{esc(p["name"]["en"])}</span><small>€{p["price"]:,}</small></button>')
        cards.append(f'''      <article class="pk-card{pop}" id="pk-{pid}" data-pk="{pid}" data-price="{p["price"]}" data-days="{p["days"]}">
        <header class="pk-head">
          <h3 class="pk-name" data-i18n="pk.{pid}.name">{esc(p["name"]["en"])}</h3>{badge}
        </header>
        <p class="pk-title" data-i18n="pk.{pid}.title">{esc(p["title"]["en"])}</p>
        <div class="pk-price"><strong>€{p["price"]:,}</strong><span data-i18n="pk.once">One-time · fixed price</span></div>
        <p class="pk-time"><b>{p["days"]}</b> <span data-i18n="pk.days">working days</span></p>
        <p class="pk-for" data-i18n="pk.{pid}.for">{esc(p["for"]["en"])}</p>
        <button type="button" class="btn pk-choose" data-pk="{pid}" aria-pressed="false"><span class="pk-choose-off" data-i18n="pk.choose">Choose this package</span><span class="pk-choose-on" data-i18n="pk.chosen">Selected</span></button>
        <ul class="pk-list" data-collapsed="true">
          {"".join(items)}
        </ul>
        <button type="button" class="pk-more" aria-expanded="false"><span class="pk-more-off" data-i18n="pk.more">Show everything included</span><span class="pk-more-on" data-i18n="pk.less">Show less</span></button>
      </article>''')

    # ---------- add-ons ----------
    chips = ['<button type="button" class="ao-chip is-on" data-cat="rec" aria-pressed="true"><span data-i18n="ao.rec">Recommended</span></button>']
    cat_count = {}
    for a in d["addons"]:
        cat_count[a[0]] = cat_count.get(a[0], 0) + 1
    for c in d["categories"]:
        keys[f"ao.cat.{c['id']}"] = c["name"]
        chips.append(f'<button type="button" class="ao-chip" data-cat="{c["id"]}" aria-pressed="false"><span data-i18n="ao.cat.{c["id"]}">{esc(c["name"]["en"])}</span> <small>{cat_count.get(c["id"], 0)}</small></button>')
    chips.append(f'<button type="button" class="ao-chip" data-cat="all" aria-pressed="false"><span data-i18n="ao.all">All</span> <small>{len(d["addons"])}</small></button>')

    rows = []
    cat_order = [c["id"] for c in d["categories"]]
    for cid in cat_order:
        rows.append(f'<li class="ao-group" data-cat="{cid}" data-i18n="ao.cat.{cid}">{esc(next(c["name"]["en"] for c in d["categories"] if c["id"] == cid))}</li>')
        for n, a in enumerate(d["addons"], 1):
            cat, price, days, rec, ka, en, ru = a
            if cat != cid:
                continue
            keys[f"ao.{n}"] = T(ka, en, ru)
            rec_badge = '<span class="ao-rec" data-i18n="ao.rec">Recommended</span>' if rec else ''
            rows.append(f'''<li class="ao-item" data-id="{n}" data-cat="{cat}" data-rec="{rec}" data-price="{price}" data-days="{days}" data-en="{esc(en)}">
            <div class="ao-text"><span class="ao-name" data-i18n="ao.{n}">{esc(en)}</span>{rec_badge}<span class="ao-meta"><b>{days}</b> <span data-i18n="ao.days">days</span></span></div>
            <span class="ao-price">€{price:,}</span>
            <button type="button" class="ao-toggle" aria-pressed="false" data-i18n-attr="aria-label:ao.add" aria-label="Add"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="ao-plus" d="M12 5v14M5 12h14"/><path class="ao-check" d="M5 12.5l4.5 4.5L19 7.5"/></svg></button>
          </li>''')

    trust = "".join(f'<li data-i18n="pk.trust.{i}"></li>' for i in range(1, 5))
    names_en = {p["id"]: p["name"]["en"] for p in d["packages"]}

    section = f'''<!-- ============ CRM PACKAGES + ADD-ONS (crm.unitty.io only) ============ -->
<!-- Built by tools/build_crm_packages.py from landings/crm.packages.data.json (Unitty Offer Template v3).
     Mobile first: the base CSS is the phone layout; min-width queries add tablet/desktop. The choice is
     added to the lead as "selected solutions" so it lands in the Zoho CRM lead description. -->
<style>
  .pk {{ padding-bottom: 120px; }}
  .pk-tabs {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding: 4px; margin-top: 28px;
    background: var(--surface); border: 1px solid var(--border); border-radius: 14px; }}
  .pk-tab {{ appearance: none; border: 0; background: transparent; color: var(--fg-dim); border-radius: 10px;
    min-height: 52px; padding: 6px 4px; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; }}
  .pk-tab small {{ font-size: 14px; font-weight: 500; color: var(--fg-mute); }}
  .pk-tab[aria-selected="true"] {{ background: var(--surface-2); color: var(--fg); box-shadow: inset 0 0 0 1px var(--border-2); }}
  .pk-tab[aria-selected="true"] small {{ color: var(--accent); }}
  .pk-track {{ display: flex; gap: 12px; margin: 16px -20px 0; padding: 4px 20px 8px; overflow-x: auto;
    scroll-snap-type: x mandatory; scroll-padding-inline: 20px; scrollbar-width: none; -webkit-overflow-scrolling: touch; }}
  .pk-track::-webkit-scrollbar {{ display: none; }}
  .pk-card {{ flex: 0 0 86%; min-width: 0; scroll-snap-align: start; display: flex; flex-direction: column; gap: 12px;
    padding: 22px 20px; border-radius: 20px; background: var(--surface); border: 1px solid var(--border); position: relative; }}
  .pk-card.is-popular {{ border-color: color-mix(in srgb, var(--accent) 45%, transparent);
    background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 8%, var(--surface)) 0%, var(--surface) 55%); }}
  .pk-card.is-chosen {{ border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent), 0 18px 50px -24px color-mix(in srgb, var(--accent) 60%, transparent); }}
  .pk-head {{ display: flex; flex-direction: column-reverse; align-items: flex-start; gap: 10px; }}
  .pk-name {{ margin: 0; font-family: var(--font-head); font-weight: 900; font-size: 24px; line-height: 1.1; color: var(--fg); }}
  .pk-badge {{ font-size: 14px; line-height: 1; padding: 7px 10px; border-radius: 999px; color: var(--accent-ink); background: var(--accent); font-weight: 600; white-space: nowrap; }}
  .pk-title {{ margin: 0; font-size: 16px; line-height: 1.4; color: var(--fg); font-weight: 600; }}
  .pk-price {{ display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 10px; }}
  .pk-price strong {{ font-family: var(--font-body); font-weight: 700; font-size: 40px; line-height: 1; letter-spacing: -0.02em; color: var(--fg); }}
  .pk-price span {{ font-size: 14px; color: var(--fg-dim); }}
  .pk-time {{ margin: 0; font-size: 15px; color: var(--fg-dim); }}
  .pk-time b {{ color: var(--accent); font-weight: 700; }}
  .pk-for {{ margin: 0; font-size: 15px; line-height: 1.5; color: var(--fg-dim); }}
  .pk-choose {{ width: 100%; justify-content: center; min-height: 50px; background: var(--surface-2); color: var(--fg); border-color: var(--border-2); }}
  .pk-card.is-popular .pk-choose, .pk-choose[aria-pressed="true"] {{ background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }}
  .pk-choose-on, .pk-choose[aria-pressed="true"] .pk-choose-off {{ display: none; }}
  .pk-choose[aria-pressed="true"] .pk-choose-on {{ display: inline; }}
  .pk-list {{ list-style: none; margin: 4px 0 0; padding: 0; display: grid; gap: 10px; }}
  .pk-list li {{ position: relative; padding-left: 26px; font-size: 15px; line-height: 1.45; color: var(--fg); }}
  .pk-list li::before {{ content: ""; position: absolute; left: 2px; top: 5px; width: 12px; height: 7px;
    border-left: 2px solid var(--accent); border-bottom: 2px solid var(--accent); transform: rotate(-45deg); }}
  .pk-list li.pk-base {{ padding-left: 0; color: var(--fg-dim); font-weight: 600; }}
  .pk-list li.pk-base::before {{ display: none; }}
  .pk-list[data-collapsed="true"] li:nth-child(n+6) {{ display: none; }}
  .pk-more {{ appearance: none; background: none; border: 0; padding: 0; min-height: 44px; margin-top: auto; align-self: flex-start;
    color: var(--accent); font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }}
  .pk-more-on, .pk-more[aria-expanded="true"] .pk-more-off {{ display: none; }}
  .pk-more[aria-expanded="true"] .pk-more-on {{ display: inline; }}
  .pk-trust {{ list-style: none; margin: 24px 0 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .pk-trust li {{ font-size: 14px; line-height: 1.45; color: var(--fg); padding: 14px; border-radius: 14px; background: var(--surface); border: 1px solid var(--border); }}
  .pk-note {{ margin: 14px 0 0; font-size: 14px; line-height: 1.5; color: var(--fg-dim); }}

  .ao {{ margin-top: 48px; }}
  .ao-title {{ margin: 0; font-family: var(--font-head); font-weight: 900; font-size: 24px; line-height: 1.15; color: var(--fg); }}
  .ao-sub {{ margin: 8px 0 0; font-size: 15px; line-height: 1.5; color: var(--fg-dim); max-width: 640px; }}
  .ao-chips {{ display: flex; gap: 8px; margin: 18px -20px 0; padding: 2px 20px 6px; overflow-x: auto; scrollbar-width: none; }}
  .ao-chips::-webkit-scrollbar {{ display: none; }}
  .ao-chip {{ appearance: none; flex: none; min-height: 44px; padding: 0 14px; border-radius: 999px; cursor: pointer;
    font: inherit; font-size: 14px; font-weight: 600; color: var(--fg); background: var(--surface); border: 1px solid var(--border); white-space: nowrap; }}
  .ao-chip small {{ font-size: 14px; color: var(--fg-mute); font-weight: 500; }}
  .ao-chip.is-on {{ background: var(--fg); color: var(--bg); border-color: var(--fg); }}
  .ao-chip.is-on small {{ color: var(--fg-mute); }}
  .ao-list {{ list-style: none; margin: 12px 0 0; padding: 0; border-top: 1px solid var(--border); }}
  .ao-group {{ display: none; padding: 20px 0 8px; font-size: 14px; font-weight: 700; color: var(--fg-dim); }}
  .ao-list.show-groups .ao-group {{ display: block; }}
  .ao-list.is-rec .ao-rec {{ display: none; }}
  .ao-item {{ display: grid; grid-template-columns: 1fr auto 44px; align-items: center; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--border); }}
  .ao-item[hidden] {{ display: none; }}
  .ao-text {{ display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; min-width: 0; }}
  .ao-name {{ flex: 1 1 100%; font-size: 15px; line-height: 1.4; color: var(--fg); }}
  .ao-rec {{ font-size: 14px; line-height: 1; padding: 4px 8px; border-radius: 999px; color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent); }}
  .ao-meta {{ font-size: 14px; color: var(--fg-dim); }}
  .ao-price {{ font-size: 16px; font-weight: 700; color: var(--fg); white-space: nowrap; }}
  .ao-toggle {{ width: 44px; height: 44px; border-radius: 12px; cursor: pointer; display: grid; place-items: center;
    background: var(--surface-2); border: 1px solid var(--border-2); color: var(--fg); transition: background .15s ease, transform .15s ease; }}
  .ao-toggle svg {{ width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }}
  .ao-check, .ao-toggle[aria-pressed="true"] .ao-plus {{ display: none; }}
  .ao-toggle[aria-pressed="true"] .ao-check {{ display: inline; }}
  .ao-toggle[aria-pressed="true"] {{ background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }}
  .ao-toggle:active {{ transform: scale(.94); }}
  .ao-item.is-on .ao-name {{ font-weight: 600; }}
  .ao-catalog {{ margin: 14px 0 0; font-size: 14px; color: var(--fg-dim); }}

  /* live summary: fixed to the bottom while the packages are on screen */
  .pk-bar {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: 60; transform: translateY(110%); transition: transform .25s ease;
    padding: 10px 16px calc(10px + env(safe-area-inset-bottom)); background: color-mix(in srgb, var(--bg) 88%, transparent);
    -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px); border-top: 1px solid var(--border-2); }}
  .pk-bar.is-visible {{ transform: none; }}
  .pk-bar-in {{ max-width: 1180px; margin: 0 auto; display: flex; align-items: center; gap: 12px; }}
  .pk-bar-sum {{ flex: 1; min-width: 0; }}
  .pk-bar-what {{ display: block; font-size: 14px; color: var(--fg-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .pk-bar-total {{ display: block; font-size: 20px; font-weight: 700; color: var(--fg); line-height: 1.25; }}
  .pk-bar-total small {{ font-size: 14px; font-weight: 500; color: var(--fg-dim); }}
  .pk-bar .btn {{ flex: none; min-height: 48px; padding: 12px 16px; }}
  .pk-bar-clear {{ display: none; }}
  .pk-picked {{ margin: 0 auto 20px; max-width: 640px; padding: 12px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5;
    color: var(--fg); background: color-mix(in srgb, var(--accent) 8%, var(--surface)); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); }}
  .pk-picked b {{ color: var(--accent); }}
  @media (prefers-reduced-motion: reduce) {{ .pk-bar {{ transition: none; }} }}

  @media (min-width: 700px) {{
    .pk-trust {{ grid-template-columns: repeat(4, 1fr); }}
    .ao-chips {{ flex-wrap: wrap; overflow: visible; margin-inline: 0; padding-inline: 0; }}
    .ao-item {{ gap: 20px; padding: 12px 0; }}
    .ao-name {{ flex: 0 1 auto; }}
    .pk-bar-clear {{ display: inline-flex; background: none; border: 0; color: var(--fg-dim); font: inherit; font-size: 14px; cursor: pointer; text-decoration: underline; }}
  }}
  @media (min-width: 980px) {{
    .pk-tabs {{ display: none; }}
    .pk-track {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 40px 0 0; padding: 0; overflow: visible; align-items: start; }}
    .pk-card {{ padding: 28px 24px; }}
    .pk-card.is-popular {{ transform: translateY(-8px); }}
    .pk-bar-total {{ font-size: 22px; }}
  }}
</style>
<section class="section pk" id="packages">
  <div class="wrap">
    <h2 class="section-title" data-i18n="pk.title">Choose where to start</h2>
    <p class="section-sub" data-i18n="pk.sub"></p>
    <div class="pk-tabs" role="tablist">{"".join(tabs)}</div>
    <div class="pk-track">
{chr(10).join(cards)}
    </div>
    <ul class="pk-trust">{trust}</ul>
    <p class="pk-note" data-i18n="pk.note"></p>

    <div class="ao" id="addons">
      <h3 class="ao-title" data-i18n="ao.title">Add-ons</h3>
      <p class="ao-sub" data-i18n="ao.sub"></p>
      <div class="ao-chips">{"".join(chips)}</div>
      <ul class="ao-list">
          {"".join(rows)}
      </ul>
      <p class="ao-catalog" data-i18n="ao.catalog"></p>
    </div>
  </div>
</section>
<div class="pk-bar" id="pkBar" aria-live="polite">
  <div class="pk-bar-in">
    <div class="pk-bar-sum">
      <span class="pk-bar-what" id="pkBarWhat"></span>
      <span class="pk-bar-total" id="pkBarTotal"></span>
    </div>
    <button type="button" class="pk-bar-clear" id="pkBarClear" data-i18n="sum.clear">Clear</button>
    <a href="#final" class="btn btn-primary" id="pkBarCta"><span data-i18n="sum.cta">Request a call</span></a>
  </div>
</div>
<script>
  // CRM packages + add-ons: pick one package and any add-ons, see the live total, send it with the lead.
  (function () {{
    var NAMES_EN = {json.dumps(names_en)};
    var sec = document.getElementById('packages');
    if (!sec) return;
    var bar = document.getElementById('pkBar');
    var chosen = null;                 // package id
    var addons = new Set();            // add-on ids
    function log(m, x) {{ try {{ console.info('[packages] ' + m, x === undefined ? '' : x); }} catch (e) {{}} }}
    function tr(key, fb) {{ try {{ var v = (typeof t === 'function') ? t(key) : null; return (v && v !== key) ? v : fb; }} catch (e) {{ return fb; }} }}
    function eur(n) {{ return '€' + n.toLocaleString('en-US'); }}
    function track(name, data) {{ try {{ if (window.UnittyTracking) window.UnittyTracking.event(name, data); }} catch (e) {{}} }}
    var cards = [].slice.call(sec.querySelectorAll('.pk-card'));
    var tabs = [].slice.call(sec.querySelectorAll('.pk-tab'));
    var track_ = sec.querySelector('.pk-track');
    var items = [].slice.call(sec.querySelectorAll('.ao-item'));
    var list = sec.querySelector('.ao-list');

    // ---- mobile tabs <-> swipe cards ----
    function markTab(id) {{ tabs.forEach(function (b) {{ b.setAttribute('aria-selected', b.dataset.pk === id ? 'true' : 'false'); }}); }}
    tabs.forEach(function (b) {{
      b.addEventListener('click', function () {{
        var c = document.getElementById('pk-' + b.dataset.pk);
        track_.scrollTo({{ left: c.offsetLeft - track_.offsetLeft - 20, behavior: 'smooth' }});
        markTab(b.dataset.pk);
      }});
    }});
    if ('IntersectionObserver' in window) {{
      var io = new IntersectionObserver(function (ents) {{
        ents.forEach(function (e) {{ if (e.isIntersecting && e.intersectionRatio > 0.6) markTab(e.target.dataset.pk); }});
      }}, {{ root: track_, threshold: [0.6] }});
      cards.forEach(function (c) {{ io.observe(c); }});
    }}
    // start on the most popular package on phones
    var pop = sec.querySelector('.pk-card.is-popular');
    if (pop) {{ markTab(pop.dataset.pk); requestAnimationFrame(function () {{ if (getComputedStyle(track_).display === 'flex') track_.scrollLeft = pop.offsetLeft - track_.offsetLeft - 20; }}); }}

    // ---- expand / collapse included items ----
    sec.querySelectorAll('.pk-more').forEach(function (b) {{
      var ul = b.previousElementSibling;
      if (ul.children.length <= 5) {{ b.hidden = true; return; }}
      b.addEventListener('click', function () {{
        var open = b.getAttribute('aria-expanded') !== 'true';
        b.setAttribute('aria-expanded', open ? 'true' : 'false');
        ul.setAttribute('data-collapsed', open ? 'false' : 'true');
      }});
    }});

    // ---- choose a package (one at a time; tap again to unselect) ----
    sec.querySelectorAll('.pk-choose').forEach(function (b) {{
      b.addEventListener('click', function () {{
        chosen = (chosen === b.dataset.pk) ? null : b.dataset.pk;
        log('>>> package', chosen);
        if (chosen) track('package_selected', {{ package: chosen }});
        render();
      }});
    }});

    // ---- add-on filter chips ----
    function filter(cat) {{
      sec.querySelectorAll('.ao-chip').forEach(function (c) {{ var on = c.dataset.cat === cat; c.classList.toggle('is-on', on); c.setAttribute('aria-pressed', on ? 'true' : 'false'); }});
      items.forEach(function (it) {{
        it.hidden = !(cat === 'all' || (cat === 'rec' ? it.dataset.rec === '1' : it.dataset.cat === cat));
      }});
      list.classList.toggle('show-groups', cat === 'all');
      list.classList.toggle('is-rec', cat === 'rec');
    }}
    sec.querySelectorAll('.ao-chip').forEach(function (c) {{ c.addEventListener('click', function () {{ filter(c.dataset.cat); }}); }});
    filter('rec');

    // ---- add / remove an add-on ----
    items.forEach(function (it) {{
      it.querySelector('.ao-toggle').addEventListener('click', function () {{
        var id = it.dataset.id;
        if (addons.has(id)) addons.delete(id); else {{ addons.add(id); track('addon_selected', {{ addon: it.dataset.en }}); }}
        log('--- add-ons', Array.from(addons));
        render();
      }});
    }});
    document.getElementById('pkBarClear').addEventListener('click', function () {{ chosen = null; addons.clear(); render(); }});

    // ---- totals, summary bar, lead payload ----
    function totals() {{
      var price = 0, days = 0;
      var card = chosen && document.getElementById('pk-' + chosen);
      if (card) {{ price += +card.dataset.price; days += +card.dataset.days; }}
      items.forEach(function (it) {{ if (addons.has(it.dataset.id)) {{ price += +it.dataset.price; days += +it.dataset.days; }} }});
      return {{ price: price, days: days }};
    }}
    function whatText() {{
      var parts = [];
      if (chosen) parts.push(tr('pk.' + chosen + '.name', NAMES_EN[chosen]));
      if (addons.size) parts.push('+' + addons.size + ' ' + tr('sum.addons', 'add-ons'));
      return parts.join(' ');
    }}
    function syncLead() {{
      // shared with the form: state.selected is the template's "selected solutions" set (sent to /api/lead)
      try {{
        if (typeof state === 'undefined' || !state.selected) return;
        Array.from(state.selected).forEach(function (k) {{ if (/^(Package|Add-on): /.test(k)) state.selected.delete(k); }});
        var tt = totals();
        if (chosen) state.selected.add('Package: ' + NAMES_EN[chosen] + ' (€' + document.getElementById('pk-' + chosen).dataset.price + ')');
        items.forEach(function (it) {{ if (addons.has(it.dataset.id)) state.selected.add('Add-on: ' + it.dataset.en + ' (€' + it.dataset.price + ', ' + it.dataset.days + 'd)'); }});
        if (chosen || addons.size) state.selected.add('Package: TOTAL €' + tt.price + ' + VAT, ~' + tt.days + ' working days');
      }} catch (e) {{ log('*** lead sync failed', e.message); }}
    }}
    function render() {{
      cards.forEach(function (c) {{
        var on = c.dataset.pk === chosen;
        c.classList.toggle('is-chosen', on);
        c.querySelector('.pk-choose').setAttribute('aria-pressed', on ? 'true' : 'false');
      }});
      items.forEach(function (it) {{
        var on = addons.has(it.dataset.id);
        it.classList.toggle('is-on', on);
        var b = it.querySelector('.ao-toggle');
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
        b.setAttribute('aria-label', tr(on ? 'ao.remove' : 'ao.add', on ? 'Remove' : 'Add'));
      }});
      var tt = totals(), any = chosen || addons.size;
      document.getElementById('pkBarWhat').textContent = any ? whatText() : tr('sum.empty', 'Pick a package or an add-on');
      document.getElementById('pkBarTotal').innerHTML = any
        ? eur(tt.price) + ' <small>' + tr('sum.vat', '+ VAT') + ' · ' + tt.days + ' ' + tr('sum.days', 'working days') + '</small>'
        : '<small>' + tr('sum.from', 'Packages from €990') + '</small>';
      syncLead();
      var fin = document.getElementById('final');
      var box = document.getElementById('pkPicked');
      if (fin && any) {{
        if (!box) {{ box = document.createElement('p'); box.id = 'pkPicked'; box.className = 'pk-picked'; var form = fin.querySelector('form'); (form || fin).parentNode.insertBefore(box, form || fin.firstChild); }}
        box.innerHTML = tr('sum.picked', 'Your selection:') + ' <b>' + whatText() + '</b> · ' + eur(tt.price) + ' ' + tr('sum.vat', '+ VAT');
      }} else if (box) box.remove();
    }}
    window.unittyPackagesRender = render;      // re-run after a language switch

    // ---- show the bar only while the packages are on screen and the form is not ----
    var inPk = false, inForm = false;
    function showBar() {{ bar.classList.toggle('is-visible', inPk && !inForm); }}
    if ('IntersectionObserver' in window) {{
      new IntersectionObserver(function (e) {{ inPk = e[0].isIntersecting; showBar(); }}, {{ threshold: 0.05 }}).observe(sec);
      var fin = document.getElementById('final');
      if (fin) new IntersectionObserver(function (e) {{ inForm = e[0].isIntersecting; showBar(); }}, {{ threshold: 0.1 }}).observe(fin);
    }}
    document.getElementById('pkBarCta').addEventListener('click', function () {{ track('package_cta', {{ package: chosen || '', addons: addons.size }}); }});
    document.addEventListener('click', function (e) {{ if (e.target.closest && e.target.closest('.lang-btn')) setTimeout(render, 0); }});
    // first render after the page's own script has defined t() and the texts
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
