# Vision model qwen3-vl:4b on the 1h-pre photo

8 sunset camera-days ({'btv_echo_cam': 6, 'bolton_summit_cam': 2}), 63 s per photo on average (median 68 s).

## Spearman rho of each answer with the late best score (percentile)

|                   |   rho |
|:------------------|------:|
| v_quality         |   nan |
| v_cover           |   nan |
| v_horizon_clear   |   nan |
| v_type_clear      |   nan |
| v_type_high_thin  |   nan |
| v_type_mid_broken |   nan |
| v_type_low_thick  |   nan |
| v_type_overcast   |   nan |
| v_type_mixed      |   nan |
| warm@i1h          |   nan |
| score@i1h         |   nan |

## Answer vs outcome

| q         |   days |   median_pct |   top25 |
|:----------|-------:|-------------:|--------:|
| (-1, 30]  |      1 |         0.04 |     0   |
| (30, 50]  |      2 |         0.15 |     0   |
| (50, 70]  |      0 |       nan    |   nan   |
| (70, 101] |      5 |         0.64 |     0.2 |

## Leave-one-month-out on these days

| features                           | model   |   n |      R2 |   spearman |   AUC(top 25%) |
|:-----------------------------------|:--------|----:|--------:|-----------:|---------------:|
| weather (d)                        | ridge   |   8 | -13.493 |      0.095 |          0.429 |
| weather (d)                        | gbm     |   8 |  -0.499 |     -0.994 |          0     |
| vision answer only                 | ridge   |   8 |   0.687 |      0.667 |          1     |
| vision answer only                 | gbm     |   8 |  -0.499 |     -0.994 |          0     |
| simple 1h image features           | ridge   |   8 |  -0.101 |      0.381 |          1     |
| simple 1h image features           | gbm     |   8 |  -0.499 |     -0.994 |          0     |
| weather + vision                   | ridge   |   8 | -17.064 |      0.238 |          0.571 |
| weather + vision                   | gbm     |   8 |  -0.499 |     -0.994 |          0     |
| weather + simple 1h image          | ridge   |   8 | -15.039 |      0.095 |          0.429 |
| weather + simple 1h image          | gbm     |   8 |  -0.499 |     -0.994 |          0     |
| weather + simple 1h image + vision | ridge   |   8 | -20.558 |      0.238 |          0.429 |
| weather + simple 1h image + vision | gbm     |   8 |  -0.499 |     -0.994 |          0     |