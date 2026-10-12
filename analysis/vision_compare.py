"""The vision model's 1h-pre answers vs Open-Meteo's cloud at the same hour, and the "light gap" combos.

    python analysis/vision_compare.py      # writes vision_compare.md
"""

import json

import numpy as np
import pandas as pd

import data

H = "h1"


def load():
    v = pd.DataFrame(map(json.loads, (data.EXPORT / "vision_qwen3-vl_4b.jsonl").read_text().splitlines()))
    v = v.drop_duplicates(["camera", "day"], keep="last")
    v["day"] = pd.to_datetime(v.day).dt.date
    t = pd.read_parquet(data.EXPORT / "analysis_table.parquet")
    d = t.merge(v, on=["camera", "day"]).dropna(subset=["y_pct_late"]).reset_index(drop=True)
    d["pct"] = d.y_pct_late
    # Open-Meteo, toward the sun (+/-10 deg): far = 60-300 km out, over = within 25 km all round.
    d["om_far_low"] = d[[f"low_mid_{H}", f"low_far_{H}"]].mean(axis=1)
    d["om_far_lowmid"] = d[[f"low_mid_{H}", f"low_far_{H}", f"mid_path_{H}"]].mean(axis=1)
    d["om_over"] = d[[f"mid_over_{H}", f"high_over_{H}"]].max(axis=1)
    d["om_total"] = d[f"cloud_cover_total@{H}"]
    d["om_low_path80"] = d[f"path80_cloud_cover_low@{H}"]
    d["om_horizon_clear"] = d.om_far_low < 20
    d["gap_ai"] = d.horizon_clear & d.cloud_type.isin(["mid_broken", "high_thin"])
    d["gap_om"] = d.om_horizon_clear & (d.om_over >= 40)
    return d


def outcome(g):
    return pd.Series({"n": len(g), "median_pct": g.pct.median(), "top25": (g.pct >= .75).mean(), "top10": (g.pct >= .9).mean()})


def main():
    d = load()
    out = [f"# Vision answers vs Open-Meteo ({len(d)} sunset camera-days, 1h-pre)\n"]
    rho = lambda a, b: d[a].corr(d[b], method="spearman")
    out += ["## Cloud cover agreement\n",
            f"Spearman of AI cloud_cover with Open-Meteo total cloud at the camera: {rho('cloud_cover', 'om_total'):.2f}; "
            f"with the blanket average (all layers, all points): {rho('cloud_cover', f'blanket_any_{H}'):.2f}; "
            f"with mid/high overhead: {rho('cloud_cover', 'om_over'):.2f}.\n",
            "Rho with the outcome (late best score, percentile): AI cloud_cover "
            f"{rho('cloud_cover', 'pct'):.2f}, Open-Meteo total {rho('om_total', 'pct'):.2f}, "
            f"blanket {rho(f'blanket_any_{H}', 'pct'):.2f}.\n"]
    d["cover_diff"] = d.cloud_cover - d.om_total
    big = d.reindex(d.cover_diff.abs().sort_values(ascending=False).index).head(12)
    out += ["Biggest disagreements (AI minus Open-Meteo total):\n",
            big[["camera", "day", "cloud_cover", "om_total", "cover_diff", "cloud_type", "pct"]].round(2).to_markdown(index=False), "\n"]
    out += ["## horizon_clear: AI vs Open-Meteo far-path low cloud (< 20 % at 60-300 km toward the sun)\n",
            pd.crosstab(d.horizon_clear, d.om_horizon_clear, rownames=["AI clear"], colnames=["Open-Meteo clear"]).to_markdown(),
            f"\nAgreement {(d.horizon_clear == d.om_horizon_clear).mean():.0%}; Spearman of AI horizon_clear with far-path low "
            f"{d.horizon_clear.astype(int).corr(d.om_far_low, method='spearman'):.2f}, with stored path80 low "
            f"{d.horizon_clear.astype(int).corr(d.om_low_path80, method='spearman'):.2f}.\n",
            "Outcome by the two horizon calls:\n",
            d.groupby(["horizon_clear", "om_horizon_clear"]).apply(outcome).round(2).to_markdown(), "\n"]
    rows = {}
    for name, m in [("(a) AI: horizon clear & mid_broken/high_thin", d.gap_ai),
                    ("(b) Open-Meteo: far low < 20 % & mid/high overhead >= 40 %", d.gap_om),
                    ("(a) and (b)", d.gap_ai & d.gap_om), ("(a) not (b)", d.gap_ai & ~d.gap_om),
                    ("(b) not (a)", ~d.gap_ai & d.gap_om), ("neither", ~d.gap_ai & ~d.gap_om),
                    ("AI clear sky", d.cloud_type == "clear"), ("all days", d.pct.notna())]:
        rows[name] = outcome(d[m])
    out += ["## Light-gap combos\n", pd.DataFrame(rows).T.round(2).to_markdown(),
            f"\n(b) captures {(d.gap_ai & d.gap_om).sum()} of {d.gap_ai.sum()} (a) days.\n"]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "vision_compare.md").write_text(text, encoding="utf-8")
    print(text)
    return d


if __name__ == "__main__":
    main()
