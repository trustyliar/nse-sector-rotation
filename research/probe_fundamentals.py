"""What fundamental data does Yahoo carry for NSE stocks, and how fresh is it?"""
import time
import pandas as pd
import yfinance as yf
s = pd.read_csv("data/derived/setups.csv"); syms = s[s.grade != "C"].symbol.head(30).tolist() + ["HAL", "BEL", "KAYNES", "DIXON", "MAZDOCK", "RELIANCE"]
KEYS = ["revenueGrowth", "earningsQuarterlyGrowth", "earningsGrowth", "profitMargins", "operatingMargins", "returnOnEquity", "debtToEquity",
        "trailingPE", "forwardPE", "mostRecentQuarter", "heldPercentInsiders", "heldPercentInstitutions", "totalRevenue"]
have = {k: 0 for k in KEYS}; q_ok = 0; latest = {}; rows = []; t0 = time.time()
for y in syms:
    try:
        t = yf.Ticker(y + ".NS"); i = t.info
        for k in KEYS:
            have[k] += i.get(k) is not None
        q = t.quarterly_income_stmt
        if q is not None and not q.empty:
            q_ok += 1; d = str(q.columns[0].date()); latest[d] = latest.get(d, 0) + 1
            rev = q.loc["Total Revenue"].dropna() if "Total Revenue" in q.index else pd.Series(dtype=float)
            ni = q.loc["Net Income"].dropna() if "Net Income" in q.index else pd.Series(dtype=float)
            rows.append((y, d, len(q.columns), [round(v / 1e7) for v in rev.head(5)], [round(v / 1e7) for v in ni.head(5)]))
    except Exception as e:
        rows.append((y, "ERR", str(e)[:60]))
    time.sleep(0.4)
print(f"{len(syms)} stocks in {time.time() - t0:.0f}s; quarterly statements for {q_ok}")
print("info fields present:", have)
print("latest quarter in statements:", dict(sorted(latest.items(), reverse=True)))
for r in rows[:14] + rows[-6:]:
    print(r)
