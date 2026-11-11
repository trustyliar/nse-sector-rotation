"""Add the Sectors and Setups pages and a shared navigation bar to the site in docs/."""
import re
from urllib.parse import quote

import pandas as pd

from common import DATA

docs = DATA / "docs"
index = (docs / "index.html").read_text()
css = re.search(r"<style>.*?</style>", index, re.S).group(0).replace("</style>", """
nav{display:flex;gap:18px;margin:0 0 18px;font-weight:600}nav a{color:var(--ink2);text-decoration:none;padding-bottom:4px}
nav a.on{color:var(--ink);border-bottom:2px solid var(--s)}td.l,th.l{text-align:left}td.up{color:var(--ink)}td.sm{font-size:12.5px;color:var(--ink2)}
select,input,button{font:inherit;padding:6px 8px;border:1px solid var(--grid);border-radius:6px;background:var(--bg);color:var(--ink);margin:0 8px 12px 0}button{cursor:pointer}
main.wide{max-width:1600px}main.wide td,main.wide th{white-space:nowrap}main.wide td.sm.l{white-space:normal;min-width:220px}
main a{color:inherit;text-decoration:underline dotted;text-underline-offset:3px}th{cursor:pointer;user-select:none}th[data-d]::after{content:" \2195"}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--s);vertical-align:middle;margin-right:6px}</style>""")
day = re.search(r"close of ([^<]+)</h1>", index).group(1)


SORT = ('<script>document.querySelectorAll("th").forEach((th,i)=>{th.title="Click to sort";th.onclick=()=>{const tb=th.closest("table").tBodies[0],'
        'd=th.dataset.d=th.dataset.d=="1"?"-1":"1",key=c=>c.dataset.v??c.textContent.trim(),num=s=>{const v=parseFloat(String(s).replace(/[^0-9.+-]/g,""));'
        'return isNaN(v)||/^[A-Za-z]/.test(s)?null:v};[...tb.rows].sort((a,b)=>{const x=key(a.cells[i]),y=key(b.cells[i]),nx=num(x),ny=num(y);'
        'return d*(nx!=null&&ny!=null?nx-ny:String(x).localeCompare(String(y)))}).forEach(r=>tb.appendChild(r))}})</script>')


def nav(on):
    items = (("index.html", "Regime"), ("sectors.html", "Sectors"), ("setups.html", "Setups"))
    return "<nav>" + "".join(f'<a href="{h}"{" class=on" if t == on else ""}>{t}</a>' for h, t in items) + "</nav>"


def page(title, on, body, script=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{title}</title>{css}</head><body><main class="wide">'
            f'{nav(on)}<h1>{title} &middot; close of {day}</h1>{body}</main>{SORT}{script}</body></html>')


if "<nav>" not in index:
    index = index.replace("</style>", css.split("</style>")[0].split("nav{")[1].join(["\nnav{", "</style>"]), 1) \
                 .replace("<main>", "<main>" + nav("Regime"), 1)
    (docs / "index.html").write_text(index)

t = pd.read_csv(DATA / "derived" / "themes.csv")
arrow = lambda d: "" if pd.isna(d) or d == 0 else (f"&#9650; {int(d)}" if d > 0 else f"&#9660; {int(-d)}")
rows = "".join(
    f'<tr><td>{r["rank"]}</td><td class="l"><b><a href="setups.html?theme={quote(r.theme)}">{r.theme}</a></b></td><td class="sm" data-v="{0 if pd.isna(r.rank_change) else r.rank_change:.0f}">{arrow(r.rank_change)}</td>'
    f'<td class="l"><span class="bar" style="width:{0.6 * r.strength:.0f}px"></span>{r.strength:.0f}</td>'
    f'<td>{r.r1w:+.1f}%</td><td>{r.r1m:+.1f}%</td><td>{r.r3m:+.1f}%</td><td>{r.above50:.0f}%</td>'
    f'<td>{r.leaders}/{r.n}</td><td>{r.setups}</td><td class="l sm">{r.top}</td></tr>' for _, r in t.iterrows())
body = ('<p class="read">Themes ranked by strength (click a theme to see its setups, click any column heading to sort): a blend of the median stock\'s 1-week (20%), 1-month (40%) and '
        '3-month (40%) return, compared across themes. The arrow shows places gained or lost against a month ago.</p>'
        '<div class="tw"><table><thead><tr><th>#</th><th class="l">Theme</th><th>vs 1m ago</th><th class="l">Strength</th>'
        '<th>1 week</th><th>1 month</th><th>3 months</th><th>&gt;50-day</th><th>RS 80+ / stocks</th><th>A-grade setups</th>'
        f'<th class="l">Highest RS</th></tr></thead><tbody>{rows}</tbody></table></div>'
        '<ul class="note"><li>Only liquid stocks count (median traded value Rs 1 crore+, price Rs 40+); themes need five or more.</li>'
        '<li>Returns are the median member\'s, so one large mover cannot carry a theme.</li>'
        '<li>RS is a 1-99 rank of each stock\'s blended 3, 6 and 12-month return against all liquid stocks.</li></ul>')
(docs / "sectors.html").write_text(page("NSE sector strength", "Sectors", body))

s = pd.read_csv(DATA / "derived" / "setups.csv")
s = s[s["grade"] != "C"].sort_values("rank_score", ascending=False).reset_index(drop=True)
tv_link = lambda x: f'https://www.tradingview.com/chart/?symbol=NSE:{x.replace("&", "_").replace("-", "_")}'
rows = "".join(
    f'<tr data-k="{r.tags}" data-t="{r.theme}" data-g="{r.grade}"><td>{i + 1}</td>'
    f'<td class="l"><b><a target="_blank" rel="noopener" href="{tv_link(r.symbol)}">{r.symbol}</a></b></td>'
    f'<td class="l">{r.theme}</td><td><b>{r.rank_score:.0f}</b></td><td>{r.grade}</td><td>{r.quality:.0f}</td>'
    f'<td class="l sm">{r.tags.replace("; ", " &middot; ")}</td><td>{r.rs}</td><td>{r.close:,.1f}</td><td>{r.runup:.0f}%</td>'
    f'<td>{r.depth:.0f}%</td><td>{r.range5:.1f}%</td><td>{r.adr:.1f}%</td><td>{r.vs_ema10:+.1f}%</td><td>{r.vs_ema20:+.1f}%</td>'
    f'<td>{r.vol_ratio:.2f}</td><td>{r.turnover_cr:,.0f}</td></tr>' for i, r in enumerate(s.itertuples()))
alltags = sorted({t for x in s["tags"] for t in x.split("; ")})
kinds = "".join(f"<option>{k}</option>" for k in alltags)
themes = "".join(f"<option>{k}</option>" for k in sorted(s["theme"].dropna().unique()))
body = (f'<p class="read">{len(s)} candidates, best first. Each is a liquid leader (price Rs 40+, above its 200-day average, RS 70+) '
        'scored on what Kristjan Kullamagi looks for: a strong prior move, a shallow orderly consolidation, tightening ranges, '
        'price riding the 10/20 EMA and volume drying up. Click a stock for its chart, a heading to sort. Shortlists for chart review, not signals.</p>'
        f'<input id="q" placeholder="Search stock or theme"><select id="g"><option value="">All grades</option><option>A+</option><option>A</option><option>B</option></select>'
        f'<select id="k"><option value="">All patterns</option>{kinds}</select><select id="t"><option value="">All themes</option>{themes}</select>'
        '<button id="dx">Download Excel (CSV)</button><button id="dt">Download TradingView watchlist</button>'
        '<div class="tw"><table><thead><tr><th>#</th><th class="l">Stock</th><th class="l">Theme</th><th>Rank score</th><th>Grade</th><th>Quality</th>'
        '<th class="l">Patterns today</th><th>RS</th><th>Close</th><th>Prior run</th><th>Off high</th><th>5-day range</th><th>ADR</th>'
        f'<th>vs 10 EMA</th><th>vs 20 EMA</th><th>Vol 5d/50d</th><th>Turnover (cr)</th></tr></thead><tbody id="b">{rows}</tbody></table></div>'
        '<ul class="note"><li><b>Quality (0-100):</b> tightness 30%, prior run 25%, EMA alignment and closeness 20%, shallow pullback 15%, volume dry-up 10%. '
        'Grade A+ is 75 or more, A is 65+, B is 55+.</li>'
        '<li><b>Rank score:</b> 65% quality, 20% relative strength, 15% theme strength, so a clean setup in a leading theme ranks highest.</li>'
        '<li><b>Prior run:</b> the best low-to-high move ending in the last 60 sessions. <b>Off high:</b> distance below the 60-session high. '
        '<b>ADR:</b> average daily range over 20 sessions.</li>'
        '<li><b>Patterns:</b> flag after a 30%+ move; tight 5-day range; inside day; narrowest range in 7 days; at the 10, 20 or 50 EMA; '
        'episodic pivot (6%+ gap on 3x volume in the last 5 sessions, still holding); breakout today (50-day closing high on 1.5x volume).</li></ul>')
js = ('<script>const $=i=>document.getElementById(i),k=$("k"),t=$("t"),q=$("q"),g=$("g"),'
      'f=()=>document.querySelectorAll("#b tr").forEach(r=>r.style.display=(!k.value||r.dataset.k.includes(k.value))&&(!t.value||r.dataset.t==t.value)'
      '&&(!g.value||r.dataset.g==g.value)&&(!q.value||r.textContent.toLowerCase().includes(q.value.toLowerCase()))?"":"none");'
      'k.onchange=t.onchange=g.onchange=q.oninput=f;const p=new URLSearchParams(location.search).get("theme");'
      'if(p){if(![...t.options].some(o=>o.value==p))t.add(new Option(p,p));t.value=p;f()}'
      'const vis=()=>[...document.querySelectorAll("#b tr")].filter(r=>r.style.display!="none"),'
      'save=(name,text,type)=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click()},'
      'cell=c=>\'"\'+c.textContent.trim().replace(/"/g,\'""\')+\'"\',day=new Date().toISOString().slice(0,10);'
      '$("dx").onclick=()=>save("nse-setups-"+day+".csv","\\ufeff"+[[...document.querySelectorAll("thead th")].map(cell).join(",")]'
      '.concat(vis().map(r=>[...r.cells].map(cell).join(","))).join("\\n"),"text/csv");'
      '$("dt").onclick=()=>save("nse-setups-"+day+".txt",vis().map(r=>"NSE:"+r.cells[1].textContent.trim().replace(/[&-]/g,"_")).join(","),"text/plain")</script>')
(docs / "setups.html").write_text(page("NSE setups", "Setups", body, js))
print("site built:", len(t), "themes,", len(s), "setups")
