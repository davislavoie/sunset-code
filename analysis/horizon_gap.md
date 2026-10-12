# Horizon light gap, image method (511 sunset camera-days)

Target: the day's best score in the sunset window, as a percentile per camera.

## Outcome by kind (gap on the 1h or 30m thumb)

| kind                    |   n |   median_pct |   top25 |   top10 |
|:------------------------|----:|-------------:|--------:|--------:|
| clear (textured < 10 %) | 117 |         0.52 |    0.3  |    0.1  |
| cloud, no gap           | 373 |         0.5  |    0.24 |    0.11 |
| clouds over a gap       |  21 |         0.64 |    0.33 |    0.19 |

## By camera: gap share

| camera            |   size |   mean |
|:------------------|-------:|-------:|
| bolton_summit_cam |    132 |  0.008 |
| btv_echo_cam      |    332 |  0.048 |
| wcax_tower_sunset |     47 |  0.085 |

## Spearman with the outcome

|                   |   rho |
|:------------------|------:|
| cloud_above_g1h   | 0.114 |
| cloud_above_g30   | 0.117 |
| cloud_frac_g1h    | 0.111 |
| cloud_frac_g30    | 0.115 |
| gap_g1h           | 0.065 |
| gap_g30           | 0.084 |
| gap_thickness_g1h | 0.066 |
| gap_thickness_g30 | 0.085 |

## Leave-one-month-out

| photos   | features               | model   |   n |     R2 |   spearman |   AUC(top 25%) |
|:---------|:-----------------------|:--------|----:|-------:|-----------:|---------------:|
| h1       | weather                | ridge   | 511 |  0.323 |      0.546 |          0.716 |
| h1       | weather                | gbm     | 511 |  0.282 |      0.54  |          0.724 |
| h1       | weather + gap features | ridge   | 511 |  0.323 |      0.541 |          0.708 |
| h1       | weather + gap features | gbm     | 511 |  0.287 |      0.545 |          0.73  |
| h1       | gap features only      | ridge   | 511 | -0.017 |     -0.01  |          0.439 |
| h1       | gap features only      | gbm     | 511 | -0.047 |      0.077 |          0.493 |
| h0 (30m) | weather                | ridge   | 511 |  0.323 |      0.546 |          0.716 |
| h0 (30m) | weather                | gbm     | 511 |  0.282 |      0.54  |          0.724 |
| h0 (30m) | weather + gap features | ridge   | 511 |  0.322 |      0.54  |          0.705 |
| h0 (30m) | weather + gap features | gbm     | 511 |  0.287 |      0.546 |          0.728 |
| h0 (30m) | gap features only      | ridge   | 511 | -0.001 |      0.045 |          0.445 |
| h0 (30m) | gap features only      | gbm     | 511 | -0.012 |      0.151 |          0.525 |