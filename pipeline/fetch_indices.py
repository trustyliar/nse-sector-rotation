"""Keep long history for the benchmark indices that the NSE daily file only supplies going forward."""
import pandas as pd
import yfinance as yf

from common import DATA, today_ist

WANT = {"Nifty 500": "^CRSLDX", "Nifty 50": "^NSEI"}      # Yahoo has no usable history for the small and mid-cap indices
p = DATA / "indices" / "indices.parquet"
old = pd.read_parquet(p)
frames = []
for name, tick in WANT.items():
    try:
        d = yf.download(tick, start="2019-01-01", interval="1d", auto_adjust=False, progress=False,
                        multi_level_index=False).dropna(subset=["Close"])
        i = pd.DatetimeIndex(d.index)
        i = i.tz_convert("Asia/Kolkata").tz_localize(None) if i.tz is not None else i
        frames.append(pd.DataFrame({"date": i.normalize(), "index": name, "open": d["Open"].values, "high": d["High"].values,
                                    "low": d["Low"].values, "close": d["Close"].values}))
        print(name, len(d), "rows to", i.max().date())
    except Exception as e:                                       # noqa: BLE001
        print(name, "failed:", e)
if frames:
    new = pd.concat(frames)
    new = new[new["date"] < pd.Timestamp(today_ist())]          # today's bar is intraday until NSE publishes the close
    old = old[~((old["index"].isin(["Nifty Smallcap 100", "Nifty Midcap 100"])) | (old["date"] >= pd.Timestamp(today_ist())))]
    allx = pd.concat([new, old]).drop_duplicates(["index", "date"], keep="last")   # NSE's own rows win where both exist
    allx.sort_values(["index", "date"]).to_parquet(p, index=False)
