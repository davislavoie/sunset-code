"""Horizon light gap from the pre-sunset thumbs, by plain image analysis (no AI).

Per thumb (320x180):
  horizon  the topmost row with a strong edge sustained across the frame: the median over columns of
           the vertical brightness change (a far shore or ridge line runs edge to edge; cloud edges, trees
           and masts are patchy), searched between 20 % and 85 % of the height.
  profile  per sky row above it: brightness and texture (share of pixels with local gradient > TEX: cloud
           detail; clear sky is smooth). Colour didn't separate cloud from hazy clear sky on these webcams.
  gap      a band just above the horizon that is much smoother than a structured cloud deck above it, or
           clearly brighter than a flat grey one: the clear strip the setting sun shines through.
           thickness = band height as a share of the sky height; cloud_above / cloud_frac = textured
           share of the deck / of the whole sky (a cloud-cover proxy).

    python analysis/horizon_gap.py            # all 1h-pre and 30m-pre sunset thumbs -> horizon_gap.parquet + horizon_gap.md
"""

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter

import data

LABELS = {"02_1h_pre": "g1h", "04_30m_pre": "g30"}
SHARE = 0.4        # horizon = topmost row whose sustained edge is at least this share of the strongest
TEX = 0.012        # gradient (0-1 brightness per px) that counts as cloud texture on the soft thumbs
DECK_TEX = 0.25    # a cloud deck: at least this share of textured pixels...
SMOOTHER = 0.5     # ...over a band at most half as textured
LIFT = 0.05        # or: a band this much brighter (0-1) than a flat deck
GREY = 0.15        # flat deck = mean saturation below this
CLEAR_SKY = 0.10   # sky textured share below this = clear
SUN = 0.92         # brighter than this = the sun / glare, masked out (with a 15 px margin)


def load(path):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float) / 255
    return rgb, rgb.mean(axis=2)


def horizon(v, tex):
    """Topmost strong, frame-wide edge with sky above it: darker or busier below than above."""
    edge = np.convolve(np.median(np.abs(np.diff(v, axis=0)), axis=1), np.ones(3) / 3, mode="same")
    lo, hi = int(.2 * len(v)), int(.85 * len(v))
    strong = [r for r in range(lo, hi) if edge[r] >= SHARE * edge[lo:hi].max()]
    for r in strong:
        above, below = slice(max(0, r - 15), r - 1), slice(r + 2, r + 17)
        if (v[above].mean() - v[below].mean()) + (tex[below].mean() - tex[above].mean()) >= 0.05:
            return r
    return strong[0]


def detect(path):
    rgb, v = load(path)
    gy, gx = np.gradient(v)
    tex = np.hypot(gx, gy) > TEX
    h = horizon(v, tex)
    # Leave out the sun and its glare: a bright disc reads as a "clear bright band".
    sun = np.asarray(Image.fromarray((v > SUN).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(31))) > 0
    keep = ~sun[:h]
    n = keep.sum(axis=1)
    ok = n >= .3 * v.shape[1]
    rows_tex = np.where(ok, (tex[:h] & keep).sum(axis=1) / np.maximum(n, 1), np.nan)
    bright = np.where(ok, (v[:h] * keep).sum(axis=1) / np.maximum(n, 1), np.nan)
    sat = np.asarray(Image.open(path).convert("HSV"), dtype=float)[:h, :, 1] / 255
    sat = np.where(ok, (sat * keep).sum(axis=1) / np.maximum(n, 1), np.nan)
    best = None
    skip = 3  # the horizon edge itself is textured
    for t in range(max(skip + 2, int(.05 * h)), int(.5 * h) + 1):
        band, deck = slice(h - t, h - skip), slice(0, h - t)
        if np.isnan(rows_tex[band]).mean() > .5 or np.isnan(rows_tex[deck]).mean() > .5:
            continue
        band_tex, deck_tex = np.nanmean(rows_tex[band]), np.nanmean(rows_tex[deck])
        lift = np.nanmean(bright[band]) - np.nanmean(bright[deck])
        # Smooth band under a structured deck, or a brighter band under a flat grey one.
        grey_deck = np.nanmean(sat[deck]) < GREY  # a blue clear sky above a paler horizon isn't a deck
        if (deck_tex >= DECK_TEX and band_tex <= SMOOTHER * deck_tex) or (lift >= LIFT and grey_deck and band_tex <= deck_tex):
            score = deck_tex - band_tex + lift
            if best is None or score > best[0]:
                best = (score, t, deck_tex)
    frac = float(np.nanmean(rows_tex)) if ok.any() else np.nan
    return {"horizon": h / len(v), "cloud_frac": frac, "gap": best is not None,
            "gap_thickness": best[1] / h if best else 0.0, "cloud_above": best[2] if best else frac}


def overlay(path, r):
    img = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(img)
    y = r["horizon"] * img.height
    d.line([(0, y), (img.width, y)], fill=(0, 255, 255), width=1)
    if r["gap"]:
        top = y - r["gap_thickness"] * y
        d.rectangle([0, top, img.width - 1, y], outline=(255, 255, 0))
    return img


def table():
    rows = []
    for cam in data.SUNSET_CAMS:
        for label, tag in LABELS.items():
            for path in sorted((data.EXPORT / "thumbs" / cam).glob(f"*_{label}.jpg")):
                rows.append({"camera": cam, "day": pd.Timestamp(path.name[:10]).date(), "tag": tag, "path": str(path), **detect(path)})
    return pd.DataFrame(rows)


def outcome(g):
    return pd.Series({"n": len(g), "median_pct": g.y_pct.median(), "top25": (g.y_pct >= .75).mean(), "top10": (g.y_pct >= .9).mean()})


def evaluate(t):
    from analyze import ENGINEERED, MET, STORED_PATH, cv, scores
    wide = t.pivot_table(index=["camera", "day"], columns="tag", values=["gap", "gap_thickness", "cloud_frac", "cloud_above"])
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    d = pd.read_parquet(data.EXPORT / "analysis_table.parquet").merge(wide.reset_index(), on=["camera", "day"])
    d = d[d.camera.isin(data.SUNSET_CAMS)].dropna(subset=["y_pct", "cloud_frac_g1h"]).reset_index(drop=True)
    d["gap_any"] = (d.gap_g1h.fillna(0) + d.gap_g30.fillna(0)) > 0
    d["kind"] = np.select([d.gap_any, d.cloud_frac_g1h < CLEAR_SKY], ["clouds over a gap", "clear (textured < 10 %)"], "cloud, no gap")
    out = [f"# Horizon light gap, image method ({len(d)} sunset camera-days)\n",
           "Target: the day's best score in the sunset window, as a percentile per camera.\n",
           "## Outcome by kind (gap on the 1h or 30m thumb)\n", d.groupby("kind").apply(outcome).round(2).to_markdown(),
           "\n## By camera: gap share\n", d.groupby("camera").gap_any.agg(["size", "mean"]).round(3).to_markdown(),
           "\n## Spearman with the outcome\n",
           pd.Series({c: d[c].astype(float).corr(d.y_pct, method="spearman") for c in wide.columns}).round(3).to_frame("rho").to_markdown()]
    for cam in data.SUNSET_CAMS:
        d[f"is_{cam}"] = (d.camera == cam).astype(int)
    cams = [f"is_{c}" for c in data.SUNSET_CAMS]
    res = []
    for tag, img in (("h1", ["gap_g1h", "gap_thickness_g1h", "cloud_frac_g1h", "cloud_above_g1h"]),
                     ("h0 (30m)", ["gap_g1h", "gap_thickness_g1h", "cloud_frac_g1h", "cloud_above_g1h",
                                   "gap_g30", "gap_thickness_g30", "cloud_frac_g30", "cloud_above_g30"])):
        base = [f"{e}_h1" for e in ENGINEERED] + [c for c in STORED_PATH + MET if c.endswith("h1")] + cams
        d[img] = d[img].astype(float)
        for name, feats in (("weather", base), ("weather + gap features", base + img), ("gap features only", img + cams)):
            for kind in ("ridge", "gbm"):
                res.append({"photos": tag, "features": name, "model": kind, **scores(d, cv(d, feats, "y_pct", kind))})
    out += ["\n## Leave-one-month-out\n", pd.DataFrame(res).round(3).to_markdown(index=False)]
    text = "\n".join(out)
    (data.ROOT / "analysis" / "horizon_gap.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    t = table()
    t.to_parquet(data.EXPORT / "horizon_gap.parquet")
    evaluate(t)
