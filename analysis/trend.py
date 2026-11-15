"""Does the trend in satellite cloud cover toward the sun improve the sunset forecast?

For every pre shot on the sunset cameras, goes_Z_trend = this shot's GOES zone Z (fan, far, near, over) minus the
previous pre shot's on the same camera and day, and goes_Z_rate = that per hour between the two captures. The 2h
shot has no earlier shot, so its "previous" is the scan from 60 minutes before its capture (ai_analysis.goes.observe,
only scans that had landed by then; cached in analysis_export/trend/earlier.jsonl, resumable). Then extra.report
compares the live model with and without the trend columns (leave-one-month-out, shuffled-input null).

    python -W ignore trend.py      # fetch the missing earlier scans, then write trend.md
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta

import pandas as pd
import requests

import data
import extra
from goes import CENTERS, HORIZONS

ZONES = ("fan", "far", "near", "over")
CACHE = data.EXPORT / "trend"
PATH = CACHE / "earlier.jsonl"
CANDIDATES = {"+fan trend": ["goes_fan_trend"], "+far trend": ["goes_far_trend"], "+fan rate": ["goes_fan_rate"],
              "+far+near trend": ["goes_far_trend", "goes_near_trend"]}
# Written by hand after reading the numbers of the run on 2026-11-14; re-read it if the data changes.
VERDICT = """
## Verdict

No. Trend does not help. The gains are at most +0.007 AUC (top-25%) and only at the 1h and 45m shots, where the
shuffled-input 95% is 0.002-0.004, so those two horizons edge past noise by about 0.003, which is too small to matter
(MAE improves by about 0.2 points). At 2h, 30m, 15m and 5m the gain is zero or negative and inside the shuffle
spread. Averaged over horizons the gain is 0.000-0.002, no larger than the shuffled 95% (0.002-0.003). The raw
Spearman correlations of trend with the outcome are all within +/-0.11 and mostly negative at the late shots,
which is also weak. The live model already carries the current satellite level; the change in it adds nothing reliable.
"""
sys.path.insert(0, str(data.ROOT))
from ai_analysis import goes as G  # noqa: E402


def read_earlier(args):
    camera, time_, day, t = args
    lat0, lon0, _ = data.LOCATION[CENTERS[camera]]
    _, az = data.sun_time_and_bearing(day, camera)
    try:
        return {"camera": camera, "time": time_, **(G.observe(t - timedelta(minutes=60), lat0, lon0, az, requests) or {})}
    except Exception as e:
        print(f"  {camera} {time_}: {e}", flush=True)


def shots():
    """Pre shots of the sunset cameras with goes_* filled from the shots cache (as horizons.build does)."""
    cap = data.captures()
    cap = cap[cap.camera.isin(data.SUNSET_CAMS) & cap.label.isin(HORIZONS)].reset_index(drop=True)
    cache = pd.read_json(data.EXPORT / "goes" / "shots.jsonl", lines=True).drop_duplicates(["camera", "time"])
    cap = cap.merge(cache, on=["camera", "time"], how="left", suffixes=("", "_cache"))
    for c in [c for c in cap if c.endswith("_cache")]:
        cap[c[:-6]] = cap[c[:-6]].fillna(cap.pop(c))
    return cap


def earlier(cap):
    """The reading 60 min before each 2h shot, fetched once and cached (skips failures; re-run to retry)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in PATH.read_text().splitlines()] if PATH.exists() else []
    done = {(r["camera"], r["time"]) for r in rows}
    todo = [(r.camera, r.time, r.day, r.t.to_pydatetime()) for r in cap[cap.label == HORIZONS[0]].itertuples()
            if (r.camera, r.time) not in done]
    print(f"{len(todo)} earlier scans to read", flush=True)
    with PATH.open("a") as f, ProcessPoolExecutor(8) as pool:
        for i, row in enumerate(pool.map(read_earlier, todo, chunksize=4), 1):
            if row:
                f.write(json.dumps(row) + "\n")
                f.flush()
            if i % 100 == 0:
                print(i, flush=True)
    return pd.DataFrame(map(json.loads, PATH.read_text().splitlines())).drop_duplicates(["camera", "time"])


def features(cap, old):
    cols = [f"goes_{z}" for z in ZONES]
    cap = cap.sort_values(["camera", "day", "t"]).reset_index(drop=True)
    g = cap.groupby(["camera", "day"])
    hours = (cap.t - g.t.shift()).dt.total_seconds() / 3600
    first = cap.label == HORIZONS[0]
    prev = g[cols].shift()
    o = cap[["camera", "time"]].merge(old[["camera", "time", *cols]], how="left", on=["camera", "time"])
    prev[first] = o.loc[first, cols].values  # the 2h shot: the scan 60 min earlier
    hours[first] = 1.0
    out = cap[["camera", "day", "label"]].rename(columns={"label": "horizon"})
    for c in cols:
        out[c + "_trend"] = cap[c] - prev[c]
        out[c + "_rate"] = out[c + "_trend"] / hours
    return out


def main():
    cap = shots()
    f = features(cap, earlier(cap))
    t = extra.table().merge(f, on=["camera", "day", "horizon"], how="left")
    tr = [c for c in f if c.endswith("_trend")]
    cover = t.groupby("horizon")[tr].count().assign(shots=t.groupby("horizon").size())
    rho = pd.DataFrame({c: t.groupby("horizon").apply(lambda g, c=c: g[c].corr(g.pct, method="spearman")) for c in tr})
    text = f"""# Does the GOES cloud trend help the forecast?

Features, per pre shot on the three sunset cameras: `goes_Z_trend` = this shot's satellite cloud fraction in zone Z
(fan 5-300 km, far 80-300 km, near 5-40 km toward the sun, over = overhead) minus the previous pre shot's on the same
camera and day; `goes_Z_rate` = that per hour between the two captures (gaps are 60, 15, 15, 15, 10 min). The 2h shot
has no earlier shot, so it uses the scan 60 minutes before its capture. Every reading uses only scans that had landed
by its capture time. Candidate sets were fixed before looking at results.

## Shots with a trend value

{cover.to_markdown()}

## Spearman correlation of each trend with pct (day's outcome percentile)

{rho.round(3).to_markdown()}

## Leave-one-month-out comparison

{extra.report(t, CANDIDATES)}
{VERDICT}"""
    (data.ROOT / "analysis" / "trend.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
