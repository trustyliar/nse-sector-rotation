"""Can a faster signal justify starting small before the regime score reaches 55?"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "pipeline")
from common import load_prices
from regime import wide, signals, compute
w = wide(load_prices()); s = signals(w); r = compute(w, s); c, l = w["close"], w["low"]; liq = s["liquid"]; n = liq.sum(axis=1)
H, STOP = 10, 0.07
fl = pd.concat([l.shift(-k) for k in range(1, H + 1)]).groupby(level=0).min()
trade = (c.shift(-H) / c - 1).where(fl > c * (1 - STOP), -STOP)
e20 = c.ewm(span=20, min_periods=20).mean(); e50 = c.ewm(span=50, min_periods=50).mean()
rs = (c / c.shift(63) - 1).where(liq).rank(axis=1, pct=True)
pull = liq & (c >= 40) & (c > s["ma50"]) & (s["ma50"] > s["ma200"]) & (e20 > e50) & (rs >= 0.7) & (l <= e20 * 1.01) & (c >= e20)
setups = s["breakout"] | pull
tot = trade.where(setups).sum(axis=1).reindex(r.index); cnt = setups.sum(axis=1).reindex(r.index)
a10 = (100 * ((c > c.rolling(10).mean()) & liq).sum(axis=1) / n).reindex(r.index)
sc, a20, a50 = r["score"], r["above20"], r["above50"]
ew = s["ret"].where(liq).mean(axis=1).fillna(0).add(1).cumprod().reindex(r.index)
G = {
 "score >= 55 (current Favourable)": sc >= 55,
 "score < 55, all days": sc < 55,
 "score < 55 & up 10+ pts from 10-day low": (sc < 55) & (sc - sc.rolling(10).min() >= 10),
 "score < 55 & up 15+ pts from 10-day low": (sc < 55) & (sc - sc.rolling(10).min() >= 15),
 "score < 55 & above its 10-day average": (sc < 55) & (sc > sc.rolling(10).mean()),
 "score < 55 & >50% above 10-day avg": (sc < 55) & (a10 > 50),
 "score < 55 & >50% above 20-day avg": (sc < 55) & (a20 > 50),
 "score < 55 & above20 up 15+ pts in 5 days": (sc < 55) & (a20.diff(5) >= 15),
 "score < 55 & index above rising 10-day avg": (sc < 55) & (ew > ew.rolling(10).mean()) & (ew.rolling(10).mean().diff() > 0),
 "score < 55 & thrust part >= 60": (sc < 55) & (r["thrust"] >= 60),
 "score < 55 & none of: rising 10+, above 10d avg": (sc < 55) & ~((sc - sc.rolling(10).min() >= 10) | (sc > sc.rolling(10).mean())),
 "score 40-55 & falling (below 10-day avg)": (sc >= 40) & (sc < 55) & (sc < sc.rolling(10).mean()),
 "score >= 55 & falling 10+ from 10-day high": (sc >= 55) & (sc.rolling(10).max() - sc >= 10),
}
rows = []
for k, m in G.items():
    m = m.shift(1).fillna(False).astype(bool)                      # state known the evening before entry
    row = {"state": k}
    for per, pm in (("19-23", r.index < "2024-01-01"), ("24-26", r.index >= "2024-01-01")):
        mm = m & pm; row[per] = f"{100 * tot[mm].sum() / max(cnt[mm].sum(), 1):+.2f}% per trade, {int(cnt[mm].sum()):6d} trades, {100 * mm.sum() / pm.sum():3.0f}% of days"
    rows.append(row)
pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 60); print(pd.DataFrame(rows).to_string(index=False))
x = pd.DataFrame({"score": sc, "a10": a10, "a20": a20, "up_from_low": sc - sc.rolling(10).min(), "vs10avg": sc - sc.rolling(10).mean()}).loc["2026-10-22":"2026-11-11"].round(0)
print(x.T.to_string())
