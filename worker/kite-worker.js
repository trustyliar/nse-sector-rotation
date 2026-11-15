// Cloudflare Worker: holds the Zerodha API secret and lets the SwingDesk journal read today's trades.
// Secrets to add in Cloudflare (Settings > Variables and secrets): KITE_API_KEY, KITE_API_SECRET
// Optional variable: SITE_URL (the journal page address). Only /login, /callback, /trades, /holdings are served.
const DEFAULT_SITE = "https://trustyliar.github.io/nse-sector-rotation/journal.html";
const sha256 = async s => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)))].map(b => b.toString(16).padStart(2, "0")).join("");
export default {
  async fetch(req, env) {
    const u = new URL(req.url), site = env.SITE_URL || DEFAULT_SITE, origin = new URL(site).origin;
    const cors = { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Headers": "authorization", "Vary": "Origin" };
    const back = h => new Response(null, { status: 302, headers: { Location: site + "#" + h } });
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (u.pathname === "/login") return new Response(null, { status: 302, headers: { Location: "https://kite.zerodha.com/connect/login?v=3&api_key=" + env.KITE_API_KEY } });
    if (u.pathname === "/callback") {
      const rt = u.searchParams.get("request_token");
      if (!rt || u.searchParams.get("status") !== "success") return back("kerr=" + encodeURIComponent("Zerodha login was not completed"));
      const r = await fetch("https://api.kite.trade/session/token", { method: "POST", headers: { "X-Kite-Version": "3", "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ api_key: env.KITE_API_KEY, request_token: rt, checksum: await sha256(env.KITE_API_KEY + rt + env.KITE_API_SECRET) }) });
      const j = await r.json().catch(() => ({}));
      return j.status === "success" ? back("kt=" + j.data.access_token) : back("kerr=" + encodeURIComponent(j.message || "Could not get a Zerodha session"));
    }
    const route = { "/trades": "/trades", "/holdings": "/portfolio/holdings" }[u.pathname];
    if (route) {
      const tk = (req.headers.get("authorization") || "").replace(/^Bearer /, "");
      const r = await fetch("https://api.kite.trade" + route, { headers: { "X-Kite-Version": "3", Authorization: "token " + env.KITE_API_KEY + ":" + tk } });
      return new Response(await r.text(), { status: r.status, headers: { ...cors, "Content-Type": "application/json" } });
    }
    return new Response("SwingDesk Zerodha bridge", { status: 200 });
  }
};
