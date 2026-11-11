"""Which market measures actually predict how the next entries perform?"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "pipeline")
from common import load_prices
from regime import wide, signals, compute
w = wide(load_prices()); s = signals(w); r = compute(w, s)
c, l = w["close"], w["low"]; H, STOP = 10, 0.07
fl = pd.concat([l.shift(-k) for k in range(1, H + 1)]).groupby(level=0).min()
trade = (c.shift(-H) / c - 1).where(fl > c * (1 - STOP), -STOP)
ema20 = c.ewm(span=20, min_periods=20).mean(); ema50 = c.ewm(span=50, min_periods=50).mean()
rs = (c / c.shift(63) - 1).where(s["liquid"]).rank(axis=1, pct=True)
pull = (s["liquid"] & (c >= 40) & (c > s["ma50"]) & (s["ma50"] > s["ma200"]) & (ema20 > ema50) & (rs >= 0.7) & (l <= ema20 * 1.01) & (c >= ema20))
setups = s["breakout"] | pull
day_ret = trade.where(setups).mean(axis=1)                     # avg result of entries made that day
day_n = setups.sum(axis=1)
F = pd.DataFrame(index=r.index)
F["score"] = r["score"]; F["score_chg5"] = r["score"].diff(5); F["score_chg10"] = r["score"].diff(10)
F["score_vs_ma10"] = r["score"] - r["score"].rolling(10).mean()
for k in ("thrust", "above20", "above50", "above200", "highs", "follow"): F[k] = r[k]
F["above20_chg5"] = r["above20"].diff(5); F["above50_chg10"] = r["above50"].diff(10)
u5, d5 = r["up4"].rolling(5).sum(), r["down4"].rolling(5).sum()
F["ratio5"] = u5 / (u5 + d5); F["up4_25d_pct"] = r["up4"].rolling(25).sum() / r["universe"]
ew = s["ret"].where(s["liquid"]).mean(axis=1).fillna(0).add(1).cumprod()      # equal-weight index of liquid stocks
F["idx_vs_ma20"] = ew / ew.rolling(20).mean() - 1; F["idx_vs_ma50"] = ew / ew.rolling(50).mean() - 1
F["idx_ret20"] = ew.pct_change(20); F["idx_ret5"] = ew.pct_change(5)
F["idx_dd"] = ew / ew.rolling(120, min_periods=60).max() - 1                  # drawdown from 6-month high
F["vol20"] = s["ret"].where(s["liquid"]).mean(axis=1).rolling(20).std()
# realised: result of setups entered 11-20 sessions ago (all fully closed by today)
F["recent_setups"] = (trade.where(setups).sum(axis=1).shift(H + 1).rolling(10).sum()
                      / day_n.shift(H + 1).rolling(10).sum())
F = F.shift(1)                                                                 # known the evening before
day_ret, day_n = day_ret.reindex(F.index), day_n.reindex(F.index)
ok = day_ret.notna() & (day_n >= 3) & F["score"].notna()
rows = []
for f in F.columns:
    row = {"feature": f}
    for per, m in (("19-23", ok & (F.index < "2024-01-01")), ("24-26", ok & (F.index >= "2024-01-01"))):
        x, y = F.loc[m, f], day_ret[m]
        row[f"ic_{per}"] = round(x.corr(y, method="spearman"), 2)
        q = pd.qcut(x, 3, labels=["lo", "mid", "hi"])
        g = (100 * y.groupby(q, observed=True).mean()).round(1)
        row[f"lo/mid/hi_{per}"] = "/".join(f"{v:+.1f}" for v in g)
    rows.append(row)
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).to_string(index=False))
print("days", int(ok.sum()), "mean day result %", round(100 * day_ret[ok].mean(), 2),
      "| 19-23:", round(100 * day_ret[ok & (F.index < '2024-01-01')].mean(), 2), "24-26:", round(100 * day_ret[ok & (F.index >= '2024-01-01')].mean(), 2))
F.join(day_ret.rename("day_ret")).join(day_n.rename("day_n")).to_pickle("/tmp/features.pkl")
