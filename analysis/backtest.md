# Backtest: simple forecast vs the actual sunset-window HSV score


## read at 01_2h_pre

|                                     |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunrise |   wcax_tower_sunset |   sunset cams pooled |
|:------------------------------------|--------------------:|---------------:|---------------------:|--------------------:|---------------------:|
| days                                |             133     |        336     |               47     |              47     |              516     |
| spearman                            |               0.575 |          0.449 |                0.318 |               0.586 |                0.497 |
| MAE (pred/100 vs actual percentile) |               0.219 |          0.246 |                0.265 |               0.203 |                0.235 |
| AUC top-25%                         |               0.749 |          0.67  |                0.626 |               0.764 |                0.704 |
| top-25% days called good            |               0.647 |          0.518 |                0.167 |               0.769 |                0.576 |
| top-25% days called poor            |               0.118 |          0.235 |                0.417 |               0.077 |                0.189 |
| 'good' calls that were top-third    |               0.528 |          0.523 |                0.333 |               0.6   |                0.533 |
| 'poor' calls that were bottom-third |               0.625 |          0.572 |                0.458 |               0.667 |                0.593 |

Predicted class (rows) vs actual tercile within camera (columns), sunset cameras:

| cls   |   bottom |   middle |   top |
|:------|---------:|---------:|------:|
| poor  |      134 |       60 |    32 |
| maybe |       21 |       43 |    42 |
| good  |       17 |       69 |    98 |

Median actual best score by predicted class, per camera:

| cls   |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunset |
|:------|--------------------:|---------------:|--------------------:|
| poor  |                 0.8 |            5.4 |                20.9 |
| maybe |                10.6 |           24.5 |                60.6 |
| good  |                19   |           29.4 |                80.5 |

## read at 02_1h_pre

|                                     |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunrise |   wcax_tower_sunset |   sunset cams pooled |
|:------------------------------------|--------------------:|---------------:|---------------------:|--------------------:|---------------------:|
| days                                |             132     |        336     |               46     |              47     |              515     |
| spearman                            |               0.549 |          0.531 |                0.317 |               0.646 |                0.542 |
| MAE (pred/100 vs actual percentile) |               0.216 |          0.226 |                0.257 |               0.186 |                0.219 |
| AUC top-25%                         |               0.75  |          0.702 |                0.619 |               0.809 |                0.722 |
| top-25% days called good            |               0.706 |          0.588 |                0.182 |               0.692 |                0.629 |
| top-25% days called poor            |               0.029 |          0.176 |                0.273 |               0     |                0.121 |
| 'good' calls that were top-third    |               0.545 |          0.543 |                0.333 |               0.6   |                0.55  |
| 'poor' calls that were bottom-third |               0.744 |          0.632 |                0.524 |               0.75  |                0.667 |

Predicted class (rows) vs actual tercile within camera (columns), sunset cameras:

| cls   |   bottom |   middle |   top |
|:------|---------:|---------:|------:|
| poor  |      130 |       44 |    21 |
| maybe |       21 |       57 |    40 |
| good  |       20 |       71 |   111 |

Median actual best score by predicted class, per camera:

| cls   |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunset |
|:------|--------------------:|---------------:|--------------------:|
| poor  |                 0.2 |            3.4 |                18.3 |
| maybe |                 8   |           21.1 |                65.5 |
| good  |                21.2 |           31.9 |                74.6 |