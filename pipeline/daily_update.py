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

from common import (DATA, COLS, IST, fetch_bhavcopy, http_get, load_adjustments, load_raw, read_state,
                    symbols_master, today_ist, write_prices, write_state, yahoo_batch)

state = read_state()
today = today_ist()
if len(sys.argv) > 1 and sys.argv[1]:
    first = dt.date.fromisoformat(sys.argv[1])
elif state.get("last_bhav_date"):
    first = dt.date.fromisoformat(state["last_bhav_date"]) + dt.timedelta(days=1)
else:
    first = today - dt.timedelta(days=9)        # first run: overlap the Yahoo backfill to validate it

RESET = len(sys.argv) > 2 and sys.argv[2] == "reset"
if RESET and (DATA / "meta" / "adjustments.csv").exists():
    (DATA / "meta" / "adjustments.csv").unlink()

master = symbols_master()
listed = set(master["symbol"])
hist = load_raw(first - dt.timedelta(days=40))
last_close = (hist[hist["date"] < pd.Timestamp(first)].sort_values("date")
              .groupby("symbol")["close"].last().to_dict())
adj_rows, log, done_dates, unresolved, warnings = [], [], [], [], []

source = ""
d = first
while d <= today:
    try:
        bhav, why = fetch_bhavcopy(d)
        source = "nse"
    except Exception as e:                                       # noqa: BLE001
        bhav, why, source = None, f"nse_error:{type(e).__name__}", "yahoo"
    # NSE publishes its official file some hours after the 3:30 pm close. For a 4 pm refresh, use Yahoo's
    # closing prices as provisional; the next run after NSE publishes replaces them with the official ones.
    now = dt.datetime.now(IST)
    early = why == "not_published" and d == today and d.weekday() < 5 and now.hour * 60 + now.minute >= 15 * 60 + 40
    if bhav is None and (str(why).startswith("nse_error") or early):
        y, _ = yahoo_batch(sorted(listed), str(d), str(d + dt.timedelta(days=1)), log=lambda *_: None)
        if len(y) > 500:
            bhav = y.assign(prev_close=float("nan"), series="EQ")
            source = "yahoo"
            log.append(f"- {d}: NSE unreachable ({why}); used Yahoo, {len(y)} stocks")
    if bhav is None:
        if d.weekday() < 5 or why != "not_published":
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
    # Integrity: NSE's previous close should equal the close we already hold.
    # A broad mismatch means a trading session is missing from the store.
    chk = [(r.prev_close, last_close[r.symbol]) for r in bhav.itertuples()
           if r.symbol in last_close and pd.notna(r.prev_close) and r.prev_close > 0]
    if chk:
        bad = sum(abs(a / b - 1) > 0.02 for a, b in chk)
        note += f"; prev-close mismatches {bad}/{len(chk)}"
        if bad > 0.2 * len(chk):
            warnings.append(f"{d}: {bad} of {len(chk)} previous closes disagree - a session may be missing")
    for r in bhav.itertuples():
        lc = last_close.get(r.symbol)
        if lc and lc > 0 and abs(r.close / lc - 1) > 0.21:       # beyond the widest circuit limit
            unresolved.append((r.symbol, str(d), lc, r.close))
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

# ---- Splits and bonuses: compare stored (as-traded) closes with Yahoo's split-adjusted series.
# Before an ex-date Yahoo/stored = the split factor, after it = 1; the step marks the ex-date.
win_start = first - dt.timedelta(days=16)
stored = load_raw(win_start)
try:
    yh, yfail = yahoo_batch(sorted(stored["symbol"].unique()), str(win_start),
                            str(today + dt.timedelta(days=1)), log=lambda *_: None)
except Exception as e:                                           # noqa: BLE001
    yh, yfail = pd.DataFrame(columns=COLS), [str(e)]
if yh["symbol"].nunique() < 0.8 * stored["symbol"].nunique():
    warnings.append(f"Yahoo cross-check unavailable ({yh['symbol'].nunique()} symbols returned); "
                    "split detection deferred to the next run")
else:
    m = stored[["date", "symbol", "close"]].merge(
        yh[["date", "symbol", "close"]].rename(columns={"close": "y"}), on=["date", "symbol"])
    m = m.sort_values(["symbol", "date"])
    m["ratio"] = m["y"] / m["close"]
    g = m.groupby("symbol")
    m["step"] = g["ratio"].shift(1) / m["ratio"]
    m["raw_ret"] = m["close"] / g["close"].shift(1)
    m["next_step"] = m.groupby("symbol")["step"].shift(-1)
    hit = m[(m["step"] - 1).abs() > 0.03].copy()
    hit = hit[(hit["raw_ret"] / hit["step"]).between(0.72, 1.39)]            # price really did step
    hit = hit[~((hit["next_step"] * hit["step"] - 1).abs() < 0.02)]          # not a one-day data glitch
    for r in hit.itertuples():
        adj_rows.append({"symbol": r.symbol, "ex_date": str(r.date.date()),
                         "factor": round(float(r.step), 6), "source": "yahoo_crosscheck"})
    recent = m[m["date"] >= pd.Timestamp(first)]
    off = recent[(recent["ratio"] - 1).abs() > 0.02]
    log.append(f"- Yahoo cross-check: {len(recent):,} stock-days compared since {first}, "
               f"{len(off)} differ >2% ({off['symbol'].nunique()} stocks)")

known = {(r["symbol"], r["ex_date"]) for r in adj_rows}
unresolved = [f"{dte} {sym}: close {a:.2f} -> {b:.2f}" for sym, dte, a, b in unresolved
              if (sym, dte) not in known]

if adj_rows:
    a = pd.concat([load_adjustments().astype({"ex_date": str}), pd.DataFrame(adj_rows)], ignore_index=True)
    a["ex_date"] = pd.to_datetime(a["ex_date"]).dt.strftime("%Y-%m-%d")
    a = a.drop_duplicates(["symbol", "ex_date"], keep="last").sort_values(["ex_date", "symbol"])
    a.to_csv(DATA / "meta" / "adjustments.csv", index=False)

state["provisional"] = str(done_dates[-1]) if done_dates and source == "yahoo" and done_dates[-1] == today else ""
state["last_run"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
write_state(state)
rep = ["# Daily update report", "", f"Run: {state['last_run']}; range {first} to {today}", "", "## Days", ""] + log
rep += ["", "## Corporate-action adjustments recorded", ""]
rep += [f"- {r['ex_date']} {r['symbol']}: factor {r['factor']} ({r['source']})" for r in adj_rows] or ["none"]
rep += ["", "## Moves beyond 21% with no split found (genuine move, listing pop, or check manually)", ""]
rep += [f"- {u}" for u in unresolved] or ["none"]
rep += ["", "## Warnings", ""] + ([f"- {w}" for w in warnings] or ["none"])
(DATA / "reports").mkdir(exist_ok=True)
(DATA / "reports" / "daily_update.md").write_text("\n".join(rep) + "\n")
print("\n".join(rep))
print(f"::notice::{len(done_dates)} day(s) stored; last NSE date {state.get('last_bhav_date')}")
