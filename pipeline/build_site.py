"""Add the Sectors and Setups pages and a shared navigation bar to the site in docs/."""
import re

import pandas as pd

from common import DATA

docs = DATA / "docs"
index = (docs / "index.html").read_text()
css = re.search(r"<style>.*?</style>", index, re.S).group(0).replace("</style>", """
nav{display:flex;gap:18px;margin:0 0 18px;font-weight:600}nav a{color:var(--ink2);text-decoration:none;padding-bottom:4px}
nav a.on{color:var(--ink);border-bottom:2px solid var(--s)}td.l,th.l{text-align:left}td.up{color:var(--ink)}td.sm{font-size:12.5px;color:var(--ink2)}
select,input{font:inherit;padding:6px 8px;border:1px solid var(--grid);border-radius:6px;background:var(--bg);color:var(--ink);margin:0 8px 12px 0}
main.wide{max-width:1180px}main.wide td,main.wide th{white-space:nowrap}main.wide td.sm.l{white-space:normal;min-width:220px}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--s);vertical-align:middle;margin-right:6px}</style>""")
day = re.search(r"close of ([^<]+)</h1>", index).group(1)


def nav(on):
    items = (("index.html", "Regime"), ("sectors.html", "Sectors"), ("setups.html", "Setups"))
    return "<nav>" + "".join(f'<a href="{h}"{" class=on" if t == on else ""}>{t}</a>' for h, t in items) + "</nav>"


def page(title, on, body, script=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{title}</title>{css}</head><body><main class="wide">'
            f'{nav(on)}<h1>{title} &middot; close of {day}</h1>{body}</main>{script}</body></html>')


if "<nav>" not in index:
    index = index.replace("</style>", css.split("</style>")[0].split("nav{")[1].join(["\nnav{", "</style>"]), 1) \
                 .replace("<main>", "<main>" + nav("Regime"), 1)
    (docs / "index.html").write_text(index)

t = pd.read_csv(DATA / "derived" / "themes.csv")
arrow = lambda d: "" if pd.isna(d) or d == 0 else (f"&#9650; {int(d)}" if d > 0 else f"&#9660; {int(-d)}")
rows = "".join(
    f'<tr><td>{r["rank"]}</td><td class="l"><b>{r.theme}</b></td><td class="sm">{arrow(r.rank_change)}</td>'
    f'<td class="l"><span class="bar" style="width:{0.6 * r.strength:.0f}px"></span>{r.strength:.0f}</td>'
    f'<td>{r.r1w:+.1f}%</td><td>{r.r1m:+.1f}%</td><td>{r.r3m:+.1f}%</td><td>{r.above50:.0f}%</td>'
    f'<td>{r.leaders}/{r.n}</td><td>{r.setups}</td><td class="l sm">{r.top}</td></tr>' for _, r in t.iterrows())
body = ('<p class="read">Themes ranked by strength: a blend of the median stock\'s 1-week (20%), 1-month (40%) and '
        '3-month (40%) return, compared across themes. The arrow shows places gained or lost against a month ago.</p>'
        '<div class="tw"><table><thead><tr><th>#</th><th class="l">Theme</th><th>vs 1m ago</th><th class="l">Strength</th>'
        '<th>1 week</th><th>1 month</th><th>3 months</th><th>&gt;50-day</th><th>RS 80+ / stocks</th><th>Setups</th>'
        f'<th class="l">Highest RS</th></tr></thead><tbody>{rows}</tbody></table></div>'
        '<ul class="note"><li>Only liquid stocks count (median traded value Rs 1 crore+, price Rs 40+); themes need five or more.</li>'
        '<li>Returns are the median member\'s, so one large mover cannot carry a theme.</li>'
        '<li>RS is a 1-99 rank of each stock\'s blended 3, 6 and 12-month return against all liquid stocks.</li></ul>')
(docs / "sectors.html").write_text(page("NSE sector strength", "Sectors", body))

s = pd.read_csv(DATA / "derived" / "setups.csv")
rank = t.set_index("theme")["rank"]
s["trank"] = s["theme"].map(rank)
s = s.sort_values(["trank", "rs"], ascending=[True, False], na_position="last")
rows = "".join(
    f'<tr data-k="{r.setup}" data-t="{r.theme}"><td class="l"><b>{r.symbol}</b></td><td class="l">{r.theme}</td>'
    f'<td>{"" if pd.isna(r.trank) else int(r.trank)}</td><td class="l">{r.setup}</td><td>{r.rs}</td><td>{r.close:,.1f}</td>'
    f'<td>{r.vs_ema20:+.1f}%</td><td>{r.vs_ema50:+.1f}%</td><td>{r.from_high:.0f}%</td><td>{r.range10:.0f}%</td>'
    f'<td>{r.turnover_cr:,.0f}</td></tr>' for r in s.itertuples())
kinds = "".join(f"<option>{k}</option>" for k in sorted(s["setup"].unique()))
themes = "".join(f"<option>{k}</option>" for k in s.drop_duplicates("theme")["theme"])
body = (f'<p class="read">{len(s)} candidates in {s["theme"].nunique()} themes, strongest themes first. Every stock is liquid, '
        'above Rs 40, above its 200-day average and has RS of 70 or more. These are shortlists for chart review, not signals.</p>'
        f'<select id="k"><option value="">All setups</option>{kinds}</select><select id="t"><option value="">All themes</option>{themes}</select>'
        '<div class="tw"><table><thead><tr><th class="l">Stock</th><th class="l">Theme</th><th>Theme rank</th><th class="l">Setup</th>'
        '<th>RS</th><th>Close</th><th>vs 20 EMA</th><th>vs 50 EMA</th><th>From 52w high</th><th>10-day range</th>'
        f'<th>Turnover (cr)</th></tr></thead><tbody id="b">{rows}</tbody></table></div>'
        '<ul class="note"><li><b>Pullback to 20 EMA:</b> 10 &gt; 20 &gt; 50 EMA &gt; 200-day, the day\'s low within 1.5% of the 20 EMA, close holding it.</li>'
        '<li><b>Pullback to 50 EMA:</b> 50 EMA above the 200-day, the low within 2% of the 50 EMA, close holding it.</li>'
        '<li><b>Tight near highs:</b> within 10% of the 52-week high, 10-day range under 8% and under 60% of the 40-day range, volume drying up.</li></ul>')
js = ('<script>const k=document.getElementById("k"),t=document.getElementById("t"),f=()=>document.querySelectorAll("#b tr")'
      '.forEach(r=>r.style.display=(!k.value||r.dataset.k==k.value)&&(!t.value||r.dataset.t==t.value)?"":"none");'
      'k.onchange=t.onchange=f</script>')
(docs / "setups.html").write_text(page("NSE setups", "Setups", body, js))
print("site built:", len(t), "themes,", len(s), "setups")
