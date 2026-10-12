"""Every frame of every day you've ranked on the dashboard (My ranking), with the pieces the HSV score is
built from, so new multipliers can be tried without rescoring images.

For each hue band (red, orange, pink, yellow) sunset_process.calculate_saturation_weighted_score sees
the share of pixels in the band (ratio) and their mean saturation (sat); the score is
sum(weight * ratio * sat ** 2 / 40), capped at 100. Recorded by wrapping that function, so the masks
stay exactly the pipeline's.

  python analysis/my_rank_frames.py [--camera btv_echo_cam] [--api http://100.107.153.41:8502]
  -> analysis_export/my_rank_frames.parquet (one row per frame) and my_rank_days.parquet (your ranks)
"""

import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

import data

sys.dont_write_bytecode = True  # sunset_code/helpers/__pycache__ is tracked
sys.path.insert(0, str(data.ROOT / "sunset_code" / "helpers"))
import sunset_process as sp  # noqa: E402

BANDS = ["red", "orange", "pink", "yellow"]  # the order rank_sunset scores them in
FRAMES = data.EXPORT / "frames"


def get(api, path):
    with urllib.request.urlopen(f"{api}{path}", timeout=60) as r:
        return json.load(r)


def pieces(path):
    """{band_ratio, band_sat} for each hue band, plus the score the pipeline gives today."""
    seen = []
    original = sp.calculate_saturation_weighted_score

    def record(mask, s, total_pixels, power=2.0, bin_size=32):
        n = int(mask.sum())
        seen.append((n / total_pixels, float(s[mask].mean()) if n else 0.0))
        return original(mask, s, total_pixels, power, bin_size)

    sp.calculate_saturation_weighted_score = record
    try:
        score = sp.rank_sunset(str(path))[0]
    finally:
        sp.calculate_saturation_weighted_score = original
    row = {"hsv": score}
    for band, (ratio, sat) in zip(BANDS, seen):
        row[f"{band}_ratio"], row[f"{band}_sat"] = ratio, sat
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", default="btv_echo_cam")
    ap.add_argument("--api", default="http://100.107.153.41:8502")
    args = ap.parse_args()

    ranks = pd.DataFrame(get(args.api, f"/api/my-ranks?camera={args.camera}"))
    frames = [x for x in get(args.api, f"/api/data?camera={args.camera}")["all_data"]
              if x["Date"] in set(ranks.date) and not x["Label"].startswith(("11_", "12_"))]
    folder = FRAMES / args.camera
    folder.mkdir(parents=True, exist_ok=True)

    def fetch(x):
        path = folder / x["Image"].split("/")[-1]
        if not path.exists():
            urllib.request.urlretrieve(x["Image"], path)
        return path

    with ThreadPoolExecutor(8) as pool:  # download in parallel; pieces() patches a module, so score one at a time
        paths = list(pool.map(fetch, frames))
    rows = [{"date": x["Date"], "ts": x["ts"], "label": data.norm_label(x["Label"]), "url": x["Image"],
             "excluded": bool(x["Excluded"]), "stored_hsv": x["HSV Score"], **pieces(p)} for x, p in zip(frames, paths)]
    pd.DataFrame(rows).to_parquet(data.EXPORT / "my_rank_frames.parquet")
    ranks.to_parquet(data.EXPORT / "my_rank_days.parquet")
    print(f"{len(rows)} frames from {len(ranks)} ranked days")


if __name__ == "__main__":
    main()
