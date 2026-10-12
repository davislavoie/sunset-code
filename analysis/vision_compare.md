# Vision answers vs Open-Meteo (160 sunset camera-days, 1h-pre)

## Cloud cover agreement

Spearman of AI cloud_cover with Open-Meteo total cloud at the camera: 0.74; with the blanket average (all layers, all points): 0.80; with mid/high overhead: 0.61.

Rho with the outcome (late best score, percentile): AI cloud_cover -0.56, Open-Meteo total -0.47, blanket -0.54.

Biggest disagreements (AI minus Open-Meteo total):

| camera            | day        |   cloud_cover |   om_total |   cover_diff | cloud_type   |   pct |
|:------------------|:-----------|--------------:|-----------:|-------------:|:-------------|------:|
| btv_echo_cam      | 2026-09-01 |            85 |          0 |           85 | overcast     |  0.17 |
| bolton_summit_cam | 2026-09-01 |            85 |          0 |           85 | low_thick    |  0.57 |
| btv_echo_cam      | 2026-08-23 |            85 |          3 |           82 | low_thick    |  0.8  |
| btv_echo_cam      | 2026-04-05 |            85 |          6 |           79 | mid_broken   |  0.14 |
| wcax_tower_sunset | 2026-08-31 |            75 |          0 |           75 | mid_broken   |  0.6  |
| wcax_tower_sunset | 2026-10-10 |            75 |          0 |           75 | mixed        |  0.27 |
| btv_echo_cam      | 2025-12-15 |            75 |          4 |           71 | mixed        |  0.56 |
| bolton_summit_cam | 2026-04-24 |            70 |          0 |           70 | mid_broken   |  0.79 |
| btv_echo_cam      | 2026-09-05 |            80 |         10 |           70 | mixed        |  0.26 |
| btv_echo_cam      | 2026-08-31 |            70 |          0 |           70 | mid_broken   |  0.04 |
| btv_echo_cam      | 2025-06-01 |            75 |          5 |           70 | mid_broken   |  0.38 |
| btv_echo_cam      | 2025-06-09 |            75 |          6 |           69 | mixed        |  0.28 |


## horizon_clear: AI vs Open-Meteo far-path low cloud (< 20 % at 60-300 km toward the sun)

| AI clear   |   False |   True |
|:-----------|--------:|-------:|
| False      |      29 |      7 |
| True       |      39 |     85 |

Agreement 71%; Spearman of AI horizon_clear with far-path low -0.50, with stored path80 low -0.53.

Outcome by the two horizon calls:

|                |   n |   median_pct |   top25 |   top10 |
|:---------------|----:|-------------:|--------:|--------:|
| (False, False) |  29 |         0.21 |    0.03 |    0    |
| (False, True)  |   7 |         0.12 |    0.29 |    0.14 |
| (True, False)  |  39 |         0.49 |    0.21 |    0.13 |
| (True, True)   |  85 |         0.67 |    0.41 |    0.14 |


## Light-gap combos

|                                                            |   n |   median_pct |   top25 |   top10 |
|:-----------------------------------------------------------|----:|-------------:|--------:|--------:|
| (a) AI: horizon clear & mid_broken/high_thin               |  85 |         0.57 |    0.33 |    0.15 |
| (b) Open-Meteo: far low < 20 % & mid/high overhead >= 40 % |  12 |         0.59 |    0.42 |    0.42 |
| (a) and (b)                                                |   9 |         0.63 |    0.44 |    0.44 |
| (a) not (b)                                                |  76 |         0.56 |    0.32 |    0.12 |
| (b) not (a)                                                |   3 |         0.29 |    0.33 |    0.33 |
| neither                                                    |  72 |         0.34 |    0.24 |    0.06 |
| AI clear sky                                               |  27 |         0.77 |    0.52 |    0.15 |
| all days                                                   | 160 |         0.54 |    0.29 |    0.11 |

(b) captures 9 of 85 (a) days.
