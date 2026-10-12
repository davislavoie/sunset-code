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

## Vision model on 160 days (follow-up)

`vision.py` ran qwen3-vl:4b (Ollama, CPU, about 54 s per photo) on the 1h-pre photo of 160 sunset
camera-days (btv 107, bolton 36, wcax 17). Full tables are in `vision_results.md` and `vision_compare.md`.

- Alone it forecasts about as well as the weather model. The AI's predicted_quality has Spearman 0.54
  with the late best score (percentile) and its cloud_cover −0.56. Leave-one-month-out: vision only
  R² 0.30 / AUC 0.72, against weather only 0.33 / 0.72.
- On top of weather plus the cheap HSV image features it adds almost nothing (gbm AUC 0.736 → 0.745).
  It isn't worth a minute of CPU per shot live.
- It is over-optimistic: 98 of 160 days get >70. Days it rates ≤50 are bad (median 21st–23rd pct,
  about 10 % top-25).
- horizon_clear=yes: median 59th pct, 35 % top-25 (n=124). =no: 19th pct, 8 % (n=36).
  cloud_type clear has the best median (77th pct). mid_broken has the best top-10 share (18 %).
- Cloud cover agrees well with Open-Meteo (Spearman 0.74 with total cloud, 0.80 with the blanket
  average). The AI's figure tracks the outcome a little better (−0.56 vs −0.47). In the dozen biggest
  disagreements, Open-Meteo says 0–10 % and the AI says 70–85 %. The photos show plainly cloudy skies
  every time, so the forecast model missed the cloud and the AI was right.
- AI horizon_clear vs Open-Meteo far-path low cloud (<20 % at 60–300 km toward the sun) agree on 71 %
  of days. The AI calls the horizon clear much more often (124 vs 92). When both say clear: median
  67th pct, 41 % top-25 (n=85). When both say blocked: 21st pct, 3 % top-25 (n=29).
- Light-gap combos. (a) AI horizon clear plus mid_broken/high_thin: n=85, median 57th pct, top-25 33 %,
  top-10 15 %. (b) Open-Meteo far low <20 % plus mid/high overhead ≥40 %: n=12, 59th pct, 42 %, 42 %.
  (b) is rare and catches only 9 of the 85 (a) days, but those 9 have a 44 % top-10 share. Plain clear
  sky (AI) still has the best median.

## Glass-lake reflections (btv_echo_cam)

`reflection.py` scores each btv thumb (15m-pre and sunset) for mirror symmetry. It searches for the
row whose flipped vertical colour gradients above best match those below. The camera cycles PTZ
presets, so the mirror row is found per image. Posts and masts carry no vertical gradient, and the
sky brightness ramp is removed per row, so neither counts.

- Jan 8 2026 is the strongest by a distance: 0.58, against a next best of 0.45 and a median of 0.19.
  About 14 of the top 20 frames are genuine calm-lake reflections; the rest are rough water, a building
  and a rainbow. Reflections (≥0.35) are rare: 12 of 335 days, 3.6 %.
- Open-Meteo 10 m wind at sunset (at the camera and 10 km out over the lake) barely predicts it
  (Spearman −0.07). The reflection rate is 10 % at ≤5 km/h and 2–5 % at 5–30 km/h. A calm forecast is
  needed, but nowhere near enough: the grid wind over a small lake is coarse, and the preset decides
  how much water is in frame. On Jan 8 the wind was 2–5 km/h, gusts under 8, at sunset.
- Reflection days score a little better (median 61st pct, 42 % top-25, n=12, vs 47th / 21 % for ≤0.20),
  but this is partly circular: a colourful sky gives more to mirror, and the HSV score already counts
  the reflected colour.
- Proposal: no wind term in the forecast. If anything, add an image-based "glass lake" badge or a small
  bonus on btv's judged shot: +5 at ≥0.35, +8 at ≥0.45.

## Upper-level wind along the sun line (follow-up)

`aloft.py` takes Open-Meteo's historical-forecast wind at 850, 700 and 500 hPa over each camera, 1 h and
2 h before sunset (517 sunset camera-days). It splits each wind into the component along the sun line:
positive means it blows from the sunset side, so path cloud is moving toward the camera. Full tables
are in `aloft.md`.

- On its own the along-sun component barely tracks the outcome (Spearman −0.03 to −0.12; wind from
  the sunset side is slightly worse). Overall speed: −0.14 to −0.20.
- Added to the full weather feature set (leave-one-month-out, AUC for a top-25 % day):
  - 1h, gbm: 0.723 → 0.774 with the along components alone (0.766 with everything aloft).
  - 2h: 0.709–0.711 → 0.734–0.738.
  - Ridge gains about +0.02 to +0.025 at both horizons.
  This is a real but modest gain, and part of it is probably a weather-regime signal (direction tells
  frontal from fair-weather flow) rather than literal cloud motion.
- The explicit "cloud on its way in" products (far low cloud × toward-camera wind, and so on) add
  nothing beyond the plain cloud features. Days with far-path low cloud ≥30 % at 2h do worst when the
  850 hPa wind blows *away* toward the sun side (easterly flow: median 17th pct, n=37) and no worse
  when it blows toward the camera (31st pct, n=156). The "it will clear in time" intuition doesn't show.
- Recommendation: if the live forecast grows past the 3-feature line, add along_700/along_500 at h1/h2.
  They are cheap, since they come from the same Open-Meteo call.

## Horizon light gap from the photos, no AI (follow-up)

`horizon_gap.py` runs plain image analysis on every 1h-pre and 30m-pre sunset thumb (about 1,100
photos in 4 s). For each photo:
- **Horizon**: the topmost row with a strong edge running across the whole frame, with darker or busier
  ground below it. This copes with btv's changing presets.
- **Sky profile**: for each row above the horizon, brightness and texture (share of pixels with real
  local gradient). Colour did not separate cloud from hazy clear sky on these webcams.
- **Gap**: a band just above the horizon that is much smoother than a structured cloud deck above it,
  or clearly brighter than a flat grey deck. The sun and its glare are masked out first.

Sample overlays are in `horizon_gap_examples.jpg`; tables are in `horizon_gap.md`.

- By eye on 20 samples, about 6–7 of the 10 flagged gaps are real. The misses come from a wrong
  horizon (Bolton's tower preset, or a cloud edge taken as the horizon). It also misses some textbook
  gaps (for example 2025-08-13: a warm strip under flat overcast). It flags rarely: 21 of 511 days
  (btv 5 %, wcax 8.5 %, Bolton 1 %).
- Outcome: gap days have median 64th pct, top-25 33 %, top-10 19 % (n=21). Cloud without a gap: 50th,
  24 %, 11 % (n=373). "Clear" (smooth sky): 52nd, 30 %, 10 % (n=117).
- Leave-one-month-out it adds nothing to the weather features (AUC 0.716 → 0.708 ridge, 0.724 → 0.730
  gbm). On its own it is at chance.
- Verdict: the 320 px thumbs, auto exposure, glare and PTZ presets make a pixel-rule gap detector too
  noisy to help. The AI's horizon_clear (above) and Open-Meteo's far-path low cloud carry the same idea
  better.

## Cloud models compared (follow-up)

`models.py` pulls Open-Meteo's historical-forecast cloud cover (total, low/mid/high and
850/700/500 hPa) from five models, 1 h before sunset. Points: over each camera, and 13/40/80/150 km
out on the bearing (240–300°) nearest the sun. The features are near (13–40 km) and far (80–150 km)
cloud for each layer, plus overhead. AUC is leave-one-month-out ridge for a top-25 % day (517
camera-days). Tables are in `models.md`.

| model | AI photo cover vs total overhead (rho) | AUC low/mid/high | + pressure levels |
|:--|--:|--:|--:|
| best_match (= HRRR here) | 0.76 | 0.701 | 0.712 |
| ECMWF IFS 0.25° | 0.70 | 0.728 | 0.728 |
| GEM HRDPS | 0.69 | 0.728 | 0.730 |
| ICON seamless | 0.71 | **0.755** | **0.766** |

- HRRR (which Open-Meteo's best_match picks over Vermont, and what the live weather fetch uses)
  agrees best with what the camera sees overhead. It is the *worst* of the five at predicting the
  sunset from the path cloud.
- ICON is clearly best. Its 10 path features alone (0.755; 0.766 with pressure levels) beat the
  full HRRR blanket-plus-met feature set (about 0.71–0.72). Two models together add little beyond
  ICON alone (best pair GEM + ICON: 0.761).
- The pressure-level cloud cover (850/700/500 hPa) adds about +0.01.
- Recommendation: fetch the path cloud with `models=icon_seamless` (same API, same call cost),
  alongside or instead of best_match. This is the cheapest real gain found so far.
- Other free sources worth a look: GOES-East observed cloud (item 6, below), KBTV METAR ceilings, and
  more Open-Meteo models (UKMO, ARPEGE, ensemble spread).

## Sharper horizon-gap prompt, 40 photos (follow-up)

`vision_gap.py` asks qwen3-vl:4b a structured prompt on the 1h-pre thumb: horizon found, cloud cover,
cloud base height, gap yes/no/unclear and its thickness, clouds overhead, underside lit, quality. It
ran on a stratified 40 of the 160 days (15 top-25 %, 15 bottom-25 %, 10 middle), so the first prompt
and the image method compare on the same photos. Tables are in `vision_gap.md`.

- qwen3-vl "thinks" even with `think: false`. On this longer prompt it rambled past its context and
  returned nothing. Pre-filling an empty think block fixes it, and it is fast: 16 s per photo, against
  about 54 s for the first prompt (which spent most of that thinking). Accuracy is no worse.
- Spearman with the outcome on these 40 (inflated by the stratified extremes):
  - predicted_quality: 0.62 new vs 0.53 old.
  - cloud_cover: −0.57 new vs −0.47 old.
  - gap_thickness: 0.65 (the best single answer).
- As a yes/no, "gap" says yes on 35 of 40, so it barely discriminates: the 5 "no" days were all bad
  (median 11th pct). The old horizon_clear splits better as a binary (75th vs 16th pct). The image
  method (`horizon_gap.py`) flagged none of the 40.
- Reading: gap_thickness and the quality score from the no-think structured prompt look at least as
  good as the old prompt at a third of the cost. That is worth confirming on all 160 days (about
  45 min at 16 s per photo) before trusting it.

## Observed cloud: GOES-East satellite and KBTV METAR (follow-up)

`goes.py` reads GOES-19's ABI-L2-ACMC clear-sky mask (CONUS, 2 km, every 5 min) from NOAA's public
S3 bucket. h5py reads the netCDF straight over HTTP range requests, so each scan costs about 0.7 MB
(of 4 MB) and under 1 s. The projection maths is checked against the GOES-R PUG worked example. For
the scans nearest 1 h before sunset and nearest sunset, it computes cloud fractions over:
- overhead (≤10 km);
- the near fan (sun ±30°, 5–40 km);
- the far fan (80–300 km);
- the whole fan;
- a narrow path (±10°, 40–300 km).

KBTV METARs come from the Iowa Environmental Mesonet: the report nearest 1 h before sunset, giving
cover, ceiling, lowest base and visibility. 513 sunset camera-days; tables are in `goes.md`.

- Agreement: GOES overhead vs the AI's photo cover 0.75; GOES fan vs Open-Meteo's blanket 0.76; GOES
  overhead vs Open-Meteo total at the camera only 0.63; METAR vs GOES overhead 0.71.
- GOES caught **8 of the 9** days Open-Meteo called clear while the photos were plainly cloudy
  (overhead 0.55–1.0). METAR caught 6.
- vs outcome: GOES fan cloud has Spearman −0.55 (−0.56 at sunset), against Open-Meteo total −0.42 to
  −0.47. METAR cover −0.49, ceiling +0.45.
- Leave-one-month-out at 1h, AUC for a top-25 % day: weather 0.715 → **0.773** with GOES (ridge;
  gbm 0.729 → 0.766). GOES alone (5 numbers) reaches 0.758. METAR adds +0.01 on its own and nothing on
  top of GOES. **This is the largest gain of anything tried.**
- Live cost: one scan every 5 min, files land about 4 min after the scan starts. About 0.7 MB and 1 s
  per camera per forecast. No API key, free, anonymous.
- Recommendation: add GOES fan/near/far cloud fractions (1h-pre, and refresh at 30m/15m) to the live
  forecast. With ICON path cloud it is the next thing to wire in.

## ICON + GOES wired into the live forecast (follow-up)

`ai_judge/predict.py` now carries several coefficient sets per horizon (in `predict_coefs.json`,
fitted by `horizons.py`). Each shot uses the best set it has every input for:
- **icon+goes**: weather, cur_pct, max_pct, ICON clear-path, GOES fan cloud;
- **base**: the old three-feature line, used when ICON or GOES is missing.

The forecast records which set it used in `predicted_with`, and redoes a shot when better inputs
arrive later. For the refit, GOES was read at every historical pre-sunset capture, exactly as live
(the latest scan landed by the capture time: `goes.py --shots`). ICON came from `models.py`'s cache
(grid bearing ≤10° off). Leave-one-month-out, same 477–482 shots per horizon (`horizons.md`):

| horizon | AUC top-25 % before → after | Spearman before → after | MAE pct pts before → after |
|:--|:--|:--|:--|
| 2h | 0.681 → **0.750** | 0.51 → 0.60 | 20.3 → 18.7 |
| 1h | 0.683 → **0.751** | 0.55 → 0.63 | 19.1 → 17.9 |
| 45m | 0.702 → **0.764** | 0.57 → 0.64 | 18.8 → 17.7 |
| 30m | 0.725 → **0.764** | 0.63 → 0.67 | 17.8 → 17.1 |
| 15m | 0.794 → 0.803 | 0.75 → 0.76 | 14.0 → 14.0 |
| 5m | 0.899 → 0.897 | 0.87 → 0.87 | 9.9 → 10.0 |

- Almost all of the gain is GOES: GOES alone scores 0.749–0.764 at 2h–30m, and ICON adds about
  +0.001 on top. ICON alone, without GOES, adds +0.005 to +0.02.
- By 15m and 5m the HSV scores already seen dominate, and neither source adds anything.
- Poor calls on top-25 % days drop at every horizon up to 15m (for example 7.4 % → 4.1 % at 1h).

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
- `vision.py`, `vision_eval.py`, `vision_compare.py`: the Ollama vision-model test and its comparison with Open-Meteo.
- `horizon_gap.py`: image-based horizon light gap (`horizon_gap.md`, `horizon_gap_examples.jpg`).
- `goes.py`: GOES-East observed cloud and KBTV METAR (`goes.md`; cache in `analysis_export/goes/`).
- `vision_gap.py`: sharper horizon-gap prompt on 40 photos (`vision_gap.md`).
- `models.py`: cloud models compared (`models.md`).
- `aloft.py`: upper-level wind along the sun line (`aloft.md`).
- `reflection.py`: btv glass-lake detector vs wind (`analysis_export/reflection.parquet`).
- Charts: `heatmap_sunset.png`, `heatmap_sunrise.png`, `heatmap_<camera>.png`, `effects.png`,
  `models.png`.
- Tables: `corr_stored.csv`, `effect_sizes.csv`.
- The raw export, thumbnails and Open-Meteo cache are in `analysis_export/` (gitignored). Rebuild
  them with the export steps and `python analysis/blanket.py`.
