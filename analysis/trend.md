# Does the GOES cloud trend help the forecast?

Features, per pre shot on the three sunset cameras: `goes_Z_trend` = this shot's satellite cloud fraction in zone Z
(fan 5-300 km, far 80-300 km, near 5-40 km toward the sun, over = overhead) minus the previous pre shot's on the same
camera and day; `goes_Z_rate` = that per hour between the two captures (gaps are 60, 15, 15, 15, 10 min). The 2h shot
has no earlier shot, so it uses the scan 60 minutes before its capture. Every reading uses only scans that had landed
by its capture time. Candidate sets were fixed before looking at results.

## Shots with a trend value

| horizon    |   goes_fan_trend |   goes_far_trend |   goes_near_trend |   goes_over_trend |   shots |
|:-----------|-----------------:|-----------------:|------------------:|------------------:|--------:|
| 01_2h_pre  |              489 |              489 |               489 |               489 |     494 |
| 02_1h_pre  |              488 |              488 |               488 |               488 |     493 |
| 03_45m_pre |              489 |              489 |               489 |               489 |     494 |
| 04_30m_pre |              486 |              486 |               486 |               486 |     492 |
| 05_15m_pre |              485 |              485 |               485 |               485 |     491 |
| 06_5m_pre  |              484 |              484 |               484 |               484 |     490 |

## Spearman correlation of each trend with pct (day's outcome percentile)

| horizon    |   goes_fan_trend |   goes_far_trend |   goes_near_trend |   goes_over_trend |
|:-----------|-----------------:|-----------------:|------------------:|------------------:|
| 01_2h_pre  |           -0.084 |           -0.073 |            -0.027 |             0.055 |
| 02_1h_pre  |           -0.045 |           -0.039 |            -0.034 |            -0.028 |
| 03_45m_pre |           -0.002 |            0.021 |             0.036 |             0.046 |
| 04_30m_pre |           -0.022 |           -0.027 |            -0.051 |            -0.064 |
| 05_15m_pre |           -0.105 |           -0.097 |            -0.111 |            -0.046 |
| 06_5m_pre  |           -0.105 |           -0.105 |            -0.083 |            -0.079 |

## Leave-one-month-out comparison

| set                     | horizon    |   n |   spearman |   AUC top-25% |   AUC top-10% |    MAE |   AUC gain |   shuffled 95% |
|:------------------------|:-----------|----:|-----------:|--------------:|--------------:|-------:|-----------:|---------------:|
| live                    | 01_2h_pre  | 488 |      0.549 |         0.716 |         0.606 | 19.829 |    nan     |        nan     |
| live+fan trend          | 01_2h_pre  | 488 |      0.549 |         0.715 |         0.605 | 19.81  |     -0     |          0.003 |
| live+far trend          | 01_2h_pre  | 488 |      0.549 |         0.715 |         0.604 | 19.803 |     -0     |          0.004 |
| live+fan rate           | 01_2h_pre  | 488 |      0.549 |         0.715 |         0.605 | 19.81  |     -0     |          0.003 |
| live+far+near trend     | 01_2h_pre  | 488 |      0.545 |         0.712 |         0.601 | 19.89  |     -0.003 |          0.002 |
| live                    | 02_1h_pre  | 487 |      0.6   |         0.739 |         0.616 | 18.318 |    nan     |        nan     |
| live+fan trend          | 02_1h_pre  | 487 |      0.61  |         0.744 |         0.627 | 18.101 |      0.005 |          0.002 |
| live+far trend          | 02_1h_pre  | 487 |      0.61  |         0.744 |         0.627 | 18.074 |      0.005 |          0.002 |
| live+fan rate           | 02_1h_pre  | 487 |      0.61  |         0.744 |         0.627 | 18.101 |      0.005 |          0.002 |
| live+far+near trend     | 02_1h_pre  | 487 |      0.61  |         0.744 |         0.629 | 18.106 |      0.005 |          0.004 |
| live                    | 03_45m_pre | 488 |      0.596 |         0.733 |         0.602 | 18.193 |    nan     |        nan     |
| live+fan trend          | 03_45m_pre | 488 |      0.604 |         0.74  |         0.603 | 18.018 |      0.007 |          0.004 |
| live+far trend          | 03_45m_pre | 488 |      0.601 |         0.738 |         0.603 | 18.082 |      0.005 |          0.004 |
| live+fan rate           | 03_45m_pre | 488 |      0.604 |         0.74  |         0.603 | 18.009 |      0.007 |          0.004 |
| live+far+near trend     | 03_45m_pre | 488 |      0.6   |         0.737 |         0.602 | 18.116 |      0.004 |          0.002 |
| live                    | 04_30m_pre | 485 |      0.614 |         0.746 |         0.632 | 17.738 |    nan     |        nan     |
| live+fan trend          | 04_30m_pre | 485 |      0.612 |         0.744 |         0.631 | 17.788 |     -0.002 |          0.002 |
| live+far trend          | 04_30m_pre | 485 |      0.612 |         0.744 |         0.631 | 17.789 |     -0.002 |          0.002 |
| live+fan rate           | 04_30m_pre | 485 |      0.612 |         0.744 |         0.631 | 17.788 |     -0.002 |          0.003 |
| live+far+near trend     | 04_30m_pre | 485 |      0.614 |         0.742 |         0.633 | 17.828 |     -0.003 |          0.003 |
| live                    | 05_15m_pre | 484 |      0.677 |         0.787 |         0.671 | 15.929 |    nan     |        nan     |
| live+fan trend          | 05_15m_pre | 484 |      0.674 |         0.786 |         0.67  | 16     |     -0.001 |          0.002 |
| live+far trend          | 05_15m_pre | 484 |      0.674 |         0.786 |         0.67  | 15.994 |     -0.001 |          0.002 |
| live+fan rate           | 05_15m_pre | 484 |      0.674 |         0.786 |         0.669 | 16.005 |     -0.001 |          0.001 |
| live+far+near trend     | 05_15m_pre | 484 |      0.673 |         0.785 |         0.668 | 16.035 |     -0.002 |          0     |
| live                    | 06_5m_pre  | 483 |      0.757 |         0.87  |         0.791 | 13.15  |    nan     |        nan     |
| live+fan trend          | 06_5m_pre  | 483 |      0.758 |         0.87  |         0.794 | 13.185 |      0     |          0.002 |
| live+far trend          | 06_5m_pre  | 483 |      0.759 |         0.871 |         0.794 | 13.181 |      0     |          0.002 |
| live+fan rate           | 06_5m_pre  | 483 |      0.759 |         0.871 |         0.795 | 13.176 |      0.001 |          0.002 |
| live+far+near trend     | 06_5m_pre  | 483 |      0.757 |         0.87  |         0.793 | 13.21  |     -0     |          0.003 |
| live+sky                | 02_1h_pre  | 486 |      0.644 |         0.747 |         0.625 | 17.081 |    nan     |        nan     |
| live+sky+fan trend      | 02_1h_pre  | 486 |      0.652 |         0.751 |         0.634 | 16.897 |      0.004 |          0.002 |
| live+sky+far trend      | 02_1h_pre  | 486 |      0.651 |         0.75  |         0.633 | 16.878 |      0.003 |          0.002 |
| live+sky+fan rate       | 02_1h_pre  | 486 |      0.652 |         0.751 |         0.634 | 16.897 |      0.004 |          0.004 |
| live+sky+far+near trend | 02_1h_pre  | 486 |      0.651 |         0.751 |         0.638 | 16.934 |      0.003 |          0.006 |
| live+sky                | 03_45m_pre | 487 |      0.665 |         0.756 |         0.629 | 16.729 |    nan     |        nan     |
| live+sky+fan trend      | 03_45m_pre | 487 |      0.676 |         0.764 |         0.631 | 16.62  |      0.007 |          0.002 |
| live+sky+far trend      | 03_45m_pre | 487 |      0.673 |         0.762 |         0.631 | 16.672 |      0.005 |          0.004 |
| live+sky+fan rate       | 03_45m_pre | 487 |      0.676 |         0.764 |         0.631 | 16.62  |      0.007 |          0.001 |
| live+sky+far+near trend | 03_45m_pre | 487 |      0.671 |         0.76  |         0.628 | 16.724 |      0.003 |          0.003 |
| live+sky                | 04_30m_pre | 482 |      0.669 |         0.764 |         0.651 | 16.632 |    nan     |        nan     |
| live+sky+fan trend      | 04_30m_pre | 482 |      0.668 |         0.762 |         0.65  | 16.662 |     -0.002 |          0.003 |
| live+sky+far trend      | 04_30m_pre | 482 |      0.667 |         0.762 |         0.649 | 16.672 |     -0.003 |          0.002 |
| live+sky+fan rate       | 04_30m_pre | 482 |      0.668 |         0.762 |         0.65  | 16.662 |     -0.002 |          0.002 |
| live+sky+far+near trend | 04_30m_pre | 482 |      0.668 |         0.761 |         0.65  | 16.758 |     -0.004 |          0.002 |
| live+sky                | 05_15m_pre | 483 |      0.728 |         0.798 |         0.691 | 15.027 |    nan     |        nan     |
| live+sky+fan trend      | 05_15m_pre | 483 |      0.726 |         0.797 |         0.69  | 15.069 |     -0.001 |          0.002 |
| live+sky+far trend      | 05_15m_pre | 483 |      0.726 |         0.797 |         0.689 | 15.06  |     -0.001 |          0.004 |
| live+sky+fan rate       | 05_15m_pre | 483 |      0.726 |         0.797 |         0.689 | 15.074 |     -0.001 |          0.001 |
| live+sky+far+near trend | 05_15m_pre | 483 |      0.724 |         0.796 |         0.69  | 15.108 |     -0.002 |          0.002 |

### Mean gain in AUC top-25%

| set                     |   horizons |   mean_gain |   mean_shuffled_95 |   beats_shuffle |
|:------------------------|-----------:|------------:|-------------------:|----------------:|
| live+fan trend          |          6 |       0.001 |              0.002 |               2 |
| live+far trend          |          6 |       0.001 |              0.003 |               2 |
| live+fan rate           |          6 |       0.002 |              0.002 |               2 |
| live+far+near trend     |          6 |       0     |              0.002 |               2 |
| live+sky+fan trend      |          4 |       0.002 |              0.002 |               2 |
| live+sky+far trend      |          4 |       0.001 |              0.003 |               2 |
| live+sky+fan rate       |          4 |       0.002 |              0.002 |               2 |
| live+sky+far+near trend |          4 |       0     |              0.003 |               1 |

## Verdict

No. Trend does not help. The gains are at most +0.007 AUC (top-25%) and only at the 1h and 45m shots, where the
shuffled-input 95% is 0.002-0.004, so those two horizons edge past noise by about 0.003, which is too small to matter
(MAE improves by about 0.2 points). At 2h, 30m, 15m and 5m the gain is zero or negative and inside the shuffle
spread. Averaged over horizons the gain is 0.000-0.002, no larger than the shuffled 95% (0.002-0.003). The raw
Spearman correlations of trend with the outcome are all within +/-0.11 and mostly negative at the late shots,
which is also weak. The live model already carries the current satellite level; the change in it adds nothing reliable.
