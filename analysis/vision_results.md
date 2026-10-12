# Vision model qwen3-vl:4b on the 1h-pre photo

160 sunset camera-days ({'btv_echo_cam': 107, 'bolton_summit_cam': 36, 'wcax_tower_sunset': 17}), 54 s per photo on average (median 52 s).

## Spearman rho of each answer with the late best score (percentile)

|                   |     rho |
|:------------------|--------:|
| v_quality         |   0.542 |
| v_cover           |  -0.557 |
| v_horizon_clear   | nan     |
| v_type_clear      | nan     |
| v_type_high_thin  | nan     |
| v_type_mid_broken | nan     |
| v_type_low_thick  | nan     |
| v_type_overcast   | nan     |
| v_type_mixed      | nan     |
| warm@i1h          |   0.377 |
| score@i1h         |   0.451 |

## Outcome by the model's predicted quality

| q         |   days |   median_pct |   top25 |
|:----------|-------:|-------------:|--------:|
| (-1, 30]  |     23 |         0.21 |    0.09 |
| (30, 50]  |     20 |         0.23 |    0.1  |
| (50, 70]  |     19 |         0.32 |    0.16 |
| (70, 101] |     98 |         0.64 |    0.4  |

## Outcome by the model's horizon_clear and cloud_type answers

|   v_horizon_clear |   days |   median_pct |   top25 |   top10 |
|------------------:|-------:|-------------:|--------:|--------:|
|                 0 |     36 |         0.19 |    0.08 |    0.03 |
|                 1 |    124 |         0.59 |    0.35 |    0.14 |

| cloud_type   |   days |   median_pct |   top25 |   top10 |
|:-------------|-------:|-------------:|--------:|--------:|
| clear        |     27 |         0.77 |    0.52 |    0.15 |
| high_thin    |     23 |         0.64 |    0.39 |    0.04 |
| low_thick    |     11 |         0.24 |    0.09 |    0    |
| mid_broken   |     65 |         0.54 |    0.31 |    0.18 |
| mixed        |      7 |         0.28 |    0    |    0    |
| overcast     |     27 |         0.16 |    0.07 |    0.04 |


## Leave-one-month-out on these days

| features                           | model   |   n |    R2 |   spearman |   AUC(top 25%) |
|:-----------------------------------|:--------|----:|------:|-----------:|---------------:|
| weather (d)                        | ridge   | 160 | 0.326 |      0.542 |          0.721 |
| weather (d)                        | gbm     | 160 | 0.235 |      0.505 |          0.696 |
| vision answer only                 | ridge   | 160 | 0.272 |      0.486 |          0.694 |
| vision answer only                 | gbm     | 160 | 0.302 |      0.528 |          0.716 |
| simple 1h image features           | ridge   | 160 | 0.158 |      0.444 |          0.673 |
| simple 1h image features           | gbm     | 160 | 0.245 |      0.475 |          0.664 |
| weather + vision                   | ridge   | 160 | 0.334 |      0.548 |          0.722 |
| weather + vision                   | gbm     | 160 | 0.243 |      0.513 |          0.695 |
| weather + simple 1h image          | ridge   | 160 | 0.317 |      0.522 |          0.717 |
| weather + simple 1h image          | gbm     | 160 | 0.359 |      0.586 |          0.736 |
| weather + simple 1h image + vision | ridge   | 160 | 0.324 |      0.533 |          0.722 |
| weather + simple 1h image + vision | gbm     | 160 | 0.363 |      0.596 |          0.745 |