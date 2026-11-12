"""What did the market look like at the trader's reversal dates, and can a rule catch them early?"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "pipeline")
from common import DATA, load_prices
from regime import wide, signals
D = ["2023-10-26", "2024-03-14", "2024-05-13", "2024-08-16", "2024-11-22", "2025-03-04", "2025-04-07", "2025-05-09",
     "2025-09-01", "2025-10-01", "2025-12-09", "2026-04-02", "2026-06-01", "2026-10-26"]
w = wide(load_prices()); s = signals(w); c = w["close"]; liq = s["liquid"]; ret = s["ret"]
cl = pd.read_csv(DATA / "meta" / "classification.csv").set_index("symbol")["mcap_cr"].dropna().sort_values(ascending=False)
small = [x for x in cl.index[250:500] if x in c.columns]                        # small-cap proxy: 251st-500th by market value
r_s = ret[small].mean(axis=1).fillna(0); idx = (1 + r_s).cumprod() * 1000
ix = pd.read_parquet(DATA / "indices" / "indices.parquet"); real = ix[ix["index"] == "NIFTY Smallcap 100"].set_index("date")["close"]
j = pd.concat([idx.pct_change().rename("p"), real.pct_change().rename("r")], axis=1).dropna()
print("proxy vs real Smallcap 100 daily-return correlation:", round(j.p.corr(j.r), 3), "on", len(j), "days")
F = pd.DataFrame(index=c.index); n = liq.sum(axis=1)
F["idx"] = idx; F["dd"] = 100 * (idx / idx.rolling(60).max() - 1); F["vs20"] = 100 * (idx / idx.rolling(20).mean() - 1)
d = idx.diff(); up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
F["rsi"] = 100 - 100 / (1 + up / dn)
for k in (20, 50):
    F[f"a{k}"] = 100 * ((c > s[f"ma{k}"]) & liq).sum(axis=1) / n
F["lows20"] = 100 * ((c <= c.rolling(20).min()) & liq).sum(axis=1) / n
F["up4"] = ((ret >= 0.04) & liq).sum(axis=1); F["dn4"] = ((ret <= -0.04) & liq).sum(axis=1)
F["dn4_5"] = 100 * F["dn4"].rolling(5).sum() / n
sc = lambda x, lo, hi: ((x - lo) / (hi - lo)).clip(0, 1)
F["oversold"] = 100 * pd.concat([sc(F.a20, 50, 15), sc(F.rsi, 50, 30), sc(F.dd, -3, -12), sc(F.lows20.rolling(5).max(), 10, 40),
                                 sc(F.vs20, 0, -6)], axis=1).mean(axis=1)
F["os5"] = F["oversold"].rolling(5).max()
hi_prev = w["high"][small].pct_change(fill_method=None)   # placeholder to keep API simple
F["r1"] = 100 * idx.pct_change()
# trigger: market was oversold within 5 sessions, and today breadth turns: index up 1%+, advancers dominate, more stocks back above 20-day
F["turn"] = (F.os5 >= 60) & (F.r1 >= 1.0) & (F.up4 >= 2 * F.dn4.clip(lower=1)) & (F.a20 > F.a20.shift(1))
F["first"] = F.turn & ~(F.turn.shift(1).rolling(8).max().fillna(0).astype(bool))
for h in (5, 10, 20):
    F[f"f{h}"] = 100 * (idx.shift(-h) / idx - 1)
pd.set_option("display.width", 220)
rows = []
for x in D:
    t = pd.Timestamp(x); i = F.index.get_indexer([t], method="nearest")[0]
    win = F.iloc[i - 6: i + 7]; low = win.idx.idxmin(); trig = F.iloc[i - 3: i + 8]; tr = trig.index[trig["first"] | trig["turn"]]
    rows.append({"his date": x, "low day": str(low.date())[5:], "os@low": round(F.at[low, "oversold"]), "a20": round(F.at[low, "a20"]), "rsi": round(F.at[low, "rsi"]),
                 "dd%": round(F.at[low, "dd"], 1), "lows20max": round(win.lows20.max()), "trigger": str(tr[0].date())[5:] if len(tr) else "none",
                 "days after low": (F.index.get_loc(tr[0]) - F.index.get_loc(low)) if len(tr) else None,
                 "up from low at trigger%": round(100 * (F.at[tr[0], "idx"] / F.at[low, "idx"] - 1), 1) if len(tr) else None,
                 "next20d%": round(F.at[tr[0], "f20"], 1) if len(tr) and pd.notna(F.at[tr[0], "f20"]) else None})
print(pd.DataFrame(rows).to_string(index=False))
T = F[F["first"] & (F.index >= "2019-10-01")]
print("\nall triggers since Oct 2019:", len(T), "| since Oct 2023:", (T.index >= "2023-10-01").sum())
for per, m in (("2019-23", T.index < "2023-10-01"), ("2023-26", T.index >= "2023-10-01")):
    x = T[m]; b = F[(F.index >= ("2019-10-01" if per == "2019-23" else "2023-10-01")) & (F.index < ("2023-10-01" if per == "2019-23" else "2027"))]
    print(per, "n", len(x), "| after trigger 5/10/20d avg %:", x.f5.mean().round(1), x.f10.mean().round(1), x.f20.mean().round(1), "| win 10d %", round(100 * (x.f10 > 0).mean()),
          "| worst 10d", x.f10.min().round(1), "| any-day baseline 10d/20d:", b.f10.mean().round(1), b.f20.mean().round(1))
print("triggers since Oct 2023:", ", ".join(f"{d.date()}({r.f10:+.0f}%)" for d, r in T[T.index >= "2023-10-01"].iterrows()))
print("today:", F.tail(1)[["oversold", "a20", "rsi", "dd"]].round(0).to_dict("records"))
