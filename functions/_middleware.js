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
// SEO (v40): every host gets its own robots.txt and sitemap.xml; the *.pages.dev preview host and
// the thank-you page are kept out of search results (X-Robots-Tag: noindex).

const HOSTS = {
  "crm.unitty.io": "crm",
  "ai.unitty.io": "ai",
  "banks.unitty.io": "banks",
  "solutions.unitty.io": "solutions",
};
const PUBLIC_HOSTS = ["start.unitty.io", ...Object.keys(HOSTS)];

function text(body, type) {
  return new Response(body, { headers: { "Content-Type": type + "; charset=utf-8", "Cache-Control": "public, max-age=3600" } });
}

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const host = url.hostname;
  const site = HOSTS[host];
  const indexable = PUBLIC_HOSTS.includes(host);

  if (url.pathname === "/robots.txt") {
    console.log(">>> robots.txt", host, indexable ? "index" : "noindex");
    return text(indexable
      ? `User-agent: *\nAllow: /\nDisallow: /thank-you\nDisallow: /api/\n\nSitemap: https://${host}/sitemap.xml\n`
      : "User-agent: *\nDisallow: /\n", "text/plain");
  }
  if (url.pathname === "/sitemap.xml" && indexable) {
    const today = new Date().toISOString().slice(0, 10);
    return text(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>https://${host}/</loc><lastmod>${today}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>\n</urlset>\n`, "application/xml");
  }

  let res;
  if (site && (url.pathname === "/" || url.pathname === "/index.html")) {
    console.log(">>> landing rewrite", host, "->", `/${site}/`);
    url.pathname = `/${site}/`;
    // query string (utm_*, fbclid, ...) is kept, so attribution keeps working
    res = await context.env.ASSETS.fetch(new Request(url.toString(), context.request));
  } else {
    res = await context.next();
  }

  // keep preview hosts and the thank-you page out of search results
  if (!indexable || url.pathname.startsWith("/thank-you")) {
    res = new Response(res.body, res);
    res.headers.set("X-Robots-Tag", "noindex, nofollow");
  }
  return res;
}
