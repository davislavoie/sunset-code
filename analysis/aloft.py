"""Upper-level wind (850/700/500 hPa) and cloud motion along the sun line: does it help the 2h/1h forecast?

along_<lvl>_<h> = wind speed (km/h) * cos(wind-from direction - sun azimuth): > 0 means the wind blows from
the sunset side, so the cloud now out on the path is moving toward the camera; < 0 means it is moving away.
inflow_* = far-path low (or mid) cloud * the toward-camera component: low cloud on its way to block the sun.

    python analysis/aloft.py      # writes aloft.md
"""

import json

import numpy as np
import pandas as pd
import requests

import data
from analyze import ENGINEERED, MET, STORED_PATH, cv, scores

LEVELS = ["850hPa", "700hPa", "500hPa"]
CENTERS = {"btv_echo_cam": "btv_echo_cam", "wcax_tower_sunset": "btv_echo_cam", "bolton_summit_cam": "bolton_summit_cam"}


def hourly(days):
    path = data.EXPORT / "openmeteo" / "aloft.json"
    centers = sorted(set(CENTERS.values()))
    if not path.exists():
        resp = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", timeout=300, params={
            "latitude": ",".join(str(data.LOCATION[c][0]) for c in centers),
            "longitude": ",".join(str(data.LOCATION[c][1]) for c in centers),
            "hourly": ",".join(f"wind_{v}_{l}" for l in LEVELS for v in ("speed", "direction")),
            "start_date": str(min(days)), "end_date": str(max(days)), "timezone": "GMT", "timeformat": "unixtime"})
        resp.raise_for_status()
        path.write_text(resp.text)
    out = {}
    for c, loc in zip(centers, json.loads(path.read_text())):
        h = pd.DataFrame(loc["hourly"])
        out[c] = h.set_index(pd.to_datetime(h.pop("time"), unit="s", utc=True))
    return out


def features(d):
    w = hourly(list(d.day))
    rows = []
    for cam, day in d[["camera", "day"]].itertuples(index=False):
        when, az = data.sun_time_and_bearing(day, cam)
        h = w[CENTERS[cam]]
        row = {"camera": cam, "day": day}
        for tag, back in (("h1", 1), ("h2", 2)):
            i = h.index.get_indexer([pd.Timestamp(when) - pd.Timedelta(hours=back)], method="nearest")[0]
            for l in LEVELS:
                spd, frm = h[f"wind_speed_{l}"].iloc[i], h[f"wind_direction_{l}"].iloc[i]
                row[f"along_{l[:3]}_{tag}"] = spd * np.cos(np.radians(frm - az))
                row[f"speed_{l[:3]}_{tag}"] = spd
        rows.append(row)
    f = pd.DataFrame(rows)
    d = d.merge(f, on=["camera", "day"])
    for tag in ("h1", "h2"):
        d[f"inflow_low_{tag}"] = d[f"low_far_{tag}"] * d[f"along_850_{tag}"].clip(lower=0)
        d[f"inflow_mid_{tag}"] = d[f"mid_path_{tag}"] * d[f"along_700_{tag}"].clip(lower=0)
        d[f"outflow_over_{tag}"] = (d[f"mid_over_{tag}"] + d[f"high_over_{tag}"]) * (-d[f"along_500_{tag}"]).clip(lower=0)
    return d


def main():
    t = pd.read_parquet(data.EXPORT / "analysis_table.parquet")
    d = t[t.camera.isin(CENTERS)].dropna(subset=["y_pct"]).reset_index(drop=True)
    d = features(d)
    for cam in CENTERS:
        d[f"is_{cam}"] = (d.camera == cam).astype(int)
    cams = [f"is_{c}" for c in CENTERS]
    out = [f"# Upper-level wind along the sun line ({len(d)} sunset camera-days)\n",
           "Target: the day's best score in the sunset window, as a percentile per camera. Leave-one-month-out.\n"]
    res = []
    for tag in ("h2", "h1"):
        base = [f"{e}_{tag}" for e in ENGINEERED] + [c for c in STORED_PATH + MET if c.endswith(tag)] + cams
        aloft = [c for c in d if c.endswith(tag) and c.split("_")[0] in ("along", "speed", "inflow", "outflow")]
        rho = {c: d[c].corr(d.y_pct, method="spearman") for c in aloft}
        out += [f"## {tag}: Spearman of each aloft feature with the outcome\n",
                pd.Series(rho).round(3).to_frame("rho").to_markdown(), "\n"]
        group = lambda p: [c for c in aloft if c.startswith(p)]
        for name, feats in (("weather", base), ("weather + aloft", base + aloft), ("aloft only", aloft + cams),
                            ("weather + speed", base + group("speed")), ("weather + along", base + group("along")),
                            ("weather + inflow/outflow", base + group("inflow") + group("outflow"))):
            for kind in ("ridge", "gbm"):
                res.append({"horizon": tag, "features": name, "model": kind, **scores(d, cv(d, feats, "y_pct", kind))})
    out += ["## Leave-one-month-out\n", pd.DataFrame(res).round(3).to_markdown(index=False)]
    # Does low cloud on its way in actually hurt? Split far-low-cloud days by the 850 hPa direction.
    far = d[d.low_far_h2 >= 30]
    split = far.assign(toward=far.along_850_h2 > 5, away=far.along_850_h2 < -5)
    out += ["\n## Days with far-path low cloud >= 30 % at 2h: wind toward vs away from the camera (850 hPa)\n",
            split.groupby(np.select([split.toward, split.away], ["toward (> 5 km/h)", "away (< -5 km/h)"], "light")).y_pct.agg(
                n="size", median="median", top25=lambda x: (x >= .75).mean()).round(2).to_markdown()]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "aloft.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
