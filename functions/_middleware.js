// Cloudflare Pages middleware — one project, several landings.
//
// Each subdomain shows its own landing from /public/<name>/index.html, while everything else
// (thank-you page, /api/lead, fonts, images, tracking.js) is shared by all of them.
//
//   start.unitty.io      -> /            (the original landing)
//   crm.unitty.io        -> /crm/
//   ai.unitty.io         -> /ai/
//   banks.unitty.io      -> /banks/
//   solutions.unitty.io  -> /solutions/
//
// Before a subdomain is connected, the same pages are reachable as start.unitty.io/crm/ etc.

const HOSTS = {
  "crm.unitty.io": "crm",
  "ai.unitty.io": "ai",
  "banks.unitty.io": "banks",
  "solutions.unitty.io": "solutions",
};

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const site = HOSTS[url.hostname];

  if (site && (url.pathname === "/" || url.pathname === "/index.html")) {
    console.log(">>> landing rewrite", url.hostname, "->", `/${site}/`);
    url.pathname = `/${site}/`;
    // query string (utm_*, fbclid, ...) is kept, so attribution keeps working
    return context.env.ASSETS.fetch(new Request(url.toString(), context.request));
  }

  return context.next();
}
