"""Compare oversold definitions: mixed (breadth + index) vs pure breadth."""
import sys
import pandas as pd
sys.path.insert(0, "pipeline")
from common import DATA, load_prices
from regime import wide, signals
DEEP = ["2023-10-26", "2024-03-13", "2024-11-13", "2025-03-03", "2025-04-07", "2025-12-08", "2026-03-23", "2026-10-23"]   # low days of the 8 deep sell-offs
w = wide(load_prices()); s = signals(w); c = w["close"]; liq = s["liquid"]; ret = s["ret"]; n = liq.sum(axis=1)
mc = pd.read_csv(DATA / "meta" / "classification.csv").set_index("symbol")["mcap_cr"].dropna().sort_values(ascending=False)
idx = (1 + ret[[x for x in mc.index[250:500] if x in c.columns]].mean(axis=1).fillna(0)).cumprod()
F = pd.DataFrame(index=c.index)
d = idx.diff(); F["rsi"] = 100 - 100 / (1 + d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean() / (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean())
F["dd"] = 100 * (idx / idx.rolling(60).max() - 1); F["vs20"] = 100 * (idx / idx.rolling(20).mean() - 1)
for k in (20, 50, 200):
    F[f"a{k}"] = 100 * ((c > s[f"ma{k}"]) & liq).sum(axis=1) / n
ma10 = c.rolling(10).mean(); F["a10"] = 100 * ((c > ma10) & liq).sum(axis=1) / n
F["lows20"] = (100 * ((c <= c.rolling(20).min()) & liq).sum(axis=1) / n).rolling(5).max()
up, dn = ((ret >= 0.04) & liq).sum(axis=1), ((ret <= -0.04) & liq).sum(axis=1)
F["dn10"] = 100 * dn.rolling(10).sum() / (up.rolling(10).sum() + dn.rolling(10).sum())        # share of 4% moves that were down, 10 days
F["dn25"] = 100 * ((c / c.shift(21) - 1 <= -0.25) & liq).sum(axis=1) / n                           # stocks down 25%+ in a month
sc = lambda x, lo, hi: ((x - lo) / (hi - lo)).clip(0, 1)
V = {"mixed (current)": [sc(F.a20, 50, 15), sc(F.rsi, 50, 30), sc(F.dd, -3, -12), sc(F.lows20, 10, 40), sc(F.vs20, 0, -6)],
     "pure breadth": [sc(F.a20, 50, 15), sc(F.a10, 45, 12), sc(F.a50, 55, 25), sc(F.lows20, 10, 40), sc(F.dn10, 50, 75)],
     "breadth, 20-day only": [sc(F.a20, 40, 12)]}
r1 = 100 * idx.pct_change(); f10 = 100 * (idx.shift(-10) / idx - 1); f20 = 100 * (idx.shift(-20) / idx - 1)
print("readings at the 8 deep lows:"); print(F.loc[pd.DatetimeIndex(DEEP), ["a10", "a20", "a50", "a200", "lows20", "dn10", "dn25", "rsi"]].round(0).astype(int).T.to_string())
for name, parts in V.items():
    o = 100 * pd.concat(parts, axis=1).mean(axis=1); os5 = o.rolling(5).max()
    turn = (os5 >= 60) & (r1 >= 1.0) & (up >= 2 * dn.clip(lower=1)) & (F.a20 > F.a20.shift(1))
    first = turn & ~(turn.shift(1).rolling(8).max().fillna(0).astype(bool))
    lag = []
    for x in DEEP:
        i = F.index.get_loc(pd.Timestamp(x)); t = first.iloc[i - 1: i + 8]; lag.append((list(t.values).index(True) - 1) if t.any() else None)
    out = [f"{name}: score at lows {[int(o[pd.Timestamp(x)]) for x in DEEP]} | days low->signal {lag}"]
    for per, m in (("2019-23", (F.index >= "2019-10-01") & (F.index < "2023-10-01")), ("2023-26", F.index >= "2023-10-01")):
        T = first & m; out.append(f"{per}: n={int(T.sum())} win10={100 * (f10[T] > 0).mean():.0f}% avg10={f10[T].mean():+.1f}% avg20={f20[T].mean():+.1f}% worst10={f10[T].min():+.0f}% days oversold={100 * (o[m] >= 60).mean():.0f}%")
    print("\n" + "\n  ".join(out))
