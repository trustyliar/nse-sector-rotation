"""Keep long history for the benchmark indices that the NSE daily file only supplies going forward."""
import pandas as pd
import yfinance as yf

from common import DATA

WANT = {"Nifty Smallcap 100": "^CNXSC", "Nifty Midcap 100": "NIFTY_MIDCAP_100.NS", "Nifty 500": "^CRSLDX", "Nifty 50": "^NSEI"}
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
    allx = pd.concat([new, old]).drop_duplicates(["index", "date"], keep="last")   # NSE's own rows win where both exist
    allx.sort_values(["index", "date"]).to_parquet(p, index=False)
