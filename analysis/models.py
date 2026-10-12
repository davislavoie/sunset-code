"""Which Open-Meteo cloud model matches the photos and the scores best?

Points: over each camera and 13/40/80/150 km out on bearings 240/260/280/300 (a day uses the bearing
nearest its sunset azimuth, at most 10 deg off). Hourly cloud_cover (+low/mid/high, +850/700/500 hPa)
from the historical-forecast API for several models, read 1 h before sunset. Cached in
analysis_export/openmeteo/models_*.json.

    python analysis/models.py      # writes models.md
"""

import json
import time

import numpy as np
import pandas as pd
import requests

import data
from analyze import cv, scores

MODELS = ["best_match", "gfs_hrrr", "ecmwf_ifs025", "gem_hrdps_continental", "icon_seamless"]
VARS = ["cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
        "cloud_cover_850hPa", "cloud_cover_700hPa", "cloud_cover_500hPa"]
BEARINGS = [240, 260, 280, 300]
KM = [13, 40, 80, 150]
CENTERS = {"btv_echo_cam": "btv_echo_cam", "wcax_tower_sunset": "btv_echo_cam", "bolton_summit_cam": "bolton_summit_cam"}


def fetch(center, model, start, end):
    lat0, lon0, _ = data.LOCATION[center]
    pts = [(0, 0, lat0, lon0)] + [(b, km, *data.destination(lat0, lon0, b, km)) for b in BEARINGS for km in KM]
    path = data.EXPORT / "openmeteo" / f"models_{center}_{model}.json"
    if not path.exists():
        for _ in range(20):
            resp = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", timeout=300, params={
                "latitude": ",".join(f"{p[2]:.4f}" for p in pts), "longitude": ",".join(f"{p[3]:.4f}" for p in pts),
                "hourly": ",".join(VARS), "models": model, "start_date": str(start), "end_date": str(end),
                "timezone": "GMT", "timeformat": "unixtime"})
            if resp.status_code == 429:
                print("  429, waiting 60 s", flush=True)
                time.sleep(60)
                continue
            resp.raise_for_status()
            path.write_text(resp.text)
            break
    frames = {}
    for (b, km, _, _), loc in zip(pts, json.loads(path.read_text())):
        h = pd.DataFrame(loc["hourly"])
        frames[(b, km)] = h.set_index(pd.to_datetime(h.pop("time"), unit="s", utc=True))
    return frames


def features(d):
    start, end = min(d.day), max(d.day)
    rows = []
    for model in MODELS:
        grids = {c: fetch(c, model, start, end) for c in sorted(set(CENTERS.values()))}
        for cam, day in d[["camera", "day"]].itertuples(index=False):
            when, az = data.sun_time_and_bearing(day, cam)
            g = grids[CENTERS[cam]]
            t = pd.Timestamp(when) - pd.Timedelta(hours=1)
            at = lambda key: g[key].iloc[g[key].index.get_indexer([t], method="nearest")[0]]
            b = min(BEARINGS, key=lambda x: abs(x - az))
            over, path = at((0, 0)), [at((b, km)) for km in KM]
            row = {"camera": cam, "day": day, "model": model, "total_over": over.cloud_cover,
                   **{f"{l}_over": over[f"cloud_cover_{l}"] for l in ("low", "mid", "high", "850hPa", "700hPa", "500hPa")}}
            for l in ("low", "mid", "high", "850hPa", "700hPa", "500hPa"):
                row[f"{l}_near"] = np.mean([p[f"cloud_cover_{l}"] for p in path[:2]])
                row[f"{l}_far"] = np.mean([p[f"cloud_cover_{l}"] for p in path[2:]])
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    t = pd.read_parquet(data.EXPORT / "analysis_table.parquet")
    d = t[t.camera.isin(CENTERS)].dropna(subset=["y_pct"]).reset_index(drop=True)[["camera", "day", "month", "y_pct"]]
    f = features(d)
    v = pd.DataFrame(map(json.loads, (data.EXPORT / "vision_qwen3-vl_4b.jsonl").read_text().splitlines()))
    v = v.drop_duplicates(["camera", "day"], keep="last").assign(day=lambda x: pd.to_datetime(x.day).dt.date)
    for cam in CENTERS:
        d[f"is_{cam}"] = (d.camera == cam).astype(int)
    std = ["low_near", "low_far", "mid_near", "mid_far", "high_near", "high_far", "total_over", "low_over", "mid_over", "high_over"]
    plev = [c for c in f if c.startswith(("850", "700", "500"))]
    cams = [f"is_{c}" for c in CENTERS]
    res = []
    for model, g in f.groupby("model", sort=False):
        m = d.merge(g, on=["camera", "day"])
        mv = m.merge(v[["camera", "day", "cloud_cover", "horizon_clear"]], on=["camera", "day"])
        row = {"model": model, "n": len(m), "missing %": round(100 * m[std].isna().any(axis=1).mean(), 1),
               "rho photo cover vs total_over": mv.cloud_cover.corr(mv.total_over, method="spearman"),
               "rho photo horizon_clear vs low_far": mv.horizon_clear.astype(int).corr(mv.low_far, method="spearman"),
               "rho score vs total_over": m.total_over.corr(m.y_pct, method="spearman"),
               "rho score vs low_far": m.low_far.corr(m.y_pct, method="spearman")}
        for name, feats in (("AUC low/mid/high", std), ("AUC + pressure levels", std + plev), ("AUC pressure levels only", plev)):
            row[name] = scores(m, cv(m, feats + cams, "y_pct", "ridge"))["AUC(top 25%)"]
        res.append(row)
    # All models together (does a second model add to the first?)
    wide = d.copy()
    for model, g in f.groupby("model", sort=False):
        wide = wide.merge(g.drop(columns="model").add_suffix(f"@{model}").rename(
            columns={f"camera@{model}": "camera", f"day@{model}": "day"}), on=["camera", "day"])
    combo = {}
    for a in MODELS:
        for b in MODELS:
            if a < b:
                feats = [f"{c}@{a}" for c in std] + [f"{c}@{b}" for c in std] + cams
                combo[f"{a} + {b}"] = scores(wide, cv(wide, feats, "y_pct", "ridge"))["AUC(top 25%)"]
    out = [f"# Cloud models compared, 1 h before sunset ({len(d)} sunset camera-days; photo checks on the 160 vision days)\n",
           "AUC = leave-one-month-out ridge, top-25 % day. 'photo cover' is the vision model's cloud_cover on the 1h-pre photo.\n",
           pd.DataFrame(res).round(3).to_markdown(index=False),
           "\n## Two models together (low/mid/high near/far/over from each)\n",
           pd.Series(combo).sort_values(ascending=False).round(3).to_frame("AUC").to_markdown()]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "models.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
