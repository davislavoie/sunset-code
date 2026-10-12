# Upper-level wind along the sun line (517 sunset camera-days)

Target: the day's best score in the sunset window, as a percentile per camera. Leave-one-month-out.

## h2: Spearman of each aloft feature with the outcome

|                 |    rho |
|:----------------|-------:|
| along_850_h2    | -0.025 |
| speed_850_h2    | -0.185 |
| along_700_h2    | -0.115 |
| speed_700_h2    | -0.136 |
| along_500_h2    | -0.096 |
| speed_500_h2    | -0.14  |
| inflow_low_h2   | -0.202 |
| inflow_mid_h2   | -0.347 |
| outflow_over_h2 | -0.035 |


## h1: Spearman of each aloft feature with the outcome

|                 |    rho |
|:----------------|-------:|
| along_850_h1    | -0.037 |
| speed_850_h1    | -0.204 |
| along_700_h1    | -0.119 |
| speed_700_h1    | -0.143 |
| along_500_h1    | -0.104 |
| speed_500_h1    | -0.144 |
| inflow_low_h1   | -0.238 |
| inflow_mid_h1   | -0.354 |
| outflow_over_h1 | -0.018 |


## Leave-one-month-out

| horizon   | features                 | model   |   n |    R2 |   spearman |   AUC(top 25%) |
|:----------|:-------------------------|:--------|----:|------:|-----------:|---------------:|
| h2        | weather                  | ridge   | 517 | 0.292 |      0.524 |          0.711 |
| h2        | weather                  | gbm     | 517 | 0.26  |      0.52  |          0.709 |
| h2        | weather + aloft          | ridge   | 517 | 0.301 |      0.541 |          0.729 |
| h2        | weather + aloft          | gbm     | 517 | 0.307 |      0.56  |          0.727 |
| h2        | aloft only               | ridge   | 517 | 0.146 |      0.371 |          0.66  |
| h2        | aloft only               | gbm     | 517 | 0.112 |      0.336 |          0.631 |
| h2        | weather + speed          | ridge   | 517 | 0.303 |      0.54  |          0.728 |
| h2        | weather + speed          | gbm     | 517 | 0.297 |      0.55  |          0.723 |
| h2        | weather + along          | ridge   | 517 | 0.306 |      0.551 |          0.734 |
| h2        | weather + along          | gbm     | 517 | 0.318 |      0.573 |          0.738 |
| h2        | weather + inflow/outflow | ridge   | 517 | 0.285 |      0.522 |          0.712 |
| h2        | weather + inflow/outflow | gbm     | 517 | 0.27  |      0.522 |          0.709 |
| h1        | weather                  | ridge   | 517 | 0.314 |      0.535 |          0.706 |
| h1        | weather                  | gbm     | 517 | 0.288 |      0.545 |          0.723 |
| h1        | weather + aloft          | ridge   | 517 | 0.325 |      0.562 |          0.732 |
| h1        | weather + aloft          | gbm     | 517 | 0.36  |      0.604 |          0.766 |
| h1        | aloft only               | ridge   | 517 | 0.131 |      0.376 |          0.652 |
| h1        | aloft only               | gbm     | 517 | 0.11  |      0.366 |          0.669 |
| h1        | weather + speed          | ridge   | 517 | 0.318 |      0.55  |          0.722 |
| h1        | weather + speed          | gbm     | 517 | 0.309 |      0.566 |          0.737 |
| h1        | weather + along          | ridge   | 517 | 0.323 |      0.56  |          0.731 |
| h1        | weather + along          | gbm     | 517 | 0.365 |      0.612 |          0.774 |
| h1        | weather + inflow/outflow | ridge   | 517 | 0.317 |      0.542 |          0.714 |
| h1        | weather + inflow/outflow | gbm     | 517 | 0.307 |      0.558 |          0.73  |

## Days with far-path low cloud >= 30 % at 2h: wind toward vs away from the camera (850 hPa)

|                   |   n |   median |   top25 |
|:------------------|----:|---------:|--------:|
| away (< -5 km/h)  |  37 |     0.17 |    0.08 |
| light             |  20 |     0.29 |    0.15 |
| toward (> 5 km/h) | 156 |     0.31 |    0.12 |