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
- **Note on the target.** The HSV score rewards colour, and by this measure clear skies give the most
  colour. If the dramatic sunsets you like are the ones lit up on mid/high cloud, the score may be
  undervaluing them, so check a few top-rated "cloudy canvas" days by eye. (An earlier version of
  this report said 31.5% of days had their best score at 2h/1h pre. That was wrong; see "Early best
  scores" below.)

## Early best scores (follow-up)

**Correction to the first version:** the 31.5% figure counted every shot before 15 min pre (2h, 1h,
45m and 30m). Only **12% of days (68)** have their overall best HSV score at the 2h or 1h shot.
Breakdown of which shot holds each camera-day's best score:
2h 43, 1h 25, 45m 44, 30m 84, 15m 103, 5m 58, sunset/sunrise 38, +5m 49, +15m 52, +30m 72.

- **The timestamps are right.** I checked 600 captures against astral sunset times:
  - 2h-pre shots are 109–119 min before sunset.
  - 1h-pre shots are 49–58 min before.
  - The sunset shot is 2–11 min after.

  There's no DST or label mix-up.
- **They're almost all dull days.** When the best shot is at 2h/1h, that best is a median score of
  **2.8**: the whole day is grey and the max is noise. On days scoring 30+, only **1 of 216** had
  its best at 2h/1h.
- **The few higher early scores come from colour that isn't sunset sky.** `rank_sunset` scores the
  top half of the frame (`horizon_y = height // 2`, with `find_horizon` commented out). Looking at
  the photos:
  - btv_echo_cam 2026-09-18 2h (27.7) and 2026-02-24 1h (21.7): low golden-hour sun lighting trees,
    brick and brown foliage in the top half.
  - wcax_tower_sunset 2026-10-05 2h (30.1) and 2026-10-07 2h (28.0): orange/pink lens-flare blobs
    plus sunlit cloud edges.
  - btv 2025-06-19 1h (22.8): bright warm cloud edges in mid-afternoon light.
- **Fix used in this analysis:** a day's score is the best shot from 15 min before to 30 min after
  sunset. All the numbers above were re-run with it. Pooled correlations and models moved by at
  most ±0.02 (e.g. ridge on all grid points ρ 0.598 → 0.597, AUC 0.743 → 0.754), so the conclusions
  stand.
- **Suggested pipeline fix (not done):** have the day's best shot (rerank / `11_ranked`) consider
  only the 15m-pre to 30m-post shots. A better long-term fix is a per-camera sky line in
  `sunset_process.py` (re-enable `find_horizon`, or a fixed `SKY_BOTTOM` per camera in
  `config/<camera>.env`) so trees and buildings aren't scored as sky.

## Forecast at every pre shot, wired in (follow-up)

**What's wired in:** `ai_judge/predict.py` writes a forecast onto each pre shot: 2h, 1h, 45m, 30m,
15m and 5m before sunset. There is no 10-minute capture; adding one would mean changing
sunset_code's intervals, which I didn't touch. The forecast fields:
- `predicted_pct`: 0–100, where the day's best sunset-window score should rank among this
  camera's earlier days.
- `predicted_score`: that rank turned back into an HSV score using the camera's past daily bests,
  so it can sit next to the actual score.
- `predicted_call`: poor (< 35), maybe, good (≥ 60) or banger (≥ 80).

Inputs are only what is known at that shot:

    weather = clear-path share - 0.5 * RH/100   (clear = path13/40/80 points with low < 20%, mid < 30%)
    cur_pct = this shot's HSV score, as a percentile of the camera's earlier daily bests
    max_pct = best shot so far today, same scale  (flagged shots count as 0, as on the dashboard)
    predicted_pct = a + b*weather + c*cur_pct + d*max_pct     (one line per horizon)

The coefficients are in `ai_judge/predict_coefs.json`, fitted by `horizons.py`, so the NUC needs
plain Python only. As sunset nears, the weight moves from the weather to what the camera is
already seeing: at 2h, weather 0.27 and shot 0.15; at 5m, weather 0.04 and shots 0.88.

How it runs:
- As a step in `python -m ai_judge watch`, after the weather fill.
- On demand: `python -m ai_judge predict --camera all [--since/--before] [--refill]`.
- It only uses earlier days as history, so a backfill is honest.
- **It has not been backfilled or run against the NUC's InfluxDB.**

**Backtest per horizon** (`horizons.py` → `horizons.md`). Leave-one-month-out, sunset cameras,
about 485 days. The target is the day's best score from 15m pre to 30m post, as a percentile within
the camera:

| shot | Spearman | AUC top-25% | typical miss (pct pts) | banger precision / recall (top-10%) | top-25% days called poor |
|---|---|---|---|---|---|
| 2h | 0.51 | 0.68 | 20 | — (almost never called) | 6.5% |
| 1h | 0.55 | 0.68 | 19 | — | 7.3% |
| 45m | 0.57 | 0.70 | 19 | — | 4.9% |
| 30m | 0.63 | 0.73 | 18 | 16% / 9% | 3.3% |
| 15m | 0.75 | 0.80 | 14 | 29% / 28% | 4.9% |
| 5m | **0.87** | **0.90** | **10** | **41% / 56%** | 3.3% |

The 15m and 5m shots fall inside the target window. Scored only against the shots still to come
(5m pre onward, and sunset onward), they still get ρ 0.69 / AUC 0.75 at 15m and ρ 0.82 /
AUC 0.89 at 5m. In plain terms:
- **The weather sets the odds two hours out.**
- **The camera itself is the real signal from about 30 minutes out.**
- **"Banger" calls only make sense at the 15m and 5m shots.** At 5m, a banger call is right 4 times
  as often as chance (41% against a 10% base rate).

**Dashboard** (html_project):
- **Day view:** a new **Forecast** card under the hero. One row per pre shot shows the shot's score,
  the predicted best (score and "top N%"), the call, and the accuracy. Accuracy is *Hit* (same call
  as what happened), *Close* (one call off) or *Miss*, plus how many percentile points it was off.
  The card header shows the day's actual best, and its footer the hit rate over all days for each
  shot.
- **Ranked images:** each day gets a **1 hr forecast** metric (predicted score, call, accuracy)
  next to its score.
- **Data:** the backend sends the forecast as a `Forecast` field. `src/forecast.js` works out the
  actual rank and the accuracy, with tests in `forecast.test.js`.
- **Preview:** I checked it locally against a read-only copy of the NUC's data, with the forecast
  computed in memory. On btv the call is a hit or close on 85% of days at 2h, rising to 96% at 5m. These rates are in-sample: the coefficients were fitted on these same days.

### Weather-only first version, kept for reference

`backtest.py` → `backtest.md`. This was the first version: weather alone, 2h/1h only.
**Backtest** (`backtest.py`, full table in `backtest.md`): every day in history, the forecast vs
the actual best score from 15m pre to 30m post. These are the **1h-pre** numbers; 2h-pre is a bit
weaker (pooled ρ 0.50, AUC 0.70).

| | bolton | btv | wcax_sunset | wcax_sunrise | sunset pooled |
|---|---|---|---|---|---|
| days | 132 | 336 | 47 | 46 | 515 |
| Spearman | 0.55 | 0.53 | 0.65 | 0.32 | 0.54 |
| AUC (top-25% day) | 0.75 | 0.70 | 0.81 | 0.62 | 0.72 |
| top-25% days called "good" | 71% | 59% | 69% | 18% | 63% |
| top-25% days called "poor" | 3% | 18% | 0% | 27% | 12% |
| "poor" calls that were bottom-third | 74% | 63% | 75% | 52% | 67% |
| "good" calls that were top-third | 55% | 54% | 60% | 33% | 55% |

Confusion matrix (sunset cameras, 1h-pre; columns are the actual tercile within the camera):

| predicted | bottom | middle | top |
|---|---|---|---|
| poor | **130** | 44 | 21 |
| maybe | 21 | 57 | 40 |
| good | 20 | 71 | **111** |

Median actual best score by predicted class:

| predicted | bolton | btv | wcax_sunset |
|---|---|---|---|
| poor | 0.2 | 3.4 | 18 |
| maybe | 8 | 21 | 66 |
| good | 21 | 32 | 75 |

In plain terms:
- **"Poor" is reliable.** It almost never misses a great day.
- **"Good" means "worth a look".** It's right about half the time: clear skies give the chance of
  colour, not a guarantee.
- **Sunrise:** the forecast is weak there.

## Caveats

- `ai_view` (dark / no-signal) isn't in the export, so those captures weren't excluded. They can
  only lower a day's score, so the effect on the best-of-day target should be small.
- wcax_tower_sunset reuses btv_echo_cam's blanket (3 km apart). The blanket's bearing is the grid
  bearing nearest the sun (within 5°). The forecasts come from the historical-forecast archive,
  which is what a live prediction would have seen.

## Files

- `data.py`: loads the export and builds per-day targets (run it for its self-check).
- `blanket.py`: the Open-Meteo fan fetch (cached, resumable).
- `images.py`: thumbnail features.
- `analyze.py`: everything above, written to `results.md`.
- `horizons.py`: the per-shot forecast fit and backtest (writes `ai_judge/predict_coefs.json`).
- `backtest.py`: the weather-only backtest.
- `vision.py`, `vision_eval.py`: the Ollama vision-model test.
- Charts: `heatmap_sunset.png`, `heatmap_sunrise.png`, `heatmap_<camera>.png`, `effects.png`,
  `models.png`.
- Tables: `corr_stored.csv`, `effect_sizes.csv`.
- The raw export, thumbnails and Open-Meteo cache are in `analysis_export/` (gitignored). Rebuild
  them with the export steps and `python analysis/blanket.py`.
