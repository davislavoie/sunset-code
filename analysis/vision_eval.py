"""Score the vision model's answers (analysis_export/vision_<model>.jsonl) like the other features.
Same days, same leave-one-month-out CV; target = best score from 5 min before sunset on (percentile).

    python analysis/vision_eval.py qwen3-vl:4b
"""

import json
import sys

import pandas as pd

import data
from analyze import ENGINEERED, MET, STORED_PATH, cv, rho, scores


def main(model):
    rows = [json.loads(l) for l in (data.EXPORT / f"vision_{model.replace(':', '_')}.jsonl").read_text().splitlines()]
    v = pd.DataFrame(rows)
    v = v.drop_duplicates(["camera", "day"], keep="last")
    v["day"] = pd.to_datetime(v.day).dt.date
    v["v_quality"] = v.predicted_quality
    v["v_cover"] = v.cloud_cover
    v["v_horizon_clear"] = v.horizon_clear.astype(int)
    for t in ("clear", "high_thin", "mid_broken", "low_thick", "overcast", "mixed"):
        v[f"v_type_{t}"] = (v.cloud_type == t).astype(int)
    vcols = [c for c in v if c.startswith("v_")]
    t = pd.read_parquet(data.EXPORT / "analysis_table.parquet")
    d = t.merge(v[["camera", "day", "sec", "cloud_type"] + vcols], on=["camera", "day"]).dropna(subset=["y_pct_late"]).reset_index(drop=True)
    for cam in data.SUNSET_CAMS:
        d[f"is_{cam}"] = (d.camera == cam).astype(int)
    cams = [f"is_{c}" for c in data.SUNSET_CAMS]
    eng = [f"{e}_{h}" for e in ENGINEERED for h in ("h0", "h1", "h2")]
    wx = [f for f in eng + STORED_PATH + MET if f in d] + cams
    simple_img = [c for c in d if c.split("@")[0] in ("bright", "sat", "blue", "gray", "edges", "warm", "score") and c.endswith("i1h")]
    out = [f"# Vision model {model} on the 1h-pre photo\n",
           f"{len(d)} sunset camera-days ({d.camera.value_counts().to_dict()}), {d.sec.mean():.0f} s per photo on average "
           f"(median {d.sec.median():.0f} s).\n",
           "## Spearman rho of each answer with the late best score (percentile)\n",
           pd.Series({c: rho(d[c], d.y_pct_late) for c in vcols + ["warm@i1h", "score@i1h"]}).round(3).to_frame("rho").to_markdown(),
           "\n## Outcome by the model's predicted quality\n",
           d.assign(q=pd.cut(d.v_quality, [-1, 30, 50, 70, 101])).groupby("q").agg(
               days=("y_pct_late", "size"), median_pct=("y_pct_late", "median"),
               top25=("y_pct_late", lambda x: (x >= .75).mean())).round(2).to_markdown(),
           "\n## Outcome by the model's horizon_clear and cloud_type answers\n",
           *[d.groupby(col).agg(days=("y_pct_late", "size"), median_pct=("y_pct_late", "median"),
                                top25=("y_pct_late", lambda x: (x >= .75).mean()),
                                top10=("y_pct_late", lambda x: (x >= .9).mean())).round(2).to_markdown() + "\n"
             for col in ("v_horizon_clear", "cloud_type")],
           "\n## Leave-one-month-out on these days\n"]
    res = []
    for name, feats in [("weather (d)", wx), ("vision answer only", vcols + cams), ("simple 1h image features", simple_img + cams),
                        ("weather + vision", wx + vcols), ("weather + simple 1h image", wx + simple_img),
                        ("weather + simple 1h image + vision", wx + simple_img + vcols)]:
        for kind in ("ridge", "gbm"):
            res.append({"features": name, "model": kind, **scores(d, cv(d, feats, "y_pct_late", kind), "y_pct_late")})
    out.append(pd.DataFrame(res).round(3).to_markdown(index=False))
    text = "\n".join(out)
    (data.ROOT / "analysis" / "vision_results.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "qwen3-vl:4b")
