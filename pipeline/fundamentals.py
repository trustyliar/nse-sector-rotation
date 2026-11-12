"""Quarterly growth numbers for the stronger liquid stocks (RS 60+), from Yahoo.

Kept in meta/fundamentals.csv on the data branch. Resumable and incremental: a stock is re-fetched
when it has never been fetched, when its data is over 10 days old, or when it has not yet reported
the quarter most others have. Usage: fundamentals.py [minutes budget]"""
import sys
import time

import numpy as np
import pandas as pd
import yfinance as yf

from common import DATA, today_ist

BUDGET = (float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else 20) * 60
t0 = time.time()
today = pd.Timestamp(today_ist())
path = DATA / "meta" / "fundamentals.csv"
stocks = pd.read_csv(DATA / "derived" / "stocks.csv", index_col=0)
want = stocks[stocks["rs"] >= 60].sort_values("rs", ascending=False).index.tolist()
old = pd.read_csv(path, index_col=0, parse_dates=["fetched"]) if path.exists() else pd.DataFrame()
common_q = old["latest_q"].mode().iloc[0] if len(old) else None


def stale(s):
    if s not in old.index:
        return True
    r = old.loc[s]
    age = (today - r["fetched"]).days
    return age > 10 or (age >= 1 and common_q and str(r["latest_q"]) < common_q)


def row(q, name):
    for n in ([name] if isinstance(name, str) else name):
        if n in q.index:
            return q.loc[n]
    return pd.Series(dtype=float)


out, fails = {}, 0
for s in [x for x in want if stale(x)]:
    if time.time() - t0 > BUDGET or fails >= 6:
        break
    try:
        t = yf.Ticker(s + ".NS")
        q = t.quarterly_income_stmt
        if q is None or q.empty:
            out[s] = {"fetched": today, "latest_q": ""}
            continue
        q = q.sort_index(axis=1, ascending=False)
        rev, ni = row(q, "Total Revenue"), row(q, "Net Income")
        op = row(q, ["Operating Income", "EBIT", "EBITDA"])
        info = t.info
        d = {"fetched": today, "latest_q": str(q.columns[0].date()), "quarters": len(q.columns),
             "roe": info.get("returnOnEquity"), "de": info.get("debtToEquity"), "pe": info.get("trailingPE"),
             "promoter": info.get("heldPercentInsiders")}
        for k in range(6):
            d[f"rev{k}"] = rev.iloc[k] / 1e7 if len(rev) > k and pd.notna(rev.iloc[k]) else np.nan      # Rs crore
            d[f"ni{k}"] = ni.iloc[k] / 1e7 if len(ni) > k and pd.notna(ni.iloc[k]) else np.nan
            d[f"op{k}"] = op.iloc[k] / 1e7 if len(op) > k and pd.notna(op.iloc[k]) else np.nan
        out[s] = d
    except Exception as e:                                       # noqa: BLE001
        fails += 1
        print(f"{s}: {type(e).__name__} {str(e)[:80]}; pausing")
        time.sleep(45)
    time.sleep(0.25)

new = pd.DataFrame.from_dict(out, orient="index")
allf = pd.concat([old[~old.index.isin(new.index)], new]) if len(old) else new
allf.index.name = "symbol"

# ---- growth metrics and a 0-100 growth score
g = lambda a, b: np.where((allf[b] > 0) & allf[a].notna(), allf[a] / allf[b] - 1, np.nan)
allf["sales_yoy"] = 100 * g("rev0", "rev4")
allf["sales_yoy_prev"] = 100 * g("rev1", "rev5")
allf["profit_yoy"] = 100 * g("ni0", "ni4")
allf["profit_yoy_prev"] = 100 * g("ni1", "ni5")
allf["turnaround"] = (allf["ni4"] <= 0) & (allf["ni0"] > 0)
allf["sales_qoq"] = 100 * g("rev0", "rev1")
allf["opm"] = 100 * allf["op0"] / allf["rev0"]
allf["opm_yago"] = 100 * allf["op4"] / allf["rev4"]
sc = lambda x, lo, hi: ((x - lo) / (hi - lo)).clip(0, 1)
p_growth = sc(allf["profit_yoy"], 0, 60).where(~allf["turnaround"], 0.8)
accel = sc(allf["sales_yoy"] - allf["sales_yoy_prev"], -5, 15).fillna(0.4)
margin = sc(allf["opm"] - allf["opm_yago"], -2, 4).fillna(0.4)
allf["growth_score"] = (100 * (0.30 * sc(allf["sales_yoy"], 0, 40) + 0.30 * p_growth + 0.20 * accel + 0.20 * margin)).round(0)
allf.loc[allf["sales_yoy"].isna() | (allf["profit_yoy"].isna() & ~allf["turnaround"]), "growth_score"] = np.nan
allf.round(2).to_csv(path)
print(f"fetched {len(new)} this run in {time.time() - t0:.0f}s; total {len(allf)} of {len(want)} wanted; with score {allf['growth_score'].notna().sum()}")
print("latest quarter:", allf["latest_q"].value_counts().head(4).to_dict())
