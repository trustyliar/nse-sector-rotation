"""Add the Sectors and Setups pages and a shared navigation bar to the site in docs/."""
import re
from urllib.parse import quote

import pandas as pd

import json
from pathlib import Path

from common import DATA, load_prices

docs = DATA / "docs"
index = (docs / "index.html").read_text()
css = re.search(r"<style>.*?</style>", index, re.S).group(0).replace("</style>", """
nav{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0 -20px 14px;padding:10px 20px;background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--grid)}
nav b{font-size:15px;font-weight:800;letter-spacing:-.01em;margin-right:14px}nav b i{font-style:normal;color:var(--s)}
nav a{color:var(--ink2);text-decoration:none;padding:6px 12px;border-radius:99px;font-weight:600;font-size:14px}nav a:hover{background:var(--soft);color:var(--ink)}
nav a.on{background:var(--ink);color:var(--bg)}td.l,th.l{text-align:left}td.sm{font-size:12.5px;color:var(--ink2)}
select,input,button{font:inherit;font-size:14px;padding:8px 12px;border:1px solid var(--grid);border-radius:10px;background:var(--card);color:var(--ink);margin:0 8px 12px 0}
input:focus,select:focus{outline:2px solid var(--s);outline-offset:1px}button{cursor:pointer;font-weight:600}button:hover{background:var(--soft)}
#add,#dx,#dt,#frm button[type=submit]{background:var(--s);border-color:var(--s);color:#fff}#add:hover,#dx:hover,#dt:hover{filter:brightness(1.08);background:var(--s)}
main.wide{max-width:1640px}main.wide td,main.wide th{white-space:nowrap}main.wide td.sm.l{white-space:normal;min-width:220px}
main a{color:inherit;text-decoration:none;border-bottom:1px dotted var(--mut)}main nav a{border-bottom:0}th{cursor:pointer;user-select:none}th[data-d]::after{content:" \2195"}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--s);vertical-align:middle;margin-right:6px}</style>""")
day = re.search(r"close of ([^<]+)</h1>", index).group(1)


SORT = ('<script>document.querySelectorAll("th").forEach((th,i)=>{th.title="Click to sort";th.onclick=()=>{const tb=th.closest("table").tBodies[0],'
        'd=th.dataset.d=th.dataset.d=="1"?"-1":"1",key=c=>c.dataset.v??c.textContent.trim(),num=s=>{const v=parseFloat(String(s).replace(/[^0-9.+-]/g,""));'
        'return isNaN(v)||/^[A-Za-z]/.test(s)?null:v};[...tb.rows].sort((a,b)=>{const x=key(a.cells[i]),y=key(b.cells[i]),nx=num(x),ny=num(y);'
        'return d*(nx!=null&&ny!=null?nx-ny:String(x).localeCompare(String(y)))}).forEach(r=>tb.appendChild(r))}})</script>')


def nav(on):
    items = (("index.html", "Regime"), ("sectors.html", "Sectors"), ("setups.html", "Setups"), ("fundamentals.html", "Fundamentals"), ("journal.html", "Journal"))
    return "<nav><b>Swing<i>Desk</i></b>" + "".join(f'<a href="{h}"{" class=on" if t == on else ""}>{t}</a>' for h, t in items) + "</nav>"


def page(title, on, body, script=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{title}</title>{css}</head><body><main class="wide">'
            f'{nav(on)}<h1>{title} &middot; close of {day}</h1>{body}</main>{SORT}{script}</body></html>')


index = re.sub(r"<nav>.*?</nav>", "", index)
if "<nav>" not in index:
    index = index.replace("</style>", css.split("</style>")[0].split("nav{")[1].join(["\nnav{", "</style>"]), 1) \
                 .replace("<main>", "<main>" + nav("Regime"), 1)
    (docs / "index.html").write_text(index)

# Reversal watch panel on the Regime page
rv = pd.read_csv(DATA / "derived" / "reversal.csv", parse_dates=["date"]).set_index("date")
x = rv.iloc[-1]
trig = rv.index[rv["first"]][-1] if rv["first"].any() else None
ago = len(rv.loc[trig:]) - 1 if trig is not None else 99
if ago <= 10:
    stop = rv.loc[trig, "low10"]
    since = 100 * (x["idx"] / rv.loc[trig, "idx"] - 1)
    state = (f"<b>&#9650; DEPLOY signal on {trig:%d %b}</b> ({ago} sessions ago). Small caps are {since:+.1f}% since. "
             + ("The signal has <b>failed</b>: small caps closed below the low before the signal." if x["idx"] < stop
                else "Exit if small caps close below the low set before the signal."))
elif x["os5"] >= 80:
    state = ("<b>&#9679; GET READY: deeply oversold.</b> Deploy on the turn day: small caps gain 1%+, stocks up 4% "
             "outnumber stocks down 4% by two to one, and more stocks are back above their 20-day average.")
elif x["os5"] >= 60:
    state = "<b>&#9679; WATCH: getting oversold.</b> No action yet; the deploy zone starts at 80."
else:
    state = "<b>STAND BY: not oversold.</b> No reversal setup in the broad market."
panel = (f'<h2>Reversal watch (small caps)</h2><div class="m"><div class="mh"><span>Oversold score</span><span class="v">{x["oversold"]:.0f}</span></div>'
         f'<div class="track"><div class="fill" style="width:{x["oversold"]:.0f}%"></div></div><div>{state}</div>'
         f'<div class="d" style="margin-top:6px">Stocks above their 10-day average: {x["a10"]:.0f}% &middot; 20-day: {x["a20"]:.0f}% &middot; '
         f'50-day: {x["a50"]:.0f}% &middot; at 20-day lows: {x["lows20"]:.0f}% &middot; down share of 4% moves, 10 days: {x["dn10"]:.0f}%. '
         'Under 60: stand by. 60 to 80: watch. 80 or more: get ready, then deploy on the turn day. In tests since 2019 that rule was higher 20 sessions later about 70% of the time; the worst case fell a further 36% (March 2020), so the exit rule matters. '
         'It catches deep sell-offs, not shallow dips.</div></div>')
score_now = float(re.search(r'<div class="num">([\d.]+)</div>', index).group(1))
live = ago <= 10 and x["idx"] >= rv.loc[trig, "low10"]
if score_now >= 55:
    stage = ("Stage 2: stock setups favoured", "The regime score is 55 or more. This is where breakout and pullback entries tested best.")
elif live:
    stage = ("Stage 1: start small through the index", "A reversal signal is live but the regime score is under 55. Tests favour index or ETF exposure here; "
             "stock setups entered this early did no better than usual. Move to stocks as A-grade setups appear and the score reaches 55.")
elif score_now >= 40:
    stage = ("Stage 0: selective only", "No live reversal signal and the regime score is under 55.")
else:
    stage = ("Stage 0: stand by", "Weak regime and no live reversal signal.")
panel = (f'<h2>Deployment stage</h2><div class="m"><div class="mh"><span>{stage[0]}</span></div><div class="d">{stage[1]}</div></div>' + panel)
if "Reversal watch" not in index:
    index = index.replace("<h2>The five parts", panel + "<h2>The five parts", 1)
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
    f'<tr data-k="{r.tags}" data-t="{r.theme}" data-g="{r.grade}" data-s="{r.stage}"><td>{i + 1}</td>'
    f'<td class="l"><b><a target="_blank" rel="noopener" href="{tv_link(r.symbol)}">{r.symbol}</a></b></td>'
    f'<td class="l">{r.theme}</td><td><b>{r.rank_score:.0f}</b></td><td>{r.grade}</td><td>{r.quality:.0f}</td><td class="l">{r.stage}</td><td>{r.trigger:,.1f}</td><td>{r.stop:,.1f}</td><td>{r.risk:.1f}%</td>'
    f'<td class="l sm">{r.tags.replace("; ", " &middot; ")}</td><td>{r.rs}</td><td>{r.close:,.1f}</td><td>{r.runup:.0f}%</td>'
    f'<td>{r.depth:.0f}%</td><td>{r.base_days}</td><td>{r.range5:.1f}%</td><td>{r.adr:.1f}%</td><td>{r.vs_ema10:+.1f}%</td><td>{r.vs_ema20:+.1f}%</td>'
    f'<td>{r.vol_ratio:.2f}</td><td>{r.turnover_cr:,.0f}</td></tr>' for i, r in enumerate(s.itertuples()))
alltags = sorted({t for x in s["tags"] for t in x.split("; ")})
kinds = "".join(f"<option>{k}</option>" for k in alltags)
themes = "".join(f"<option>{k}</option>" for k in sorted(s["theme"].dropna().unique()))
body = (f'<p class="read">{len(s)} candidates, best first. Each is a liquid leader (price Rs 40+, above its 200-day average, RS 70+) '
        'scored on what Kristjan Kullamagi looks for: a strong prior move, a shallow orderly consolidation, tightening ranges, '
        'price riding the 10/20 EMA and volume drying up. Click a stock for its chart, a heading to sort. Shortlists for chart review, not signals.</p>'
        f'<input id="q" placeholder="Search stock or theme"><select id="g"><option value="">All grades</option><option>A+</option><option>A</option><option>B</option></select>'
        '<select id="s"><option value="">All stages</option><option>Ready</option><option>Triggered today</option><option>Building</option><option>Extended</option></select>'
        f'<select id="k"><option value="">All patterns</option>{kinds}</select><select id="t"><option value="">All themes</option>{themes}</select>'
        '<button id="dx">Download Excel (CSV)</button><button id="dt">Download TradingView watchlist</button>'
        '<div class="tw"><table><thead><tr><th>#</th><th class="l">Stock</th><th class="l">Theme</th><th>Rank score</th><th>Grade</th><th>Quality</th><th class="l">Stage</th><th>Trigger</th><th>Stop</th><th>Risk</th>'
        '<th class="l">Patterns today</th><th>RS</th><th>Close</th><th>Prior run</th><th>Off high</th><th>Base (days)</th><th>5-day range</th><th>ADR</th>'
        f'<th>vs 10 EMA</th><th>vs 20 EMA</th><th>Base vol / run vol</th><th>Turnover (cr)</th></tr></thead><tbody id="b">{rows}</tbody></table></div>'
        '<ul class="note"><li><b>Stage:</b> <i>Ready</i> = coiled at the 10/20 EMA and not yet moved, the anticipation point. <i>Triggered today</i> = closed above yesterday\'s high on a strong day. <i>Extended</i> = more than 1.5 daily ranges above the 10 EMA. <i>Building</i> = base still forming, or overhead supply: a red candle of 8%+ in the last 25 sessions that was followed by more selling (12%+ over three sessions) and that price has not closed back above; also <i>still deep</i> (20%+ below the high, needs time) and <i>wide red candles</i> (three or more red days of 7%+ since the high). All three lose 30% of their quality score. Stocks in the 5% circuit band are left out entirely. <b>Trigger</b> is today\'s high, the buy-stop level for tomorrow; <b>Stop</b> is today\'s low, kept between 0.4 and 1.5 daily ranges; <b>Risk</b> is the gap between them.</li>'
        '<li><b>Quality (0-100):</b> tightness 25%, prior run 20%, EMA alignment and closeness 20%, time in a base 15%, shallow pullback 10%, volume dry-up 10%. '
        'Stocks still making new highs with no base, and stocks with a daily range under 3%, are marked down. '
        'Grade A+ is 75 or more, A is 65+, B is 55+.</li>'
        '<li><b>Rank score:</b> 65% quality, 20% relative strength, 15% theme strength, so a clean setup in a leading theme ranks highest.</li>'
        '<li><b>Prior run:</b> the sharpest move into the 60-session high, measured from the low of the 30 sessions before it. <b>Off high:</b> distance below the 60-session high. '
        '<b>Base:</b> sessions since that high. <b>Base vol / run vol:</b> average volume in the base against the run before it. <b>ADR:</b> average daily range over 20 sessions.</li>'
        '<li><b>Patterns:</b> flag after a 30%+ move; tight 5-day range; inside day; narrowest range in 7 days; at the 10, 20 or 50 EMA; turning up off the EMA (closes above the prior day\'s high after touching the 20 EMA); '
        'episodic pivot (6%+ gap on 3x volume in the last 5 sessions, still holding); breakout today (50-day closing high on 1.5x volume).</li></ul>')
js = ('<script>const $=i=>document.getElementById(i),k=$("k"),t=$("t"),q=$("q"),g=$("g"),sg=$("s"),'
      'f=()=>document.querySelectorAll("#b tr").forEach(r=>r.style.display=(!k.value||r.dataset.k.includes(k.value))&&(!t.value||r.dataset.t==t.value)'
      '&&(!g.value||r.dataset.g==g.value)&&(!sg.value||r.dataset.s==sg.value)&&(!q.value||r.textContent.toLowerCase().includes(q.value.toLowerCase()))?"":"none");'
      'k.onchange=t.onchange=g.onchange=sg.onchange=q.oninput=f;const p=new URLSearchParams(location.search).get("theme");'
      'if(p){if(![...t.options].some(o=>o.value==p))t.add(new Option(p,p));t.value=p;f()}'
      'const vis=()=>[...document.querySelectorAll("#b tr")].filter(r=>r.style.display!="none"),'
      'save=(name,text,type)=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click()},'
      'cell=c=>\'"\'+c.textContent.trim().replace(/"/g,\'""\')+\'"\',day=new Date().toISOString().slice(0,10);'
      '$("dx").onclick=()=>save("nse-setups-"+day+".csv","\\ufeff"+[[...document.querySelectorAll("thead th")].map(cell).join(",")]'
      '.concat(vis().map(r=>[...r.cells].map(cell).join(","))).join("\\n"),"text/csv");'
      '$("dt").onclick=()=>save("nse-setups-"+day+".txt",vis().map(r=>"NSE:"+r.cells[1].textContent.trim().replace(/[&-]/g,"_")).join(","),"text/plain")</script>')
(docs / "setups.html").write_text(page("NSE setups", "Setups", body, js))
# Fundamentals: setups joined with quarterly growth numbers (a separate section; the setup scoring is untouched)
fpath = DATA / "meta" / "fundamentals.csv"
if fpath.exists():
    fz = pd.read_csv(fpath, index_col=0)
    nf = Path(__file__).resolve().parent.parent / "config" / "fund_notes.json"
    notes = json.loads(nf.read_text()) if nf.exists() else {}
    m = pd.read_csv(DATA / "derived" / "setups.csv")
    m = m[m["grade"] != "C"].merge(fz, left_on="symbol", right_index=True, how="left")
    m["tf"] = 0.5 * m["rank_score"] + 0.5 * m["growth_score"]
    m["label"] = pd.cut(m["growth_score"], [-1, 50, 70, 101], labels=["Weak", "Good", "Strong"], right=False).astype(object).fillna("No data")
    m = m.sort_values(["tf", "rank_score"], ascending=False, na_position="last").reset_index(drop=True)
    nn = lambda v, f="{:.0f}", suf="": "&ndash;" if pd.isna(v) else f.format(v) + suf
    qlab = lambda q: "&ndash;" if not isinstance(q, str) or len(q) < 7 else pd.Timestamp(q).strftime("%b %Y")
    frows = "".join(
        f'<tr data-g="{r.label}" data-s="{r.stage}"><td>{i + 1}</td>'
        f'<td class="l"><b><a target="_blank" rel="noopener" href="{tv_link(r.symbol)}">{r.symbol}</a></b></td><td class="l">{r.theme}</td>' + (f'<td><button class="nb" data-n="{r.symbol}">Read</button></td>' if r.symbol in notes else '<td>&ndash;</td>') +
        f'<td><b>{nn(r.tf)}</b></td><td>{r.grade}</td><td class="l">{r.stage}</td><td>{nn(r.growth_score)}</td><td class="l">{r.label}</td>'
        f'<td class="l">{qlab(r.latest_q)}</td><td>{nn(r.rev0, "{:,.0f}")}</td><td>{nn(r.sales_yoy, "{:+.0f}", "%")}</td><td>{nn(r.sales_yoy_prev, "{:+.0f}", "%")}</td>'
        f'<td>{nn(r.ni0, "{:,.0f}")}</td><td>{"Turnaround" if r.turnaround is True else nn(r.profit_yoy, "{:+.0f}", "%")}</td>'
        f'<td>{nn(r.opm, "{:.0f}", "%")}</td><td>{nn(r.opm_yago, "{:.0f}", "%")}</td><td>{nn(r.roe * 100 if pd.notna(r.roe) else r.roe, "{:.0f}", "%")}</td>'
        f'<td>{nn(r.de / 100 if pd.notna(r.de) else r.de, "{:.1f}")}</td><td>{nn(r.pe)}</td></tr>' for i, r in enumerate(m.itertuples()))
    strong = int(((m["label"] == "Strong") & (m["stage"] == "Ready")).sum())
    fbody = (f'<p class="read">The same {len(m)} setups, joined with each company\'s latest quarterly numbers. {strong} are both Ready and Strong on growth. '
             'The idea is conviction: a clean setup in a company whose sales and profits are growing fast is easier to hold. Click a heading to sort.</p>'
             '<input id="q" placeholder="Search stock or theme"><select id="g"><option value="">All growth</option><option>Strong</option><option>Good</option><option>Weak</option><option>No data</option></select>'
             '<select id="s"><option value="">All stages</option><option>Ready</option><option>Triggered today</option><option>Building</option><option>Extended</option></select>'
             '<div class="tw"><table><thead><tr><th>#</th><th class="l">Stock</th><th class="l">Theme</th><th>Note</th><th>Techno-funda</th><th>Setup</th><th class="l">Stage</th><th>Growth score</th><th class="l">Growth</th>'
             '<th class="l">Quarter</th><th>Sales (cr)</th><th>Sales YoY</th><th>Prev qtr YoY</th><th>Profit (cr)</th><th>Profit YoY</th><th>Op. margin</th><th>Year ago</th><th>ROE</th><th>Debt/equity</th><th>P/E</th>'
             f'</tr></thead><tbody id="b">{frows}</tbody></table></div>'
             '<ul class="note"><li><b>Growth score (0-100):</b> sales growth year on year 30%, profit growth 30%, acceleration against the previous quarter 20%, operating margin against a year ago 20%. Strong is 70+, Good is 50+.</li>'
             '<li><b>Techno-funda</b> is the average of the setup rank score and the growth score.</li>'
             '<li><b>Source and limits:</b> figures come from Yahoo Finance and can be wrong, late, or a mix of standalone and consolidated. A stock showing an older quarter has not had its latest results loaded yet. Check the company\'s own filing before relying on a number.</li>'
             '<li><b>Notes</b> (the Read button) are written by hand from results releases, presentations and news coverage for shortlisted stocks only, with links. They are a starting point: confirm order book and guidance in the company filing. Stocks without a button have not been researched yet.</li></ul>'
             '<div id="dr" hidden><div class="dh"><b id="dt2"></b><button id="dx2">Close</button></div><div id="dbd"></div></div>'
             '<style>.nb{background:var(--acc,#2457d6);color:#fff;border:0;border-radius:6px;padding:3px 10px;cursor:pointer;font-size:12px}'
             '#dr{position:fixed;top:0;right:0;width:min(480px,100vw);height:100vh;overflow:auto;background:var(--card,#fff);color:var(--ink,#111);box-shadow:-6px 0 24px rgba(0,0,0,.25);padding:16px;z-index:50;font-size:14px;line-height:1.45}'
             '#dr[hidden]{display:none}#dr .dh{display:flex;justify-content:space-between;align-items:center;font-size:17px;margin-bottom:8px}'
             '#dr h4{margin:12px 0 2px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;opacity:.6}#dr p{margin:0}#dr .tk{background:rgba(36,87,214,.1);padding:8px;border-radius:8px;margin-top:12px}</style>')
    fjs = ('<script>const $=i=>document.getElementById(i),q=$("q"),g=$("g"),sg=$("s"),f=()=>document.querySelectorAll("#b tr").forEach(r=>r.style.display='
           '(!g.value||r.dataset.g==g.value)&&(!sg.value||r.dataset.s==sg.value)&&(!q.value||r.textContent.toLowerCase().includes(q.value.toLowerCase()))?"":"none");'
           'g.onchange=sg.onchange=q.oninput=f</script><script>const N=' + json.dumps(notes).replace("</", "<\\/") + ';'
           'const E=t=>String(t).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])),L=[["book","Order book"],["cover","Cover"],["guidance","Guidance"],["execution","Execution"],["driver","What is driving growth"],["risks","Risks"]];'
           'document.querySelectorAll(".nb").forEach(b=>b.onclick=()=>{const n=N[b.dataset.n];$("dt2").textContent=b.dataset.n;'
           '$("dbd").innerHTML="<p style=opacity:.6>"+E(n.asof)+"</p>"+L.map(([k,t])=>"<h4>"+t+"</h4><p>"+E(n[k])+"</p>").join("")+"<div class=tk><b>Read-through:</b> "+E(n.take)+"</div><h4>Sources</h4>"'
           '+n.src.map(s=>"<p><a target=_blank rel=noopener href=\'"+s[1]+"\'>"+E(s[0])+"</a></p>").join("");$("dr").hidden=false});'
           '$("dx2").onclick=()=>$("dr").hidden=true</script>')
    (docs / "fundamentals.html").write_text(page("NSE techno-funda", "Fundamentals", fbody, fjs))

# Journal: latest close for every NSE stock, and the page itself (trades stay in the visitor's browser)
px = load_prices(pd.Timestamp.today() - pd.Timedelta(days=12)).sort_values("date")
lastpx = px.groupby("symbol")["close"].last().round(2)
(docs / "prices.json").write_text(json.dumps({"date": px["date"].max().strftime("%d %b %Y"), "p": lastpx.to_dict()}, separators=(",", ":")))
jb = (Path(__file__).parent / "journal_body.html").read_text()
jbody, jscript = jb.split("<script>", 1)
(docs / "journal.html").write_text(page("Trade journal", "Journal", jbody, "<script>" + jscript).replace("close of " + day, "prices as of close of " + day))
print("site built:", len(t), "themes,", len(s), "setups")
