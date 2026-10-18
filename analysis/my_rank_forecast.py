"""Does the forecast predict *your* ranking (My ranking), and does training on it help?

Same shots and inputs as horizons.py (as live), on the btv_echo_cam days you've ranked. Target: your score
as a percentile among your ranked days. Leave-one-month-out throughout.

  live      the coefficients in ai_analysis/predict_coefs.json (fitted on the HSV score, all cameras)
  hsv-fit   the same features refitted on these days' HSV percentile
  mine-fit  the same features refitted on your percentile
  +aod      mine-fit plus Open-Meteo aerosol optical depth at sunset (air-quality API; haze/smoke)

  python analysis/my_rank_forecast.py   (needs analysis_export/ and my_rank_days.parquet from my_rank_frames.py)
"""

import json
import urllib.request

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import data
import horizons
from horizons import HORIZONS, predict

CAMERA = "btv_echo_cam"
AQ_URL = ("https://air-quality-api.open-meteo.com/v1/air-quality?latitude={}&longitude={}"
          "&hourly=aerosol_optical_depth&start_date={}&end_date={}&timezone=GMT")


def aod_at_sunset(days):
    """Aerosol optical depth at each day's sunset hour (local sunset rounded to the hour)."""
    lat, lon, _ = data.LOCATION[CAMERA]
    with urllib.request.urlopen(AQ_URL.format(lat, lon, min(days), max(days)), timeout=60) as r:
        h = json.load(r)["hourly"]
    aod = pd.Series(h["aerosol_optical_depth"], index=pd.to_datetime(h["time"], utc=True))
    return {d: aod.get(pd.Timestamp(data.sun_time_and_bearing(pd.Timestamp(d).date(), CAMERA)[0]).tz_convert("UTC").round("h"))
            for d in days}


def live(g, h):
    m = next(m for m in predict.MODELS if h in m["coefs"] and all(g[f].notna().all() for f in m["features"]))
    c = np.array(m["coefs"][h])
    return np.clip(np.c_[np.ones(len(g)), g[m["features"]].values] @ c, 0, 1), m["name"]


def main():
    mine = pd.read_parquet(data.EXPORT / "my_rank_days.parquet")
    mine["mine_pct"] = mine.score.rank(pct=True)
    t = horizons.build()
    t = t[t.camera == CAMERA].merge(mine[["date", "mine_pct"]], left_on=t[t.camera == CAMERA].day.astype(str),
                                    right_on="date")
    t["hsv_pct"] = t.groupby("horizon").y.rank(pct=True)
    t["aod"] = t.day.astype(str).map(aod_at_sunset(sorted(t.day.astype(str).unique())))
    feats = horizons.SETS["base"]
    rows = []
    for h in HORIZONS:
        g = t[t.horizon == h].dropna(subset=feats + ["aod"]).reset_index(drop=True)
        preds = {"live": live(g, h)[0],
                 "hsv-fit": horizons.lomo(g.assign(pct=g.hsv_pct), feats),
                 "mine-fit": horizons.lomo(g.assign(pct=g.mine_pct), feats),
                 "+aod": horizons.lomo(g.assign(pct=g.mine_pct), feats + ["aod"])}
        for name, p in preds.items():
            rows.append({"horizon": h, "model": name, "days": len(g),
                         "spearman vs mine": spearmanr(p, g.mine_pct)[0],
                         "AUC my top-25%": roc_auc_score(g.mine_pct >= .75, p)})
    r = pd.DataFrame(rows)
    text = ("# Forecast vs your ranking (btv_echo_cam, leave-one-month-out)\n\n"
            + r.pivot_table(index="horizon", columns="model", values="spearman vs mine", sort=False).round(3).to_markdown()
            + "\n\nAUC for your top-25 % days\n\n"
            + r.pivot_table(index="horizon", columns="model", values="AUC my top-25%", sort=False).round(3).to_markdown()
            + f"\n\n{r.days.min()}-{r.days.max()} days per horizon.\n")
    (data.ROOT / "analysis" / "my_rank_forecast.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
