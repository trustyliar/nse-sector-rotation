"""One-time history backfill from Yahoo for every NSE-listed equity."""
import sys
import time

import pandas as pd

from common import DATA, SERIES, symbols_master, write_prices, yahoo_batch, write_state, read_state

START = sys.argv[1] if len(sys.argv) > 1 else "2019-01-01"
t0 = time.time()
master = symbols_master()
syms = sorted(master.loc[master["series"].isin(SERIES), "symbol"])
print(f"{len(master)} listed, {len(syms)} in series {sorted(SERIES)}")

px, failed = yahoo_batch(syms, START)
if failed:
    print(f"retrying {len(failed)} symbols singly-batched after a pause")
    time.sleep(30)
    px2, failed = yahoo_batch(failed, START, batch=20, pause=3)
    px = pd.concat([px, px2], ignore_index=True)

# Yahoo occasionally carries ghost rows on market holidays: drop thin dates.
per_day = px.groupby("date")["symbol"].nunique()
thin = per_day[per_day < 0.25 * per_day.rolling(20, min_periods=1).median()].index
px = px[~px["date"].isin(thin)]
px = px.drop_duplicates(["date", "symbol"])
write_prices(px)

# Benchmarks
import yfinance as yf
idx_frames = []
for name, tick in {"Nifty 50": "^NSEI", "Nifty 500": "^CRSLDX", "Nifty Bank": "^NSEBANK"}.items():
    try:
        d = yf.download(tick, start=START, interval="1d", auto_adjust=False, progress=False,
                        multi_level_index=False).dropna(subset=["Close"])
        i = pd.DatetimeIndex(d.index)
        if i.tz is not None:
            i = i.tz_convert("Asia/Kolkata").tz_localize(None)
        idx_frames.append(pd.DataFrame({"date": i.normalize(), "index": name, "open": d["Open"].values,
                                        "high": d["High"].values, "low": d["Low"].values,
                                        "close": d["Close"].values}))
        print(f"index {name}: {len(d)} rows")
    except Exception as e:                                       # noqa: BLE001
        print(f"index {name} failed: {e}")
if idx_frames:
    (DATA / "indices").mkdir(parents=True, exist_ok=True)
    pd.concat(idx_frames).to_parquet(DATA / "indices" / "indices.parquet", index=False)

state = {}          # a fresh backfill supersedes earlier NSE rows and adjustments
adjf = DATA / "meta" / "adjustments.csv"
if adjf.exists():
    adjf.unlink()
state.update({"backfill_start": START, "backfill_run": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
              "backfill_last_date": str(px["date"].max().date())})
write_state(state)

got = px["symbol"].nunique()
rep = ["# Backfill report", "",
       f"- Run: {state['backfill_run']}, took {time.time() - t0:.0f}s",
       f"- Symbols requested: {len(syms)}; with data: {got}; no data: {len(failed)}",
       f"- Rows: {len(px):,}; dates: {px['date'].min().date()} to {px['date'].max().date()} "
       f"({px['date'].nunique()} trading days)",
       f"- Thin dates dropped as holiday artefacts: {len(thin)}",
       "", "## Symbols per day (last 8 days)", ""]
rep += [f"- {d.date()}: {n}" for d, n in px.groupby("date")["symbol"].nunique().tail(8).items()]
rep += ["", "## Symbols per day (yearly median)", ""]
pdn = px.groupby("date")["symbol"].nunique()
rep += [f"- {y}: {int(v)}" for y, v in pdn.groupby(pdn.index.year).median().items()]
rep += ["", "## No data from Yahoo", "", ", ".join(sorted(failed)) or "none"]
(DATA / "reports").mkdir(exist_ok=True)
(DATA / "reports" / "backfill.md").write_text("\n".join(rep) + "\n")
print("\n".join(rep[:14]))
