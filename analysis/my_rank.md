# The HSV score against My ranking (btv_echo_cam, 120 ranked days, 2026-10-12)

Data: `my_rank_frames.py` (every frame of every ranked day, with the per-band pieces of the score) and
`my_rank_forecast.py`. Agreement is Spearman ρ between the day's best HSV score (ruled-out shots left
out) and your score; "cv" is 5-fold cross-validation over days.

## Multipliers: already about as good as they get

| | ρ with your score |
|---|---|
| current weights (red 4, orange 3, pink 9, yellow 2) | 0.750 |
| weights fitted freely, cross-validated | 0.742 |
| same, fitted on all 120 days (optimistic) | 0.779 |
| saturation power 1.5 / 2.5 / 3 instead of 2 (cv) | 0.754 / 0.726 / 0.720 |
| saturation floor 35 / 50 instead of 20 (cv) | 0.734 / 0.714 |

The fits agree on direction (orange ~1, yellow ~0.5, pink ~4.4 relative to red 4) but don't beat the
current weights out of sample, so the multipliers are unchanged. The HSV score picks the same frame
you did on 90 % of days.

## Where it disagrees with you

- **Too high:** grey-purple overcast at dusk (the pink band from saturation 20 catches mauve cloud) and
  the odd night frame with street lights.
- **Too low:** views where the horizon sits well below the middle of the frame (52-90 % down). The
  score only reads the top half, so the glow at the horizon is cut off (2026-03-02: 0.3 vs your 50).
  The camera moves between several preset views; on most the half line is right at the horizon.
  A simple edge-based horizon finder was worse than the fixed half (ρ 0.39), so it isn't used.

## Change made: soft cap

`score = 100 * (1 - e^(-raw / 55.3))` replaces `min(100, raw)` in `sunset_process.py` (and the browser
copy in `scoring.js`). The constant is the least-squares fit to your scores.

| | linear, capped at 100 | soft cap |
|---|---|---|
| ρ with your score | 0.750 | 0.749 (same order) |
| mean absolute difference from your score | 15.8 | 13.7 |
| btv daily bests: skew | 1.27 | 0.45 |
| btv daily bests at 99+ (ties) | 15 | 0 |

Stored scores keep the old scale until they are recomputed (`python -m ai_judge rescore --camera all`).

## Haze / smoke (Open-Meteo air quality)

Aerosol optical depth at sunset is available back to 2025 (2025-07-02: 0.47, PM2.5 28, in the top 2 %
of ranked days). It doesn't argue for a deduction: on hazy days your score sits slightly *above* the
HSV score (ρ of your score minus the curved HSV score with AOD +0.14; with PM2.5 +0.06). You ranked
2025-07-02 at 80.

## Forecast

See `my_rank_forecast.md`. On the ranked days the live forecast tracks your score weakly (ρ 0.12 at
2 h, 0.46 at 5 min). Those days are harder than average even for the HSV target (ρ 0.22 at 2 h vs
0.48 on all btv days). Refitting on your score, with or without AOD, did worse leave-one-month-out,
so the live coefficients stay. Rerun `my_rank_forecast.py` once more days (and other cameras) are
ranked.
