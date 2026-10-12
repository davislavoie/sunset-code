"""A sharper, step-by-step horizon-gap prompt for the local vision model, on a 40-photo stratified sample
of the days the first prompt (vision.py) already judged, so the two prompts and horizon_gap.py compare
on the same photos. Uses the local 320 px 1h-pre thumbs (the image server is offline). Answers are
appended to analysis_export/vision_gap_<model>.jsonl (resumable).

    python analysis/vision_gap.py qwen3-vl:4b          # run (about 10 s per photo on CPU)
    python analysis/vision_gap.py qwen3-vl:4b --eval   # compare -> vision_gap.md
"""

import base64
import json
import sys
import time

import pandas as pd
import requests

import data
from vision import OLLAMA

PROMPT = """This webcam photo was taken 1 hour before sunset, looking roughly toward where the sun will set.
Find the horizon toward the sun (the far shore, ridge or skyline), then look at the cloud deck above it and
at the strip of sky between the cloud base and the horizon. Answer in JSON:
horizon_found (true if you can see where land or water meets the sky),
cloud_cover (0-100, percent of the visible sky covered by cloud),
cloud_base (where the bottom of the main cloud deck sits in the frame: none, touching_horizon, low, mid, high),
gap (yes / no / unclear: is there a band of clear or bright sky between the cloud base and the horizon that the setting sun could shine through),
gap_thickness (0-100, that band's height as a percent of the sky's height in the frame; 0 if no gap),
clouds_overhead (true if there is cloud higher up that could catch the light),
underside_lit (likely / possible / unlikely: will the setting sun light the undersides of the clouds from below),
predicted_quality (0-100, 0 = grey/no colour, 100 = spectacular),
reason (one short sentence)."""
SCHEMA = {
    "type": "object",
    "properties": {
        "horizon_found": {"type": "boolean"}, "cloud_cover": {"type": "number"},
        "cloud_base": {"type": "string", "enum": ["none", "touching_horizon", "low", "mid", "high"]},
        "gap": {"type": "string", "enum": ["yes", "no", "unclear"]}, "gap_thickness": {"type": "number"},
        "clouds_overhead": {"type": "boolean"},
        "underside_lit": {"type": "string", "enum": ["likely", "possible", "unlikely"]},
        "predicted_quality": {"type": "number"}, "reason": {"type": "string"},
    },
    "required": ["horizon_found", "cloud_cover", "cloud_base", "gap", "gap_thickness", "clouds_overhead",
                 "underside_lit", "predicted_quality", "reason"],
}


def sample():
    """15 top-25 % days, 15 bottom-25 %, 10 in between, from the first prompt's 160 days."""
    v = pd.DataFrame(map(json.loads, (data.EXPORT / "vision_qwen3-vl_4b.jsonl").read_text().splitlines()))
    v = v.drop_duplicates(["camera", "day"], keep="last").assign(day=lambda x: pd.to_datetime(x.day).dt.date)
    t = pd.read_parquet(data.EXPORT / "analysis_table.parquet")[["camera", "day", "y_pct_late"]]
    d = v.merge(t, on=["camera", "day"]).dropna(subset=["y_pct_late"])
    top, bottom = d[d.y_pct_late >= .75], d[d.y_pct_late < .25]
    mid = d[(d.y_pct_late >= .25) & (d.y_pct_late < .75)]
    return pd.concat([top.sample(15, random_state=0), bottom.sample(15, random_state=0), mid.sample(10, random_state=0)])


def ask(model, path):
    body = {"model": model, "stream": False, "think": False, "format": SCHEMA, "options": {"temperature": 0, "num_predict": 400},
            # qwen3-vl thinks even with think=False (and with this prompt it rambles past the context);
            # an empty think block as the start of the answer skips that: ~8 s per photo instead of minutes.
            "messages": [{"role": "user", "content": PROMPT, "images": [base64.b64encode(path.read_bytes()).decode()]},
                         {"role": "assistant", "content": "<think>\n\n</think>\n\n"}]}
    resp = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=900)
    resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])


def run(model):
    out = data.EXPORT / f"vision_gap_{model.replace(':', '_')}.jsonl"
    done = {(r["camera"], r["day"]) for r in map(json.loads, out.read_text().splitlines())} if out.exists() else set()
    todo = [r for r in sample().itertuples() if (r.camera, str(r.day)) not in done]
    print(f"{len(todo)} photos to judge", flush=True)
    with out.open("a") as f:
        for i, r in enumerate(todo, 1):
            started = time.monotonic()
            a = ask(model, data.EXPORT / "thumbs" / r.camera / f"{r.day}_02_1h_pre.jpg")
            f.write(json.dumps({"camera": r.camera, "day": str(r.day), "sec": round(time.monotonic() - started, 1), **a}) + "\n")
            f.flush()
            print(i, r.camera, r.day, f"{time.monotonic() - started:.0f}s", a["gap"], a["predicted_quality"], flush=True)


def evaluate(model):
    s = sample()
    g = pd.DataFrame(map(json.loads, (data.EXPORT / f"vision_gap_{model.replace(':', '_')}.jsonl").read_text().splitlines()))
    g = g.assign(day=lambda x: pd.to_datetime(x.day).dt.date).add_prefix("new_").rename(columns={"new_camera": "camera", "new_day": "day"})
    img = pd.read_parquet(data.EXPORT / "horizon_gap.parquet").query("tag == 'g1h'")[["camera", "day", "gap", "gap_thickness"]]
    d = s.merge(g, on=["camera", "day"]).merge(img.add_prefix("img_").rename(columns={"img_camera": "camera", "img_day": "day"}),
                                             on=["camera", "day"], how="left")
    pct = d.y_pct_late
    outcome = lambda m: {"n": int(m.sum()), "median_pct": pct[m].median(), "top25": (pct[m] >= .75).mean(), "top10": (pct[m] >= .9).mean()}
    rho = lambda c: d[c].astype(float).corr(pct, method="spearman")
    rows = {"new: gap yes": outcome(d.new_gap == "yes"), "new: gap no": outcome(d.new_gap == "no"),
            "new: gap unclear": outcome(d.new_gap == "unclear"),
            "new: overhead cloud + gap yes": outcome(d.new_clouds_overhead & (d.new_gap == "yes")),
            "new: underside lit likely": outcome(d.new_underside_lit == "likely"),
            "old: horizon_clear": outcome(d.horizon_clear), "old: not horizon_clear": outcome(~d.horizon_clear),
            "image: gap": outcome(d.img_gap.fillna(False).astype(bool)), "all 40": outcome(pct.notna())}
    out = [f"# Sharper horizon-gap prompt vs the first prompt vs horizon_gap.py ({len(d)} photos, 1h-pre)\n",
           f"Sample: 15 top-25 %, 15 bottom-25 %, 10 middle days (late best score percentile). "
           f"{d.new_sec.mean():.0f} s per photo.\n",
           "## Spearman with the outcome\n",
           pd.Series({"new predicted_quality": rho("new_predicted_quality"), "old predicted_quality": rho("predicted_quality"),
                      "new cloud_cover": rho("new_cloud_cover"), "old cloud_cover": rho("cloud_cover"),
                      "new gap_thickness": rho("new_gap_thickness"), "image gap_thickness": rho("img_gap_thickness"),
                      "new gap == yes": d.new_gap.eq("yes").astype(float).corr(pct, method="spearman"),
                      "old horizon_clear": d.horizon_clear.astype(float).corr(pct, method="spearman")}).round(3).to_frame("rho").to_markdown(),
           "\n## Outcome by answer\n", pd.DataFrame(rows).T.round(2).to_markdown(),
           "\n## Agreement\n",
           pd.crosstab(d.new_gap, d.horizon_clear, rownames=["new gap"], colnames=["old horizon_clear"]).to_markdown(), "\n",
           pd.crosstab(d.new_gap, d.img_gap, rownames=["new gap"], colnames=["image gap"]).to_markdown(),
           "\n## Answers\n", d[["camera", "day", "y_pct_late", "new_gap", "new_gap_thickness", "new_cloud_base", "new_clouds_overhead",
                               "new_underside_lit", "new_predicted_quality", "predicted_quality", "horizon_clear", "img_gap", "new_reason"]]
           .sort_values("y_pct_late", ascending=False).round(2).to_markdown(index=False)]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "vision_gap.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen3-vl:4b"
    evaluate(model) if "--eval" in sys.argv else run(model)
