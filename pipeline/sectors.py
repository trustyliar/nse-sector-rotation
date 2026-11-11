"""Stock relative strength, theme (sector) rankings and setup scans. Run nightly after regime.py."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "config")
from common import DATA, load_prices
from regime import wide, MIN_TURNOVER
from themes import theme

w = wide(load_prices(pd.Timestamp.today() - pd.Timedelta(days=560)))
c, h, l, v, tv = w["close"], w["high"], w["low"], w["volume"], w["turnover"]
cl = pd.read_csv(DATA / "meta" / "classification.csv")
th = pd.Series({r.symbol: theme(r.symbol, r.yahoo_industry, r.name) for r in cl.itertuples()})
mcap = cl.set_index("symbol")["mcap_cr"]
med_tv = tv.rolling(20, min_periods=10).median()
liquid = (med_tv >= MIN_TURNOVER) & (c >= 40) & c.notna()


def rs_rating(at=-1):
    """1-99 percentile of blended 3/6/12-month return among liquid stocks."""
    cc = c.iloc[: len(c) + at + 1] if at != -1 else c
    parts = [(cc.iloc[-1] / cc.shift(n).iloc[-1] - 1) for n in (63, 126, 252)]
    blend = (0.4 * parts[0] + 0.3 * parts[1].fillna(parts[0]) + 0.3 * parts[2].fillna(parts[1]).fillna(parts[0]))
    blend = blend[liquid.iloc[len(cc) - 1]]
    return (blend.rank(pct=True) * 98 + 1).round()


def theme_table(at=-1):
    i = len(c) + at
    liq = liquid.iloc[i]
    syms = liq[liq].index
    d = pd.DataFrame({"theme": th.reindex(syms), "rs": rs_rating(at).reindex(syms)})
    for n, k in ((5, "r1w"), (21, "r1m"), (63, "r3m")):
        d[k] = (c.iloc[i] / c.iloc[i - n] - 1).reindex(syms) * 100
    d["a50"] = (c.iloc[i] > c.iloc[i - 49: i + 1].mean()).reindex(syms)
    g = d.groupby("theme")
    t = pd.DataFrame({"n": g.size(), "r1w": g["r1w"].median(), "r1m": g["r1m"].median(), "r3m": g["r3m"].median(),
                      "above50": 100 * g["a50"].mean(), "leaders": g["rs"].apply(lambda s: (s >= 80).sum()),
                      "avg_rs": g["rs"].mean()})
    t = t[(t["n"] >= 5) & (t.index != "Unclassified")]
    pr = lambda s: s.rank(pct=True)
    t["strength"] = (100 * (0.2 * pr(t["r1w"]) + 0.4 * pr(t["r1m"]) + 0.4 * pr(t["r3m"]))).round(0)
    t["rank"] = t["strength"].rank(ascending=False, method="first").astype(int)
    return t.sort_values("rank"), d


now, stocks = theme_table(-1)
then, _ = theme_table(-22)
now["rank_1m_ago"] = then["rank"].reindex(now.index)
now["rank_change"] = now["rank_1m_ago"] - now["rank"]
stocks = stocks.sort_values("rs", ascending=False)
now["top"] = [", ".join(stocks[stocks["theme"] == t].index[:4]) for t in now.index]

# ---- setups, on leaders only: liquid, price >= 40, above 200-day average, RS >= 70
e10, e20, e50 = (c.ewm(span=n, min_periods=n).mean().iloc[-1] for n in (10, 20, 50))
last, lo, hi = c.iloc[-1], l.iloc[-1], h.iloc[-1]
ma200 = c.rolling(200, min_periods=150).mean().iloc[-1]
hi52 = h.rolling(250, min_periods=120).max().iloc[-1]
rng10 = h.tail(10).max() / l.tail(10).min() - 1
rng40 = h.tail(40).max() / l.tail(40).min() - 1
vdry = v.tail(10).mean() / v.tail(50).mean()
rs = stocks["rs"].reindex(c.columns)
base = liquid.iloc[-1] & (last > ma200) & (rs >= 70)
up = (e10 > e20) & (e20 > e50) & (e50 > ma200)
S = {"Pullback to 20 EMA": base & up & (lo <= e20 * 1.015) & (last >= e20 * 0.99) & (last <= e20 * 1.04),
     "Pullback to 50 EMA": base & (e50 > ma200) & (lo <= e50 * 1.02) & (last >= e50 * 0.99) & (last <= e50 * 1.04),
     "Tight near highs": base & up & (last >= hi52 * 0.90) & (rng10 <= 0.08) & (rng10 <= 0.6 * rng40) & (vdry < 0.9)}
rows = []
for kind, m in S.items():
    for s in m[m].index:
        rows.append({"symbol": s, "theme": th.get(s, ""), "setup": kind, "close": round(float(last[s]), 2),
                     "rs": int(rs[s]), "from_high": round(100 * (last[s] / hi52[s] - 1), 1),
                     "vs_ema20": round(100 * (last[s] / e20[s] - 1), 1), "vs_ema50": round(100 * (last[s] / e50[s] - 1), 1),
                     "range10": round(100 * rng10[s], 1), "turnover_cr": round(med_tv.iloc[-1][s] / 1e7, 1),
                     "mcap_cr": mcap.get(s)})
setups = pd.DataFrame(rows).sort_values(["rs", "symbol"], ascending=[False, True]) if rows else pd.DataFrame()
now["setups"] = setups.groupby("theme").symbol.nunique().reindex(now.index).fillna(0).astype(int) if len(setups) else 0
(DATA / "derived").mkdir(exist_ok=True)
now.round(1).to_csv(DATA / "derived" / "themes.csv")
setups.to_csv(DATA / "derived" / "setups.csv", index=False)
stocks.assign(close=last.reindex(stocks.index).round(2)).to_csv(DATA / "derived" / "stocks.csv")
print(now.head(12)[["n", "r1w", "r1m", "r3m", "above50", "leaders", "rank_change", "setups", "top"]].round(1).to_string())
print("themes", len(now), "| setups", len(setups), setups["setup"].value_counts().to_dict() if len(setups) else "")
