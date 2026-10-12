# Sharper horizon-gap prompt vs the first prompt vs horizon_gap.py (40 photos, 1h-pre)

Sample: 15 top-25 %, 15 bottom-25 %, 10 middle days (late best score percentile). 16 s per photo.

## Spearman with the outcome

|                       |     rho |
|:----------------------|--------:|
| new predicted_quality |   0.62  |
| old predicted_quality |   0.526 |
| new cloud_cover       |  -0.573 |
| old cloud_cover       |  -0.472 |
| new gap_thickness     |   0.646 |
| image gap_thickness   | nan     |
| new gap == yes        |   0.39  |
| old horizon_clear     |   0.512 |

## Outcome by answer

|                               |   n |   median_pct |   top25 |   top10 |
|:------------------------------|----:|-------------:|--------:|--------:|
| new: gap yes                  |  35 |         0.56 |    0.43 |    0.14 |
| new: gap no                   |   5 |         0.11 |    0    |    0    |
| new: gap unclear              |   0 |       nan    |  nan    |  nan    |
| new: overhead cloud + gap yes |  17 |         0.42 |    0.35 |    0.06 |
| new: underside lit likely     |  14 |         0.6  |    0.43 |    0.07 |
| old: horizon_clear            |  25 |         0.75 |    0.52 |    0.16 |
| old: not horizon_clear        |  15 |         0.16 |    0.13 |    0.07 |
| image: gap                    |   0 |       nan    |  nan    |  nan    |
| all 40                        |  40 |         0.36 |    0.38 |    0.12 |

## Agreement

| new gap   |   False |   True |
|:----------|--------:|-------:|
| no        |       4 |      1 |
| yes       |      11 |     24 |


| new gap   |   False |
|:----------|--------:|
| no        |       5 |
| yes       |      35 |

## Answers

| camera            | day        |   y_pct_late | new_gap   |   new_gap_thickness | new_cloud_base   | new_clouds_overhead   | new_underside_lit   |   new_predicted_quality |   predicted_quality | horizon_clear   | img_gap   | new_reason                                                                                                                                  |
|:------------------|:-----------|-------------:|:----------|--------------------:|:-----------------|:----------------------|:--------------------|------------------------:|--------------------:|:----------------|:----------|:--------------------------------------------------------------------------------------------------------------------------------------------|
| btv_echo_cam      | 2026-02-23 |         0.99 | yes       |                  25 | touching_horizon | False                 | possible            |                      75 |                  25 | False           | False     | The setting sun's light will illuminate the gap between cloud base and horizon, creating a bright band for the viewer.                      |
| btv_echo_cam      | 2026-09-11 |         0.94 | yes       |                  30 | mid              | False                 | possible            |                      80 |                  90 | True            | False     | Sunset conditions with a clear gap allowing bright light to shine through, creating a vibrant scene.                                        |
| btv_echo_cam      | 2026-09-26 |         0.93 | yes       |                  30 | low              | True                  | likely              |                      85 |                  75 | True            | False     | The setting sun's light will illuminate the undersides of clouds, creating a vibrant sky with a clear gap for the sun to shine through.     |
| btv_echo_cam      | 2025-10-05 |         0.93 | yes       |                  40 | low              | False                 | possible            |                      85 |                  85 | True            | False     | Sunset glow visible through a clear gap in low clouds, with bright reflection on water.                                                     |
| btv_echo_cam      | 2026-09-24 |         0.92 | yes       |                  30 | low              | False                 | possible            |                      75 |                  95 | True            | False     | Sunset glow visible through a clear gap in low clouds, with warm lighting and partial cloud cover.                                          |
| btv_echo_cam      | 2026-07-10 |         0.89 | yes       |                  40 | low              | False                 | possible            |                      85 |                  90 | True            | False     | Sunset glow visible through a clear gap in low clouds, with warm colors and good visibility.                                                |
| btv_echo_cam      | 2026-02-16 |         0.89 | yes       |                  30 | low              | False                 | possible            |                      80 |                  85 | True            | False     | The sun is setting behind a low cloud deck with a visible gap allowing light to reach the horizon, creating a bright band of sky.           |
| btv_echo_cam      | 2025-11-02 |         0.87 | yes       |                  30 | low              | False                 | possible            |                      85 |                  85 | True            | False     | Clear sky band visible above cloud base, allowing sunset light to illuminate the scene with warm tones.                                     |
| btv_echo_cam      | 2026-07-12 |         0.84 | yes       |                  30 | low              | True                  | likely              |                      85 |                  85 | True            | False     | The setting sun's light will illuminate the undersides of clouds and the gap, creating a vibrant sunset scene.                              |
| bolton_summit_cam | 2026-07-12 |         0.83 | yes       |                  30 | low              | True                  | likely              |                      85 |                  75 | True            | False     | Sunset glow through a clear gap in low clouds with visible horizon and overhead clouds catching light.                                      |
| btv_echo_cam      | 2025-10-11 |         0.82 | yes       |                  30 | low              | False                 | possible            |                      80 |                  85 | True            | False     | Sunset glow visible through a clear gap in low clouds, with bright reflection on water.                                                     |
| bolton_summit_cam | 2026-08-21 |         0.8  | yes       |                  30 | mid              | True                  | likely              |                      85 |                  95 | True            | False     | Clear gap between cloud base and horizon allows sunset light to illuminate undersides of clouds.                                            |
| bolton_summit_cam | 2026-04-24 |         0.79 | yes       |                  30 | low              | True                  | likely              |                      85 |                  50 | False           | False     | The setting sun's light will illuminate the gap between cloud base and horizon, creating a bright band visible in the frame.                |
| btv_echo_cam      | 2026-09-23 |         0.77 | yes       |                  30 | mid              | False                 | possible            |                      75 |                 100 | True            | False     | Clear gap between cloud base and horizon allows sunset light to illuminate the scene, with moderate cloud cover and bright sky band.        |
| wcax_tower_sunset | 2026-10-03 |         0.75 | yes       |                  30 | mid              | True                  | likely              |                      85 |                  85 | True            | False     | Clear gap between cloud base and horizon allows sunset light to illuminate undersides of clouds.                                            |
| bolton_summit_cam | 2026-08-27 |         0.63 | yes       |                  30 | mid              | True                  | likely              |                      85 |                  80 | True            | False     | The setting sun's light will illuminate the undersides of clouds, creating a vibrant sunset with a clear gap allowing for bright colors.    |
| btv_echo_cam      | 2026-09-18 |         0.62 | yes       |                  40 | low              | False                 | possible            |                      80 |                  90 | True            | False     | The setting sun will illuminate the gap between cloud base and horizon, creating a bright band of sky for the sunset.                       |
| btv_echo_cam      | 2025-12-15 |         0.56 | yes       |                  30 | low              | True                  | likely              |                      85 |                  75 | True            | False     | The setting sun's light will illuminate the undersides of clouds and the gap, creating a vibrant sunset scene.                              |
| btv_echo_cam      | 2025-09-22 |         0.42 | yes       |                  30 | low              | True                  | likely              |                      85 |                  75 | True            | False     | The setting sun's light will illuminate the undersides of clouds and the gap, creating a vibrant sunset scene.                              |
| btv_echo_cam      | 2026-05-17 |         0.37 | yes       |                  30 | mid              | False                 | possible            |                      85 |                  85 | True            | False     | Clear sky band visible above cloud base, suggesting good sunset lighting.                                                                   |
| bolton_summit_cam | 2026-07-09 |         0.35 | no        |                   0 | touching_horizon | False                 | unlikely            |                      30 |                  25 | False           | False     | Clouds cover the horizon and most of the sky, with no visible gap for the setting sun to illuminate the undersides.                         |
| btv_echo_cam      | 2026-02-24 |         0.34 | yes       |                  30 | low              | False                 | possible            |                      75 |                  80 | True            | False     | Clear gap allows sunset light to illuminate cloud undersides, with moderate cloud cover and visible horizon.                                |
| wcax_tower_sunset | 2026-10-04 |         0.33 | yes       |                  30 | mid              | True                  | likely              |                      85 |                  85 | True            | False     | Clear gap allows sun to illuminate undersides of clouds, vibrant colors from sunset.                                                        |
| btv_echo_cam      | 2026-05-13 |         0.31 | yes       |                  30 | low              | True                  | likely              |                      85 |                  75 | True            | False     | Sunset glow visible through a clear gap in the cloud deck, with clouds catching light from below.                                           |
| btv_echo_cam      | 2026-03-24 |         0.29 | yes       |                  30 | low              | False                 | possible            |                      65 |                  30 | False           | False     | The setting sun's light will illuminate the gap between cloud base and horizon, creating a bright band for the viewer.                      |
| btv_echo_cam      | 2026-03-13 |         0.25 | yes       |                  30 | low              | False                 | possible            |                      70 |                  30 | False           | False     | The setting sun's light will illuminate the gap between cloud base and horizon, creating a bright band for the viewer.                      |
| btv_echo_cam      | 2026-03-26 |         0.21 | yes       |                  25 | touching_horizon | True                  | possible            |                      75 |                  30 | False           | False     | The setting sun will illuminate the gap between cloud base and horizon, creating a bright band for the sunset.                              |
| btv_echo_cam      | 2025-06-03 |         0.2  | yes       |                  30 | mid              | False                 | possible            |                      80 |                  45 | True            | False     | The setting sun's light will illuminate the gap between cloud base and horizon, creating a bright band for the sunset.                      |
| btv_echo_cam      | 2026-09-01 |         0.17 | yes       |                  25 | touching_horizon | True                  | likely              |                      75 |                  40 | False           | False     | The setting sun will illuminate the gap between cloud base and horizon, creating a bright band for the undersides of clouds to catch light. |
| btv_echo_cam      | 2026-07-18 |         0.16 | yes       |                  25 | touching_horizon | False                 | possible            |                      75 |                  50 | False           | False     | The setting sun will illuminate the gap between cloud base and horizon, creating a bright band for the sunset.                              |
| btv_echo_cam      | 2025-12-22 |         0.14 | yes       |                  20 | touching_horizon | False                 | possible            |                      70 |                  40 | True            | False     | Low cloud deck touching horizon with a visible gap allowing sunset light to illuminate the undersides of clouds.                            |
| btv_echo_cam      | 2025-11-10 |         0.12 | no        |                   0 | touching_horizon | False                 | unlikely            |                      30 |                  30 | False           | False     | Overcast sky with cloud base touching horizon, no gap for sunset light, low cloud cover.                                                    |
| btv_echo_cam      | 2025-11-09 |         0.11 | no        |                   0 | touching_horizon | False                 | unlikely            |                      20 |                  25 | False           | False     | Overcast sky with cloud base touching horizon, no gap for sunset light.                                                                     |
| btv_echo_cam      | 2026-05-02 |         0.09 | yes       |                  25 | touching_horizon | True                  | possible            |                      75 |                  50 | True            | False     | The setting sun's light will illuminate the gap between cloud base and horizon, creating a bright band for the sunset.                      |
| wcax_tower_sunset | 2026-09-09 |         0.08 | yes       |                  25 | touching_horizon | True                  | likely              |                      75 |                  30 | False           | False     | The setting sun will illuminate the gap between cloud base and horizon, creating a bright band for the undersides of clouds to catch light. |
| bolton_summit_cam | 2026-09-09 |         0.08 | no        |                   0 | touching_horizon | False                 | unlikely            |                      30 |                  30 | False           | False     | Low cloud cover with no visible gap for sunset light, resulting in muted, grey conditions.                                                  |
| btv_echo_cam      | 2026-07-14 |         0.04 | yes       |                  25 | touching_horizon | False                 | possible            |                      75 |                  55 | False           | False     | The setting sun will illuminate the gap between cloud base and horizon, creating a bright band for the photo.                               |
| btv_echo_cam      | 2026-08-07 |         0.04 | yes       |                  30 | low              | True                  | likely              |                      75 |                  50 | False           | False     | The setting sun's light will illuminate the undersides of clouds, creating a bright gap between cloud base and horizon.                     |
| btv_echo_cam      | 2025-05-22 |         0.04 | yes       |                  25 | touching_horizon | True                  | possible            |                      75 |                  30 | False           | False     | The setting sun will illuminate the gap between cloud base and horizon, creating a bright band for the photo.                               |
| bolton_summit_cam | 2026-05-20 |         0.02 | no        |                   0 | none             | False                 | unlikely            |                       0 |                  90 | True            | False     | The image is completely black with no visible horizon, clouds, or sky details.                                                              |