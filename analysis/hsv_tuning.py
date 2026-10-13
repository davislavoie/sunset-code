"""HSV score tweaks and cloud colour-contrast measures, judged against My ranking (btv_echo_cam).

Step 1 (features, ~5 min): one pass over the frames my_rank_frames.py downloaded. For each frame and each
crop of the top of the image (40-70 % of the height; the pipeline uses 50 %) it records, per hue band, a
histogram of (saturation, value) for the band's pixels, so saturation/value floors and the crop can be
changed without reading the images again. Pink is split into 140-149 / 150-159 / 160-169 / 170-179 so the
mauve end can be weighed separately. Contrast measures are taken on the scored crop (top 50 %).

Step 2 (evaluation): day score = best non-excluded frame; agreement with your score as Spearman rho and mean
absolute difference after the soft cap (its constant refitted on the training days). Every tuned variant is
5-fold cross-validated over days (parameters picked on 4 folds, judged on the 5th), repeated over 20 splits.

  python analysis/hsv_tuning.py [--features]   -> analysis/hsv_tuning.md
"""

import argparse
import sys
from multiprocessing import Pool

import cv2
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import spearmanr

import data

CROPS = [0.4, 0.5, 0.55, 0.6, 0.65, 0.7]
BANDS = {"red": (0, 7), "orange": (8, 24), "yellow": (25, 35), "pink140": (140, 149), "pink150": (150, 159),
         "pink160": (160, 169), "pink170": (170, 179)}
S_BIN = 4  # saturation histogram bin width
V_EDGES = np.array([38, 48, 64, 80, 96, 128, 160, 192, 256])  # value bins; 38 = the pipeline's brightness floor
WEIGHTS = {"red": 4, "orange": 3, "yellow": 2, "pink": 9}
ZOOMED = {"2026-01-30", "2026-01-31", "2026-02-01", "2026-02-26"}  # camera zoomed on the sun; left out
FEATURES = data.EXPORT / "hsv_tuning.npz"
CONTRAST = ["colorfulness", "hue_spread", "sat_spread", "v_spread_col", "v_range_sky", "lit_vs_cloud",
            "local_contrast_col", "edge_col", "warm_cool"]


def frame_features(path):
    img = cv2.imread(str(path))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H = img.shape[0]
    hist = np.zeros((len(CROPS), len(BANDS), 256 // S_BIN, len(V_EDGES) - 1), np.uint32)
    for c, frac in enumerate(CROPS):
        h, s, v = (hsv[: int(H * frac), :, i].ravel() for i in range(3))
        keep = v >= 38
        h, s, v = h[keep], s[keep], v[keep]
        vb = np.searchsorted(V_EDGES, v, side="right") - 1
        for b, (lo, hi) in enumerate(BANDS.values()):
            m = (h >= lo) & (h <= hi)
            np.add.at(hist[c, b], (s[m] // S_BIN, vb[m]), 1)

    # Contrast measures on the scored region (top half)
    sky = img[: H // 2].astype(np.float32)
    h, s, v = (hsv[: H // 2, :, i].astype(np.float32) for i in range(3))
    col = (v >= 38) & (s >= 20) & ((h < 36) | (h >= 140))  # the pipeline's coloured pixels
    B, G, R = sky[..., 0], sky[..., 1], sky[..., 2]
    rg, yb = R - G, 0.5 * (R + G) - B
    out = {"colorfulness": np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean()),  # Hasler-Susstrunk
           "v_range_sky": np.percentile(v, 95) - np.percentile(v, 5)}
    gray = cv2.cvtColor(img[: H // 2], cv2.COLOR_BGR2GRAY).astype(np.float32)
    local = np.sqrt(np.maximum(cv2.blur(gray ** 2, (31, 31)) - cv2.blur(gray, (31, 31)) ** 2, 0))
    edge = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    n = col.sum()
    if n > 500:
        ang = h[col] * np.pi / 90  # OpenCV hue 0-179 -> 0-2pi
        out |= {"hue_spread": np.sqrt(-2 * np.log(max(np.hypot(np.cos(ang).mean(), np.sin(ang).mean()), 1e-6))),
                "sat_spread": s[col].std(),
                "v_spread_col": np.percentile(v[col], 90) - np.percentile(v[col], 10),
                "local_contrast_col": local[col].mean(),
                "edge_col": edge[col].mean(),
                # lit coloured cloud against the rest of the sky (grey/dark cloud, blue)
                "lit_vs_cloud": v[col].mean() - v[~col & (v >= 38)].mean() if (~col & (v >= 38)).sum() > 500 else 0.0,
                # warm and pink/purple both present: geometric mean of their shares of the sky
                "warm_cool": np.sqrt(((h[col] < 36).mean()) * ((h[col] >= 140).mean())) * n / col.size}
    else:
        out |= dict.fromkeys(["hue_spread", "sat_spread", "v_spread_col", "local_contrast_col", "edge_col",
                              "lit_vs_cloud", "warm_cool"], 0.0)
    return hist, [float(out[k]) for k in CONTRAST], img.shape[0] * img.shape[1]


def build_features():
    f = pd.read_parquet(data.EXPORT / "my_rank_frames.parquet")
    paths = [data.EXPORT / "frames" / "btv_echo_cam" / u.split("/")[-1] for u in f.url]
    with Pool(8) as pool:
        res = pool.map(frame_features, paths, chunksize=8)
    np.savez_compressed(FEATURES, hist=np.stack([r[0] for r in res]), contrast=np.array([r[1] for r in res]),
                        pixels=np.array([r[2] for r in res]))


# ---------------------------------------------------------------- scoring variants from the histograms

S_MID = np.arange(0, 256, S_BIN) + (S_BIN - 1) / 2


def raw_score(hist, pixels, crop=0.5, sat_floor=20, pink_sat_floor=20, pink_v_floor=38, pink_lo=140,
              pink_w=None, grey_pen=0.0, power=2.0):
    """Uncapped HSV score per frame, as rank_sunset computes it with the given changes. Pink is scored as one
    band (as in the pipeline) over hues pink_lo-179 unless pink_w gives each pink sub-band its own weight."""
    c = CROPS.index(crop)
    h = hist[:, c].astype(np.float64)  # frames x bands x s x v
    names = list(BANDS)
    s_ok = S_MID >= sat_floor
    v_lo = V_EDGES[:-1]

    def band(idx, sfl=sat_floor, vfl=38):
        m = h[:, idx][:, :, (S_MID >= sfl)][:, :, :, v_lo >= vfl].sum(axis=(1, 3))  # frames x s
        sm = S_MID[S_MID >= sfl]
        n = m.sum(1)
        mean_s = np.divide((m * sm).sum(1), n, out=np.zeros_like(n), where=n > 0)
        return n / pixels * mean_s ** power / 40

    score = sum(WEIGHTS[b] * band([names.index(b)]) for b in ("red", "orange", "yellow"))
    pinks = [i for i, b in enumerate(names) if b.startswith("pink") and int(b[4:]) >= pink_lo]
    if pink_w is None:
        score += WEIGHTS["pink"] * band(pinks, pink_sat_floor, pink_v_floor)
    else:
        score += sum(w * band([i], pink_sat_floor, pink_v_floor) for i, w in zip(pinks, pink_w))
    if grey_pen:  # share of pink-hue pixels too dull to count (s 8-19): grey-purple overcast
        dull = h[:, pinks][:, :, (S_MID >= 8) & ~s_ok].sum(axis=(1, 2, 3)) / pixels
        score = score * np.exp(-grey_pen * dull)
    return score


def day_best(frames, per_frame):
    return pd.Series(per_frame, frames.index)[~frames.excluded].groupby(frames.date).max()


def fit_k(raw, mine):
    return minimize_scalar(lambda k: np.abs(100 * (1 - np.exp(-raw / k)) - mine).mean(),
                           bounds=(5, 500), method="bounded").x


def cv(frames, days, variants, reps=20, seed=0):
    """variants: {name: per-frame raw score}. Picks the best variant on 4 folds by rho (ties go to the first,
    the baseline), refits the soft cap there, scores the 5th. Returns pooled out-of-fold rho and MAE, and how
    often each variant was picked."""
    best = {k: day_best(frames, v).reindex(days.index) for k, v in variants.items()}
    rng = np.random.default_rng(seed)
    rhos, maes, picks = [], [], {}
    for _ in range(reps):
        fold = rng.permutation(len(days)) % 5
        pred = pd.Series(np.nan, days.index)
        for f in range(5):
            tr, te = fold != f, fold == f
            name = max(best, key=lambda k: round(spearmanr(best[k][tr], days.score[tr])[0], 4))
            picks[name] = picks.get(name, 0) + 1
            k = fit_k(best[name][tr].values, days.score[tr].values)
            pred[te] = 100 * (1 - np.exp(-best[name][te] / k))
        rhos.append(spearmanr(pred, days.score)[0])
        maes.append((pred - days.score).abs().mean())
    top = max(picks, key=picks.get)
    return np.mean(rhos), np.mean(maes), f"{top} ({picks[top]}/{reps * 5})"


def in_sample(frames, days, raw):
    b = day_best(frames, raw).reindex(days.index)
    k = fit_k(b.values, days.score.values)
    return spearmanr(b, days.score)[0], (100 * (1 - np.exp(-b / k)) - days.score).abs().mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", action="store_true", help="recompute the image features first")
    if ap.parse_args().features or not FEATURES.exists():
        build_features()
    z = np.load(FEATURES)
    hist, pixels = z["hist"], z["pixels"].astype(float)
    frames = pd.read_parquet(data.EXPORT / "my_rank_frames.parquet")
    days = pd.read_parquet(data.EXPORT / "my_rank_days.parquet").set_index("date")
    days = days[~days.index.isin(ZOOMED)]
    con = pd.DataFrame(z["contrast"], columns=CONTRAST, index=frames.index)

    base = raw_score(hist, pixels)
    pipe = frames.hsv.where(frames.hsv < 100)  # the stored pieces are capped; check against uncapped frames only
    check = np.corrcoef(base[pipe.notna()], pipe.dropna())[0, 1]
    rows = []

    def family(name, variants):
        r, m, pick = cv(frames, days, {"current": base, **variants})
        rows.append({"change": name, "cv rho": r, "cv mean abs diff": m, "picked most": pick})

    rows.append({"change": "current score", **dict(zip(["cv rho", "cv mean abs diff"], cv(frames, days, {"current": base})[:2]))})
    family("crop: top 40-70 % of the frame", {f"top {c:.0%}": raw_score(hist, pixels, crop=c) for c in CROPS if c != 0.5})
    family("pink saturation floor", {f"pink s>={s}": raw_score(hist, pixels, pink_sat_floor=s) for s in (28, 36, 44, 52, 60)})
    family("pink value floor", {f"pink v>={v}": raw_score(hist, pixels, pink_v_floor=v) for v in (48, 64, 80, 96, 128)})
    family("pink hue starts later", {f"pink from {lo}": raw_score(hist, pixels, pink_lo=lo) for lo in (150, 160)})
    family("grey-pink penalty", {f"x e^(-{g} dull)": raw_score(hist, pixels, grey_pen=g) for g in (2, 5, 10, 20, 40)})
    family("pink sub-band weights", {f"{w}": raw_score(hist, pixels, pink_w=w)
                                     for w in ([4.5, 9, 9, 9], [0, 9, 9, 9], [4.5, 9, 12, 12], [0, 6, 12, 12], [4.5, 6, 9, 12])})
    family("all of the above together", {
        f"top {c:.0%}, pink s>={s}, v>={v}": raw_score(hist, pixels, crop=c, pink_sat_floor=s, pink_v_floor=v)
        for c in (0.5, 0.55, 0.6) for s in (20, 36, 52) for v in (38, 64, 96)})

    # Contrast: alone, then as a multiplier on the HSV score
    alone = []
    for k in CONTRAST:
        b = day_best(frames, con[k].values).reindex(days.index)
        resid = days.score.rank() - day_best(frames, base).reindex(days.index).rank()
        alone.append({"measure": k, "rho with your score": spearmanr(b, days.score)[0],
                      "rho with the HSV score": spearmanr(b, day_best(frames, base).reindex(days.index))[0],
                      "rho with what HSV misses": spearmanr(b, resid)[0]})
    for k in CONTRAST:
        zk = (con[k] - con[k].mean()) / con[k].std()
        family(f"HSV x (1 + w * {k})", {f"w={w}": base * np.clip(1 + w * zk.values, 0, None)
                                         for w in (-0.2, -0.1, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)})

    def times(raw, k, w):  # raw x (1 + w * standardised measure), floored at 0
        return raw * np.clip(1 + w * ((con[k] - con[k].mean()) / con[k].std()).values, 0, None)

    family("any one contrast measure (measure and w picked in the folds)",
           {f"{k} w={w}": times(base, k, w) for k in CONTRAST for w in (-0.2, 0.2, 0.4, 0.6)})
    family("pink value floor + hue spread + lit contrast (all picked in the folds)",
           {f"pink v>={v}, hue w={wh}, lit w={wl}": times(times(raw_score(hist, pixels, pink_v_floor=v), "hue_spread", wh),
                                                        "lit_vs_cloud", wl)
            for v in (38, 96, 128) for wh in (0, 0.2, 0.3, 0.4) for wl in (0, 0.2, 0.3, 0.4)})
    # What went into sunset_process.py: pink v>=128, hue w 0.4 and lit w 0.3 written out with the means and
    # standard deviations above (1 + 0.4 (x - 0.2557) / 0.1597 = 0.36 + 2.5 x; 1 + 0.3 (x - 7.77) / 34.72 = 0.93 + 0.0086 x)
    shipped = (raw_score(hist, pixels, pink_v_floor=128) * np.clip(0.36 + 2.5 * con.hue_spread.values, 0, None)
               * np.clip(0.93 + 0.0086 * con.lit_vs_cloud.values, 0, None))
    family("shipped: pink v>=128 x (0.36 + 2.5 hue spread) x (0.93 + 0.0086 lit contrast)", {"shipped": shipped})
    for name, raw in (("current", base), ("shipped", shipped)):
        r, m = in_sample(frames, days, raw)
        rows.append({"change": f"{name}, all {len(days)} days in sample", "cv rho": r, "cv mean abs diff": m,
                     "picked most": f"soft cap k = {fit_k(day_best(frames, raw).reindex(days.index).values, days.score.values):.1f}"})

    t = pd.DataFrame(rows)
    a = pd.DataFrame(alone)
    md = (f"# HSV tuning and cloud contrast vs My ranking (btv_echo_cam, {len(days)} days, script `hsv_tuning.py`)\n\n"
          f"Four zoomed-in days left out. Histogram rebuild of the current score vs the pipeline's: r = {check:.4f}.\n"
          "Each row: 5-fold cross-validation over days, 20 random splits; the variant is picked on 4 folds (the current\n"
          "score is always a candidate) and judged on the 5th. Mean abs diff is after the soft cap, refitted per fold.\n\n"
          + t.round(3).to_markdown(index=False) + "\n\n## Contrast measures on their own (best frame of the day)\n\n"
          + a.round(3).to_markdown(index=False) + "\n")
    (data.ROOT / "analysis" / "hsv_tuning_results.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
