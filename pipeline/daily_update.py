"""Nightly update: append the official NSE bhavcopy for every trading day not yet stored.

- Checks the date inside each file (NSE can serve a stale copy on holidays).
- Detects splits/bonuses and records an adjustment factor instead of rewriting history.
- Falls back to Yahoo if NSE cannot be reached.
Usage: daily_update.py [first_date YYYY-MM-DD]"""
import datetime as dt
import io
import sys
import time

import pandas as pd

from common import (DATA, COLS, fetch_bhavcopy, http_get, load_adjustments, load_raw, read_state,
                    symbols_master, today_ist, write_prices, write_state, yahoo_batch)

state = read_state()
today = today_ist()
if len(sys.argv) > 1 and sys.argv[1]:
    first = dt.date.fromisoformat(sys.argv[1])
elif state.get("last_bhav_date"):
    first = dt.date.fromisoformat(state["last_bhav_date"]) + dt.timedelta(days=1)
else:
    first = today - dt.timedelta(days=9)        # first run: overlap the Yahoo backfill to validate it

master = symbols_master()
listed = set(master["symbol"])
hist = load_raw(first - dt.timedelta(days=40))
last_close = (hist[hist["date"] < pd.Timestamp(first)].sort_values("date")
              .groupby("symbol")["close"].last().to_dict())
adj_rows, log, done_dates, unresolved = [], [], [], []


def yahoo_split_factor(sym, d):
    try:
        import yfinance as yf
        sp = yf.Ticker(sym + ".NS").splits
        if len(sp):
            idx = pd.DatetimeIndex(sp.index).tz_localize(None).normalize()
            hit = sp[(idx >= pd.Timestamp(d) - pd.Timedelta(days=3)) & (idx <= pd.Timestamp(d) + pd.Timedelta(days=1))]
            if len(hit):
                return 1.0 / float(hit.iloc[-1])
    except Exception:                                            # noqa: BLE001
        pass
    return None


d = first
while d <= today:
    if d.weekday() >= 5:
        d += dt.timedelta(days=1)
        continue
    try:
        bhav, why = fetch_bhavcopy(d)
        source = "nse"
    except Exception as e:                                       # noqa: BLE001
        bhav, why, source = None, f"nse_error:{type(e).__name__}", "yahoo"
    if bhav is None and why.startswith("nse_error"):
        y, _ = yahoo_batch(sorted(listed), str(d), str(d + dt.timedelta(days=1)), log=lambda *_: None)
        if len(y) > 500:
            bhav = y.assign(prev_close=float("nan"), series="EQ")
            log.append(f"- {d}: NSE unreachable ({why}); used Yahoo, {len(y)} stocks")
    if bhav is None:
        log.append(f"- {d}: skipped ({why})")
        if d == today and why == "not_published":
            break
        d += dt.timedelta(days=1)
        continue

    bhav = bhav[bhav["symbol"].isin(listed)]
    # Validate against anything already stored for this date (the Yahoo backfill).
    old = hist[hist["date"] == pd.Timestamp(d)].set_index("symbol")["close"]
    note = ""
    if len(old):
        j = bhav.set_index("symbol")["close"].to_frame("nse").join(old.rename("old"), how="inner")
        diff = (j["nse"] / j["old"] - 1).abs()
        note = (f"; vs stored: {len(j)} common, {(diff > 0.01).sum()} differ >1%, "
                f"{(diff > 0.05).sum()} differ >5%, only-NSE {len(bhav) - len(j)}, only-stored {len(old) - len(j)}")
    # Corporate actions: NSE's previous close vs the close we hold, and impossible gaps.
    for r in bhav.itertuples():
        lc = last_close.get(r.symbol)
        if not lc or lc <= 0:
            continue
        factor, src = None, None
        if pd.notna(r.prev_close) and r.prev_close > 0 and abs(r.prev_close / lc - 1) > 0.02:
            factor, src = r.prev_close / lc, "nse_prev_close"
        elif abs(r.close / lc - 1) > 0.21:                       # beyond the widest circuit limit
            f = yahoo_split_factor(r.symbol, d)
            if f and abs(f - 1) > 0.02:
                factor, src = f, "yahoo_splits"
            else:
                unresolved.append(f"{d} {r.symbol}: close {lc:.2f} -> {r.close:.2f}, no split found")
        if factor:
            adj_rows.append({"symbol": r.symbol, "ex_date": str(d), "factor": round(factor, 6), "source": src})
    write_prices(bhav[COLS], replace_dates=True)
    for r in bhav.itertuples():
        last_close[r.symbol] = r.close
    done_dates.append(d)
    if source == "nse":
        state["last_bhav_date"] = str(d)
    log.append(f"- {d}: {len(bhav)} stocks from {source}{note}")

    # All NSE index closes for the day (kept for benchmarks and sector cross-checks).
    try:
        r = http_get(f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{d:%d%m%Y}.csv")
        if r.status_code == 200:
            ix = pd.read_csv(io.StringIO(r.text))
            ix.columns = [c.strip() for c in ix.columns]
            ix = pd.DataFrame({"date": pd.Timestamp(d), "index": ix["Index Name"].astype(str).str.strip(),
                               "open": pd.to_numeric(ix["Open Index Value"], errors="coerce"),
                               "high": pd.to_numeric(ix["High Index Value"], errors="coerce"),
                               "low": pd.to_numeric(ix["Low Index Value"], errors="coerce"),
                               "close": pd.to_numeric(ix["Closing Index Value"], errors="coerce")})
            p = DATA / "indices" / "indices.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists():
                o = pd.read_parquet(p)
                o = o[~((o["date"] == pd.Timestamp(d)) & o["index"].isin(ix["index"]))]
                ix = pd.concat([o, ix], ignore_index=True)
            ix.sort_values(["index", "date"]).to_parquet(p, index=False)
    except Exception as e:                                       # noqa: BLE001
        log.append(f"  - index file failed: {type(e).__name__}")
    time.sleep(1)
    d += dt.timedelta(days=1)

if adj_rows:
    a = pd.concat([load_adjustments().astype({"ex_date": str}), pd.DataFrame(adj_rows)], ignore_index=True)
    a["ex_date"] = pd.to_datetime(a["ex_date"]).dt.strftime("%Y-%m-%d")
    a.drop_duplicates(["symbol", "ex_date"], keep="last").to_csv(DATA / "meta" / "adjustments.csv", index=False)

state["last_run"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
write_state(state)
rep = ["# Daily update report", "", f"Run: {state['last_run']}; range {first} to {today}", "", "## Days", ""] + log
rep += ["", "## Corporate-action adjustments recorded", ""]
rep += [f"- {r['ex_date']} {r['symbol']}: factor {r['factor']} ({r['source']})" for r in adj_rows] or ["none"]
rep += ["", "## Large gaps with no split found (check manually)", ""] + ([f"- {u}" for u in unresolved] or ["none"])
(DATA / "reports").mkdir(exist_ok=True)
(DATA / "reports" / "daily_update.md").write_text("\n".join(rep) + "\n")
print("\n".join(rep))
print(f"::notice::{len(done_dates)} day(s) stored; last NSE date {state.get('last_bhav_date')}")
