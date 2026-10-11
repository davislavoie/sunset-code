camera-days: {'bolton_summit_cam': 133, 'btv_echo_cam': 340, 'wcax_tower_sunrise': 47, 'wcax_tower_sunset': 48}
best shot at 2h/1h pre (so y != y_late): 49.8%

## stored fields, Spearman rho (top 20 by pooled sunset)
|                              |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunrise |   wcax_tower_sunset |   sunset_pooled |
|:-----------------------------|--------------------:|---------------:|---------------------:|--------------------:|----------------:|
| path40_cloud_cover_low@h0    |               -0.55 |          -0.53 |               nan    |               -0.51 |           -0.53 |
| cloud_cover_total@h0         |               -0.58 |          -0.46 |               nan    |               -0.36 |           -0.49 |
| path50_cloud_cover_low@h0    |               -0.58 |          -0.47 |               nan    |               -0.37 |           -0.49 |
| path80_cloud_cover_mid@h1    |               -0.43 |          -0.49 |                 0.02 |               -0.56 |           -0.48 |
| cloud_cover_low@h0           |               -0.62 |          -0.43 |               nan    |               -0.38 |           -0.48 |
| path80_cloud_cover_low@h1    |               -0.6  |          -0.42 |                -0.4  |               -0.56 |           -0.47 |
| path13_cloud_cover_low@h1    |               -0.55 |          -0.44 |                -0.58 |               -0.45 |           -0.47 |
| path80_cloud_cover_mid@h0    |               -0.49 |          -0.46 |               nan    |               -0.5  |           -0.46 |
| path50_cloud_cover_low@h1    |               -0.51 |          -0.45 |                -0.35 |               -0.48 |           -0.46 |
| path13_cloud_cover_low@h0    |               -0.49 |          -0.45 |               nan    |               -0.49 |           -0.46 |
| path40_cloud_cover_low@h1    |               -0.57 |          -0.43 |                -0.26 |               -0.49 |           -0.46 |
| precipitation_probability@h1 |               -0.51 |          -0.44 |                -0.3  |               -0.49 |           -0.46 |
| precipitation_probability@h0 |               -0.51 |          -0.43 |               nan    |               -0.49 |           -0.46 |
| path80_cloud_cover_mid@h2    |               -0.38 |          -0.47 |                -0.14 |               -0.56 |           -0.46 |
| path150_cloud_cover_mid@h0   |               -0.39 |          -0.47 |               nan    |               -0.55 |           -0.45 |
| path80_cloud_cover_low@h0    |               -0.5  |          -0.42 |               nan    |               -0.5  |           -0.44 |
| precipitation_probability@h2 |               -0.54 |          -0.39 |                -0.42 |               -0.49 |           -0.44 |
| path80_cloud_cover_low@h2    |               -0.59 |          -0.38 |                -0.41 |               -0.46 |           -0.43 |
| path50_cloud_cover_mid@h2    |               -0.37 |          -0.45 |                -0.07 |               -0.47 |           -0.43 |
| cloud_cover_total@h1         |               -0.52 |          -0.38 |                -0.54 |               -0.42 |           -0.43 |

## strongest blanket points, sunset pooled
| layer   |   offset |   km | hour   |    rho |
|:--------|---------:|-----:|:-------|-------:|
| low     |      -10 |   40 | h0     | -0.532 |
| low     |        0 |   40 | h0     | -0.524 |
| low     |      -30 |   25 | h0     | -0.524 |
| low     |       20 |   25 | h0     | -0.521 |
| low     |       20 |   40 | h0     | -0.518 |
| low     |       10 |   40 | h0     | -0.516 |
| low     |      -10 |   25 | h0     | -0.51  |
| low     |      -30 |   80 | h0     | -0.503 |
| low     |       10 |   25 | h0     | -0.503 |
| low     |        0 |   25 | h0     | -0.502 |
| low     |      -20 |   40 | h0     | -0.502 |
| low     |       30 |   40 | h0     | -0.502 |

## most positive blanket points, sunset pooled
| layer   |   offset |   km | hour   |    rho |
|:--------|---------:|-----:|:-------|-------:|
| high    |      -30 |  160 | h1     | -0.19  |
| high    |      -10 |  220 | h2     | -0.188 |
| high    |      -30 |  300 | h0     | -0.184 |
| high    |      -20 |  300 | h2     | -0.181 |
| high    |      -30 |  300 | h1     | -0.151 |
| high    |      -30 |  300 | h2     | -0.144 |

## strongest blanket points, sunrise
| layer   |   offset |   km | hour   |    rho |
|:--------|---------:|-----:|:-------|-------:|
| low     |      -30 |  120 | h0     | -0.696 |
| low     |       10 |   13 | h1     | -0.683 |
| low     |       20 |   13 | h1     | -0.668 |
| low     |      -20 |   25 | h1     | -0.639 |
| low     |      -10 |   13 | h1     | -0.637 |
| low     |       30 |   13 | h1     | -0.636 |
| low     |        0 |   13 | h1     | -0.632 |
| low     |      -20 |  160 | h0     | -0.63  |

## engineered blanket features, rho
|                    |   pooled |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunrise |   wcax_tower_sunset |
|:-------------------|---------:|--------------------:|---------------:|---------------------:|--------------------:|
| low_near_h0        |    -0.53 |               -0.59 |          -0.51 |                -0.55 |               -0.55 |
| low_near_h1        |    -0.51 |               -0.61 |          -0.46 |                -0.64 |               -0.56 |
| low_near_h2        |    -0.47 |               -0.51 |          -0.43 |                -0.36 |               -0.52 |
| low_mid_h0         |    -0.49 |               -0.55 |          -0.45 |                -0.56 |               -0.64 |
| low_mid_h1         |    -0.49 |               -0.6  |          -0.44 |                -0.53 |               -0.58 |
| low_mid_h2         |    -0.45 |               -0.58 |          -0.4  |                -0.45 |               -0.56 |
| low_far_h0         |    -0.45 |               -0.5  |          -0.43 |                -0.5  |               -0.58 |
| low_far_h1         |    -0.46 |               -0.54 |          -0.43 |                -0.39 |               -0.58 |
| low_far_h2         |    -0.44 |               -0.53 |          -0.41 |                -0.43 |               -0.53 |
| mid_over_h0        |    -0.38 |               -0.35 |          -0.4  |                -0.2  |               -0.34 |
| mid_over_h1        |    -0.41 |               -0.39 |          -0.42 |                -0.26 |               -0.38 |
| mid_over_h2        |    -0.38 |               -0.38 |          -0.38 |                -0.11 |               -0.4  |
| high_over_h0       |    -0.25 |               -0.34 |          -0.23 |                -0.18 |               -0.07 |
| high_over_h1       |    -0.23 |               -0.34 |          -0.2  |                -0.12 |               -0.15 |
| high_over_h2       |    -0.25 |               -0.38 |          -0.19 |                -0.04 |               -0.29 |
| mid_path_h0        |    -0.45 |               -0.48 |          -0.44 |                -0.27 |               -0.44 |
| mid_path_h1        |    -0.43 |               -0.45 |          -0.43 |                -0.11 |               -0.41 |
| mid_path_h2        |    -0.43 |               -0.4  |          -0.44 |                -0.15 |               -0.42 |
| high_path_h0       |    -0.26 |               -0.36 |          -0.24 |                -0.13 |               -0.07 |
| high_path_h1       |    -0.25 |               -0.37 |          -0.21 |                -0.13 |               -0.14 |
| high_path_h2       |    -0.28 |               -0.41 |          -0.24 |                -0.08 |               -0.2  |
| clear_corridor_h0  |     0.54 |                0.61 |           0.51 |                 0.6  |                0.66 |
| clear_corridor_h1  |     0.53 |                0.63 |           0.49 |                 0.61 |                0.62 |
| clear_corridor_h2  |     0.48 |                0.63 |           0.43 |                 0.49 |                0.58 |
| clear_lowmid_h0    |     0.56 |                0.64 |           0.53 |                 0.49 |                0.71 |
| clear_lowmid_h1    |     0.56 |                0.63 |           0.52 |                 0.51 |                0.69 |
| clear_lowmid_h2    |     0.52 |                0.61 |           0.48 |                 0.41 |                0.64 |
| blanket_low_all_h0 |    -0.57 |               -0.66 |          -0.53 |                -0.68 |               -0.69 |
| blanket_low_all_h1 |    -0.54 |               -0.67 |          -0.5  |                -0.66 |               -0.59 |
| blanket_low_all_h2 |    -0.51 |               -0.65 |          -0.45 |                -0.55 |               -0.6  |
| blanket_any_h0     |    -0.58 |               -0.64 |          -0.56 |                -0.49 |               -0.59 |
| blanket_any_h1     |    -0.56 |               -0.65 |          -0.53 |                -0.46 |               -0.56 |
| blanket_any_h2     |    -0.53 |               -0.62 |          -0.49 |                -0.39 |               -0.57 |
| canvas_gap_h0      |     0.16 |                0.16 |           0.12 |                 0.34 |                0.53 |
| canvas_gap_h1      |     0.21 |                0.21 |           0.19 |                 0.3  |                0.36 |
| canvas_gap_h2      |     0.19 |                0.29 |           0.14 |                 0.33 |                0.27 |

## effect sizes
| feature                 | camera            | bin    |   days |   median best |   share top-25% days |
|:------------------------|:------------------|:-------|-------:|--------------:|---------------------:|
| low_mid_h0              | pooled(pct)       | <10%   |    246 |          0.68 |                 0.4  |
| low_mid_h0              | pooled(pct)       | 10-40% |    103 |          0.44 |                 0.18 |
| low_mid_h0              | pooled(pct)       | 40-70% |     46 |          0.32 |                 0.07 |
| low_mid_h0              | pooled(pct)       | >=70%  |    123 |          0.23 |                 0.11 |
| low_mid_h0              | bolton_summit_cam | <10%   |     76 |         27.42 |                 0.37 |
| low_mid_h0              | bolton_summit_cam | 10-40% |     25 |          5.23 |                 0.2  |
| low_mid_h0              | bolton_summit_cam | 40-70% |     15 |          0.71 |                 0.07 |
| low_mid_h0              | bolton_summit_cam | >=70%  |     16 |          0.42 |                 0    |
| low_mid_h0              | btv_echo_cam      | <10%   |    149 |         30.56 |                 0.39 |
| low_mid_h0              | btv_echo_cam      | 10-40% |     65 |         20.34 |                 0.2  |
| low_mid_h0              | btv_echo_cam      | 40-70% |     28 |         10.28 |                 0.07 |
| low_mid_h0              | btv_echo_cam      | >=70%  |     97 |          6.16 |                 0.13 |
| low_mid_h0              | wcax_tower_sunset | <10%   |     21 |         84.73 |                 0.57 |
| low_mid_h0              | wcax_tower_sunset | 10-40% |     13 |         44.08 |                 0.08 |
| low_mid_h0              | wcax_tower_sunset | 40-70% |      3 |         27.99 |                 0    |
| low_mid_h0              | wcax_tower_sunset | >=70%  |     10 |         21.66 |                 0    |
| low_far_h0              | pooled(pct)       | <10%   |    235 |          0.67 |                 0.37 |
| low_far_h0              | pooled(pct)       | 10-40% |    106 |          0.51 |                 0.25 |
| low_far_h0              | pooled(pct)       | 40-70% |     68 |          0.4  |                 0.13 |
| low_far_h0              | pooled(pct)       | >=70%  |    109 |          0.23 |                 0.08 |
| low_far_h0              | bolton_summit_cam | <10%   |     74 |         26.6  |                 0.38 |
| low_far_h0              | bolton_summit_cam | 10-40% |     28 |          5.54 |                 0.14 |
| low_far_h0              | bolton_summit_cam | 40-70% |     16 |          1.48 |                 0.06 |
| low_far_h0              | bolton_summit_cam | >=70%  |     14 |          0.66 |                 0.07 |
| low_far_h0              | btv_echo_cam      | <10%   |    134 |         29.33 |                 0.36 |
| low_far_h0              | btv_echo_cam      | 10-40% |     70 |         21.84 |                 0.31 |
| low_far_h0              | btv_echo_cam      | 40-70% |     45 |         15.61 |                 0.18 |
| low_far_h0              | btv_echo_cam      | >=70%  |     90 |          6.43 |                 0.09 |
| low_far_h0              | wcax_tower_sunset | <10%   |     27 |         68.92 |                 0.44 |
| low_far_h0              | wcax_tower_sunset | 10-40% |      8 |         46.88 |                 0.12 |
| low_far_h0              | wcax_tower_sunset | 40-70% |      7 |         30.13 |                 0    |
| low_far_h0              | wcax_tower_sunset | >=70%  |      5 |         15.46 |                 0    |
| low_near_h0             | pooled(pct)       | <10%   |    283 |          0.67 |                 0.38 |
| low_near_h0             | pooled(pct)       | 10-40% |     82 |          0.47 |                 0.16 |
| low_near_h0             | pooled(pct)       | 40-70% |     46 |          0.28 |                 0.11 |
| low_near_h0             | pooled(pct)       | >=70%  |    107 |          0.17 |                 0.07 |
| low_near_h0             | bolton_summit_cam | <10%   |     79 |         25.84 |                 0.37 |
| low_near_h0             | bolton_summit_cam | 10-40% |     17 |          4.91 |                 0.12 |
| low_near_h0             | bolton_summit_cam | 40-70% |     11 |          6.26 |                 0.18 |
| low_near_h0             | bolton_summit_cam | >=70%  |     25 |          0.19 |                 0.04 |
| low_near_h0             | btv_echo_cam      | <10%   |    176 |         29.33 |                 0.38 |
| low_near_h0             | btv_echo_cam      | 10-40% |     56 |         19.74 |                 0.18 |
| low_near_h0             | btv_echo_cam      | 40-70% |     32 |          6.73 |                 0.09 |
| low_near_h0             | btv_echo_cam      | >=70%  |     75 |          3.81 |                 0.08 |
| low_near_h0             | wcax_tower_sunset | <10%   |     28 |         69.88 |                 0.43 |
| low_near_h0             | wcax_tower_sunset | 10-40% |      9 |         45.63 |                 0.11 |
| low_near_h0             | wcax_tower_sunset | 40-70% |      3 |         27.99 |                 0    |
| low_near_h0             | wcax_tower_sunset | >=70%  |      7 |         19.85 |                 0    |
| high_over_h0            | pooled(pct)       | <10%   |    400 |          0.56 |                 0.28 |
| high_over_h0            | pooled(pct)       | 10-40% |     25 |          0.39 |                 0.04 |
| high_over_h0            | pooled(pct)       | 40-70% |     24 |          0.43 |                 0.25 |
| high_over_h0            | pooled(pct)       | >=70%  |     69 |          0.22 |                 0.17 |
| high_over_h0            | bolton_summit_cam | <10%   |     97 |         16.12 |                 0.31 |
| high_over_h0            | bolton_summit_cam | 10-40% |      9 |          4.97 |                 0    |
| high_over_h0            | bolton_summit_cam | 40-70% |      6 |          7.77 |                 0.17 |
| high_over_h0            | bolton_summit_cam | >=70%  |     20 |          0.9  |                 0.15 |
| high_over_h0            | btv_echo_cam      | <10%   |    268 |         21.74 |                 0.28 |
| high_over_h0            | btv_echo_cam      | 10-40% |     12 |         14.62 |                 0.08 |
| high_over_h0            | btv_echo_cam      | 40-70% |     15 |          8.48 |                 0.2  |
| high_over_h0            | btv_echo_cam      | >=70%  |     44 |          5.64 |                 0.16 |
| high_over_h0            | wcax_tower_sunset | <10%   |     35 |         52.75 |                 0.26 |
| high_over_h0            | wcax_tower_sunset | 10-40% |      4 |         27.42 |                 0    |
| high_over_h0            | wcax_tower_sunset | 40-70% |      3 |        100    |                 0.67 |
| high_over_h0            | wcax_tower_sunset | >=70%  |      5 |         45.36 |                 0.4  |
| mid_over_h0             | pooled(pct)       | <10%   |    363 |          0.6  |                 0.31 |
| mid_over_h0             | pooled(pct)       | 10-40% |     30 |          0.3  |                 0.1  |
| mid_over_h0             | pooled(pct)       | 40-70% |     29 |          0.44 |                 0.17 |
| mid_over_h0             | pooled(pct)       | >=70%  |     96 |          0.24 |                 0.12 |
| mid_over_h0             | bolton_summit_cam | <10%   |     96 |         19.5  |                 0.31 |
| mid_over_h0             | bolton_summit_cam | 10-40% |      6 |          2.54 |                 0    |
| mid_over_h0             | bolton_summit_cam | 40-70% |      8 |          3.22 |                 0.25 |
| mid_over_h0             | bolton_summit_cam | >=70%  |     22 |          1.31 |                 0.09 |
| mid_over_h0             | btv_echo_cam      | <10%   |    227 |         24.84 |                 0.31 |
| mid_over_h0             | btv_echo_cam      | 10-40% |     21 |          8.48 |                 0.14 |
| mid_over_h0             | btv_echo_cam      | 40-70% |     20 |         17.35 |                 0.15 |
| mid_over_h0             | btv_echo_cam      | >=70%  |     71 |          5.85 |                 0.14 |
| mid_over_h0             | wcax_tower_sunset | <10%   |     40 |         58.36 |                 0.32 |
| mid_over_h0             | wcax_tower_sunset | 10-40% |      3 |         15.46 |                 0    |
| mid_over_h0             | wcax_tower_sunset | 40-70% |      1 |         45.36 |                 0    |
| mid_over_h0             | wcax_tower_sunset | >=70%  |      3 |         37.9  |                 0    |
| clear_lowmid_h0         | pooled(pct)       | <25%   |    148 |          0.23 |                 0.07 |
| clear_lowmid_h0         | pooled(pct)       | 25-50% |     67 |          0.37 |                 0.18 |
| clear_lowmid_h0         | pooled(pct)       | 50-75% |     70 |          0.45 |                 0.2  |
| clear_lowmid_h0         | pooled(pct)       | >=75%  |    233 |          0.69 |                 0.42 |
| clear_lowmid_h0         | bolton_summit_cam | <25%   |     28 |          0.66 |                 0    |
| clear_lowmid_h0         | bolton_summit_cam | 25-50% |     15 |          1.61 |                 0.2  |
| clear_lowmid_h0         | bolton_summit_cam | 50-75% |     19 |          7.53 |                 0.11 |
| clear_lowmid_h0         | bolton_summit_cam | >=75%  |     70 |         29.74 |                 0.41 |
| clear_lowmid_h0         | btv_echo_cam      | <25%   |    114 |          6.2  |                 0.09 |
| clear_lowmid_h0         | btv_echo_cam      | 25-50% |     45 |         12.85 |                 0.2  |
| clear_lowmid_h0         | btv_echo_cam      | 50-75% |     41 |         21.13 |                 0.27 |
| clear_lowmid_h0         | btv_echo_cam      | >=75%  |    139 |         32.67 |                 0.4  |
| clear_lowmid_h0         | wcax_tower_sunset | <25%   |      6 |         15.98 |                 0    |
| clear_lowmid_h0         | wcax_tower_sunset | 25-50% |      7 |         27.99 |                 0    |
| clear_lowmid_h0         | wcax_tower_sunset | 50-75% |     10 |         34.8  |                 0.1  |
| clear_lowmid_h0         | wcax_tower_sunset | >=75%  |     24 |         80.54 |                 0.5  |
| relative_humidity_2m@h1 | pooled(pct)       | <60%   |    252 |          0.64 |                 0.36 |
| relative_humidity_2m@h1 | pooled(pct)       | 60-75% |    136 |          0.46 |                 0.21 |
| relative_humidity_2m@h1 | pooled(pct)       | 75-90% |     92 |          0.37 |                 0.16 |
| relative_humidity_2m@h1 | pooled(pct)       | >=90%  |     39 |          0.15 |                 0    |
| relative_humidity_2m@h1 | bolton_summit_cam | <60%   |     29 |         29.8  |                 0.45 |
| relative_humidity_2m@h1 | bolton_summit_cam | 60-75% |     40 |         27.25 |                 0.38 |
| relative_humidity_2m@h1 | bolton_summit_cam | 75-90% |     35 |          7.83 |                 0.17 |
| relative_humidity_2m@h1 | bolton_summit_cam | >=90%  |     28 |          0.21 |                 0    |
| relative_humidity_2m@h1 | btv_echo_cam      | <60%   |    197 |         25.43 |                 0.34 |
| relative_humidity_2m@h1 | btv_echo_cam      | 60-75% |     86 |         10.59 |                 0.14 |
| relative_humidity_2m@h1 | btv_echo_cam      | 75-90% |     48 |          7.02 |                 0.17 |
| relative_humidity_2m@h1 | btv_echo_cam      | >=90%  |      9 |          2.73 |                 0    |
| relative_humidity_2m@h1 | wcax_tower_sunset | <60%   |     26 |         69.88 |                 0.42 |
| relative_humidity_2m@h1 | wcax_tower_sunset | 60-75% |     10 |         31.85 |                 0.1  |
| relative_humidity_2m@h1 | wcax_tower_sunset | 75-90% |      9 |         23.48 |                 0.11 |
| relative_humidity_2m@h1 | wcax_tower_sunset | >=90%  |      2 |         11.22 |                 0    |

## clear low/mid corridor (>=50% of path points): by high cloud overhead
| high_over_h0   |   days |   median_pct |   top25 |
|:---------------|-------:|-------------:|--------:|
| (-1, 10]       |    269 |         0.66 |    0.36 |
| (10, 40]       |     13 |         0.48 |    0.08 |
| (40, 70]       |     12 |         0.63 |    0.42 |
| (70, 101]      |     16 |         0.8  |    0.56 |

## models, sunset cameras pooled, leave-one-month-out, target = best-score percentile
| features                                 | model   |   n |     R2 |   spearman |   AUC(top 25%) |
|:-----------------------------------------|:--------|----:|-------:|-----------:|---------------:|
| (a) climatology (train mean)             | -       | 521 | -0.007 |     -0.195 |          0.392 |
| (b) stored 3-point path + overhead       | ridge   | 521 |  0.346 |      0.548 |          0.699 |
| (b) stored 3-point path + overhead       | gbm     | 521 |  0.318 |      0.545 |          0.712 |
| (c) dense blanket (engineered)           | ridge   | 521 |  0.353 |      0.557 |          0.715 |
| (c) dense blanket (engineered)           | gbm     | 521 |  0.289 |      0.537 |          0.711 |
| (c') dense blanket (all grid points)     | ridge   | 521 |  0.379 |      0.598 |          0.743 |
| (c') dense blanket (all grid points)     | gbm     | 521 |  0.308 |      0.544 |          0.721 |
| (d) blanket + stored + humidity/temp/dew | ridge   | 521 |  0.357 |      0.567 |          0.723 |
| (d) blanket + stored + humidity/temp/dew | gbm     | 521 |  0.347 |      0.577 |          0.724 |

## per camera, model (d) gbm
|                   |   n |    R2 |   spearman |   AUC(top 25%) |
|:------------------|----:|------:|-----------:|---------------:|
| bolton_summit_cam | 133 | 0.432 |      0.65  |          0.784 |
| btv_echo_cam      | 340 | 0.312 |      0.547 |          0.699 |
| wcax_tower_sunset |  48 | 0.363 |      0.602 |          0.747 |

## sunrise ridge LOMO (47 days, 3 months)
{'n': 47, 'R2': 0.029, 'spearman': 0.395, 'AUC(top 25%)': 0.633}

## image features (target = best score from 5 min before sunset on, percentile)
| features                  | model   |   n |    R2 |   spearman |   AUC(top 25%) |
|:--------------------------|:--------|----:|------:|-----------:|---------------:|
| weather (d)               | ridge   | 515 | 0.341 |      0.564 |          0.735 |
| weather (d)               | gbm     | 515 | 0.318 |      0.557 |          0.726 |
| image only                | ridge   | 515 | 0.453 |      0.696 |          0.824 |
| image only                | gbm     | 515 | 0.572 |      0.757 |          0.842 |
| weather + image           | ridge   | 515 | 0.479 |      0.705 |          0.832 |
| weather + image           | gbm     | 515 | 0.596 |      0.767 |          0.841 |
| weather + image @i2h only | gbm     | 515 | 0.355 |      0.588 |          0.74  |
| weather + image @i1h only | gbm     | 515 | 0.397 |      0.621 |          0.759 |
| weather + image @i30 only | gbm     | 515 | 0.53  |      0.721 |          0.813 |

## image feature rho with late best (pooled)
|            |    rho |
|:-----------|-------:|
| warm@i15   |  0.741 |
| score@i15  |  0.713 |
| warm@i30   |  0.608 |
| score@i30  |  0.583 |
| sat@i30    |  0.531 |
| sat@i15    |  0.514 |
| score@i1h  |  0.456 |
| blue@i2h   |  0.432 |
| sat@i1h    |  0.42  |
| blue@i1h   |  0.416 |
| blue@i30   |  0.412 |
| bright@i1h | -0.377 |
| score@i2h  |  0.365 |
| sat@i2h    |  0.362 |
| bright@i30 | -0.361 |
| warm@i1h   |  0.355 |
| blue@i15   |  0.333 |
| bright@i15 | -0.273 |
| bright@i2h | -0.267 |
| edges@i15  |  0.245 |
| edges@i30  |  0.217 |
| edges@i2h  |  0.199 |
| edges@i1h  |  0.198 |
| warm@i2h   |  0.191 |
| gray@i30   | -0.177 |
| gray@i15   | -0.103 |
| gray@i2h   | -0.08  |
| gray@i1h   | -0.027 |