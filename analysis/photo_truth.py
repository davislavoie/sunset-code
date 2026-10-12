"""Does each cloud source match what the 1 h-pre photo actually shows?

Truth = the cloud cover the vision model (qwen3-vl 4b) read off the 02_1h_pre photo, from two
independent prompts (vision.py and vision_gap.py), averaged. The photo looks toward the sun, so this
is cloud on the sunset side. Sources at the same shot come from metar_shots.parquet (metar.py).

    python analysis/photo_truth.py      # writes photo_truth.md
"""

import json

import pandas as pd
from sklearn.metrics import roc_auc_score

import data

SOURCES = ["goes_over", "goes_near", "goes_far", "goes_fan", "icon_low", "icon_mid", "icon_high", "icon_total",
           "BTV_cover", "metar_path", "metar_west", "BTV_ceiling"]


def answers(name, cols):
    v = pd.DataFrame(map(json.loads, (data.EXPORT / name).read_text().splitlines()))
    return v.drop_duplicates(["camera", "day"], keep="last").assign(day=lambda x: pd.to_datetime(x.day).dt.date)[["camera", "day", *cols]]


def main():
    t = pd.read_parquet(data.EXPORT / "metar_shots.parquet")
    t = t[t.horizon == "02_1h_pre"]
    a = answers("vision_qwen3-vl_4b.jsonl", ["cloud_cover", "cloud_type"]).rename(columns={"cloud_cover": "photo_a"})
    b = answers("vision_gap_qwen3-vl_4b.jsonl", ["cloud_cover", "cloud_base"]).rename(columns={"cloud_cover": "photo_b"})
    d = t.merge(a, on=["camera", "day"], how="left").merge(b, on=["camera", "day"], how="left")
    d = d.dropna(subset=["photo_a", "photo_b"], how="all")
    d["photo"] = d[["photo_a", "photo_b"]].mean(axis=1)
    rows = []
    for c in SOURCES:
        s = -d[c] if c == "BTV_ceiling" else d[c]  # high ceiling = less cloud
        ok = s.notna()
        cloudy = d.photo >= 60
        sharp = (d.photo >= 60) | (d.photo <= 20)  # clear-cut photos only
        rows.append({"source": c, "rho vs photo": s.corr(d.photo, method="spearman"),
                     "rho vs prompt A": s.corr(d.photo_a, method="spearman"),
                     "rho vs prompt B": s.corr(d.photo_b, method="spearman"),
                     "AUC cloudy (>=60) vs not": roc_auc_score(cloudy[ok], s[ok]),
                     "AUC clear (<=20) vs cloudy (>=60)": roc_auc_score(cloudy[ok & sharp], s[ok & sharp])})
    by_base = d.dropna(subset=["cloud_base"]).groupby("cloud_base")[["photo", "goes_fan", "icon_low", "icon_mid", "icon_high",
                                                                     "metar_west", "BTV_ceiling"]].agg(["mean"]).round(2)
    by_base.columns = [c for c, _ in by_base.columns]
    by_base.insert(0, "n", d.dropna(subset=["cloud_base"]).groupby("cloud_base").size())
    text = "\n".join([
        f"# Cloud sources vs the photo ({len(d)} camera-days, 1 h before sunset)\n",
        f"Truth: vision-model cloud cover read off the photo, mean of two prompts (they agree at rho "
        f"{d.photo_a.corr(d.photo_b, method='spearman'):.2f}). {(d.photo >= 60).mean():.0%} of these photos read >= 60 % cloudy, "
        f"{(d.photo <= 20).mean():.0%} <= 20 %.\n",
        "## Agreement with the photo\n", pd.DataFrame(rows).set_index("source").round(2).to_markdown(),
        "\n## By the cloud base the model saw (prompt B)\n", by_base.to_markdown()])
    (data.ROOT / "analysis" / "photo_truth.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
