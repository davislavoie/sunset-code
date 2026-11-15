# Cloud thickness (GOES optical depth) toward the sun

Does GOES cloud *thickness* toward the sun add to the live forecast? Coverage (goes_far, goes_fan) can't tell
thin cirrus, which lets the sun through and lights up, from a thick deck that blocks it; optical depth can.

Features per zone (over within 10 km, near 5-40 km, far 80-300 km, fan 5-300 km, sun bearing +/-30 deg):

- cod_valid_<z>  share of the zone's pixels with a COD value
- cod_med_<z>    median COD of pixels with COD > 0
- cod_thin_<z>   share of the zone's pixels with 0 < COD < 5 (THIN)
- cod_thick_<z>  share with COD >= 20 (THICK)            (both thresholds fixed before looking at results)
- cod_log_<z>    mean log1p(COD) over the zone, clear (COD 0) and missing pixels as 0
- cod_good_<z>   share the quality flag marks good (DQF & 4 == 0)
- cod_day_<z>    share retrieved by the day algorithm (DQF & 1 == 0): a diagnostic, not a candidate

## Download cost

COD and DQF are gzip chunks of 52 x 2500 (full rows); the reader takes only the rows any zone touches. Mean 1.20 MB per scan (median 1.06, max 2.79), including the 0.26 MB header block, vs the 4.7 MB file. 3085 scans downloaded for 3407 shots.

## Coverage (pre shots in extra.table() with a COD reading)

| horizon    |   shots |   with COD |
|:-----------|--------:|-----------:|
| 01_2h_pre  |     494 |        489 |
| 02_1h_pre  |     493 |        488 |
| 03_45m_pre |     494 |        489 |
| 04_30m_pre |     492 |        486 |
| 05_15m_pre |     491 |        485 |
| 06_5m_pre  |     490 |        484 |

## Comparability

Product attributes: the day algorithm (visible reflectance) runs where the solar zenith angle is under 82 deg (sun elevation over 8 deg), the night algorithm (infrared brightness-temperature differences) above it; DQF marks pixels with solar zenith 65-90 deg (sun 0-25 deg up) as degraded by twilight, so 'good' only happens with the sun over 25 deg or below the horizon. Far zone, quartiles (25% / median / 75%):

### By horizon

| horizon    |   cached_shots | sun_elev              | day_algo           | good               | valid              | median_cod          | thick              |
|:-----------|---------------:|:----------------------|:-------------------|:-------------------|:-------------------|:--------------------|:-------------------|
| 01_2h_pre  |            570 | 17.88 / 18.69 / 19.59 | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | 2.06 / 5.04 / 12.81 | 0.00 / 0.08 / 0.27 |
| 02_1h_pre  |            569 | 8.06 / 8.45 / 9.35    | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | 2.15 / 5.37 / 14.25 | 0.01 / 0.10 / 0.31 |
| 03_45m_pre |            570 | 5.62 / 6.06 / 6.79    | 0.79 / 0.99 / 1.00 | 0.00 / 0.00 / 0.01 | 0.95 / 1.00 / 1.00 | 1.99 / 4.37 / 10.99 | 0.01 / 0.08 / 0.26 |
| 04_30m_pre |            567 | 3.21 / 3.74 / 4.25    | 0.00 / 0.00 / 0.07 | 0.01 / 0.07 / 0.31 | 0.35 / 0.76 / 0.97 | 1.09 / 2.79 / 4.11  | 0.00 / 0.00 / 0.00 |
| 05_15m_pre |            566 | 0.75 / 1.51 / 1.77    | 0.00 / 0.00 / 0.00 | 0.01 / 0.07 / 0.34 | 0.25 / 0.72 / 0.96 | 1.07 / 2.63 / 4.07  | 0.00 / 0.00 / 0.00 |
| 06_5m_pre  |            565 | -1.25 / 0.14 / 0.23   | 0.00 / 0.00 / 0.00 | 0.01 / 0.08 / 0.34 | 0.25 / 0.71 / 0.96 | 1.06 / 2.68 / 4.12  | 0.00 / 0.00 / 0.00 |

### By sun elevation at the camera (deg)

| sun_elev   |   cached_shots | sun_elev              | day_algo           | good               | valid              | median_cod          | thick              |
|:-----------|---------------:|:----------------------|:-------------------|:-------------------|:-------------------|:--------------------|:-------------------|
| (-10, 0]   |            163 | -1.41 / -1.35 / -1.26 | 0.00 / 0.00 / 0.00 | 0.01 / 0.06 / 0.25 | 0.23 / 0.70 / 0.95 | 1.03 / 2.62 / 4.16  | 0.00 / 0.00 / 0.00 |
| (0, 4]     |           1318 | 0.24 / 1.46 / 2.40    | 0.00 / 0.00 / 0.00 | 0.01 / 0.08 / 0.34 | 0.27 / 0.72 / 0.96 | 1.06 / 2.62 / 4.03  | 0.00 / 0.00 / 0.00 |
| (4, 8]     |            925 | 4.61 / 5.92 / 6.89    | 0.41 / 0.93 / 1.00 | 0.00 / 0.00 / 0.03 | 0.90 / 1.00 / 1.00 | 1.84 / 4.02 / 9.14  | 0.00 / 0.06 / 0.19 |
| (8, 12]    |            431 | 8.38 / 8.98 / 9.48    | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | 2.08 / 5.53 / 14.34 | 0.01 / 0.09 / 0.33 |
| (12, 16]   |             45 | 14.38 / 14.62 / 15.44 | 0.99 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 0.99 / 1.00 / 1.00 | 4.11 / 7.37 / 11.77 | 0.06 / 0.12 / 0.22 |
| (16, 25]   |            525 | 18.18 / 18.80 / 19.67 | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | 1.93 / 4.79 / 12.99 | 0.00 / 0.07 / 0.27 |

### Spearman with the existing coverage (all shots)

|               |   goes_far |   goes_fan |
|:--------------|-----------:|-----------:|
| cod_valid_far |       0.44 |       0.44 |
| cod_med_far   |       0.26 |       0.27 |
| cod_thin_far  |       0.65 |       0.65 |
| cod_thick_far |       0.32 |       0.32 |
| cod_log_far   |       0.84 |       0.84 |
| cod_good_far  |      -0.03 |      -0.03 |
| cod_day_far   |       0.03 |       0.03 |
| cod_valid_fan |       0.45 |       0.45 |
| cod_med_fan   |       0.26 |       0.27 |
| cod_thin_fan  |       0.66 |       0.65 |
| cod_thick_fan |       0.31 |       0.32 |
| cod_log_fan   |       0.83 |       0.84 |
| cod_good_fan  |      -0.04 |      -0.04 |
| cod_day_fan   |       0.02 |       0.02 |

Per horizon (far zone): with the night algorithm, clear pixels have no COD, so the 'valid' share becomes the cloud mask's cloudy share; with the day algorithm, clear pixels read 0 and valid is ~1.

| horizon    |   cod_valid_far |   cod_thin_far |   cod_thick_far |   cod_log_far |
|:-----------|----------------:|---------------:|----------------:|--------------:|
| 01_2h_pre  |           -0.08 |           0.3  |            0.66 |          0.88 |
| 02_1h_pre  |           -0.04 |           0.5  |            0.67 |          0.87 |
| 03_45m_pre |            0.35 |           0.59 |            0.65 |          0.84 |
| 04_30m_pre |            0.96 |           0.87 |            0.25 |          0.85 |
| 05_15m_pre |            1    |           0.89 |          nan    |          0.87 |
| 06_5m_pre  |            1    |           0.89 |          nan    |          0.87 |

## Spearman with the outcome (pct) per horizon

|                |   01_2h_pre |   02_1h_pre |   03_45m_pre |   04_30m_pre |   05_15m_pre |   06_5m_pre |
|:---------------|------------:|------------:|-------------:|-------------:|-------------:|------------:|
| cod_valid_over |       0.051 |       0.016 |       -0.272 |       -0.42  |       -0.431 |      -0.451 |
| cod_med_over   |      -0.366 |      -0.334 |       -0.161 |       -0.2   |       -0.207 |      -0.212 |
| cod_thin_over  |       0.086 |       0.043 |       -0.208 |       -0.291 |       -0.293 |      -0.323 |
| cod_thick_over |      -0.396 |      -0.425 |       -0.111 |        0     |        0     |       0     |
| cod_log_over   |      -0.452 |      -0.459 |       -0.4   |       -0.445 |       -0.44  |      -0.442 |
| cod_good_over  |       0     |       0.022 |       -0.114 |       -0.143 |       -0.103 |      -0.105 |
| cod_day_over   |       0.051 |       0.075 |        0.101 |        0     |        0     |       0     |
| cod_valid_far  |      -0.043 |      -0.017 |       -0.112 |       -0.466 |       -0.502 |      -0.518 |
| cod_med_far    |      -0.453 |      -0.38  |       -0.307 |       -0.15  |       -0.178 |      -0.188 |
| cod_thin_far   |       0.051 |      -0.07  |       -0.148 |       -0.385 |       -0.41  |      -0.412 |
| cod_thick_far  |      -0.521 |      -0.533 |       -0.475 |       -0.07  |        0     |       0     |
| cod_log_far    |      -0.563 |      -0.565 |       -0.534 |       -0.506 |       -0.537 |      -0.547 |
| cod_good_far   |      -0.049 |       0     |       -0.048 |       -0.187 |       -0.192 |      -0.198 |
| cod_day_far    |      -0.043 |      -0.017 |        0.046 |        0.108 |        0     |       0     |
| cod_valid_fan  |      -0.044 |      -0.005 |       -0.176 |       -0.475 |       -0.512 |      -0.526 |
| cod_med_fan    |      -0.461 |      -0.391 |       -0.301 |       -0.153 |       -0.17  |      -0.184 |
| cod_thin_fan   |       0.049 |      -0.067 |       -0.166 |       -0.39  |       -0.416 |      -0.418 |
| cod_thick_fan  |      -0.531 |      -0.543 |       -0.474 |       -0.07  |        0     |       0     |
| cod_log_fan    |      -0.568 |      -0.572 |       -0.539 |       -0.514 |       -0.544 |      -0.554 |
| cod_good_fan   |      -0.049 |       0.043 |       -0.082 |       -0.195 |       -0.202 |      -0.206 |
| cod_day_fan    |      -0.044 |       0.013 |        0.063 |        0.108 |        0     |       0     |
| goes_far       |      -0.514 |      -0.501 |       -0.491 |       -0.487 |       -0.507 |      -0.518 |
| goes_fan       |      -0.525 |      -0.508 |       -0.501 |       -0.495 |       -0.516 |      -0.526 |

## extra.report (leave-one-month-out; gain in AUC top-25% vs the 95th percentile of the gain with the new inputs shuffled)

| set                          | horizon    |   n |   spearman |   AUC top-25% |   AUC top-10% |    MAE |   AUC gain |   shuffled 95% |
|:-----------------------------|:-----------|----:|-----------:|--------------:|--------------:|-------:|-----------:|---------------:|
| live                         | 01_2h_pre  | 488 |      0.549 |         0.716 |         0.606 | 19.829 |    nan     |        nan     |
| live+thick far               | 01_2h_pre  | 488 |      0.565 |         0.716 |         0.615 | 19.077 |      0     |          0.005 |
| live+thin far                | 01_2h_pre  | 488 |      0.559 |         0.715 |         0.617 | 19.032 |     -0.001 |          0.003 |
| live+thin+thick far          | 01_2h_pre  | 488 |      0.56  |         0.715 |         0.615 | 19.003 |     -0.001 |          0.002 |
| live+log far                 | 01_2h_pre  | 488 |      0.558 |         0.712 |         0.616 | 19.06  |     -0.004 |          0.002 |
| live+thin over+thick far     | 01_2h_pre  | 488 |      0.566 |         0.716 |         0.616 | 19.018 |      0.001 |          0.004 |
| live                         | 02_1h_pre  | 487 |      0.6   |         0.739 |         0.616 | 18.318 |    nan     |        nan     |
| live+thick far               | 02_1h_pre  | 487 |      0.612 |         0.739 |         0.625 | 17.814 |      0.001 |          0.005 |
| live+thin far                | 02_1h_pre  | 487 |      0.607 |         0.74  |         0.629 | 17.933 |      0.002 |          0.003 |
| live+thin+thick far          | 02_1h_pre  | 487 |      0.609 |         0.739 |         0.625 | 17.85  |     -0     |          0.003 |
| live+log far                 | 02_1h_pre  | 487 |      0.61  |         0.739 |         0.628 | 17.849 |     -0     |          0.002 |
| live+thin over+thick far     | 02_1h_pre  | 487 |      0.609 |         0.737 |         0.622 | 17.805 |     -0.002 |          0.003 |
| live                         | 03_45m_pre | 488 |      0.596 |         0.733 |         0.602 | 18.193 |    nan     |        nan     |
| live+thick far               | 03_45m_pre | 488 |      0.597 |         0.733 |         0.603 | 18.073 |     -0     |          0.003 |
| live+thin far                | 03_45m_pre | 488 |      0.597 |         0.735 |         0.608 | 18.131 |      0.002 |          0.004 |
| live+thin+thick far          | 03_45m_pre | 488 |      0.595 |         0.734 |         0.606 | 18.132 |      0.001 |          0.003 |
| live+log far                 | 03_45m_pre | 488 |      0.595 |         0.733 |         0.607 | 18.116 |     -0     |          0.003 |
| live+thin over+thick far     | 03_45m_pre | 488 |      0.594 |         0.732 |         0.601 | 18.162 |     -0.001 |          0.004 |
| live                         | 04_30m_pre | 485 |      0.614 |         0.746 |         0.632 | 17.738 |    nan     |        nan     |
| live+thick far               | 04_30m_pre | 485 |      0.606 |         0.743 |         0.629 | 17.926 |     -0.003 |          0.001 |
| live+thin far                | 04_30m_pre | 485 |      0.611 |         0.745 |         0.633 | 17.764 |     -0     |          0.002 |
| live+thin+thick far          | 04_30m_pre | 485 |      0.605 |         0.743 |         0.631 | 17.915 |     -0.002 |          0.002 |
| live+log far                 | 04_30m_pre | 485 |      0.612 |         0.745 |         0.635 | 17.753 |     -0.001 |          0.004 |
| live+thin over+thick far     | 04_30m_pre | 485 |      0.609 |         0.75  |         0.642 | 17.842 |      0.004 |          0.005 |
| live                         | 05_15m_pre | 484 |      0.677 |         0.787 |         0.671 | 15.929 |    nan     |        nan     |
| live+thick far               | 05_15m_pre | 484 |      0.677 |         0.787 |         0.671 | 15.929 |      0     |          0     |
| live+thin far                | 05_15m_pre | 484 |      0.676 |         0.786 |         0.672 | 15.949 |     -0.001 |          0.003 |
| live+thin+thick far          | 05_15m_pre | 484 |      0.676 |         0.786 |         0.672 | 15.949 |     -0.001 |          0.001 |
| live+log far                 | 05_15m_pre | 484 |      0.677 |         0.788 |         0.678 | 15.907 |      0.001 |          0.001 |
| live+thin over+thick far     | 05_15m_pre | 484 |      0.68  |         0.794 |         0.686 | 15.902 |      0.007 |          0     |
| live                         | 06_5m_pre  | 483 |      0.757 |         0.87  |         0.791 | 13.15  |    nan     |        nan     |
| live+thick far               | 06_5m_pre  | 483 |      0.757 |         0.87  |         0.791 | 13.15  |      0     |          0     |
| live+thin far                | 06_5m_pre  | 483 |      0.756 |         0.869 |         0.791 | 13.177 |     -0.001 |          0.001 |
| live+thin+thick far          | 06_5m_pre  | 483 |      0.756 |         0.869 |         0.791 | 13.177 |     -0.001 |          0.002 |
| live+log far                 | 06_5m_pre  | 483 |      0.756 |         0.869 |         0.792 | 13.214 |     -0.001 |          0.002 |
| live+thin over+thick far     | 06_5m_pre  | 483 |      0.759 |         0.873 |         0.797 | 13.275 |      0.002 |          0.002 |
| live+sky                     | 02_1h_pre  | 486 |      0.644 |         0.747 |         0.625 | 17.081 |    nan     |        nan     |
| live+sky+thick far           | 02_1h_pre  | 486 |      0.655 |         0.749 |         0.634 | 16.763 |      0.002 |          0.003 |
| live+sky+thin far            | 02_1h_pre  | 486 |      0.654 |         0.752 |         0.64  | 16.852 |      0.005 |          0.006 |
| live+sky+thin+thick far      | 02_1h_pre  | 486 |      0.654 |         0.75  |         0.637 | 16.812 |      0.003 |          0.005 |
| live+sky+log far             | 02_1h_pre  | 486 |      0.654 |         0.75  |         0.637 | 16.802 |      0.002 |          0.003 |
| live+sky+thin over+thick far | 02_1h_pre  | 486 |      0.651 |         0.746 |         0.63  | 16.829 |     -0.001 |          0.003 |
| live+sky                     | 03_45m_pre | 487 |      0.665 |         0.756 |         0.629 | 16.729 |    nan     |        nan     |
| live+sky+thick far           | 03_45m_pre | 487 |      0.67  |         0.759 |         0.633 | 16.659 |      0.002 |          0.003 |
| live+sky+thin far            | 03_45m_pre | 487 |      0.669 |         0.761 |         0.639 | 16.688 |      0.004 |          0.003 |
| live+sky+thin+thick far      | 03_45m_pre | 487 |      0.668 |         0.76  |         0.638 | 16.706 |      0.003 |          0.002 |
| live+sky+log far             | 03_45m_pre | 487 |      0.666 |         0.758 |         0.635 | 16.704 |      0.001 |          0.002 |
| live+sky+thin over+thick far | 03_45m_pre | 487 |      0.669 |         0.759 |         0.636 | 16.621 |      0.003 |          0.001 |
| live+sky                     | 04_30m_pre | 482 |      0.669 |         0.764 |         0.651 | 16.632 |    nan     |        nan     |
| live+sky+thick far           | 04_30m_pre | 482 |      0.665 |         0.763 |         0.648 | 16.725 |     -0.002 |          0.001 |
| live+sky+thin far            | 04_30m_pre | 482 |      0.672 |         0.767 |         0.656 | 16.568 |      0.003 |          0.001 |
| live+sky+thin+thick far      | 04_30m_pre | 482 |      0.667 |         0.766 |         0.653 | 16.668 |      0.001 |          0.002 |
| live+sky+log far             | 04_30m_pre | 482 |      0.673 |         0.766 |         0.657 | 16.598 |      0.002 |          0.002 |
| live+sky+thin over+thick far | 04_30m_pre | 482 |      0.669 |         0.769 |         0.661 | 16.621 |      0.004 |          0.005 |
| live+sky                     | 05_15m_pre | 483 |      0.728 |         0.798 |         0.691 | 15.027 |    nan     |        nan     |
| live+sky+thick far           | 05_15m_pre | 483 |      0.728 |         0.798 |         0.691 | 15.027 |      0     |          0     |
| live+sky+thin far            | 05_15m_pre | 483 |      0.726 |         0.798 |         0.692 | 15.024 |      0.001 |          0.004 |
| live+sky+thin+thick far      | 05_15m_pre | 483 |      0.726 |         0.798 |         0.692 | 15.024 |      0.001 |          0.002 |
| live+sky+log far             | 05_15m_pre | 483 |      0.726 |         0.8   |         0.696 | 14.999 |      0.002 |          0.001 |
| live+sky+thin over+thick far | 05_15m_pre | 483 |      0.727 |         0.803 |         0.703 | 14.948 |      0.005 |          0.001 |

### Mean gain in AUC top-25%

| set                          |   horizons |   mean_gain |   mean_shuffled_95 |   beats_shuffle |
|:-----------------------------|-----------:|------------:|-------------------:|----------------:|
| live+thick far               |          6 |      -0     |              0.002 |               0 |
| live+thin far                |          6 |       0     |              0.003 |               0 |
| live+thin+thick far          |          6 |      -0.001 |              0.002 |               0 |
| live+log far                 |          6 |      -0.001 |              0.002 |               1 |
| live+thin over+thick far     |          6 |       0.002 |              0.003 |               2 |
| live+sky+thick far           |          4 |       0.001 |              0.002 |               0 |
| live+sky+thin far            |          4 |       0.003 |              0.004 |               2 |
| live+sky+thin+thick far      |          4 |       0.002 |              0.003 |               1 |
| live+sky+log far             |          4 |       0.002 |              0.002 |               1 |
| live+sky+thin over+thick far |          4 |       0.003 |              0.002 |               2 |

## Verdict

**No: thickness does not help the forecast, and it should not go live.**

- Score: every candidate set's gain in AUC top-25% is between -0.004 and +0.007, and the mean gain over the
  horizons is at or below the mean "shuffled 95%" for every set (best: +thin over+thick far, +0.002 vs 0.003).
  The few single horizons that beat the shuffle do so by 0.001-0.007 out of ~50 comparisons: noise.
- Why: the thickness numbers mostly repeat coverage. log1p(COD) correlates 0.84-0.88 with goes_far per horizon and
  thick far 0.65-0.67 on the day-algorithm horizons. On their own they rank the outcome only a little better than
  coverage (log far rho -0.56 vs goes_far -0.51 at 2 h and 1 h), and that edge vanishes once the live line
  (which has goes_fan and the HSV scores) is in the fit.
- Comparability: the shots straddle the product's algorithm switch at sun elevation 8 deg. 2 h and 1 h before
  sunset (sun ~19 and ~8.5 deg up) are the day algorithm (1 h only just: its
  sun sits 0-1.5 deg above the switch), 45 min is mixed, 30/15/5 min are all the night
  algorithm. The night algorithm gives no value on clear pixels (valid share = cloud share, rho 0.96-1.0 with
  goes_far), never gave COD of 20 or more here (cod_thick_far is 0 on every 15 and 5 min shot) and puts nearly all cloud
  under 5, so 'thin' then means 'cloudy'. No day-algorithm pixel is flagged good at these sun angles
  (twilight, solar zenith 65-90 deg); 'good' only appears on night-algorithm pixels.
  So the 2 h and the 15 min readings are not the same measurement, and a feature like cod_thick_far would carry
  a different meaning by horizon and, near 1 h / 45 min, by season.
- What is left: only the day-algorithm horizons (2 h, 1 h) measure thickness as intended, and there thick far
  (rho -0.52/-0.53 with pct) is about as predictive as log far (-0.56) yet adds nothing on top of the live line.
