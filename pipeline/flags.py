"""Warning flags for every stock, for the journal's open-position cards. Written to docs/flags.json.
Each stock: e = [EMA10, EMA20, EMA50], f = [[severity 1-3, text], ...], r = next results date or ''."""
import json

import numpy as np
import pandas as pd

from common import DATA, load_prices


def build(docs):
    px = load_prices(pd.Timestamp.today() - pd.Timedelta(days=260)).sort_values(["symbol", "date"])
    ep = DATA / "meta" / "earnings.csv"
    er = pd.read_csv(ep, index_col=0, parse_dates=["next_result"])["next_result"] if ep.exists() else pd.Series(dtype="datetime64[ns]")
    out = {}
    for s, g in px.groupby("symbol"):
        if len(g) < 55:
            continue
        c, o, h, l, v = (g[k].astype(float).to_numpy() for k in ("close", "open", "high", "low", "volume"))
        cs = pd.Series(c)
        e10, e20, e50 = (cs.ewm(span=n, adjust=False).mean().to_numpy() for n in (10, 20, 50))
        i, f = len(c) - 1, []
        avgv = v[i - 50:i].mean() or 1
        ret = c[i] / c[i - 1] - 1
        below = lambda e: int(next((k for k in range(len(c)) if c[i - k] >= e[i - k]), len(c)))
        if c[i] < e50[i]:
            f.append([3, f"Closed below the 50 EMA ({e50[i]:.2f}); the trend has broken"])
        elif c[i] < e20[i]:
            f.append([2, f"Closed below the 20 EMA ({e20[i]:.2f}){', ' + str(below(e20)) + ' sessions in a row' if below(e20) > 1 else ''}"])
        elif c[i] < e10[i]:
            f.append([1, f"Closed below the 10 EMA ({e10[i]:.2f}){', ' + str(below(e10)) + ' sessions in a row' if below(e10) > 1 else ''}"])
        elif l[i] <= e20[i] * 1.005 and c[i] >= e20[i]:
            f.append([1, f"Tested the 20 EMA ({e20[i]:.2f}) today and held"])
        if v[i] >= 2.5 * avgv and c[i] > e10[i] * 1.10 and (ret > 0.06 or c[i] < l[i] + 0.4 * (h[i] - l[i])):
            f.append([3, f"Climax volume ({v[i] / avgv:.1f}x average) after an extended run; a common top"])
        elif v[i] >= 2 * avgv and ret <= -0.03:
            f.append([3, f"Heavy selling: down {ret * 100:.1f}% on {v[i] / avgv:.1f}x average volume"])
        if ret <= -0.05:
            f.append([2, f"Big red candle: {ret * 100:.1f}% today"])
        if o[i] < c[i - 1] * 0.97 and c[i] < o[i]:
            f.append([2, f"Gapped down {(o[i] / c[i - 1] - 1) * 100:.1f}% and sold off"])
        if c[i] < c[i - 1] < c[i - 2] < c[i - 3]:
            f.append([1, "Three lower closes in a row"])
        if c[i] > e20[i] * 1.20:
            f.append([1, f"Extended: {(c[i] / e20[i] - 1) * 100:.0f}% above the 20 EMA; consider trailing the stop"])
        d = er.get(s, pd.NaT)
        out[s] = {"e": [round(float(x), 2) for x in (e10[i], e20[i], e50[i])], "f": f, "r": d.strftime("%Y-%m-%d") if pd.notna(d) else ""}
    (docs / "flags.json").write_text(json.dumps({"date": px["date"].max().strftime("%Y-%m-%d"), "s": out}, separators=(",", ":")))
    return len(out)
