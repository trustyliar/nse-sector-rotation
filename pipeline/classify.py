"""Build meta/classification.csv: sector and industry for every NSE equity.

Sources: Yahoo (fine-grained industry + market cap, every stock) and NSE's index
constituent lists (NSE's own broad sector, top ~750 stocks). Resumable: symbols
already classified are skipped, so a throttled run can simply be started again.
Manual corrections live in config/classification_overrides.csv and always win."""
import io
import sys
import time
from pathlib import Path

import pandas as pd

from common import DATA, SERIES, http_get, symbols_master

BUDGET = float(sys.argv[1]) * 60 if len(sys.argv) > 1 else 40 * 60
t0 = time.time()
out_path = DATA / "meta" / "classification.csv"
master = symbols_master()
master = master[master["series"].isin(SERIES)]

nse = {}
for tag, f in (("Nifty 500", "ind_nifty500list.csv"), ("Nifty Total Market", "ind_niftytotalmarket_list.csv"),
               ("Nifty Microcap 250", "ind_niftymicrocap250_list.csv")):
    try:
        r = http_get(f"https://nsearchives.nseindia.com/content/indices/{f}")
        d = pd.read_csv(io.StringIO(r.text))
        d.columns = [c.strip() for c in d.columns]
        for row in d.itertuples():
            nse.setdefault(str(row.Symbol).strip(), (str(row.Industry).strip(), tag))
        print(f"{tag}: {len(d)} rows")
    except Exception as e:                                       # noqa: BLE001
        print(f"{tag} failed: {e}")

cols = ["symbol", "name", "isin", "nse_sector", "index_group", "yahoo_sector", "yahoo_industry", "mcap_cr"]
old = pd.read_csv(out_path) if out_path.exists() else pd.DataFrame(columns=cols)
done = {r.symbol: r for r in old.itertuples() if isinstance(r.yahoo_industry, str) and r.yahoo_industry}

import yfinance as yf
rows, limited, fetched = [], 0, 0
# Largest names first is not known yet, so index members first: they matter most.
order = sorted(master["symbol"], key=lambda s: (s not in nse, s))
for s in order:
    name, isin = master.loc[master["symbol"] == s, ["name", "isin"]].iloc[0]
    sec, grp = nse.get(s, ("", ""))
    if s in done:
        r = done[s]
        rows.append([s, name, isin, sec, grp, r.yahoo_sector, r.yahoo_industry, r.mcap_cr])
        continue
    ys = yi = ""
    mc = None
    if time.time() - t0 < BUDGET and limited < 6:
        for attempt in range(2):
            try:
                info = yf.Ticker(s + ".NS").info
                ys, yi = info.get("sector") or "", info.get("industry") or ""
                mc = info.get("marketCap")
                fetched += 1
                break
            except Exception as e:                               # noqa: BLE001
                if "Rate" in type(e).__name__ or "429" in str(e):
                    limited += 1
                    print(f"rate limited at {s} (#{limited}); pausing 90s")
                    time.sleep(90)
                else:
                    break
        time.sleep(0.35)
    rows.append([s, name, isin, sec, grp, ys, yi, round(mc / 1e7) if mc else None])
    if fetched and fetched % 200 == 0:
        print(f"fetched {fetched}, {time.time() - t0:.0f}s")

df = pd.DataFrame(rows, columns=cols)
ov = Path("config/classification_overrides.csv")
if ov.exists():
    o = pd.read_csv(ov, comment="#").set_index("symbol")
    for c in ("nse_sector", "yahoo_sector", "yahoo_industry"):
        if c in o.columns:
            m = df["symbol"].map(o[c])
            df[c] = m.where(m.notna(), df[c])
df.sort_values("symbol").to_csv(out_path, index=False)

have = (df["yahoo_industry"].fillna("") != "").sum()
rep = ["# Classification report", "",
       f"- Symbols: {len(df)}; with Yahoo industry: {have}; with NSE sector: {(df['nse_sector'] != '').sum()}",
       f"- Fetched this run: {fetched}; rate-limit pauses: {limited}; took {time.time() - t0:.0f}s",
       f"- Distinct Yahoo sectors: {df['yahoo_sector'].replace('', pd.NA).nunique()}; "
       f"industries: {df['yahoo_industry'].replace('', pd.NA).nunique()}",
       "", "## Stocks per Yahoo industry (top 40)", ""]
vc = df["yahoo_industry"].replace("", pd.NA).value_counts()
rep += [f"- {k}: {v}" for k, v in vc.head(40).items()]
rep += ["", "## Stocks per NSE sector", ""]
rep += [f"- {k}: {v}" for k, v in df["nse_sector"].replace("", pd.NA).value_counts().items()]
(DATA / "reports").mkdir(exist_ok=True)
(DATA / "reports" / "classification.md").write_text("\n".join(rep) + "\n")
print("\n".join(rep[:6]))
