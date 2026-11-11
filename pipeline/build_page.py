"""Build the daily page (docs/index.html on the data branch) from derived/regime.csv."""
import json

import pandas as pd

from common import DATA
from regime import ZONES

r = pd.read_csv(DATA / "derived" / "regime.csv", parse_dates=["date"]).set_index("date")
last, prev = r.iloc[-1], r.iloc[-6]
PARTS = [("thrust", "Thrust", "Share of +4% days vs -4% days, last 10 sessions"),
         ("above20", "Short-term participation", "Stocks above their 20-day average"),
         ("above50", "Medium-term participation", "Stocks above their 50-day average"),
         ("highs", "Highs vs lows", "52-week highs as a share of highs plus lows, last 20 sessions"),
         ("follow", "Follow-through", "Recent breakouts still above their breakout close")]
weak = min(PARTS, key=lambda p: last[p[0]])
strong = max(PARTS, key=lambda p: last[p[0]])
chg = last["score"] - prev["score"]
reading = (f"The score is {last['score']:.0f}, {'up' if chg >= 0 else 'down'} {abs(chg):.0f} points in five sessions. "
           f"Strongest part: {strong[1].lower()} ({last[strong[0]]:.0f}). "
           f"Weakest part: {weak[1].lower()} ({last[weak[0]]:.0f}).")
hist = r.tail(250)
data = {"dates": [d.strftime("%d %b %Y") for d in hist.index], "score": [round(float(v), 1) for v in hist["score"]],
        "zones": [[a, b] for a, b in ZONES]}
icon = {"Weak": "&#9660;", "Mixed": "&#9679;", "Favourable": "&#9650;"}[last["zone"]]
meters = "".join(
    f'<div class="m"><div class="mh"><span>{name}</span><span class="v">{last[k]:.0f}'
    f'<small>{last[k] - prev[k]:+.0f}</small></span></div>'
    f'<div class="track"><div class="fill" style="width:{max(0, min(100, last[k])):.1f}%"></div></div>'
    f'<div class="d">{desc}</div></div>' for k, name, desc in PARTS)
rows = "".join(
    f"<tr><td>{d:%a %d %b}</td><td>{x.score:.0f}</td><td>{x.zone}</td><td>{x.up4:.0f}</td><td>{x.down4:.0f}</td>"
    f"<td>{x.above20:.0f}%</td><td>{x.above50:.0f}%</td><td>{x.above200:.0f}%</td></tr>"
    for d, x in r.tail(10).iloc[::-1].iterrows())
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NSE market regime</title>
<style>
:root{{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--mut:#898781;--grid:#e1e0d9;--s:#2a78d6;--card:#f4f4f1}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--mut:#898781;--grid:#2c2c2a;--s:#5b9be8;--card:#232321}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:880px;margin:0 auto;padding:24px 16px 48px}}h1{{font-size:15px;font-weight:600;color:var(--ink2);margin:0}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);margin:36px 0 12px;font-weight:600}}
.hero{{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;margin:8px 0 4px}}.num{{font-size:72px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums}}
.zone{{font-size:22px;font-weight:600}}.sub{{color:var(--ink2)}}.read{{margin:12px 0 0;max-width:62ch}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
.m{{background:var(--card);border-radius:10px;padding:12px 14px}}.mh{{display:flex;justify-content:space-between;gap:10px;font-weight:600}}.v{{white-space:nowrap}}
.v{{font-variant-numeric:tabular-nums}}.v small{{color:var(--mut);font-weight:400;margin-left:6px}}
.track{{height:8px;background:var(--grid);border-radius:4px;margin:8px 0 6px;overflow:hidden}}.fill{{height:100%;background:var(--s);border-radius:4px}}
.d{{font-size:12.5px;color:var(--ink2)}}#chart{{position:relative}}svg{{display:block;width:100%;height:auto}}
#tip{{position:absolute;pointer-events:none;background:var(--ink);color:var(--bg);padding:4px 8px;border-radius:6px;font-size:12.5px;white-space:nowrap;display:none;transform:translate(-50%,-130%)}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{text-align:right;padding:6px 8px;border-bottom:1px solid var(--grid)}}
th{{color:var(--mut);font-weight:600;font-size:12.5px}}th:first-child,td:first-child,th:nth-child(3),td:nth-child(3){{text-align:left}}
.tw{{overflow-x:auto}}.note{{color:var(--ink2);font-size:13.5px;max-width:70ch}}.note li{{margin:4px 0}}
</style></head><body><main>
<h1>NSE market regime &middot; close of {r.index[-1]:%A %d %B %Y}</h1>
<div class="hero"><div class="num">{last['score']:.0f}</div><div><div class="zone">{icon} {last['zone']}</div>
<div class="sub">{chg:+.0f} vs five sessions ago &middot; {last['universe']:.0f} liquid stocks</div></div></div>
<p class="read">{reading}</p>
<h2>The five parts (each 0-100, change over five sessions)</h2><div class="grid">{meters}</div>
<h2>Score, last 250 sessions</h2><div id="chart"><svg id="svg" viewBox="0 0 860 300" role="img" aria-label="Regime score over the last 250 sessions"></svg><div id="tip"></div></div>
<h2>Last 10 sessions</h2><div class="tw"><table><thead><tr><th>Session</th><th>Score</th><th>Zone</th><th>Up 4%+</th><th>Down 4%+</th><th>&gt;20-day</th><th>&gt;50-day</th><th>&gt;200-day</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>How to read this</h2><ul class="note">
<li><b>Favourable (55+):</b> in the 2019-2026 backtest, mechanical breakout and pullback entries did about 0.4 points better per trade here than below 55, in both halves of the test.</li>
<li><b>Mixed (40-55) and Weak (under 40):</b> results were worse on average, though the few setups that appear in deep washouts held up well.</li>
<li><b>No leverage tier:</b> readings above 70 were not better than 55-70, so the score does not say when to press.</li>
<li>The score is the plain average of the five parts across liquid NSE stocks (median traded value of Rs 1 crore or more). It describes conditions; it is not a forecast or advice.</li></ul>
</main><script>
const D={json.dumps(data)},W=860,H=300,L=36,R=40,T=14,B=26,n=D.score.length,ns="http://www.w3.org/2000/svg";
const x=i=>L+i*(W-L-R)/(n-1),y=v=>T+(100-v)*(H-T-B)/100,svg=document.getElementById("svg"),tip=document.getElementById("tip");
const el=(t,a,txt)=>{{const e=document.createElementNS(ns,t);for(const k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;svg.appendChild(e);return e}};
[0,25,50,75,100].forEach(v=>{{el("line",{{x1:L,x2:W-R,y1:y(v),y2:y(v),stroke:"var(--grid)","stroke-width":1}});el("text",{{x:L-8,y:y(v)+4,"text-anchor":"end","font-size":11,fill:"var(--mut)"}},v)}});
D.zones.slice(1).forEach(z=>{{el("line",{{x1:L,x2:W-R,y1:y(z[0]),y2:y(z[0]),stroke:"var(--mut)","stroke-width":1,"stroke-dasharray":"4 4"}});el("text",{{x:L+6,y:y(z[0])-5,"font-size":11,fill:"var(--ink2)"}},z[1]+" "+z[0]+"+")}});
[0,Math.round(n/4),Math.round(n/2),Math.round(3*n/4),n-1].forEach(i=>el("text",{{x:x(i),y:H-6,"text-anchor":i==n-1?"end":i==0?"start":"middle","font-size":11,fill:"var(--mut)"}},D.dates[i].slice(3)));
el("path",{{d:D.score.map((v,i)=>(i?"L":"M")+x(i).toFixed(1)+" "+y(v).toFixed(1)).join(""),fill:"none",stroke:"var(--s)","stroke-width":2,"stroke-linejoin":"round"}});
el("circle",{{cx:x(n-1),cy:y(D.score[n-1]),r:4,fill:"var(--s)",stroke:"var(--bg)","stroke-width":2}});
el("text",{{x:x(n-1)+8,y:y(D.score[n-1])+4,"font-size":13,"font-weight":600,fill:"var(--ink)"}},Math.round(D.score[n-1]));
const cl=el("line",{{y1:T,y2:H-B,stroke:"var(--mut)","stroke-width":1,visibility:"hidden"}}),dot=el("circle",{{r:4,fill:"var(--s)",stroke:"var(--bg)","stroke-width":2,visibility:"hidden"}});
const hit=el("rect",{{x:L,y:T,width:W-L-R,height:H-T-B,fill:"transparent"}});
hit.addEventListener("pointermove",e=>{{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)*W/b.width,i=Math.max(0,Math.min(n-1,Math.round((px-L)/((W-L-R)/(n-1)))));
cl.setAttribute("x1",x(i));cl.setAttribute("x2",x(i));cl.setAttribute("visibility","visible");dot.setAttribute("cx",x(i));dot.setAttribute("cy",y(D.score[i]));dot.setAttribute("visibility","visible");
tip.style.display="block";tip.style.left=(x(i)*b.width/W)+"px";tip.style.top=(y(D.score[i])*b.height/H)+"px";tip.textContent=D.dates[i]+": "+D.score[i]}});
hit.addEventListener("pointerleave",()=>{{cl.setAttribute("visibility","hidden");dot.setAttribute("visibility","hidden");tip.style.display="none"}});
</script></body></html>"""
(DATA / "docs").mkdir(exist_ok=True)
(DATA / "docs" / "index.html").write_text(html)
(DATA / "docs" / ".nojekyll").write_text("")
print("page built:", r.index[-1].date(), last["score"], last["zone"])
