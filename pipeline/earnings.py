"""Next results date per stock (RS 50+), from Yahoo's calendar. Kept in meta/earnings.csv.
Refetched weekly or once the stored date has passed. Usage: earnings.py [minutes budget]"""
import sys
import time

import pandas as pd
import yfinance as yf

from common import DATA, today_ist

BUDGET = (float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else 12) * 60
t0 = time.time()
today = pd.Timestamp(today_ist())
path = DATA / "meta" / "earnings.csv"
stocks = pd.read_csv(DATA / "derived" / "stocks.csv", index_col=0)
want = stocks[stocks["rs"] >= 50].sort_values("rs", ascending=False).index.tolist()
old = pd.read_csv(path, index_col=0, parse_dates=["fetched", "next_result"]) if path.exists() else pd.DataFrame(columns=["next_result", "fetched"])


def stale(s):
    if s not in old.index:
        return True
    r = old.loc[s]
    return (today - r["fetched"]).days >= 7 or (pd.notna(r["next_result"]) and r["next_result"] < today)


out, fails = {}, 0
for s in [x for x in want if stale(x)]:
    if time.time() - t0 > BUDGET or fails >= 8:
        break
    try:
        cal = yf.Ticker(s + ".NS").calendar
        ds = cal.get("Earnings Date") if isinstance(cal, dict) else None
        ds = [pd.Timestamp(d) for d in (ds or [])]
        fut = sorted(d for d in ds if d >= today - pd.Timedelta(days=1))
        out[s] = {"next_result": fut[0] if fut else pd.NaT, "fetched": today}
        fails = 0
    except Exception as e:
        fails += 1
        if "Too Many" in str(e) or "429" in str(e):
            time.sleep(45)
    time.sleep(0.3)
new = pd.DataFrame.from_dict(out, orient="index")
res = pd.concat([old[~old.index.isin(new.index)], new]) if len(new) else old
res.index.name = "symbol"
path.parent.mkdir(exist_ok=True)
res.to_csv(path)
print(f"results dates: {len(new)} fetched this run, {res['next_result'].notna().sum()} with a date, {len(res)} total")
