# Forecast at each pre shot (sunset cameras, leave-one-month-out)

Target: the day's best score from 15m pre to 30m post, as a percentile within the camera.

| horizon                             |   days |   spearman |   AUC top-25% |   MAE (percentile pts) |   banger precision (top-10%) |   banger recall |   poor calls on top-25% days |
|:------------------------------------|-------:|-----------:|--------------:|-----------------------:|-----------------------------:|----------------:|-----------------------------:|
| 01_2h_pre                           |    487 |      0.508 |         0.682 |                 20.277 |                        0.2   |           0.019 |                        0.065 |
| 02_1h_pre                           |    486 |      0.551 |         0.684 |                 19.103 |                        0     |           0     |                        0.073 |
| 03_45m_pre                          |    487 |      0.57  |         0.703 |                 18.774 |                        0     |           0     |                        0.049 |
| 04_30m_pre                          |    485 |      0.633 |         0.727 |                 17.68  |                        0.156 |           0.093 |                        0.033 |
| 05_15m_pre                          |    484 |      0.752 |         0.796 |                 13.889 |                        0.288 |           0.278 |                        0.049 |
| 05_15m_pre (vs shots still to come) |    484 |      0.688 |         0.754 |                 16.188 |                        0.192 |           0.185 |                        0.066 |
| 06_5m_pre                           |    483 |      0.868 |         0.9   |                  9.883 |                        0.411 |           0.556 |                        0.033 |
| 06_5m_pre (vs shots still to come)  |    483 |      0.819 |         0.885 |                 11.948 |                        0.37  |           0.5   |                        0.041 |

## Per camera

| horizon    | camera            |   days |   spearman |   AUC top-25% |   MAE (percentile pts) |   banger precision (top-10%) |   banger recall |   poor calls on top-25% days |
|:-----------|:------------------|-------:|-----------:|--------------:|-----------------------:|-----------------------------:|----------------:|-----------------------------:|
| 01_2h_pre  | bolton_summit_cam |    123 |      0.629 |         0.75  |                 18.286 |                        0.5   |           0.077 |                        0     |
| 01_2h_pre  | btv_echo_cam      |    326 |      0.466 |         0.655 |                 21.137 |                        0     |           0     |                        0.098 |
| 01_2h_pre  | wcax_tower_sunset |     38 |      0.545 |         0.707 |                 19.345 |                      nan     |           0     |                        0     |
| 02_1h_pre  | bolton_summit_cam |    122 |      0.635 |         0.75  |                 18.234 |                      nan     |           0     |                        0     |
| 02_1h_pre  | btv_echo_cam      |    326 |      0.528 |         0.657 |                 19.415 |                        0     |           0     |                        0.11  |
| 02_1h_pre  | wcax_tower_sunset |     38 |      0.571 |         0.696 |                 19.217 |                      nan     |           0     |                        0     |
| 03_45m_pre | bolton_summit_cam |    123 |      0.723 |         0.815 |                 16.976 |                        0     |           0     |                        0     |
| 03_45m_pre | btv_echo_cam      |    326 |      0.534 |         0.67  |                 19.309 |                        0     |           0     |                        0.073 |
| 03_45m_pre | wcax_tower_sunset |     38 |      0.509 |         0.668 |                 20.003 |                      nan     |           0     |                        0     |
| 04_30m_pre | bolton_summit_cam |    122 |      0.791 |         0.836 |                 15.733 |                        0.25  |           0.308 |                        0     |
| 04_30m_pre | btv_echo_cam      |    325 |      0.59  |         0.697 |                 18.333 |                        0     |           0     |                        0.049 |
| 04_30m_pre | wcax_tower_sunset |     38 |      0.611 |         0.671 |                 18.352 |                        1     |           0.125 |                        0     |
| 05_15m_pre | bolton_summit_cam |    123 |      0.886 |         0.962 |                 10.698 |                        0.407 |           0.846 |                        0     |
| 05_15m_pre | btv_echo_cam      |    323 |      0.726 |         0.754 |                 14.653 |                        0.16  |           0.121 |                        0.062 |
| 05_15m_pre | wcax_tower_sunset |     38 |      0.69  |         0.7   |                 17.731 |                      nan     |           0     |                        0.1   |
| 06_5m_pre  | bolton_summit_cam |    123 |      0.898 |         0.94  |                  9.402 |                        0.524 |           0.846 |                        0     |
| 06_5m_pre  | btv_echo_cam      |    322 |      0.867 |         0.893 |                  9.737 |                        0.333 |           0.455 |                        0.037 |
| 06_5m_pre  | wcax_tower_sunset |     38 |      0.857 |         0.879 |                 12.675 |                        0.571 |           0.5   |                        0.1   |

## Coefficients (intercept, weather, cur_pct, max_pct)

- 01_2h_pre: [0.3595, 0.2634, 0.191, 0.191]
- 02_1h_pre: [0.3147, 0.266, 0.273, 0.131]
- 03_45m_pre: [0.2859, 0.2324, 0.3036, 0.1593]
- 04_30m_pre: [0.2577, 0.2058, 0.3503, 0.1466]
- 05_15m_pre: [0.1838, 0.1339, 0.6011, 0.0728]
- 06_5m_pre: [0.0866, 0.0239, 0.5523, 0.3526]