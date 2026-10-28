/* Unitty landing - tracking & attribution (shared by / and /thank-you)
 *
 * What it does
 *  1. Loads Microsoft Clarity (project yczxtdyn7h, same as unitty.io) and the Meta Pixel (1468998947504136).
 *  2. Captures attribution on every page view: the full URL, every query parameter (utm_*, fbclid, gclid, ...),
 *     the referrer and the time. Stored as first-touch (kept forever) and last-touch (latest marketing visit).
 *  3. Keeps the Meta click/browser IDs (_fbc / _fbp) so the CRM can later report lead quality back to Meta
 *     through the Conversions API.
 *  4. Tags every Clarity session with the site version, page, language and campaign, so funnels can be split
 *     by landing version and traffic source.
 *
 * Bump SITE_VERSION on every published change - it is written to each Lead (Landing_Version) and to Clarity.
 */
(function () {
  'use strict';

  var BUILD = 'v38-2026-10-28';
  // Which landing this is: <meta name="unitty-landing" content="crm"> (start / crm / ai / banks / solutions).
  // The thank-you page gets it from the ?v= parameter the landing passes along.
  var LANDING = (function () {
    var m = document.querySelector('meta[name="unitty-landing"]');
    if (m && m.content) return m.content;
    try { var v = new URLSearchParams(location.search).get('v') || ''; if (v.indexOf('-v') > 0) return v.split('-v')[0]; } catch (e) {}
    return 'start';
  })();
  var SITE_VERSION = LANDING + '-' + BUILD;          // e.g. "crm-v27-2026-10-26" -> Lead.Landing_Version
  var CLARITY_ID = 'yczxtdyn7h';
  var META_PIXEL_ID = '1468998947504136';

  var CLICK_IDS = ['fbclid', 'gclid', 'gbraid', 'wbraid', 'ttclid', 'msclkid', 'li_fat_id', 'yclid', 'twclid'];
  var UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'utm_id'];
  var FIRST_KEY = 'unitty_attr_first';
  var LAST_KEY = 'unitty_attr_last';

  function log(msg, extra) {
    try { console.info('[tracking] ' + msg, extra === undefined ? '' : extra); } catch (e) {}
  }

  var path = location.pathname.replace(/\/index\.html$/, '/');
  var PAGE = /^\/thank-you/.test(path) ? 'thank-you' : 'landing';

  // ---------- storage helpers (private mode / blocked storage safe) ----------
  function readJSON(key) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : null; } catch (e) { return null; }
  }
  function writeJSON(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  }
  function getCookie(name) {
    var m = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.$?*|{}()[\]\\/+^]/g, '\\$&') + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }
  function setCookie(name, value, days) {
    try {
      var exp = new Date(Date.now() + days * 864e5).toUTCString();
      var domain = /(^|\.)unitty\.io$/.test(location.hostname) ? '; domain=.unitty.io' : '';
      document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + exp + '; path=/' + domain + '; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');
    } catch (e) {}
  }

  // ---------- 1. attribution capture ----------
  var params = {};
  try { new URLSearchParams(location.search).forEach(function (v, k) { if (v !== '') params[k] = v; }); } catch (e) {}

  var referrer = document.referrer || '';
  var externalReferrer = referrer && referrer.indexOf(location.origin) !== 0;
  var hasMarketing = Object.keys(params).some(function (k) { return UTM_KEYS.indexOf(k) !== -1 || CLICK_IDS.indexOf(k) !== -1; });

  var touch = {
    url: location.href,
    page: PAGE,
    params: params,
    referrer: referrer || '(direct)',
    ts: new Date().toISOString(),
    version: SITE_VERSION
  };

  if (PAGE === 'landing') {
    if (!readJSON(FIRST_KEY)) { writeJSON(FIRST_KEY, touch); log('>>> first touch stored', touch.url); }
    // last touch = latest visit that carried campaign data or came from another site
    if (hasMarketing || externalReferrer || !readJSON(LAST_KEY)) { writeJSON(LAST_KEY, touch); log('--- last touch stored', touch.url); }
  }

  // Meta click ID: keep _fbc even if the Pixel is blocked, so the CRM can still match the lead.
  if (params.fbclid) {
    var existing = getCookie('_fbc');
    if (!existing || existing.split('.').pop() !== params.fbclid) {
      setCookie('_fbc', 'fb.1.' + Date.now() + '.' + params.fbclid, 90);
      log('+++ _fbc set from fbclid');
    }
  }

  function pick(obj, keys) {
    var out = {};
    keys.forEach(function (k) { if (obj && obj[k]) out[k] = obj[k]; });
    return out;
  }

  // Everything the lead form sends to /api/lead
  function getAttribution() {
    var first = readJSON(FIRST_KEY) || touch;
    var last = readJSON(LAST_KEY) || first;
    var lastP = last.params || {};
    var firstP = first.params || {};
    var clickFrom = function (k) { return lastP[k] || firstP[k] || ''; };
    return {
      landing_version: SITE_VERSION,
      landing_url: first.url || '',            // full first landing URL, all parameters
      last_touch_url: last.url || '',
      first_touch: first,                      // {url, params, referrer, ts, version}
      last_touch: last,
      utm: pick(lastP, UTM_KEYS),              // last-touch campaign (what the CRM utm_* fields hold)
      first_utm: pick(firstP, UTM_KEYS),
      fbclid: clickFrom('fbclid'),
      gclid: clickFrom('gclid') || clickFrom('gbraid') || clickFrom('wbraid'),
      click_ids: Object.assign(pick(firstP, CLICK_IDS), pick(lastP, CLICK_IDS)),
      fbc: getCookie('_fbc'),
      fbp: getCookie('_fbp'),
      referrer: last.referrer || '(direct)',
      first_referrer: first.referrer || '(direct)',
      submission_url: location.href,
      user_agent: navigator.userAgent,
      screen: (window.screen ? screen.width + 'x' + screen.height : ''),
      tz: (Intl.DateTimeFormat().resolvedOptions().timeZone || ''),
      submitted_at: new Date().toISOString()
    };
  }

  function newEventId() {
    try { if (crypto && crypto.randomUUID) return crypto.randomUUID(); } catch (e) {}
    return 'ev-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10);
  }

  // ---------- 2. Microsoft Clarity ----------
  (function (c, l, a, r, i, t, y) {
    c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
    t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
    y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
  })(window, document, 'clarity', 'script', CLARITY_ID);

  function clarity() {
    try { window.clarity.apply(null, arguments); } catch (e) {}
  }
  var attrNow = getAttribution();
  clarity('set', 'site', location.hostname);
  clarity('set', 'landing', LANDING);
  clarity('set', 'page', PAGE);
  clarity('set', 'landing_version', SITE_VERSION);
  clarity('set', 'lang', (function () { try { return localStorage.getItem('unitty-lang') || 'ka'; } catch (e) { return 'ka'; } })());
  ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'].forEach(function (k) {
    if (attrNow.utm[k]) clarity('set', k, attrNow.utm[k]);
  });
  clarity('set', 'traffic', attrNow.fbclid ? 'meta_click' : (attrNow.gclid ? 'google_click' : (attrNow.utm.utm_source || 'organic_or_direct')));

  // ---------- 3. Meta Pixel ----------
  /* eslint-disable */
  !function (f, b, e, v, n, t, s) {
    if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
    if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
    t = b.createElement(e); t.async = !0; t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
  }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
  /* eslint-enable */
  window.fbq('init', META_PIXEL_ID);
  window.fbq('track', 'PageView');

  // Thank-you page: fire the browser Lead event once, with the same event_id the server sends to the
  // Conversions API, so Meta counts it once.
  if (PAGE === 'thank-you') {
    var eid = '';
    try { eid = new URLSearchParams(location.search).get('eid') || ''; } catch (e) {}
    if (eid) {
      var firedKey = 'unitty_lead_fired_' + eid;
      var already = false;
      try { already = sessionStorage.getItem(firedKey) === '1'; } catch (e) {}
      if (!already) {
        window.fbq('track', 'Lead', { content_name: LANDING + ' lead form', landing_version: SITE_VERSION }, { eventID: eid });
        clarity('event', 'lead_thankyou_view');
        try { sessionStorage.setItem(firedKey, '1'); } catch (e) {}
        log('+++ Meta Lead event sent', eid);
      }
    }
  }

  // ---------- public API ----------
  window.UnittyTracking = {
    version: SITE_VERSION,
    landing: LANDING,
    page: PAGE,
    getAttribution: getAttribution,
    newEventId: newEventId,
    event: function (name, data) {
      clarity('event', name);
      if (data) Object.keys(data).forEach(function (k) { clarity('set', k, String(data[k])); });
    },
    trackMeta: function (name, data) { try { window.fbq('trackCustom', name, data || {}); } catch (e) {} }
  };
  log('<<< ready', { page: PAGE, version: SITE_VERSION, utm: attrNow.utm, fbclid: !!attrNow.fbclid });
})();
