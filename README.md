# NSE sector rotation and market regime system

End-of-day system for NSE swing trading: sector relative strength, setup scans and a
market regime score, refreshed once each evening by a scheduled GitHub job.

## Status

| Layer | State |
|---|---|
| Price history (2019 onward, all NSE equities) | Done |
| Nightly update from the NSE bhavcopy | Done, scheduled |
| Industry classification | Done (Yahoo taxonomy; Indian theme mapping pending) |
| Regime score and backtest | Next |
| Sector ranking, setup scans, daily page | Later |

## How it works

- Code lives on `main`; data lives on the `data` branch (`prices/`, `indices/`, `meta/`, `reports/`).
- `pipeline/daily_update.py` runs at about 19:37 and 21:07 IST on trading days, plus 08:07 IST
  the next morning. It appends the official NSE bhavcopy for every day not yet stored, checks
  the date inside each file, and tries weekends too (special sessions such as Muhurat trading).
- Stored prices are as-traded. Splits and bonuses are recorded in `meta/adjustments.csv` and
  applied when prices are loaded (`common.load_prices`). They are detected nightly by comparing
  stored closes with Yahoo's split-adjusted series.
- `pipeline/backfill.py` (one-time) pulled history from Yahoo; `pipeline/repair_gaps.py`
  audited large jumps in that history against NSE's official files.
- `pipeline/classify.py` builds `meta/classification.csv`; manual corrections go in
  `config/classification_overrides.csv`.

## Known limits

- History covers currently listed stocks only, so backtests carry some survivorship bias.
- Demergers are not adjusted (prices show the gap, as most charting tools do).
- See `reports/gap_audit.md` on the data branch for jumps that could not be verified.
