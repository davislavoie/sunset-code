# What predicts a good sunset (by the HSV score)

Data: every capture in InfluxDB `sunset_images` up to 2026-10-11, plus a new dense cloud blanket from
Open-Meteo's historical-forecast API. Target: each camera-day's **best HSV score**, using only
captures that are allowed to be the day's best shot (thumbs-down and blocked-view captures are left
out, as in `store.exclusion`). For the pooled analysis the target is that score's **percentile
within its camera**, because the cameras score on different scales: wcax_tower_sunset's median day
is 52, bolton_summit_cam's is 10. A "good" day is one in its camera's top 25%.

| camera | days | median best score |
|---|---|---|
| btv_echo_cam | 340 | 20 |
| bolton_summit_cam | 133 | 10 |
| wcax_tower_sunset | 48 | 52 |
| wcax_tower_sunrise | 47 | 42 (analysed separately) |

## Headline

1. **Low cloud is the main signal, and every kind of cloud hurts the score.** The best single
   predictor is how clear the corridor toward the sun is. `clear_lowmid` is the share of points on
   the sun's bearing (±10°, 5–300 km out) that have under 20% low cloud and under 30% mid cloud.
   Spearman ρ = **+0.56** pooled; per camera: bolton +0.64, btv +0.53, wcax_sunset +0.71.
   - When ≥75% of the corridor is clear (233 days), the median day lands at the **69th
     percentile** and **42%** of days are top-25%.
   - When <25% is clear (148 days), the median day is at the **23rd percentile** and only **7%** are
     top-25%.
   - In raw score for btv: median best **33** when the corridor is clear vs **6** when it's clouded.
     For bolton: **30** vs **0.7**.
2. **High cloud is not the "canvas" the photography rule of thumb expects, at least not for this
   score.** Every reading in the blanket (every layer, bearing, distance and hour) correlates
   *negatively* with the score. High cloud is the least harmful layer (ρ about −0.25, against about
   −0.5 for low). Only when the low/mid corridor is clear does lots of high cloud overhead turn
   mildly positive: on 16 days with ≥70% high cloud overhead, the median day was at the 80th
   percentile and 56% were top-25%. That sample is too small to rely on.
3. **The denser blanket adds little over the 3 points already stored.** The heat map
   (`heatmap_sunset.png`) is almost flat. Low cloud anywhere from 5 to 300 km and from −30° to +30°
   correlates at about −0.4 to −0.53. The strongest single point is low cloud at −10°, 40 km, at
   sunset (ρ −0.53), which matches the stored `path40_cloud_cover_low` (ρ −0.53). Cloud fields are
   spatially smooth at the model's resolution, so extra points mostly repeat the same information.
4. **Humidity helps a little; temperature and dew point don't add much.** RH 1 h before the sun:
   - Under 60% RH (252 days): median at the 64th percentile.
   - 90% RH or more (39 days): median at the 15th percentile, and **0** of those days were top-25%.

   But RH overlaps heavily with cloud. In the models, adding it moves ρ by only about 0.01–0.02.
5. **The pre-sunset photos are the strongest signal of all, but only close to sunset.** The test
   predicts the best score from 5 minutes before sunset onward, so no shot used as a feature is
   also part of the target:

   | features | Spearman | AUC (top 25%) |
   |---|---|---|
   | weather only | 0.56 | 0.73 |
   | + 2h-pre photo | 0.59 | 0.74 |
   | + 1h-pre photo | 0.62 | 0.76 |
   | + 30m-pre photo | 0.72 | 0.81 |
   | + all pre photos (to 15m) | **0.77** | **0.84** |

   The strongest photo features are the share of warm pixels (red/orange/pink) and the HSV score of
   the 15-minute and 30-minute shots themselves: ρ 0.74 / 0.71 for the 15m shot. At 2 h out the
   photo adds very little. This is a "nowcast" that sharpens as sunset approaches, not a forecast.

## Models (leave-one-month-out CV, 521 sunset camera-days)

| features | model | R² | Spearman | AUC (top 25%) |
|---|---|---|---|---|
| (a) climatology | — | 0.00 | — | 0.5 (by construction) |
| (b) stored 3-point path + overhead | ridge | 0.35 | 0.55 | 0.70 |
| (c) dense blanket, engineered summaries | ridge | 0.35 | 0.56 | 0.72 |
| (c′) dense blanket, all 630 grid readings | ridge | **0.38** | **0.60** | **0.74** |
| (d) blanket + stored + humidity/temp/dew | gbm | 0.35 | 0.58 | 0.72 |
| **one-line formula, no training:** `clear_lowmid` at 1 h before | — | — | 0.56 | 0.73 |

Per camera, model (d): bolton ρ 0.65 / AUC 0.78; btv ρ 0.55 / AUC 0.70; wcax_sunset ρ 0.60 / AUC
0.75. The best weather model explains about a third of the day-to-day variance. Gradient boosting
doesn't beat ridge regression here, because there's too little data for it to find interactions.

**Sunrise (wcax_tower_sunrise, 47 days):** the same story. Low cloud toward the sunrise correlates
at ρ −0.6 to −0.7 (strongest: low cloud 13 km out, 1 h before), and the corridor-clear fraction at
+0.6. That's too few days and months for a trustworthy model: ridge CV gives ρ 0.40.

## Recommendation (not wired in)

- **Don't add more sampling points yet.** The blanket's best result (c′, ρ 0.60) is only about 0.05
  above the 3 points you already store (ρ 0.55). Each extra point costs an Open-Meteo call every
  capture. If you do add any, use a cheap 3×3: bearings −10°, 0°, +10° × 25 / 40 / 80 km, and read
  low and mid cloud.
- **Simple production score** (0–1, higher is better), read 1–2 h before sunset:

      clear = share of path points with low < 20% and mid < 30%
      predicted = clear - 0.5 * (relative_humidity_2m / 100)

  This scores ρ 0.56 and AUC 0.73 on the whole history with no training. With today's
  13/40/80 km points, `clear` is just "how many of the 3 are clear", which gets most of the way.
- **Refine the prediction with the photo as sunset approaches.** From 30 min out, the warm-pixel
  share and HSV score of the latest pre-shot are much better predictors than any weather. A live
  "sunset odds" that starts from the weather formula and switches to the latest photo's warm share
  would be the real gain.
- **Note on the target.** The HSV score rewards colour, and the data says clear skies give the most
  colour by this measure: 31.5% of days had their best score at the 2h or 1h-pre shot, not around
  sunset. If the dramatic sunsets you like are the ones lit up on mid/high cloud, the score may be
  undervaluing them. It's worth checking a few top-rated "cloudy canvas" days by eye.

## Caveats

- `ai_view` (dark / no-signal) isn't in the export, so those captures weren't excluded. They can
  only lower a day's score, so the effect on the best-of-day target should be small.
- wcax_tower_sunset reuses btv_echo_cam's blanket (3 km apart). The blanket's bearing is the grid
  bearing nearest the sun (within 5°). The forecasts come from the historical-forecast archive,
  which is what a live prediction would have seen.
- No local vision model (Ollama) is running on this PC, so the LLM image test was skipped. The
  hand-made image features already reach AUC 0.84.

## Files

- `data.py`: loads the export and builds per-day targets (run it for its self-check).
- `blanket.py`: the Open-Meteo fan fetch (cached, resumable).
- `images.py`: thumbnail features.
- `analyze.py`: everything above, written to `results.md`.
- Charts: `heatmap_sunset.png`, `heatmap_sunrise.png`, `heatmap_<camera>.png`, `effects.png`,
  `models.png`.
- Tables: `corr_stored.csv`, `effect_sizes.csv`.
- The raw export, thumbnails and Open-Meteo cache are in `analysis_export/` (gitignored). Rebuild
  them with the export steps and `python analysis/blanket.py`.
