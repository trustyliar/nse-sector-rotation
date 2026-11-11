"""Does the regime score separate good and bad periods for breakout and pullback trades?"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "pipeline")
from common import load_prices
from regime import wide, signals, compute

w = wide(load_prices()); s = signals(w); r = compute(w, s)
c, h, l = w["close"], w["high"], w["low"]
H, STOP = 10, 0.07
fl = pd.concat([l.shift(-k) for k in range(1, H + 1)]).groupby(level=0).min()
fwd = c.shift(-H) / c - 1
trade = fwd.where(fl > c * (1 - STOP), -STOP)                     # stop at -7%, else exit after 10 sessions
ema20 = c.ewm(span=20, min_periods=20).mean(); ema50 = c.ewm(span=50, min_periods=50).mean()
rs = (c / c.shift(63) - 1).where(s["liquid"]).rank(axis=1, pct=True)
pull = (s["liquid"] & (c >= 40) & (c > s["ma50"]) & (s["ma50"] > s["ma200"]) & (ema20 > ema50)
        & (rs >= 0.7) & (l <= ema20 * 1.01) & (c >= ema20))
sc = r["score"].shift(1)                                          # score known the evening before entry

def trades(mask, name):
    t = trade.where(mask).stack().rename("ret").reset_index()
    t.columns = ["date", "symbol", "ret"]; t["score"] = t["date"].map(sc); t["kind"] = name
    return t.dropna()
T = pd.concat([trades(s["breakout"], "breakout"), trades(pull, "pullback")])
T["bin"] = pd.cut(T["score"], [0, 30, 40, 50, 55, 60, 70, 100], right=False)
T["period"] = np.where(T["date"] < "2024-01-01", "2019-23", "2024-26")

def tab(g):
    return pd.Series({"n": len(g), "win%": 100 * (g.ret > 0).mean(), "avg%": 100 * g.ret.mean(),
                      "stopped%": 100 * (g.ret <= -STOP + 1e-9).mean(),
                      "big%": 100 * (g.ret >= 0.10).mean()})
pd.set_option("display.width", 200)
for kind in ("breakout", "pullback"):
    x = T[T.kind == kind].groupby(["period", "bin"], observed=True).apply(tab, include_groups=False).round(1)
    print(f"\n== {kind} trades by prior-day score =="); print(x.to_string())
print("\n== share of days per score bin =="); 
d = pd.cut(r["score"], [0, 30, 40, 50, 55, 60, 70, 100], right=False).value_counts(normalize=True).sort_index().mul(100).round(1)
print(d.to_string())
# which components carry the signal: rank correlation with mean trade result of that day's entries
daily = T.groupby("date").ret.mean()
comp = r[["thrust", "above20", "above50", "above200", "highs", "follow", "score"]].shift(1)
print("\n== rank correlation of each input with next-day entries' average result ==")
for per, m in (("2019-23", daily.index < "2024-01-01"), ("2024-26", daily.index >= "2024-01-01")):
    print(per, comp.loc[daily.index[m]].corrwith(daily[m], method="spearman").round(2).to_dict())
print("\n== monthly average score =="); m = r["score"].resample("QE").mean().round(0)
print(" ".join(f"{i.year}Q{i.quarter}:{int(v)}" for i, v in m.items()))
print("\n== last 10 sessions =="); print(r.tail(10)[["score", "zone", "thrust", "above20", "above50", "highs", "follow", "up4", "down4", "universe"]].round(0).to_string())
