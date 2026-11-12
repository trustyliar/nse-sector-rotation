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

# ---- setups: Kullamagi-style quality score on leaders (liquid, price >= 40, above 200-day, RS >= 70)
# What is scored: a strong prior move, an orderly shallow consolidation, tightening ranges,
# price riding the 10/20 EMA, and volume drying up. Tags describe what the chart is doing today.
o = load_prices(pd.Timestamp.today() - pd.Timedelta(days=40)).pivot(index="date", columns="symbol", values="open").reindex(columns=c.columns)
e10, e20, e50 = (c.ewm(span=n, min_periods=n).mean().iloc[-1] for n in (10, 20, 50))
last, lo, hi = c.iloc[-1], l.iloc[-1], h.iloc[-1]
ma200 = c.rolling(200, min_periods=150).mean().iloc[-1]
hi52 = h.rolling(250, min_periods=120).max().iloc[-1]
adr = (h / l - 1).tail(20).mean()
rng = lambda n: h.tail(n).max() / l.tail(n).min() - 1
rng5, rng10, rng30 = rng(5), rng(10), rng(30)
vdry = v.tail(5).mean() / v.tail(50).mean()
Hh, Ll = h.tail(120).to_numpy(), l.tail(120).to_numpy()
runup, since = {}, {}
for j, sym in enumerate(c.columns):                    # sharpest run: low within 30 sessions before the 60-session high
    col = Hh[60:, j]
    if np.isnan(col).all():
        continue
    pos = 60 + int(np.nanargmax(col))
    low = np.nanmin(Ll[pos - 30: pos + 1, j]) if not np.isnan(Ll[pos - 30: pos + 1, j]).all() else np.nan
    runup[sym], since[sym] = Hh[pos, j] / low - 1, 119 - pos
runup, since = pd.Series(runup).reindex(c.columns), pd.Series(since).reindex(c.columns)
hi60 = h.tail(60).max()
depth = 1 - last / hi60
clip = lambda x: x.clip(0, 1)
sc_move = clip((runup - 0.15) / 0.60)
sc_tight = 0.7 * clip((3.2 - rng5 / adr) / 1.9) + 0.3 * clip((0.75 - rng10 / rng30) / 0.40)
align = ((last >= e10).astype(int) + (e10 >= e20) + (e20 >= e50) + (e50 >= ma200)) / 4
near = pd.concat([(last / e10 - 1).abs(), (last / e20 - 1).abs()], axis=1).min(axis=1)
sc_trend = 0.6 * align + 0.4 * clip(1 - near / (1.5 * adr))
sc_dry = clip((1.1 - vdry) / 0.6)
sc_depth = clip((0.25 - depth) / 0.20)
# A setup needs a base: time spent going sideways after the high. None = still running (no setup).
sc_base = (clip((since - 2) / 4) * clip((55 - since) / 20)).fillna(0)
quality = 100 * (0.20 * sc_move + 0.25 * sc_tight + 0.20 * sc_trend + 0.10 * sc_dry + 0.10 * sc_depth + 0.15 * sc_base)
quality = quality * (0.5 + 0.5 * sc_base.clip(lower=0.0)) * clip(adr / 0.03).clip(lower=0.7)   # no base or a sleepy stock: marked down
rs = stocks["rs"].reindex(c.columns)
tstr = th.reindex(c.columns).map(now["strength"]).fillna(50)
rank_score = 0.65 * quality + 0.20 * rs + 0.15 * tstr
base = liquid.iloc[-1] & (last > ma200) & (rs >= 70) & (adr >= 0.02)
up = (e10 >= e20) & (e20 >= e50)
day_rng = h / l - 1
gap = (o / c.shift(1) - 1).tail(5)
epday = (gap >= 0.06) & (v.tail(5) >= 3 * v.shift(1).rolling(50, min_periods=30).mean().tail(5))
ep_low = l.tail(5).where(epday).min()
TAGS = {
    "Flag after big move": (runup >= 0.30) & since.between(4, 40) & (depth <= 0.20) & (last >= e20),
    "Tight range": up & (rng5 <= 1.7 * adr) & (depth <= 0.20) & (since >= 4),
    "Inside day": up & (hi <= h.iloc[-2]) & (lo >= l.iloc[-2]) & (depth <= 0.20),
    "Narrowest in 7": up & (day_rng.iloc[-1] <= day_rng.tail(7).min()) & (depth <= 0.20),
    "At 10 EMA": up & (lo <= e10 * (1 + 0.4 * adr)) & (last >= e10 * 0.995) & (last <= e10 * (1 + adr)),
    "At 20 EMA": up & (lo <= e20 * (1 + 0.4 * adr)) & (last >= e20 * 0.99) & (last <= e20 * (1 + adr)),
    "At 50 EMA": (e50 > ma200) & (lo <= e50 * (1 + 0.5 * adr)) & (last >= e50 * 0.99) & (last <= e50 * (1 + 1.2 * adr)),
    "Episodic pivot": epday.any() & (last >= ep_low),
    "Breakout today": (last > c.shift(1).rolling(50, min_periods=50).max().iloc[-1]) & (v.iloc[-1] >= 1.5 * v.shift(1).rolling(50, min_periods=30).mean().iloc[-1]),
    "Volume dry-up": (vdry <= 0.6) & (depth <= 0.20),
}
ACTION = [k for k in TAGS if k != "Volume dry-up"]
tagdf = pd.DataFrame({k: m.reindex(c.columns).fillna(False).astype(bool) for k, m in TAGS.items()})
cand = base & tagdf[ACTION].any(axis=1)
rows = []
for s in cand[cand].index:
    q = float(quality[s])
    rows.append({"symbol": s, "theme": th.get(s, ""), "rank_score": round(float(rank_score[s]), 1), "quality": round(q, 1),
                 "grade": "A+" if q >= 75 else "A" if q >= 65 else "B" if q >= 55 else "C",
                 "tags": "; ".join(k for k in TAGS if tagdf.at[s, k]), "setup": "; ".join(k for k in TAGS if tagdf.at[s, k]),
                 "rs": int(rs[s]), "close": round(float(last[s]), 2), "adr": round(100 * adr[s], 1),
                 "runup": round(100 * runup[s], 0), "depth": round(100 * depth[s], 1), "range5": round(100 * rng5[s], 1),
                 "vs_ema10": round(100 * (last[s] / e10[s] - 1), 1), "vs_ema20": round(100 * (last[s] / e20[s] - 1), 1),
                 "vol_ratio": round(float(vdry[s]), 2), "turnover_cr": round(med_tv.iloc[-1][s] / 1e7, 1)})
setups = pd.DataFrame(rows).sort_values("rank_score", ascending=False) if rows else pd.DataFrame()
now["setups"] = (setups[setups["grade"].isin(["A+", "A"])].groupby("theme").symbol.nunique().reindex(now.index).fillna(0).astype(int)
                 if len(setups) else 0)
(DATA / "derived").mkdir(exist_ok=True)
now.round(1).to_csv(DATA / "derived" / "themes.csv")
setups.to_csv(DATA / "derived" / "setups.csv", index=False)
stocks.assign(close=last.reindex(stocks.index).round(2)).to_csv(DATA / "derived" / "stocks.csv")
print(now.head(12)[["n", "r1w", "r1m", "r3m", "above50", "leaders", "rank_change", "setups", "top"]].round(1).to_string())
print("themes", len(now), "| setups", len(setups), setups["grade"].value_counts().to_dict(), tagdf[cand].sum().to_dict())
