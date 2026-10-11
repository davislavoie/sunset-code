"""Everything in REPORT.md: correlations, the blanket heat map, effect sizes, CV models, image features.

    python analysis/analyze.py      (after blanket.py has cached the Open-Meteo blanket)

Pooled sunset analysis uses y_pct: the day's best score as a percentile within its camera, since
the cameras' score scales differ (wcax's median day is 52, bolton's 10).
"""

import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

import blanket
import data
import images

warnings.filterwarnings("ignore")
OUT = data.ROOT / "analysis"
LATE = ["06_5m_pre", "07_sunset", "07_sunrise", "08_5m_post", "09_15m_post", "10_30m_post"]


def rho(x, y):
    m = x.notna() & y.notna()
    return spearmanr(x[m], y[m])[0] if m.sum() > 15 and x[m].nunique() > 3 else np.nan


def load():
    cap = data.captures()
    d = data.days(cap)
    late = cap[~cap.excluded & cap.label.isin(LATE)].groupby(["camera", "day"]).score.max().rename("y_late")
    pre = cap[cap.label.isin(images.PRE)].pivot_table(index=["camera", "day"], columns="label", values="score")
    pre.columns = [f"score@{images.PRE[c]}" for c in pre.columns]
    d = d.join(late, on=["camera", "day"]).join(pre, on=["camera", "day"])
    for col in ("y", "y_late"):
        d[col.replace("y", "y_pct")] = d.groupby("camera")[col].rank(pct=True)
    f = pd.read_parquet(data.EXPORT / "blanket_features.parquet")
    d = d.merge(f, on=["camera", "day"], how="left")
    d = d.merge(images.table(), on=["camera", "day"], how="left")
    return engineer(d)


def band(d, layer, offs, kms, tag="h0"):
    cols = [f"{layer}_o{o}_k{k}_{tag}" for o in offs for k in kms if f"{layer}_o{o}_k{k}_{tag}" in d]
    return d[cols].mean(axis=1)


def engineer(d):
    """A handful of physically motivated summaries of the blanket."""
    on = [-10, 0, 10]
    allo = blanket.OFFSETS
    for tag in ("h0", "h1", "h2"):
        d[f"low_near_{tag}"] = band(d, "low", on, [5, 13, 25, 40], tag)
        d[f"low_mid_{tag}"] = band(d, "low", on, [60, 80, 120], tag)
        d[f"low_far_{tag}"] = band(d, "low", on, [160, 220, 300], tag)
        d[f"mid_over_{tag}"] = band(d, "mid", allo, [5, 13, 25], tag)
        d[f"high_over_{tag}"] = band(d, "high", allo, [5, 13, 25], tag)
        d[f"mid_path_{tag}"] = band(d, "mid", on, [40, 60, 80, 120], tag)
        d[f"high_path_{tag}"] = band(d, "high", on, [40, 60, 80, 120], tag)
        lows = [f"low_o{o}_k{k}_{tag}" for o in on for k in blanket.KM if f"low_o{o}_k{k}_{tag}" in d]
        mids = [c.replace("low_", "mid_") for c in lows]
        d[f"clear_corridor_{tag}"] = (d[lows] < 20).mean(axis=1).where(d[lows].notna().any(axis=1))
        d[f"clear_lowmid_{tag}"] = ((d[lows].values < 20) & (d[mids].values < 30)).mean(axis=1)
        d.loc[d[lows].isna().all(axis=1), f"clear_lowmid_{tag}"] = np.nan
        d[f"blanket_low_all_{tag}"] = band(d, "low", allo, blanket.KM, tag)
        d[f"blanket_any_{tag}"] = (band(d, "low", allo, blanket.KM, tag) + band(d, "mid", allo, blanket.KM, tag)
                                   + band(d, "high", allo, blanket.KM, tag)) / 3
        d[f"canvas_gap_{tag}"] = d[f"high_over_{tag}"] + d[f"mid_over_{tag}"] - d[f"low_far_{tag}"] - d[f"low_mid_{tag}"]
    return d


ENGINEERED = ["low_near", "low_mid", "low_far", "mid_over", "high_over", "mid_path", "high_path",
              "clear_corridor", "clear_lowmid", "blanket_low_all", "blanket_any", "canvas_gap"]
STORED_PATH = [f"path{k}_cloud_cover_{l}@{t}" for k in (13, 40, 80) for l in ("low", "mid", "high") for t in ("h0", "h1", "h2")] + \
              [f"cloud_cover_{l}@{t}" for l in ("low", "mid", "high", "total") for t in ("h0", "h1", "h2")]
MET = [f"{v}@{t}" for v in ("temperature_2m", "relative_humidity_2m", "dew_point_2m", "dewpoint_depression",
                             "precipitation", "precipitation_probability", "visibility") for t in ("h0", "h1", "h2")]


def heatmap(d, sub, title, path):
    """Spearman rho of y_pct with each blanket reading: offset x km, per layer and hour."""
    fig, axes = plt.subplots(3, 3, figsize=(15, 11), sharex=True, sharey=True)
    best = []
    for i, layer in enumerate(("low", "mid", "high")):
        for j, tag in enumerate(("h2", "h1", "h0")):
            m = np.full((len(blanket.OFFSETS), len(blanket.KM)), np.nan)
            for a, o in enumerate(blanket.OFFSETS):
                for b, k in enumerate(blanket.KM):
                    c = f"{layer}_o{o}_k{k}_{tag}"
                    if c in sub:
                        m[a, b] = rho(sub[c], sub.y_pct)
                        best.append((layer, o, k, tag, m[a, b]))
            ax = axes[i, j]
            im = ax.imshow(m, cmap="RdBu", vmin=-0.6, vmax=0.6, aspect="auto")
            for a in range(m.shape[0]):
                for b in range(m.shape[1]):
                    ax.text(b, a, f"{m[a, b]:.2f}", ha="center", va="center", fontsize=7)
            ax.set_title(f"{layer} cloud, {dict(h0='at sun', h1='1 h before', h2='2 h before')[tag]}")
            ax.set_xticks(range(len(blanket.KM)), blanket.KM)
            ax.set_yticks(range(len(blanket.OFFSETS)), [f"{o:+d}°" for o in blanket.OFFSETS])
            if i == 2:
                ax.set_xlabel("km toward the sun")
            if j == 0:
                ax.set_ylabel("bearing vs sun")
    fig.colorbar(im, ax=axes, shrink=0.6, label="Spearman rho with best score (percentile)")
    fig.suptitle(title)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return pd.DataFrame(best, columns=["layer", "offset", "km", "hour", "rho"])


def cv(d, feats, target="y_pct", model="gbm"):
    """Leave-one-month-out predictions."""
    pred = pd.Series(np.nan, index=d.index)
    for month in d.month.unique():
        test = d.month == month
        train = ~test
        if model == "clim":
            pred[test] = d.loc[train, target].mean()
            continue
        X = d[feats]
        if model == "gbm":
            m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20,
                                              l2_regularization=1.0)
        else:
            m = make_pipeline(SimpleImputer(), StandardScaler(), RidgeCV(alphas=np.logspace(-1, 4, 20)))
        m.fit(X[train], d.loc[train, target])
        pred[test] = m.predict(X[test])
    return pred


def scores(d, pred, target="y_pct"):
    m = pred.notna() & d[target].notna()
    good = d.loc[m, target] >= 0.75
    return {"n": int(m.sum()), "R2": r2_score(d.loc[m, target], pred[m]),
            "spearman": spearmanr(d.loc[m, target], pred[m])[0],
            "AUC(top 25%)": roc_auc_score(good, pred[m]) if pred[m].nunique() > 1 else 0.5}


def main():
    d = load()
    d.to_parquet(data.EXPORT / "analysis_table.parquet")
    lines = []
    say = lines.append
    ss = d[d.camera.isin(data.SUNSET_CAMS)].reset_index(drop=True)
    sr = d[d.camera == "wcax_tower_sunrise"].reset_index(drop=True)
    say(f"camera-days: {d.groupby('camera').size().to_dict()}")
    say(f"days whose best shot overall is before the 15m-pre..30m-post window: {(d.y_all > d.y + 1e-9).mean():.1%}")

    # 1. Stored fields.
    stored = [c for c in d if "@h" in c and not c.startswith("t@") and not c.startswith("score@")
              and not any(c.startswith(x) for x in ("bright", "sat", "blue", "gray", "edges", "warm"))]
    corr = pd.DataFrame({cam: {c: rho(g[c], g.y) for c in stored} for cam, g in d.groupby("camera")})
    corr["sunset_pooled"] = {c: rho(ss[c], ss.y_pct) for c in stored}
    corr = corr.reindex(corr.sunset_pooled.abs().sort_values(ascending=False).index)
    corr.round(3).to_csv(OUT / "corr_stored.csv")
    say("\n## stored fields, Spearman rho (top 20 by pooled sunset)\n" + corr.head(20).round(2).to_markdown())

    # 2. Blanket heat maps.
    best = heatmap(d, ss, "Sunset cameras pooled: rho of each blanket point with the day's best score", OUT / "heatmap_sunset.png")
    best_sr = heatmap(d, sr, "wcax_tower_sunrise: rho of each blanket point with the morning's best score", OUT / "heatmap_sunrise.png")
    for cam in data.SUNSET_CAMS:
        heatmap(d, ss[ss.camera == cam], f"{cam}: rho with best score", OUT / f"heatmap_{cam}.png")
    say("\n## strongest blanket points, sunset pooled\n" + best.sort_values("rho").head(12).round(3).to_markdown(index=False))
    say("\n## most positive blanket points, sunset pooled\n" + best.sort_values("rho").tail(6).round(3).to_markdown(index=False))
    say("\n## strongest blanket points, sunrise\n" + best_sr.sort_values("rho").head(8).round(3).to_markdown(index=False))
    eng = [f"{e}_{t}" for e in ENGINEERED for t in ("h0", "h1", "h2")]
    ec = pd.DataFrame({"pooled": {c: rho(ss[c], ss.y_pct) for c in eng},
                       **{cam: {c: rho(g[c], g.y) for c in eng} for cam, g in d.groupby("camera")}})
    say("\n## engineered blanket features, rho\n" + ec.round(2).to_markdown())

    # 3. Effect sizes in plain numbers.
    eff = []
    for feat, bins, names in [
        ("low_mid_h0", [-1, 10, 40, 70, 101], ["<10%", "10-40%", "40-70%", ">=70%"]),
        ("low_far_h0", [-1, 10, 40, 70, 101], ["<10%", "10-40%", "40-70%", ">=70%"]),
        ("low_near_h0", [-1, 10, 40, 70, 101], ["<10%", "10-40%", "40-70%", ">=70%"]),
        ("high_over_h0", [-1, 10, 40, 70, 101], ["<10%", "10-40%", "40-70%", ">=70%"]),
        ("mid_over_h0", [-1, 10, 40, 70, 101], ["<10%", "10-40%", "40-70%", ">=70%"]),
        ("clear_lowmid_h0", [-0.01, 0.25, 0.5, 0.75, 1.01], ["<25%", "25-50%", "50-75%", ">=75%"]),
        ("relative_humidity_2m@h1", [0, 60, 75, 90, 101], ["<60%", "60-75%", "75-90%", ">=90%"]),
    ]:
        for cam, g in [("pooled(pct)", ss)] + [(c, ss[ss.camera == c]) for c in data.SUNSET_CAMS]:
            col = "y_pct" if cam.startswith("pooled") else "y"
            cut = pd.cut(g[feat], bins, labels=names)
            for name, gg in g.groupby(cut):
                eff.append((feat, cam, name, len(gg), gg[col].median(), (gg.y_pct >= .75).mean()))
    eff = pd.DataFrame(eff, columns=["feature", "camera", "bin", "days", "median best", "share top-25% days"])
    eff.round(3).to_csv(OUT / "effect_sizes.csv", index=False)
    say("\n## effect sizes\n" + eff.round(2).to_markdown(index=False))
    # High cloud given clear low corridor: the classic "canvas" check.
    clear = ss[ss.clear_lowmid_h0 >= 0.5]
    hb = clear.groupby(pd.cut(clear.high_over_h0, [-1, 10, 40, 70, 101]))
    say("\n## clear low/mid corridor (>=50% of path points): by high cloud overhead\n"
        + hb.agg(days=("y_pct", "size"), median_pct=("y_pct", "median"), top25=("good", "mean")).round(2).to_markdown())

    # 4. Models (leave-one-month-out), sunset cameras pooled; camera one-hot so the model knows the site.
    for cam in data.SUNSET_CAMS:
        ss[f"is_{cam}"] = (ss.camera == cam).astype(int)
    cams = [f"is_{c}" for c in data.SUNSET_CAMS]
    grid_cols = [c for c in ss if c.split("_")[0] in ("low", "mid", "high") and "_o" in c and "_k" in c]
    sets = {
        "(b) stored 3-point path + overhead": STORED_PATH,
        "(c) dense blanket (engineered)": eng,
        "(c') dense blanket (all grid points)": grid_cols + eng,
        "(d) blanket + stored + humidity/temp/dew": eng + STORED_PATH + MET,
    }
    rows = [("(a) climatology (train mean)", "-", scores(ss, cv(ss, [], model="clim")))]
    preds = {}
    for name, feats in sets.items():
        feats = [f for f in feats if f in ss] + cams
        for kind in ("ridge", "gbm"):
            p = cv(ss, feats, model=kind)
            preds[(name, kind)] = p
            rows.append((name, kind, scores(ss, p)))
    res = pd.DataFrame([{"features": a, "model": b, **s} for a, b, s in rows])
    say("\n## models, sunset cameras pooled, leave-one-month-out, target = best-score percentile\n"
        + res.round(3).to_markdown(index=False))
    # Per camera from the pooled model (d, gbm).
    best_p = preds[("(d) blanket + stored + humidity/temp/dew", "gbm")]
    say("\n## per camera, model (d) gbm\n" + pd.DataFrame(
        {cam: scores(ss[ss.camera == cam], best_p[ss.camera == cam]) for cam in data.SUNSET_CAMS}).T.round(3).to_markdown())

    # Sunrise: too few days for a model; correlations only (above). Quick ridge for honesty.
    sr_feats = [f for f in eng + STORED_PATH if f in sr]
    if len(sr.month.unique()) > 1:
        say("\n## sunrise ridge LOMO (47 days, 3 months)\n" + str({k: round(v, 3) for k, v in scores(sr, cv(sr, sr_feats, model="ridge")).items()}))

    # 5. Image features: do the pre-shots add to the weather? Same days for both, target = late best.
    img_cols = [c for c in ss if c.split("@")[0] in ("bright", "sat", "blue", "gray", "edges", "warm", "score")]
    wx = [f for f in eng + STORED_PATH + MET if f in ss] + cams
    im = ss[ss[[c for c in img_cols if c.endswith("i1h")]].notna().any(axis=1) & ss.y_pct_late.notna()].reset_index(drop=True)
    im_rows = []
    for name, feats in [("weather (d)", wx), ("image only", img_cols + cams), ("weather + image", wx + img_cols)]:
        for kind in ("ridge", "gbm"):
            im_rows.append({"features": name, "model": kind, **scores(im, cv(im, feats, "y_pct_late", kind), "y_pct_late")})
    for horizon in ("i2h", "i1h", "i30"):
        cols = [c for c in img_cols if c.endswith(horizon)]
        im_rows.append({"features": f"weather + image @{horizon} only", "model": "gbm",
                        **scores(im, cv(im, wx + cols, "y_pct_late", "gbm"), "y_pct_late")})
    say("\n## image features (target = best score from 5 min before sunset on, percentile)\n"
        + pd.DataFrame(im_rows).round(3).to_markdown(index=False))
    ic = pd.Series({c: rho(im[c], im.y_pct_late) for c in img_cols}).sort_values(key=abs, ascending=False)
    say("\n## image feature rho with late best (pooled)\n" + ic.round(3).to_frame("rho").to_markdown())

    # Charts.
    fig, ax = plt.subplots(figsize=(9, 4.5))
    r = res[res.model.isin(["gbm", "-"])]
    ax.barh(r.features, r.spearman, color=["#999"] + ["#3b75af"] * (len(r) - 1))
    for i, (s, a) in enumerate(zip(r.spearman, r["AUC(top 25%)"])):
        ax.text(max(s, 0) + 0.01, i, f"rho {s:.2f}  AUC {a:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, 0.9)
    ax.set_xlabel("Spearman rho, predicted vs actual (leave-one-month-out)")
    ax.set_title("How well each feature set predicts the day's best sunset score")
    fig.savefig(OUT / "models.png", dpi=110, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for ax, feat, lab in zip(axes, ["low_near_h0", "low_mid_h0", "high_over_h0"],
                             ["low cloud 5-40 km toward sun", "low cloud 60-120 km toward sun", "high cloud overhead (5-25 km)"]):
        cut = pd.cut(ss[feat], [-1, 10, 40, 70, 101], labels=["<10%", "10-40%", "40-70%", ">=70%"])
        groups = [ss.y_pct[cut == b].dropna() for b in cut.cat.categories]
        ax.boxplot(groups, labels=[f"{b}\n(n={len(g)})" for b, g in zip(cut.cat.categories, groups)])
        ax.set_title(lab)
    axes[0].set_ylabel("best score, percentile within camera")
    fig.suptitle("Sunset cameras pooled, readings at sunset")
    fig.savefig(OUT / "effects.png", dpi=110, bbox_inches="tight")
    plt.close(fig)

    (OUT / "results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
