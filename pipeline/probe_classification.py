"""Probe which sources of industry classification are reachable from GitHub."""
import io, json, time, traceback, zipfile
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}

def show(label, fn):
    try:
        print(f"[{label}] {fn()}")
    except Exception as e:
        print(f"[{label}] ERROR {type(e).__name__}: {str(e)[:200]}")

def csv_probe(url):
    r = requests.get(url, headers=UA, timeout=30)
    t = r.text
    return f"HTTP {r.status_code} rows={t.count(chr(10))} head={t[:300]!r}"

for u in ["https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
          "https://nsearchives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv",
          "https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
          "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv",
          "https://niftyindices.com/IndexConstituent/ind_niftytotalmarket_list.csv"]:
    show(u.split("/")[2] + " " + u.split("/")[-1], lambda u=u: csv_probe(u))

def nse_api():
    s = requests.Session(); s.headers.update(UA)
    r0 = s.get("https://www.nseindia.com/", timeout=30)
    out = [f"home HTTP {r0.status_code} cookies={list(s.cookies.keys())}"]
    s.headers.update({"Referer": "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE"})
    for sym in ["RELIANCE", "KAYNES", "ZENTEC", "M&M", "NETWEB"]:
        r = s.get("https://www.nseindia.com/api/quote-equity",
                  params={"symbol": sym}, timeout=30)
        try:
            j = r.json(); out.append(f"{sym}: HTTP {r.status_code} {json.dumps(j.get('industryInfo'))}")
        except Exception:
            out.append(f"{sym}: HTTP {r.status_code} body={r.text[:120]!r}")
        time.sleep(0.5)
    return "\n   ".join(out)
show("nse quote api", nse_api)

def yahoo_info():
    import yfinance as yf
    out = []
    for sym in ["RELIANCE.NS", "KAYNES.NS", "ZENTEC.NS", "M&M.NS", "NETWEB.NS", "SHAILY.NS"]:
        i = yf.Ticker(sym).info
        out.append(f"{sym}: sector={i.get('sector')} | industry={i.get('industry')} | mcap={i.get('marketCap')}")
        time.sleep(0.3)
    return "\n   ".join(out)
show("yahoo info", yahoo_info)

def bhav_cols():
    r = requests.get("https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20261111_F_0000.csv.zip",
                     headers=UA, timeout=30)
    z = zipfile.ZipFile(io.BytesIO(r.content)); t = z.read(z.namelist()[0]).decode()
    L = t.splitlines()
    rel = [x for x in L if ",RELIANCE," in x][:2]
    import collections
    idx = L[0].split(",").index("SctySrs")
    series = collections.Counter(x.split(",")[idx] for x in L[1:])
    return f"file={z.namelist()[0]}\n   cols={L[0]}\n   {rel}\n   series={dict(series.most_common(12))}"
show("bhavcopy columns", bhav_cols)
