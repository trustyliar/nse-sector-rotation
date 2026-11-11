"""Market regime score (0-100) from breadth, participation and breakout follow-through.

Every component is a naturally bounded percentage, combined with equal weights: nothing is
fitted, which keeps the score from being tuned to the past. Run nightly after daily_update."""
import numpy as np
import pandas as pd

from common import DATA, load_prices

MIN_TURNOVER = 1e7        # Rs 1 crore median daily traded value
# Zones are provisional. The backtest (research/) supports 55+ as better than below 55 in both
# 2019-23 and 2024-26, but does NOT show that 70+ beats 55-70, so there is no leverage tier.
ZONES = [(0, "Weak"), (40, "Mixed"), (55, "Favourable")]


def wide(df):
    w = {c: df.pivot(index="date", columns="symbol", values=c) for c in ("close", "high", "low", "volume", "turnover")}
    return w


def signals(w):
    """Per-stock daily flags shared by the regime score and the backtest."""
    c, v = w["close"], w["volume"]
    liquid = (w["turnover"].rolling(20, min_periods=10).median().shift(1) >= MIN_TURNOVER) & (c >= 20)
    ret = c.pct_change(fill_method=None)
    ma20, ma50, ma200 = (c.rolling(n, min_periods=n).mean() for n in (20, 50, 200))
    s = {"liquid": liquid, "ret": ret, "ma20": ma20, "ma50": ma50, "ma200": ma200}
    s["breakout"] = (liquid & (c >= 40) & (c > c.shift(1).rolling(50, min_periods=50).max())
                     & (v >= 1.5 * v.shift(1).rolling(50, min_periods=30).mean())
                     & (c > ma50) & (ma50 > ma200))
    return s


def compute(w, s=None):
    s = s or signals(w)
    c, liquid, ret = w["close"], s["liquid"], s["ret"]
    n = liquid.sum(axis=1).replace(0, np.nan)
    out = pd.DataFrame(index=c.index)
    out["universe"] = n
    up, dn = ((ret >= 0.04) & liquid).sum(axis=1), ((ret <= -0.04) & liquid).sum(axis=1)
    out["up4"], out["down4"] = up, dn
    u10, d10 = up.rolling(10).sum(), dn.rolling(10).sum()
    out["thrust"] = 100 * u10 / (u10 + d10).replace(0, np.nan)                  # A: 10-day share of +4% vs -4% days
    for k, name in ((20, "above20"), (50, "above50"), (200, "above200")):       # B, C, (F)
        ma = s[f"ma{k}"]
        out[name] = 100 * ((c > ma) & liquid).sum(axis=1) / (liquid & ma.notna()).sum(axis=1).replace(0, np.nan)
    hi = ((c >= c.rolling(250, min_periods=200).max()) & liquid).sum(axis=1).rolling(20).sum()
    lo = ((c <= c.rolling(250, min_periods=200).min()) & liquid).sum(axis=1).rolling(20).sum()
    out["highs"] = 100 * hi / (hi + lo).replace(0, np.nan)                      # E: 52-week highs vs lows, 20 days
    bo = s["breakout"]
    held = cnt = 0
    for k in range(1, 11):                                                      # D: are recent breakouts holding?
        b = bo.shift(k).fillna(False).astype(bool)
        held = held + (b & (c >= c.shift(k))).sum(axis=1)
        cnt = cnt + (b & c.notna()).sum(axis=1)
    out["breakouts10"] = cnt
    out["follow"] = (100 * held / cnt.replace(0, np.nan)).fillna(0) * np.minimum(1, cnt / 15)
    comp = ["thrust", "above20", "above50", "highs", "follow"]
    out["score"] = out[comp].mean(axis=1, skipna=False).round(1)
    z = pd.cut(out["score"], [-1] + [a for a, _ in ZONES[1:]] + [101], labels=[b for _, b in ZONES], right=False)
    out["zone"] = z.astype(object)
    return out.dropna(subset=["score"])


if __name__ == "__main__":
    w = wide(load_prices())
    r = compute(w)
    (DATA / "derived").mkdir(exist_ok=True)
    r.round(2).to_csv(DATA / "derived" / "regime.csv")
    print(r.tail(5)[["score", "zone", "thrust", "above20", "above50", "highs", "follow", "up4", "down4"]].to_string())
