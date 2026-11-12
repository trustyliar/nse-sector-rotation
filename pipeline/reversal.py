"""Reversal watch for small caps: an oversold score and a turn-day trigger. See research/reversals.py."""
import pandas as pd

from common import DATA, load_prices
from regime import wide, signals

w = wide(load_prices(pd.Timestamp.today() - pd.Timedelta(days=700)))
s = signals(w); c = w["close"]; liq = s["liquid"]; ret = s["ret"]
mc = pd.read_csv(DATA / "meta" / "classification.csv").set_index("symbol")["mcap_cr"].dropna().sort_values(ascending=False)
small = [x for x in mc.index[250:500] if x in c.columns]          # small-cap proxy: 251st-500th company by market value
idx = (1 + ret[small].mean(axis=1).fillna(0)).cumprod() * 1000
F = pd.DataFrame(index=c.index); n = liq.sum(axis=1)
F["idx"] = idx
F["dd"] = 100 * (idx / idx.rolling(60).max() - 1)
F["vs20"] = 100 * (idx / idx.rolling(20).mean() - 1)
d = idx.diff()
F["rsi"] = 100 - 100 / (1 + d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean() / (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean())
F["a20"] = 100 * ((c > s["ma20"]) & liq).sum(axis=1) / n
F["lows20"] = 100 * ((c <= c.rolling(20).min()) & liq).sum(axis=1) / n
F["up4"] = ((ret >= 0.04) & liq).sum(axis=1)
F["dn4"] = ((ret <= -0.04) & liq).sum(axis=1)
sc = lambda x, lo, hi: ((x - lo) / (hi - lo)).clip(0, 1)
F["a10"] = 100 * ((c > c.rolling(10).mean()) & liq).sum(axis=1) / n
F["a50"] = 100 * ((c > s["ma50"]) & liq).sum(axis=1) / n
F["dn10"] = 100 * F["dn4"].rolling(10).sum() / (F["up4"].rolling(10).sum() + F["dn4"].rolling(10).sum())
# Pure breadth: how few stocks hold their 10, 20 and 50-day averages, how many sit at 20-day lows,
# and how lopsided the 4% moves have been. Tested equal to a version using index RSI and drawdown.
F["oversold"] = 100 * pd.concat([sc(F.a20, 50, 15), sc(F.a10, 45, 12), sc(F.a50, 55, 25), sc(F.lows20.rolling(5).max(), 10, 40),
                                 sc(F.dn10, 50, 75)], axis=1).mean(axis=1)
F["os5"] = F["oversold"].rolling(5).max()
F["r1"] = 100 * idx.pct_change()
F["turn"] = (F.os5 >= 80) & (F.r1 >= 1.0) & (F.up4 >= 2 * F.dn4.clip(lower=1)) & (F.a20 > F.a20.shift(1))
F["first"] = F.turn & ~(F.turn.shift(1).rolling(8).max().fillna(0).astype(bool))
F["low10"] = idx.rolling(10).min()
(DATA / "derived").mkdir(exist_ok=True)
F.dropna(subset=["oversold"]).tail(400).round(2).to_csv(DATA / "derived" / "reversal.csv")
print(F.tail(3)[["oversold", "os5", "a20", "rsi", "dd", "turn"]].round(1).to_string())
