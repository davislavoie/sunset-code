# Horizon light band (scratch run 2026-10-13)

```
514 camera-days; 480 with GOES; 120 ranked
| feature      |   all days |   cloudy toward sun (goes_near>=.5) |   your score (btv) |
|:-------------|-----------:|------------------------------------:|-------------------:|
| lift@h1      |      0.389 |                               0.294 |              0.334 |
| lift@m30     |      0.377 |                               0.31  |              0.196 |
| lift_max@h1  |      0.365 |                               0.31  |              0.266 |
| lift_max@m30 |      0.345 |                               0.275 |              0.182 |
| ratio@h1     |      0.361 |                               0.267 |              0.299 |
| ratio@m30    |      0.353 |                               0.288 |              0.163 |
| warm@h1      |      0.233 |                               0.314 |             -0.133 |
| warm@m30     |      0.496 |                               0.469 |              0.094 |
sat gap (near - far), cloudy days: 0.224 320
photo lift_max@h1 vs satellite gap: -0.125
02_1h_pre lift vs cur_pct: 0.267  vs goes_fan: -0.304
04_30m_pre lift vs cur_pct: 0.22  vs goes_fan: -0.278
| shot       | features           |   n |   spearman |   AUC top25 |
|:-----------|:-------------------|----:|-----------:|------------:|
| 02_1h_pre  | live               | 480 |      0.634 |       0.752 |
| 02_1h_pre  | live + lift        | 480 |      0.639 |       0.761 |
| 02_1h_pre  | live + lift + warm | 480 |      0.64  |       0.764 |
| 04_30m_pre | live               | 477 |      0.672 |       0.764 |
| 04_30m_pre | live + lift        | 477 |      0.681 |       0.778 |
| 04_30m_pre | live + lift + warm | 477 |      0.68  |       0.777 |
```
