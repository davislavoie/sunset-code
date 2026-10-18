"""Does the height of the clouds toward the sun matter? GOES-East cloud-top height (ABI-L2-ACHAC).

The clear-sky mask (analysis/goes.md) says cloud or no cloud. Cloud-top height adds how high the top layer
is: high cloud (tops 6 km+, cirrus) is what lights up after sunset; low cloud far toward the sun blocks it.
Reading and zones are ai_analysis/goes.py (heights), as the live pipeline stores them. For each sunset
camera-day: the scan landed 1 h before sunset (h1) and at sunset (h0), cached in analysis_export/goes/heights/.

A higher layer hides any cloud under it, so the KBTV METAR (cloud layers seen from below, up to 12,000 ft;
analysis/goes.py) is tried alongside. Checked against the HSV score (sunset-window best, percentile; all sunset cameras) and your score
(My ranking, btv_echo_cam, my_rank_days.parquet from my_rank_frames.py).

    python analysis/cloud_height.py   (needs analysis_export/analysis_table.parquet and goes/*.json from goes.py)
"""

import json
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta

import numpy as np
import pandas as pd
import requests

import data
import goes as goes_analysis
from analyze import cv, scores

G = goes_analysis.G
CACHE = data.EXPORT / "goes" / "heights"
CACHE.mkdir(parents=True, exist_ok=True)
FIELDS = [f"{k}_{z}" for z in ("over", "near", "far") for k in ("top", "high", "mid", "low")]


def read_day(args):
    cam, day = args
    path = CACHE / f"{cam}_{day}.json"
    if path.exists():
        return json.loads(path.read_text())
    when, az = data.sun_time_and_bearing(pd.Timestamp(day).date(), cam)
    lat0, lon0, _ = data.LOCATION[goes_analysis.CENTERS[cam]]
    row = {"camera": cam, "day": str(day)}
    session = requests.Session()
    for tag, back in (("h1", 1), ("h0", 0)):
        try:
            got = G.observe_heights(when - timedelta(hours=back) + G.LATENCY, lat0, lon0, az, session) or {}
            row.update({f"{k.replace('goes_', '')}@{tag}": v for k, v in got.items()})
        except Exception as e:
            print(f"  {cam} {day} {tag}: {e}", flush=True)
            return None  # not cached: retried next run
    path.write_text(json.dumps(row))
    return row


def fetch(t):
    todo = list(t[["camera", "day"]].drop_duplicates().astype(str).itertuples(index=False, name=None))
    print(f"{len(todo)} camera-days", flush=True)
    rows = []
    # h5py holds a global lock even while waiting on the network, so use processes.
    with ProcessPoolExecutor(12) as pool:
        for i, row in enumerate(pool.map(read_day, todo, chunksize=4), 1):
            if row:
                rows.append(row)
            if i % 100 == 0:
                print(i, flush=True)
    return pd.DataFrame(rows).assign(day=lambda x: pd.to_datetime(x.day).dt.date)


def kind_of_sky(r, tag):
    """One label per day from the near and far fan: what the light has to get through."""
    v = lambda f: 0.0 if pd.isna(r.get(f"{f}@{tag}")) else r[f"{f}@{tag}"]
    if v("low_far") >= 0.5:
        return "low bank far toward the sun"
    if v("high_near") >= 0.3 and v("low_far") < 0.2:
        return "high cloud near, far side open"
    if pd.isna(r.get(f"top_near@{tag}")) and pd.isna(r.get(f"top_far@{tag}")):
        return "clear"
    if v("high_near") + v("low_near") < 0.1:
        return "mostly clear"
    return "mixed"


def photo_check(d):
    """The satellite layers 1 h before sunset vs the cloud type the vision model read off the 02_1h_pre photo
    (vision.py, analysis_export/vision_qwen3-vl_4b.jsonl) and, if present, hand labels in
    analysis_export/goes/heights_photo_labels.csv (camera, day, layer: clear / low / mid / high / mixed)."""
    out = []
    near = [f"{k}_near@h1" for k in ("high", "mid", "low")] + ["top_near@h1"]
    path = data.EXPORT / "vision_qwen3-vl_4b.jsonl"
    if path.exists():
        v = pd.DataFrame(map(json.loads, path.read_text().splitlines())).drop_duplicates(["camera", "day"], keep="last")
        v = v.assign(day=lambda x: pd.to_datetime(x.day).dt.date)[["camera", "day", "cloud_type"]]
        g = d.merge(v, on=["camera", "day"])
        out += [f"\n## Satellite layers vs the photo's cloud type (vision model, {len(g)} camera-days)\n",
                "Mean share of the near fan (5-40 km toward the sun) per layer, and median top (km), by what the photo shows.\n",
                g.groupby("cloud_type")[near].agg("mean").round(2).join(g.groupby("cloud_type").size().rename("days"))
                .to_markdown()]
    path = data.EXPORT / "goes" / "heights_photo_labels.csv"
    if path.exists():
        lab = pd.read_csv(path).assign(day=lambda x: pd.to_datetime(x.day).dt.date)
        g = d.merge(lab, on=["camera", "day"])
        sat = g[[f"{k}_near@h1" for k in ("high", "mid", "low")]].fillna(0)
        g["satellite"] = np.where(sat.sum(axis=1) < 0.1, "clear", sat.idxmax(axis=1).str.split("_").str[0])
        out += [f"\n## Satellite's main layer vs hand labels from the photos ({len(g)} camera-days)\n",
                pd.crosstab(g.layer, g.satellite).to_markdown(),
                f"\nAgree on {(g.layer == g.satellite).mean():.0%} (mixed labels count as misses).\n"]
    return out


def main():
    t = pd.read_parquet(data.EXPORT / "analysis_table.parquet")
    t = t[t.camera.isin(goes_analysis.CENTERS)].dropna(subset=["y_pct"])
    h = fetch(t)
    d = t.merge(h, on=["camera", "day"])
    mask = pd.DataFrame(json.loads(p.read_text()) for p in (data.EXPORT / "goes").glob("*_*.json"))
    mask = mask.assign(day=lambda x: pd.to_datetime(x.day).dt.date)
    d = d.merge(mask[["camera", "day"] + [c for c in mask if c.endswith("_g1h")]], on=["camera", "day"], how="left")
    d = d.merge(goes_analysis.metar(sorted(set(d.day))), on="day", how="left")
    mine = pd.read_parquet(data.EXPORT / "my_rank_days.parquet")
    mine = mine.assign(day=pd.to_datetime(mine.date).dt.date, mine_pct=mine.score.rank(pct=True))[["day", "mine_pct"]]
    dm = d[d.camera == "btv_echo_cam"].merge(mine, on="day")
    rho = lambda df, a, b: df[a].astype(float).corr(df[b], method="spearman")

    out = [f"# Cloud-top height toward the sun ({len(d)} sunset camera-days, {len(dm)} of them ranked by you)\n",
           "GOES-East cloud-top height (ABI-L2-ACHAC, ~10 km pixels, top layer only), 1 h before sunset (h1) "
           "and at sunset (h0). top = median height of the zone's cloud tops (km); high / mid / low = share of the zone "
           "with tops at 6 km+ / 2-6 km / under 2 km. Zones: overhead (15 km), near fan (5-40 km toward the sun), "
           "far fan (80-300 km).\n",
           "## Spearman with the outcome\n",
           pd.DataFrame({f"{f}@{tag}": {"HSV score (all cameras)": rho(d, f"{f}@{tag}", "y_pct"),
                                        "your score (btv, ranked days)": rho(dm, f"{f}@{tag}", "mine_pct")}
                         for tag in ("h1", "h0") for f in FIELDS}).T.round(3).to_markdown(),
           "\n## KBTV METAR 1 h before sunset (Spearman)\n",
           pd.DataFrame({c: {"HSV score (all cameras)": rho(d, c, "y_pct"), "your score (btv, ranked days)": rho(dm, c, "mine_pct")}
                         for c in ("metar_cover", "metar_ceiling", "metar_base")}).T.round(3).to_markdown()]

    d["sky"] = d.apply(kind_of_sky, axis=1, tag="h1")
    dm["sky"] = dm.apply(kind_of_sky, axis=1, tag="h1")
    by = d.groupby("sky").agg(days=("y_pct", "size"), hsv_pct=("y_pct", "mean"))
    by = by.join(dm.groupby("sky").agg(ranked_days=("mine_pct", "size"), your_pct=("mine_pct", "mean")))
    out += photo_check(d)
    out += ["\n## By kind of sky 1 h before sunset (mean percentile; 0.5 is an average day)\n",
            by.sort_values("hsv_pct", ascending=False).round(2).to_markdown()]

    for cam in goes_analysis.CENTERS:
        d[f"is_{cam}"] = (d.camera == cam).astype(int)
    cams = [f"is_{c}" for c in goes_analysis.CENTERS]
    mask_f = [f"{z}_g1h" for z in ("over", "near", "far", "fan") if f"{z}_g1h" in d]
    height_f = [f"{f}@h1" for f in FIELDS if not f.startswith("top")]  # top is None on clear zones
    metar_f = ["metar_cover", "metar_ceiling", "metar_base"]
    res = []
    for name, feats in (("cloud mask (what's live)", mask_f + cams), ("cloud mask + height", mask_f + height_f + cams),
                        ("height only", height_f + cams), ("cloud mask + METAR", mask_f + metar_f + cams),
                        ("cloud mask + height + METAR", mask_f + height_f + metar_f + cams)):
        for kind in ("ridge", "gbm"):
            res.append({"features": name, "model": kind, **scores(d, cv(d, feats, "y_pct", kind))})
    dm2 = dm.assign(month=pd.to_datetime(dm.day).dt.to_period("M").astype(str)).reset_index(drop=True)
    for name, feats in (("cloud mask, your score", mask_f), ("cloud mask + height, your score", mask_f + height_f),
                        ("cloud mask + METAR, your score", mask_f + metar_f),
                        ("cloud mask + height + METAR, your score", mask_f + height_f + metar_f)):
        res.append({"features": name, "model": "ridge", **scores(dm2, cv(dm2, feats, "mine_pct", "ridge"), "mine_pct")})
    out += ["\n## Leave-one-month-out, 1 h before sunset\n", pd.DataFrame(res).round(3).to_markdown(index=False)]
    text = "\n".join(out) + "\n"
    (data.ROOT / "analysis" / "cloud_height.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
