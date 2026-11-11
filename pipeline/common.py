"""Shared helpers: paths, NSE downloads, monthly parquet storage, split adjustment."""
import datetime as dt
import io
import json
import os
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

DATA = Path(os.environ.get("DATA_DIR", "data"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
SERIES = {"EQ", "BE", "BZ"}          # normal, trade-for-trade, and Z-category equities
COLS = ["date", "symbol", "open", "high", "low", "close", "volume", "turnover"]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def today_ist() -> dt.date:
    return dt.datetime.now(IST).date()


def http_get(url: str, tries: int = 3):
    """GET with retries. Returns the response for 200/404, raises otherwise."""
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=45)
            if r.status_code in (200, 404):
                return r
            last = RuntimeError(f"HTTP {r.status_code} for {url}")
        except requests.RequestException as e:
            last = e
        time.sleep(3 * (i + 1))
    raise last


def symbols_master() -> pd.DataFrame:
    """NSE's list of listed equities (companies only, no ETFs)."""
    r = http_get("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv")
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"SYMBOL": "symbol", "NAME OF COMPANY": "name", "SERIES": "series",
                            "DATE OF LISTING": "listed", "ISIN NUMBER": "isin"})
    df = df[["symbol", "name", "series", "listed", "isin"]]
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
    (DATA / "meta").mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA / "meta" / "symbols.csv", index=False)
    return df


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    df = df[COLS].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["symbol"] = df["symbol"].astype(str)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype("float32")
    df["volume"] = df["volume"].astype("int64")
    df["turnover"] = df["turnover"].astype("float64")
    return df.sort_values(["date", "symbol"]).reset_index(drop=True)


def month_path(period) -> Path:
    return DATA / "prices" / f"{period.year}" / f"{period.year}-{period.month:02d}.parquet"


def write_prices(df: pd.DataFrame, replace_dates: bool = False) -> None:
    """Write rows into monthly files. With replace_dates, existing rows for the
    same dates are dropped first (the new source is authoritative for those days)."""
    df = normalise(df)
    for period, part in df.groupby(df["date"].dt.to_period("M")):
        p = month_path(period)
        p.parent.mkdir(parents=True, exist_ok=True)
        if replace_dates and p.exists():
            old = pd.read_parquet(p)
            old = old[~old["date"].isin(part["date"].unique())]
            part = normalise(pd.concat([old, part], ignore_index=True))
        part.to_parquet(p, index=False, compression="zstd")


def load_raw(start=None) -> pd.DataFrame:
    files = sorted((DATA / "prices").glob("*/*.parquet"))
    if start is not None:
        s = pd.Timestamp(start).to_period("M")
        files = [f for f in files if pd.Period(f.stem, "M") >= s]
    if not files:
        return pd.DataFrame(columns=COLS)
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start)]
    return df


def load_adjustments() -> pd.DataFrame:
    p = DATA / "meta" / "adjustments.csv"
    if p.exists():
        return pd.read_csv(p, parse_dates=["ex_date"])
    return pd.DataFrame(columns=["symbol", "ex_date", "factor", "source"])


def load_prices(start=None, adjusted: bool = True) -> pd.DataFrame:
    """Price history. Stored rows are as-recorded; splits and bonuses that happened
    after a row was stored are applied here from meta/adjustments.csv."""
    df = load_raw(start)
    if not adjusted or df.empty:
        return df
    adj = load_adjustments()
    for r in adj.itertuples():
        m = (df["symbol"] == r.symbol) & (df["date"] < r.ex_date)
        if m.any():
            for c in ("open", "high", "low", "close"):
                df.loc[m, c] = (df.loc[m, c] * r.factor).astype("float32")
            df.loc[m, "volume"] = (df.loc[m, "volume"] / r.factor).round().astype("int64")
    return df


def read_state() -> dict:
    p = DATA / "meta" / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def write_state(state: dict) -> None:
    (DATA / "meta").mkdir(parents=True, exist_ok=True)
    (DATA / "meta" / "state.json").write_text(json.dumps(state, indent=2, default=str))


def fetch_bhavcopy(d: dt.date):
    """Official NSE cash-market bhavcopy for one day.
    Returns (DataFrame, None) on success, (None, reason) otherwise."""
    url = (f"https://nsearchives.nseindia.com/content/cm/"
           f"BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")
    r = http_get(url)
    if r.status_code == 404:
        return None, "not_published"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    raw = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
    raw.columns = [c.strip() for c in raw.columns]
    dates = set(raw["TradDt"].astype(str).str.strip())
    if dates != {f"{d:%Y-%m-%d}"}:          # NSE sometimes serves a stale copy on holidays
        return None, f"stale_file(dates={sorted(dates)[:3]})"
    raw["SctySrs"] = raw["SctySrs"].astype(str).str.strip()
    raw = raw[(raw["FinInstrmTp"].astype(str).str.strip() == "STK") & raw["SctySrs"].isin(SERIES)]
    out = pd.DataFrame({
        "date": pd.Timestamp(d), "symbol": raw["TckrSymb"].astype(str).str.strip(),
        "open": raw["OpnPric"], "high": raw["HghPric"], "low": raw["LwPric"],
        "close": raw["ClsPric"], "volume": raw["TtlTradgVol"], "turnover": raw["TtlTrfVal"],
        "prev_close": raw["PrvsClsgPric"], "series": raw["SctySrs"]})
    out = out.dropna(subset=["close"]).drop_duplicates("symbol")
    return out.reset_index(drop=True), None


def yahoo_batch(symbols, start, end=None, batch=80, pause=1.5, log=print):
    """Daily OHLCV from Yahoo (split-adjusted, not dividend-adjusted) for NSE symbols."""
    import yfinance as yf
    frames, failed = [], []
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        tick = [s + ".NS" for s in chunk]
        try:
            df = yf.download(tick, start=start, end=end, interval="1d", auto_adjust=False,
                             actions=False, group_by="ticker", threads=True, progress=False)
        except Exception as e:                                   # noqa: BLE001
            log(f"batch {i} failed: {type(e).__name__}: {str(e)[:120]}")
            failed += chunk
            time.sleep(20)
            continue
        got = 0
        lvl0 = set(df.columns.get_level_values(0)) if isinstance(df.columns, pd.MultiIndex) else set()
        for s, t in zip(chunk, tick):
            if t not in lvl0:
                failed.append(s)
                continue
            sub = df[t].dropna(subset=["Close"])
            if sub.empty:
                failed.append(s)
                continue
            idx = pd.DatetimeIndex(sub.index)
            if idx.tz is not None:
                idx = idx.tz_convert("Asia/Kolkata").tz_localize(None)
            frames.append(pd.DataFrame({
                "date": idx.normalize(), "symbol": s, "open": sub["Open"].values,
                "high": sub["High"].values, "low": sub["Low"].values,
                "close": sub["Close"].values, "volume": sub["Volume"].fillna(0).values}))
            got += 1
        log(f"batch {i // batch + 1}/{(len(symbols) - 1) // batch + 1}: {got}/{len(chunk)} ok")
        time.sleep(pause)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLS[:-1])
    if not out.empty:
        out = out[(out["close"] > 0) & (out["volume"] > 0)]
        tp = (out["high"] + out["low"] + out["close"]) / 3
        out["turnover"] = tp * out["volume"]                    # approximation; NSE gives exact
    return out, failed
