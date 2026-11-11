"""One-off check: can GitHub's servers download NSE and Yahoo EOD data?
Writes reports/access_test.md so the result can be read from the repo."""
import datetime as dt, io, time, zipfile, traceback
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
lines = ["# Data access test", "", f"Run (UTC): {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M}", ""]

def probe(label, url):
    try:
        r = requests.get(url, headers=UA, timeout=30)
        note = ""
        if r.status_code == 200:
            body = r.content
            if url.endswith(".zip"):
                z = zipfile.ZipFile(io.BytesIO(body))
                body = z.read(z.namelist()[0])
            text = body.decode("utf-8", "replace")
            rows = text.count("\n")
            note = f"rows={rows}; header=`{text.splitlines()[0][:160]}`"
        lines.append(f"- {label}: HTTP {r.status_code}, {len(r.content)} bytes. {note}")
        return r.status_code == 200
    except Exception as e:
        lines.append(f"- {label}: ERROR {type(e).__name__}: {str(e)[:150]}")
        return False

lines.append("## NSE static files")
for host in ("nsearchives.nseindia.com", "archives.nseindia.com"):
    probe(f"EQUITY_L ({host})", f"https://{host}/content/equities/EQUITY_L.csv")

lines += ["", "## NSE daily files, last 8 calendar days"]
today = dt.date.today()
for back in range(0, 8):
    d = today - dt.timedelta(days=back)
    if d.weekday() >= 5:
        continue
    lines.append(f"### {d:%Y-%m-%d (%a)}")
    probe("CM bhavcopy (new UDiFF)",
          f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")
    probe("sec_bhavdata_full",
          f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d:%d%m%Y}.csv")
    probe("index close",
          f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{d:%d%m%Y}.csv")
    time.sleep(1)

lines += ["", "## Yahoo Finance (yfinance)"]
try:
    import yfinance as yf
    lines.append(f"- yfinance version {yf.__version__}")
    t0 = time.time()
    one = yf.download("RELIANCE.NS", period="1mo", interval="1d", progress=False, auto_adjust=True)
    lines.append(f"- single ticker RELIANCE.NS: {len(one)} rows in {time.time()-t0:.1f}s")
    batch = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","SBIN.NS","ITC.NS","LT.NS",
             "BHARTIARTL.NS","AXISBANK.NS","KOTAKBANK.NS","MARUTI.NS","SUNPHARMA.NS","TITAN.NS",
             "BAJFINANCE.NS","HAL.NS","BEL.NS","DIXON.NS","POLYCAB.NS","KAYNES.NS","CDSL.NS","BSE.NS",
             "MAZDOCK.NS","COCHINSHIP.NS","ZENTEC.NS","NETWEB.NS","KPITTECH.NS","PERSISTENT.NS",
             "TRENT.NS","SUZLON.NS","IREDA.NS","RVNL.NS","IRFC.NS","NHPC.NS","PFC.NS","RECLTD.NS",
             "APARINDS.NS","CGPOWER.NS","SIEMENS.NS","ABB.NS"]
    t0 = time.time()
    df = yf.download(batch, period="5y", interval="1d", progress=False, auto_adjust=True,
                     group_by="ticker", threads=True)
    ok = [t for t in batch if t in df.columns.get_level_values(0) and df[t]["Close"].notna().sum() > 0]
    lines.append(f"- batch of {len(batch)} tickers, 5y daily: {len(ok)} returned data, "
                 f"{len(df)} rows, {time.time()-t0:.1f}s")
    missing = sorted(set(batch) - set(ok))
    if missing:
        lines.append(f"- no data for: {', '.join(missing)}")
    idx = yf.download("^NSEI", period="1mo", interval="1d", progress=False, auto_adjust=True)
    lines.append(f"- Nifty 50 index (^NSEI): {len(idx)} rows")
except Exception:
    lines.append("- yfinance FAILED:\n```\n" + traceback.format_exc()[-800:] + "\n```")

print("\n".join(lines))
import os
os.makedirs("reports", exist_ok=True)
open("reports/access_test.md", "w").write("\n".join(lines) + "\n")
