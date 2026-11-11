"""Audit large one-day jumps in the Yahoo-sourced history against NSE's official files.

For each jump, the official closes on that day and the previous session decide:
- NSE shows no such jump  -> Yahoo scale error; earlier history is rescaled to match.
- NSE shows the same jump -> real discontinuity (demerger, unadjusted split, news); left
  as is and listed for review.
Usage: repair_gaps.py [boundary YYYY-MM-DD]  (only dates before the boundary are audited)"""
import datetime as dt
import io
import sys
import time
import zipfile

import pandas as pd

from common import DATA, SERIES, fetch_bhavcopy, http_get, load_raw, read_state, write_prices, write_state

boundary = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "2026-10-19")
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_cache, src_count = {}, {}


def nse_closes(d: dt.date):
    """symbol -> official close for one day, trying NSE's three archive formats."""
    if d in _cache:
        return _cache[d]
    out, src = None, None
    try:
        b, _ = fetch_bhavcopy(d)
        if b is not None:
            out, src = dict(zip(b["symbol"], b["close"])), "udiff"
    except Exception:                                            # noqa: BLE001
        pass
    if out is None:
        try:
            r = http_get(f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d:%d%m%Y}.csv", tries=2)
            if r.status_code == 200:
                x = pd.read_csv(io.StringIO(r.text))
                x.columns = [c.strip() for c in x.columns]
                x["SERIES"] = x["SERIES"].astype(str).str.strip()
                dates = pd.to_datetime(x["DATE1"].astype(str).str.strip(), format="mixed", dayfirst=True).dt.date
                if set(dates) == {d}:
                    x = x[x["SERIES"].isin(SERIES)]
                    out, src = dict(zip(x["SYMBOL"].astype(str).str.strip(),
                                        pd.to_numeric(x["CLOSE_PRICE"], errors="coerce"))), "full"
        except Exception:                                        # noqa: BLE001
            pass
    if out is None:
        try:
            r = http_get(f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{d.year}/"
                         f"{MON[d.month - 1]}/cm{d:%d}{MON[d.month - 1]}{d.year}bhav.csv.zip", tries=2)
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                x = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
                x = x[x["SERIES"].astype(str).str.strip().isin(SERIES)]
                out, src = dict(zip(x["SYMBOL"].astype(str).str.strip(), x["CLOSE"])), "old"
        except Exception:                                        # noqa: BLE001
            pass
    src_count[src] = src_count.get(src, 0) + 1
    _cache[d] = out
    time.sleep(0.4)
    return out


df = load_raw().sort_values(["symbol", "date"]).reset_index(drop=True)
g = df.groupby("symbol")
df["prev_date"] = g["date"].shift(1)
df["prev_close"] = g["close"].shift(1)
df["ret"] = df["close"] / df["prev_close"] - 1
df["tv20"] = g["turnover"].transform(lambda s: s.rolling(20, min_periods=5).median().shift(1)) / 1e7
ev = df[((df["ret"] < -0.25) | (df["ret"] > 0.30)) & (df["date"] < boundary)].copy()
print(f"{len(ev)} jumps to audit across {ev['date'].nunique()} dates")

fixed, real, unverified = [], [], []
for r in ev.itertuples():
    cd, cp = nse_closes(r.date.date()), nse_closes(r.prev_date.date())
    a = (cd or {}).get(r.symbol)
    b = (cp or {}).get(r.symbol)
    row = [str(r.date.date()), r.symbol, round(r.ret, 3), None, round(r.tv20, 1) if pd.notna(r.tv20) else None]
    if not a or not b or pd.isna(a) or pd.isna(b) or b <= 0:
        unverified.append(row)
        continue
    nret = a / b - 1
    row[3] = round(nret, 3)
    k = (1 + r.ret) / (1 + nret)
    if abs(k - 1) > 0.10:                # Yahoo and NSE disagree about this day: rescale earlier history
        m = (df["symbol"] == r.symbol) & (df["date"] < r.date)
        for c in ("open", "high", "low", "close"):
            df.loc[m, c] = df.loc[m, c] * k
        df.loc[m, "volume"] = (df.loc[m, "volume"] / k).round()
        df.loc[m, "turnover"] = df.loc[m, "turnover"]          # value traded is unaffected by scale
        fixed.append(row + [round(k, 4)])
    else:
        real.append(row)

if fixed:
    write_prices(df)
state = read_state()
state["gap_audit"] = {"run": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "audited": len(ev),
                      "rescaled": len(fixed), "real": len(real), "unverified": len(unverified)}
write_state(state)


def table(rows, extra=False):
    head = "| Date | Symbol | Stored move | NSE move | Turnover (cr) |" + (" Rescale |" if extra else "")
    sep = "|---|---|---|---|---|" + ("---|" if extra else "")
    return [head, sep] + ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows]


rep = ["# Gap audit report", "",
       f"- Jumps audited (before {boundary.date()}): {len(ev)}",
       f"- Yahoo errors rescaled to match NSE: {len(fixed)}",
       f"- Real discontinuities left as is: {len(real)}",
       f"- Could not verify (no NSE file or symbol absent): {len(unverified)}",
       f"- NSE files by format: {src_count}",
       "", "## Rescaled", ""] + table(sorted(fixed), True)
rep += ["", "## Real discontinuities (demerger, unadjusted split, or news)", ""] + table(sorted(real))
rep += ["", "## Unverified", ""] + table(sorted(unverified))
(DATA / "reports").mkdir(exist_ok=True)
(DATA / "reports" / "gap_audit.md").write_text("\n".join(rep) + "\n")
print("\n".join(rep[:8]))
