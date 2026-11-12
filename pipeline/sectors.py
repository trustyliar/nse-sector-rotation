"""Stock relative strength, theme (sector) rankings and setup scans. Run nightly after regime.py."""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "config")
from common import DATA, load_prices
from regime import wide, MIN_TURNOVER
from themes import theme

ASOF = os.environ.get("ASOF")                      # research: score the market as of a past date
END = pd.Timestamp(ASOF) if ASOF else pd.Timestamp.today()
OUT = Path(os.environ.get("OUT_DIR", DATA / "derived"))
w = {k: x.loc[:END] for k, x in wide(load_prices(END - pd.Timedelta(days=560))).items()}
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
o = load_prices(END - pd.Timedelta(days=50)).pivot(index="date", columns="symbol", values="open").loc[:END].reindex(columns=c.columns)
e10, e20, e50 = (c.ewm(span=n, min_periods=n).mean().iloc[-1] for n in (10, 20, 50))
last, lo, hi = c.iloc[-1], l.iloc[-1], h.iloc[-1]
ma200 = c.rolling(200, min_periods=150).mean().iloc[-1]
hi52 = h.rolling(250, min_periods=120).max().iloc[-1]
adr = (h / l - 1).tail(20).mean()
rng = lambda n: h.tail(n).max() / l.tail(n).min() - 1
rng5, rng10, rng30 = rng(5), rng(10), rng(30)
vdry = v.tail(5).mean() / v.tail(50).mean()
Hh, Ll, Vv = h.tail(120).to_numpy(), l.tail(120).to_numpy(), v.tail(120).to_numpy()
runup, since, basevol = {}, {}, {}
for j, sym in enumerate(c.columns):                    # sharpest run: low within 30 sessions before the 60-session high
    col = Hh[60:, j]
    if np.isnan(col).all():
        continue
    pos = 60 + int(np.nanargmax(col))
    low = np.nanmin(Ll[pos - 30: pos + 1, j]) if not np.isnan(Ll[pos - 30: pos + 1, j]).all() else np.nan
    runup[sym], since[sym] = Hh[pos, j] / low - 1, 119 - pos
    if 119 - pos >= 3:                                  # volume in the base against volume in the run before it
        basevol[sym] = np.nanmean(Vv[pos + 1:, j]) / np.nanmean(Vv[pos - 30: pos + 1, j])
runup, since = pd.Series(runup).reindex(c.columns), pd.Series(since).reindex(c.columns)
hi60 = h.tail(60).max()
depth = 1 - last / hi60
clip = lambda x: x.clip(0, 1)
sc_move = clip((runup - 0.15) / 0.45)
crng5 = c.tail(5).max() / c.tail(5).min() - 1          # tightness of closes: one shakeout bar should not hide a tight base
sc_tight = 0.35 * clip((3.2 - rng5 / adr) / 1.9) + 0.35 * clip((1.6 - crng5 / adr) / 1.1) + 0.3 * clip((0.75 - rng10 / rng30) / 0.40)
E20 = c.ewm(span=20, min_periods=20).mean()
rising20 = E20.iloc[-1] > E20.iloc[-6]
align = ((last >= e20 * (1 - 0.5 * adr)).astype(int) + (e10 >= e20) + (e20 >= e50) + (e50 >= ma200) + rising20) / 5
near = pd.concat([(last / e10 - 1).abs(), (last / e20 - 1).abs()], axis=1).min(axis=1)   # the EMAs have caught up with price
sc_trend = 0.6 * align + 0.4 * clip(1 - near / (1.5 * adr))
basevol = pd.Series(basevol).reindex(c.columns)
sc_dry = clip((1.0 - basevol.fillna(vdry)) / 0.6)
sc_depth = clip((0.25 - depth) / 0.20)
# A setup needs a base: time spent going sideways after the high. None = still running (no setup).
sc_base = (clip((since - 1) / 3) * clip((50 - since) / 20)).fillna(0)   # full credit for a 4-30 session base; none while still at the high
quality = 100 * (0.20 * sc_move + 0.25 * sc_tight + 0.20 * sc_trend + 0.10 * sc_dry + 0.10 * sc_depth + 0.15 * sc_base)
quality = quality * (0.5 + 0.5 * sc_base.clip(lower=0.0)) * clip(adr / 0.03).clip(lower=0.7)   # no base or a sleepy stock: marked down
# Overhead supply: a large red candle in the last 25 sessions that was FOLLOWED by more selling (three-session
# fall of 12%+ or two daily ranges) and that price has not yet closed back above. A big red candle that
# stabilised at once is normal in good bases and is not flagged (checked against the trader's past winners).
Ot, Ct = o.reindex(c.index).tail(25), c.tail(25)
thr = pd.concat([1.3 * adr, pd.Series(0.08, index=adr.index)], axis=1).max(axis=1)
prev = c.shift(1)
bad = (Ct / Ot - 1).le(-thr, axis=1) | c.pct_change(fill_method=None).tail(25).le(-thr, axis=1)
leg3 = (c.shift(-2).ffill() / prev - 1).tail(25)          # fall from the close before the candle to two sessions after it
bad = bad & leg3.le(-pd.concat([2 * adr, pd.Series(0.12, index=adr.index)], axis=1).max(axis=1), axis=1)
supply = pd.Series(False, index=c.columns)
for sym in bad.columns[bad.any()]:
    day = bad.index[bad[sym]][-1]
    ref = max(Ot.at[day, sym], prev.at[day, sym]) if pd.notna(Ot.at[day, sym]) else prev.at[day, sym]
    supply[sym] = bool(last[sym] < ref)
quality = quality * (1 - 0.3 * supply)
rs = stocks["rs"].reindex(c.columns)
tstr = th.reindex(c.columns).map(now["strength"]).fillna(50)
rank_score = 0.65 * quality + 0.20 * rs + 0.15 * tstr
base = liquid.iloc[-1] & ((last > ma200) | ma200.isna()) & (rs >= 70) & (adr >= 0.02)      # recent listings have no 200-day average yet
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
    "At 20 EMA": (e20 >= e50) & (lo <= e20 * (1 + 0.4 * adr)) & (last >= e20 * (1 - 0.6 * adr)) & (last <= e20 * (1 + adr)),
    "At 50 EMA": (e50 > ma200) & (lo <= e50 * (1 + 0.5 * adr)) & (last >= e50 * 0.99) & (last <= e50 * (1 + 1.2 * adr)),
    "Turning up off EMA": up & (since >= 4) & (depth <= 0.20) & (l.tail(3).min() <= e20 * (1 + 0.5 * adr)) & (last > h.iloc[-2]) & (last >= e20),
    "Episodic pivot": epday.any() & (last >= ep_low),
    "Breakout today": (last > c.shift(1).rolling(50, min_periods=50).max().iloc[-1]) & (v.iloc[-1] >= 1.5 * v.shift(1).rolling(50, min_periods=30).mean().iloc[-1]),
    "Volume dry-up": (vdry <= 0.6) & (depth <= 0.20),
    "Overhead supply": supply,
}
# Where the stock is relative to an entry: coiled and waiting, triggered today, or already gone.
chg = last / c.iloc[-2] - 1
st_ext = last > e10 * (1 + 1.5 * adr)
st_trig = (last > h.iloc[-2]) & (chg >= 0.5 * adr) & ~st_ext
st_ready = ~st_trig & ~st_ext & (last >= e20 * (1 - 0.6 * adr)) & (last <= e10 * (1 + adr))
trigger = hi                                             # buy-stop level for tomorrow: today's high
stop = pd.concat([lo, trigger * (1 - 1.5 * adr)], axis=1).max(axis=1)
stop = pd.concat([stop, trigger * (1 - 0.4 * adr)], axis=1).min(axis=1)
ACTION = [k for k in TAGS if k not in ("Volume dry-up", "Overhead supply")]
tagdf = pd.DataFrame({k: m.reindex(c.columns).fillna(False).astype(bool) for k, m in TAGS.items()})
cand = base & tagdf[ACTION].any(axis=1)
rows = []
for s in cand[cand].index:
    q = float(quality[s])
    rows.append({"symbol": s, "theme": th.get(s, ""), "rank_score": round(float(rank_score[s]), 1), "quality": round(q, 1),
                 "grade": "A+" if q >= 75 else "A" if q >= 65 else "B" if q >= 55 else "C",
                 "tags": "; ".join(k for k in TAGS if tagdf.at[s, k]), "setup": "; ".join(k for k in TAGS if tagdf.at[s, k]),
                 "stage": "Building" if supply[s] else "Extended" if st_ext[s] else "Triggered today" if st_trig[s] else "Ready" if st_ready[s] else "Building",
                 "trigger": round(float(trigger[s]), 2), "stop": round(float(stop[s]), 2), "risk": round(100 * (1 - stop[s] / trigger[s]), 1),
                 "rs": int(rs[s]), "close": round(float(last[s]), 2), "adr": round(100 * adr[s], 1),
                 "runup": round(100 * runup[s], 0), "depth": round(100 * depth[s], 1), "range5": round(100 * rng5[s], 1),
                 "vs_ema10": round(100 * (last[s] / e10[s] - 1), 1), "vs_ema20": round(100 * (last[s] / e20[s] - 1), 1),
                 "vol_ratio": round(float(basevol.fillna(vdry)[s]), 2), "base_days": int(since[s]) if pd.notna(since[s]) else 0, "turnover_cr": round(med_tv.iloc[-1][s] / 1e7, 1)})
setups = pd.DataFrame(rows).sort_values("rank_score", ascending=False) if rows else pd.DataFrame()
now["setups"] = (setups[setups["grade"].isin(["A+", "A"])].groupby("theme").symbol.nunique().reindex(now.index).fillna(0).astype(int)
                 if len(setups) else 0)
OUT.mkdir(parents=True, exist_ok=True)
now.round(1).to_csv(OUT / "themes.csv")
setups.to_csv(OUT / "setups.csv", index=False)
if ASOF:
    pd.DataFrame({"quality": quality, "rs": rs, "liquid": liquid.iloc[-1], "above200": last > ma200, "adr": adr, "eligible": base,
                  "candidate": cand, "runup": runup, "since": since, "depth": depth, "move": sc_move, "tight": sc_tight, "trend": sc_trend,
                  "dry": sc_dry, "depthS": sc_depth, "baseS": sc_base, "vs20": last / e20 - 1, "rng5_adr": rng5 / adr}).to_csv(OUT / "all_scores.csv")
stocks.assign(close=last.reindex(stocks.index).round(2)).to_csv(OUT / "stocks.csv")
print(now.head(12)[["n", "r1w", "r1m", "r3m", "above50", "leaders", "rank_change", "setups", "top"]].round(1).to_string())
print("themes", len(now), "| setups", len(setups), setups["grade"].value_counts().to_dict(), tagdf[cand].sum().to_dict())
