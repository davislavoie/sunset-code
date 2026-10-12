# GOES-East observed cloud and KBTV METAR (513 sunset camera-days)

Cost: 684 KB and 0.8 s per scan on average (HTTP range reads of a 4 MB file).

## Agreement (Spearman)

|                           |   over_g1h |   near_g1h |   far_g1h |   fan_g1h |   path_g1h |
|:--------------------------|-----------:|-----------:|----------:|----------:|-----------:|
| Open-Meteo total @h1      |       0.63 |       0.6  |      0.52 |      0.53 |       0.49 |
| Open-Meteo blanket @h1    |       0.69 |       0.72 |      0.75 |      0.76 |       0.72 |
| AI photo cover (160 days) |       0.75 |       0.76 |      0.67 |      0.68 |       0.63 |
| METAR cover               |       0.71 |       0.67 |      0.59 |      0.6  |       0.56 |

## The 9 days Open-Meteo called clear but the photos were cloudy

| camera            | day        |   cloud_cover_total@h1 |   over_g1h |   fan_g1h |   metar_cover |   metar_ceiling |
|:------------------|:-----------|-----------------------:|-----------:|----------:|--------------:|----------------:|
| btv_echo_cam      | 2026-09-01 |                      0 |       1    |      0.85 |          1    |            5500 |
| bolton_summit_cam | 2026-09-01 |                      0 |       1    |      0.88 |          1    |            5500 |
| btv_echo_cam      | 2026-08-23 |                      3 |       0    |      0.45 |          0.75 |           15000 |
| btv_echo_cam      | 2026-04-05 |                      6 |       0.95 |      0.91 |          1    |            4800 |
| wcax_tower_sunset | 2026-08-31 |                      0 |       1    |      0.94 |          0.44 |           30000 |
| wcax_tower_sunset | 2026-10-10 |                      0 |       1    |      1    |          0.44 |           30000 |
| btv_echo_cam      | 2025-12-15 |                      4 |       0.55 |      0.83 |          0.75 |            4500 |
| bolton_summit_cam | 2026-04-24 |                      0 |       1    |      0.04 |          0.44 |           30000 |
| btv_echo_cam      | 2026-08-31 |                      0 |       1    |      0.94 |          0.44 |           30000 |

## Spearman with the outcome (sunset-window best, percentile)

|               |    rho |
|:--------------|-------:|
| over_g1h      | -0.436 |
| near_g1h      | -0.487 |
| far_g1h       | -0.538 |
| fan_g1h       | -0.545 |
| path_g1h      | -0.53  |
| over_g0       | -0.505 |
| near_g0       | -0.52  |
| far_g0        | -0.549 |
| fan_g0        | -0.558 |
| path_g0       | -0.55  |
| metar_cover   | -0.489 |
| metar_ceiling |  0.449 |
| metar_base    |  0.351 |
| metar_vis     |  0.31  |

## Leave-one-month-out (1 h before sunset)

| features               | model   |   n |    R2 |   spearman |   AUC(top 25%) |
|:-----------------------|:--------|----:|------:|-----------:|---------------:|
| weather                | ridge   | 513 | 0.319 |      0.543 |          0.715 |
| weather                | gbm     | 513 | 0.295 |      0.552 |          0.729 |
| weather + GOES         | ridge   | 513 | 0.381 |      0.613 |          0.773 |
| weather + GOES         | gbm     | 513 | 0.335 |      0.59  |          0.766 |
| weather + METAR        | ridge   | 513 | 0.33  |      0.557 |          0.725 |
| weather + METAR        | gbm     | 513 | 0.299 |      0.555 |          0.723 |
| weather + GOES + METAR | ridge   | 513 | 0.381 |      0.612 |          0.771 |
| weather + GOES + METAR | gbm     | 513 | 0.329 |      0.588 |          0.759 |
| GOES only              | ridge   | 513 | 0.284 |      0.515 |          0.758 |
| GOES only              | gbm     | 513 | 0.205 |      0.472 |          0.716 |
| METAR only             | ridge   | 513 | 0.227 |      0.5   |          0.698 |
| METAR only             | gbm     | 513 | 0.243 |      0.488 |          0.688 |