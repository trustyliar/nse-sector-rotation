"""Score the trader's own past winners as of the evening before each entry."""
import os, subprocess, sys
import pandas as pd
sys.path.insert(0, "pipeline")
from common import load_raw
E = {"HAPPSTMNDS": ["2021-03-30", "2021-04-27", "2021-05-25"], "KDDL": ["2026-07-29"],
     "FCL": ["2022-08-04", "2022-08-30", "2026-08-06", "2026-09-04"], "MAZDOCK": ["2023-06-15", "2023-07-07", "2024-06-11"],
     "GRSE": ["2024-06-12"], "JKLAKSHMI": ["2022-11-23"], "GANECOS": ["2021-02-04"], "GARUDA": ["2025-08-12"],
     "GRWRHITECH": ["2023-09-25"], "GLAND": ["2026-06-23", "2026-07-28"], "HSCL": ["2024-08-19"], "FILATEX": ["2026-09-11", "2026-11-11"]}
days = pd.DatetimeIndex(sorted(load_raw("2020-06-01")["date"].unique()))
rows = []
for sym, ds in E.items():
    for d in ds:
        prev = days[days < pd.Timestamp(d)][-1]
        out = f"/tmp/asof/{prev.date()}"
        if not os.path.exists(out + "/all_scores.csv"):
            subprocess.run([sys.executable, "pipeline/sectors.py"], env={**os.environ, "ASOF": str(prev.date()), "OUT_DIR": out},
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        a = pd.read_csv(out + "/all_scores.csv", index_col=0); st = pd.read_csv(out + "/setups.csv")
        if sym not in a.index or pd.isna(a.at[sym, "quality"]):
            rows.append({"stock": sym, "entry": d, "note": "no data"}); continue
        r = a.loc[sym]; q = r.quality
        el = a[a.eligible & a.quality.notna()]
        tags = st.loc[st.symbol == sym, "tags"].iloc[0] if (st.symbol == sym).any() else ""
        why = [] if r.eligible else [k for k, ok in (("RS<70", r.rs >= 70), ("below 200d", r.above200), ("illiquid", r.liquid), ("ADR<2%", r.adr >= 0.02)) if not ok]
        rows.append({"stock": sym, "entry": d, "Q": round(q), "grade": "A+" if q >= 75 else "A" if q >= 65 else "B" if q >= 55 else "C",
                     "top%": round(100 * (el.quality > q).mean()) if r.eligible else None, "RS": r.rs, "run%": round(100 * r.runup),
                     "base": r.since, "off%": round(100 * r.depth), "vs20%": round(100 * r.vs20, 1), "r5/adr": round(r.rng5_adr, 1),
                     "mv": round(r.move, 2), "ti": round(r.tight, 2), "tr": round(r.trend, 2), "dr": round(r.dry, 2), "ba": round(r.baseS, 2),
                     "note": ("; ".join(why) + " | " if why else "") + tags})
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
t = pd.DataFrame(rows); print(t.to_string(index=False))
print("\ngrades:", t["grade"].value_counts().to_dict(), "| listed as candidate:", int((t["note"].fillna("").str.len() > 0).sum() - t["note"].fillna("").str.contains("RS<|below|illiq|ADR<|no data").sum()), "of", len(t))
