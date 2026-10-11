"""Backtest ai_judge/predict.py's simple forecast on all history, against the day's actual best
HSV score in the sunset window (15 min before to 30 min after). Writes backtest.md.

    python analysis/backtest.py
"""

import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import data

sys.path.insert(0, str(data.ROOT))
from ai_judge.predict import simple_score  # noqa: E402

CLASSES = ["poor", "maybe", "good"]


def table():
    cap = data.captures()
    d = data.days(cap)
    d["pct"] = d.groupby("camera").y.rank(pct=True)
    d["tercile"] = d.groupby("camera").y.transform(lambda y: pd.qcut(y.rank(method="first"), 3, labels=["bottom", "middle", "top"]))
    out = []
    for label in ("01_2h_pre", "02_1h_pre"):
        p = cap[cap.label == label]
        res = [simple_score({k: (None if v != v else v) for k, v in r.items()}) for r in p.to_dict("records")]
        p = p.assign(pred=[r[0] if r else np.nan for r in res], cls=[r[1] if r else None for r in res])
        out.append(p[["camera", "day", "pred", "cls"]].assign(at=label).merge(d, on=["camera", "day"]).dropna(subset=["pred"]))
    return pd.concat(out)


def metrics(g):
    return pd.Series({
        "days": len(g),
        "spearman": spearmanr(g.pred, g.y)[0],
        "MAE (pred/100 vs actual percentile)": (g.pred / 100 - g.pct).abs().mean(),
        "AUC top-25%": roc_auc_score(g.pct >= 0.75, g.pred),
        "top-25% days called good": (g[g.pct >= .75].cls == "good").mean(),
        "top-25% days called poor": (g[g.pct >= .75].cls == "poor").mean(),
        "'good' calls that were top-third": (g[g.cls == "good"].tercile == "top").mean(),
        "'poor' calls that were bottom-third": (g[g.cls == "poor"].tercile == "bottom").mean(),
    })


def main():
    t = table()
    lines = ["# Backtest: simple forecast vs the actual sunset-window HSV score\n"]
    for at, g in t.groupby("at"):
        lines.append(f"\n## read at {at}\n")
        per = pd.DataFrame({cam: metrics(gg) for cam, gg in g.groupby("camera")})
        per["sunset cams pooled"] = metrics(g[g.camera.isin(data.SUNSET_CAMS)].assign(
            y=lambda x: x.pct))  # pooled: compare on percentiles
        lines.append(per.round(3).to_markdown())
        ss = g[g.camera.isin(data.SUNSET_CAMS)]
        cm = pd.crosstab(ss.cls, ss.tercile).reindex(index=CLASSES, columns=["bottom", "middle", "top"])
        lines.append("\nPredicted class (rows) vs actual tercile within camera (columns), sunset cameras:\n")
        lines.append(cm.to_markdown())
        med = ss.groupby("cls").y.median().reindex(CLASSES)
        lines.append("\nMedian actual best score by predicted class, per camera:\n")
        lines.append(ss.pivot_table(index="cls", columns="camera", values="y", aggfunc="median").reindex(CLASSES).round(1).to_markdown())
    text = "\n".join(lines)
    (data.ROOT / "analysis" / "backtest.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
