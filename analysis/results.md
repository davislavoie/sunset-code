camera-days: {'bolton_summit_cam': 133, 'btv_echo_cam': 336, 'wcax_tower_sunrise': 47, 'wcax_tower_sunset': 48}
days whose best shot overall is before the 15m-pre..30m-post window: 31.7%

## stored fields, Spearman rho (top 20 by pooled sunset)
|                              |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunrise |   wcax_tower_sunset |   sunset_pooled |
|:-----------------------------|--------------------:|---------------:|---------------------:|--------------------:|----------------:|
| path40_cloud_cover_low@h0    |               -0.54 |          -0.54 |               nan    |               -0.47 |           -0.53 |
| path50_cloud_cover_low@h0    |               -0.57 |          -0.49 |               nan    |               -0.33 |           -0.49 |
| cloud_cover_low@h0           |               -0.59 |          -0.46 |               nan    |               -0.4  |           -0.49 |
| cloud_cover_total@h0         |               -0.55 |          -0.47 |               nan    |               -0.37 |           -0.48 |
| path13_cloud_cover_low@h1    |               -0.54 |          -0.45 |                -0.58 |               -0.41 |           -0.47 |
| path13_cloud_cover_low@h0    |               -0.49 |          -0.47 |               nan    |               -0.48 |           -0.47 |
| path40_cloud_cover_low@h1    |               -0.56 |          -0.44 |                -0.24 |               -0.47 |           -0.47 |
| path50_cloud_cover_low@h1    |               -0.5  |          -0.46 |                -0.34 |               -0.48 |           -0.47 |
| path80_cloud_cover_low@h1    |               -0.57 |          -0.42 |                -0.39 |               -0.55 |           -0.46 |
| path80_cloud_cover_mid@h1    |               -0.39 |          -0.47 |                 0.04 |               -0.57 |           -0.46 |
| precipitation_probability@h0 |               -0.5  |          -0.44 |               nan    |               -0.51 |           -0.46 |
| precipitation_probability@h1 |               -0.49 |          -0.44 |                -0.28 |               -0.5  |           -0.45 |
| path150_cloud_cover_mid@h0   |               -0.38 |          -0.46 |               nan    |               -0.55 |           -0.45 |
| path80_cloud_cover_low@h0    |               -0.49 |          -0.44 |               nan    |               -0.49 |           -0.45 |
| path80_cloud_cover_mid@h2    |               -0.35 |          -0.47 |                -0.12 |               -0.59 |           -0.44 |
| path80_cloud_cover_mid@h0    |               -0.45 |          -0.44 |               nan    |               -0.51 |           -0.44 |
| path80_cloud_cover_low@h2    |               -0.58 |          -0.39 |                -0.4  |               -0.44 |           -0.44 |
| precipitation_probability@h2 |               -0.51 |          -0.4  |                -0.4  |               -0.51 |           -0.44 |
| path50_cloud_cover_low@h2    |               -0.52 |          -0.41 |                -0.33 |               -0.35 |           -0.43 |
| cloud_cover_total@h2         |               -0.49 |          -0.4  |                -0.33 |               -0.48 |           -0.43 |

## strongest blanket points, sunset pooled
| layer   |   offset |   km | hour   |    rho |
|:--------|---------:|-----:|:-------|-------:|
| low     |      -10 |   40 | h0     | -0.536 |
| low     |       20 |   25 | h0     | -0.533 |
| low     |        0 |   40 | h0     | -0.528 |
| low     |      -30 |   25 | h0     | -0.528 |
| low     |       20 |   40 | h0     | -0.524 |
| low     |       10 |   40 | h0     | -0.524 |
| low     |      -10 |   25 | h0     | -0.518 |
| low     |       10 |   25 | h0     | -0.514 |
| low     |      -30 |   80 | h0     | -0.512 |
| low     |      -30 |  120 | h0     | -0.512 |
| low     |      -20 |   80 | h0     | -0.505 |
| low     |        0 |   25 | h0     | -0.505 |

## most positive blanket points, sunset pooled
| layer   |   offset |   km | hour   |    rho |
|:--------|---------:|-----:|:-------|-------:|
| high    |      -30 |  300 | h0     | -0.179 |
| high    |      -30 |  160 | h1     | -0.175 |
| high    |      -10 |  220 | h2     | -0.173 |
| high    |      -20 |  300 | h2     | -0.156 |
| high    |      -30 |  300 | h1     | -0.14  |
| high    |      -30 |  300 | h2     | -0.122 |

## strongest blanket points, sunrise
| layer   |   offset |   km | hour   |    rho |
|:--------|---------:|-----:|:-------|-------:|
| low     |      -30 |  120 | h0     | -0.688 |
| low     |       10 |   13 | h1     | -0.675 |
| low     |       20 |   13 | h1     | -0.662 |
| low     |      -20 |   25 | h1     | -0.627 |
| low     |      -10 |   13 | h1     | -0.627 |
| low     |      -20 |  160 | h0     | -0.626 |
| low     |       30 |   13 | h1     | -0.625 |
| low     |        0 |   13 | h1     | -0.622 |

## engineered blanket features, rho
|                    |   pooled |   bolton_summit_cam |   btv_echo_cam |   wcax_tower_sunrise |   wcax_tower_sunset |
|:-------------------|---------:|--------------------:|---------------:|---------------------:|--------------------:|
| low_near_h0        |    -0.54 |               -0.58 |          -0.53 |                -0.54 |               -0.55 |
| low_near_h1        |    -0.51 |               -0.58 |          -0.48 |                -0.62 |               -0.55 |
| low_near_h2        |    -0.48 |               -0.48 |          -0.46 |                -0.34 |               -0.49 |
| low_mid_h0         |    -0.51 |               -0.54 |          -0.48 |                -0.54 |               -0.65 |
| low_mid_h1         |    -0.5  |               -0.58 |          -0.46 |                -0.51 |               -0.58 |
| low_mid_h2         |    -0.47 |               -0.58 |          -0.42 |                -0.44 |               -0.54 |
| low_far_h0         |    -0.46 |               -0.49 |          -0.45 |                -0.48 |               -0.59 |
| low_far_h1         |    -0.48 |               -0.53 |          -0.45 |                -0.37 |               -0.6  |
| low_far_h2         |    -0.46 |               -0.53 |          -0.44 |                -0.42 |               -0.53 |
| mid_over_h0        |    -0.37 |               -0.34 |          -0.39 |                -0.19 |               -0.36 |
| mid_over_h1        |    -0.4  |               -0.36 |          -0.41 |                -0.23 |               -0.39 |
| mid_over_h2        |    -0.38 |               -0.34 |          -0.38 |                -0.09 |               -0.43 |
| high_over_h0       |    -0.22 |               -0.31 |          -0.2  |                -0.16 |               -0.04 |
| high_over_h1       |    -0.21 |               -0.31 |          -0.19 |                -0.11 |               -0.12 |
| high_over_h2       |    -0.23 |               -0.36 |          -0.18 |                -0.02 |               -0.28 |
| mid_path_h0        |    -0.42 |               -0.43 |          -0.42 |                -0.26 |               -0.45 |
| mid_path_h1        |    -0.42 |               -0.42 |          -0.42 |                -0.09 |               -0.42 |
| mid_path_h2        |    -0.42 |               -0.39 |          -0.43 |                -0.12 |               -0.44 |
| high_path_h0       |    -0.23 |               -0.32 |          -0.22 |                -0.12 |               -0.04 |
| high_path_h1       |    -0.22 |               -0.33 |          -0.19 |                -0.11 |               -0.11 |
| high_path_h2       |    -0.25 |               -0.39 |          -0.21 |                -0.07 |               -0.18 |
| clear_corridor_h0  |     0.56 |                0.6  |           0.53 |                 0.58 |                0.67 |
| clear_corridor_h1  |     0.54 |                0.61 |           0.51 |                 0.59 |                0.63 |
| clear_corridor_h2  |     0.49 |                0.61 |           0.45 |                 0.47 |                0.55 |
| clear_lowmid_h0    |     0.57 |                0.62 |           0.55 |                 0.48 |                0.71 |
| clear_lowmid_h1    |     0.56 |                0.61 |           0.54 |                 0.49 |                0.7  |
| clear_lowmid_h2    |     0.53 |                0.59 |           0.51 |                 0.39 |                0.66 |
| blanket_low_all_h0 |    -0.58 |               -0.65 |          -0.55 |                -0.66 |               -0.69 |
| blanket_low_all_h1 |    -0.55 |               -0.66 |          -0.52 |                -0.65 |               -0.58 |
| blanket_low_all_h2 |    -0.52 |               -0.63 |          -0.48 |                -0.53 |               -0.57 |
| blanket_any_h0     |    -0.57 |               -0.61 |          -0.56 |                -0.47 |               -0.57 |
| blanket_any_h1     |    -0.55 |               -0.62 |          -0.54 |                -0.44 |               -0.57 |
| blanket_any_h2     |    -0.53 |               -0.6  |          -0.51 |                -0.37 |               -0.58 |
| canvas_gap_h0      |     0.2  |                0.2  |           0.16 |                 0.34 |                0.53 |
| canvas_gap_h1      |     0.23 |                0.22 |           0.22 |                 0.3  |                0.33 |
| canvas_gap_h2      |     0.21 |                0.33 |           0.18 |                 0.33 |                0.23 |

## effect sizes
| feature                 | camera            | bin    |   days |   median best |   share top-25% days |
|:------------------------|:------------------|:-------|-------:|--------------:|---------------------:|
| low_mid_h0              | pooled(pct)       | <10%   |    244 |          0.68 |                 0.41 |
| low_mid_h0              | pooled(pct)       | 10-40% |    102 |          0.46 |                 0.19 |
| low_mid_h0              | pooled(pct)       | 40-70% |     45 |          0.32 |                 0.07 |
| low_mid_h0              | pooled(pct)       | >=70%  |    123 |          0.24 |                 0.09 |
| low_mid_h0              | bolton_summit_cam | <10%   |     76 |         13.57 |                 0.37 |
| low_mid_h0              | bolton_summit_cam | 10-40% |     25 |          4.57 |                 0.2  |
| low_mid_h0              | bolton_summit_cam | 40-70% |     15 |          0.17 |                 0.07 |
| low_mid_h0              | bolton_summit_cam | >=70%  |     16 |          0.16 |                 0    |
| low_mid_h0              | btv_echo_cam      | <10%   |    147 |         30.47 |                 0.4  |
| low_mid_h0              | btv_echo_cam      | 10-40% |     64 |         19.7  |                 0.2  |
| low_mid_h0              | btv_echo_cam      | 40-70% |     27 |          7.35 |                 0.07 |
| low_mid_h0              | btv_echo_cam      | >=70%  |     97 |          4.37 |                 0.11 |
| low_mid_h0              | wcax_tower_sunset | <10%   |     21 |         84.73 |                 0.57 |
| low_mid_h0              | wcax_tower_sunset | 10-40% |     13 |         44.08 |                 0.08 |
| low_mid_h0              | wcax_tower_sunset | 40-70% |      3 |          6.71 |                 0    |
| low_mid_h0              | wcax_tower_sunset | >=70%  |     10 |         17.69 |                 0    |
| low_far_h0              | pooled(pct)       | <10%   |    233 |          0.67 |                 0.38 |
| low_far_h0              | pooled(pct)       | 10-40% |    105 |          0.52 |                 0.26 |
| low_far_h0              | pooled(pct)       | 40-70% |     67 |          0.42 |                 0.13 |
| low_far_h0              | pooled(pct)       | >=70%  |    109 |          0.27 |                 0.06 |
| low_far_h0              | bolton_summit_cam | <10%   |     74 |         13.57 |                 0.38 |
| low_far_h0              | bolton_summit_cam | 10-40% |     28 |          4.82 |                 0.14 |
| low_far_h0              | bolton_summit_cam | 40-70% |     16 |          1.24 |                 0.06 |
| low_far_h0              | bolton_summit_cam | >=70%  |     14 |          0.15 |                 0.07 |
| low_far_h0              | btv_echo_cam      | <10%   |    132 |         29.33 |                 0.37 |
| low_far_h0              | btv_echo_cam      | 10-40% |     69 |         21.13 |                 0.32 |
| low_far_h0              | btv_echo_cam      | 40-70% |     44 |         14.94 |                 0.18 |
| low_far_h0              | btv_echo_cam      | >=70%  |     90 |          4.42 |                 0.07 |
| low_far_h0              | wcax_tower_sunset | <10%   |     27 |         68.92 |                 0.44 |
| low_far_h0              | wcax_tower_sunset | 10-40% |      8 |         46.88 |                 0.12 |
| low_far_h0              | wcax_tower_sunset | 40-70% |      7 |         12.01 |                 0    |
| low_far_h0              | wcax_tower_sunset | >=70%  |      5 |         12.11 |                 0    |
| low_near_h0             | pooled(pct)       | <10%   |    280 |          0.67 |                 0.38 |
| low_near_h0             | pooled(pct)       | 10-40% |     81 |          0.43 |                 0.17 |
| low_near_h0             | pooled(pct)       | 40-70% |     46 |          0.26 |                 0.11 |
| low_near_h0             | pooled(pct)       | >=70%  |    107 |          0.19 |                 0.06 |
| low_near_h0             | bolton_summit_cam | <10%   |     79 |         14.27 |                 0.37 |
| low_near_h0             | bolton_summit_cam | 10-40% |     17 |          4.57 |                 0.12 |
| low_near_h0             | bolton_summit_cam | 40-70% |     11 |          5.96 |                 0.18 |
| low_near_h0             | bolton_summit_cam | >=70%  |     25 |          0.14 |                 0.04 |
| low_near_h0             | btv_echo_cam      | <10%   |    173 |         29.2  |                 0.38 |
| low_near_h0             | btv_echo_cam      | 10-40% |     55 |         15.61 |                 0.2  |
| low_near_h0             | btv_echo_cam      | 40-70% |     32 |          3.45 |                 0.09 |
| low_near_h0             | btv_echo_cam      | >=70%  |     75 |          1.94 |                 0.07 |
| low_near_h0             | wcax_tower_sunset | <10%   |     28 |         69.88 |                 0.43 |
| low_near_h0             | wcax_tower_sunset | 10-40% |      9 |         37.9  |                 0.11 |
| low_near_h0             | wcax_tower_sunset | 40-70% |      3 |          6.71 |                 0    |
| low_near_h0             | wcax_tower_sunset | >=70%  |      7 |         19.85 |                 0    |
| high_over_h0            | pooled(pct)       | <10%   |    398 |          0.55 |                 0.28 |
| high_over_h0            | pooled(pct)       | 10-40% |     25 |          0.4  |                 0.04 |
| high_over_h0            | pooled(pct)       | 40-70% |     22 |          0.56 |                 0.27 |
| high_over_h0            | pooled(pct)       | >=70%  |     69 |          0.25 |                 0.17 |
| high_over_h0            | bolton_summit_cam | <10%   |     97 |          7.91 |                 0.31 |
| high_over_h0            | bolton_summit_cam | 10-40% |      9 |          3.35 |                 0    |
| high_over_h0            | bolton_summit_cam | 40-70% |      6 |          7.62 |                 0.17 |
| high_over_h0            | bolton_summit_cam | >=70%  |     20 |          0.46 |                 0.15 |
| high_over_h0            | btv_echo_cam      | <10%   |    266 |         20.44 |                 0.28 |
| high_over_h0            | btv_echo_cam      | 10-40% |     12 |         13.84 |                 0.08 |
| high_over_h0            | btv_echo_cam      | 40-70% |     13 |          4.37 |                 0.23 |
| high_over_h0            | btv_echo_cam      | >=70%  |     44 |          3.28 |                 0.16 |
| high_over_h0            | wcax_tower_sunset | <10%   |     35 |         52.75 |                 0.26 |
| high_over_h0            | wcax_tower_sunset | 10-40% |      4 |         27.42 |                 0    |
| high_over_h0            | wcax_tower_sunset | 40-70% |      3 |        100    |                 0.67 |
| high_over_h0            | wcax_tower_sunset | >=70%  |      5 |         45.36 |                 0.4  |
| mid_over_h0             | pooled(pct)       | <10%   |    360 |          0.59 |                 0.31 |
| mid_over_h0             | pooled(pct)       | 10-40% |     30 |          0.3  |                 0.13 |
| mid_over_h0             | pooled(pct)       | 40-70% |     28 |          0.46 |                 0.18 |
| mid_over_h0             | pooled(pct)       | >=70%  |     96 |          0.26 |                 0.12 |
| mid_over_h0             | bolton_summit_cam | <10%   |     96 |          8.37 |                 0.31 |
| mid_over_h0             | bolton_summit_cam | 10-40% |      6 |          1.84 |                 0    |
| mid_over_h0             | bolton_summit_cam | 40-70% |      8 |          3.22 |                 0.25 |
| mid_over_h0             | bolton_summit_cam | >=70%  |     22 |          0.49 |                 0.09 |
| mid_over_h0             | btv_echo_cam      | <10%   |    224 |         23.66 |                 0.3  |
| mid_over_h0             | btv_echo_cam      | 10-40% |     21 |          8.07 |                 0.19 |
| mid_over_h0             | btv_echo_cam      | 40-70% |     19 |         16.35 |                 0.16 |
| mid_over_h0             | btv_echo_cam      | >=70%  |     71 |          3.51 |                 0.14 |
| mid_over_h0             | wcax_tower_sunset | <10%   |     40 |         58.36 |                 0.32 |
| mid_over_h0             | wcax_tower_sunset | 10-40% |      3 |          6.71 |                 0    |
| mid_over_h0             | wcax_tower_sunset | 40-70% |      1 |         45.36 |                 0    |
| mid_over_h0             | wcax_tower_sunset | >=70%  |      3 |         37.9  |                 0    |
| clear_lowmid_h0         | pooled(pct)       | <25%   |    147 |          0.23 |                 0.06 |
| clear_lowmid_h0         | pooled(pct)       | 25-50% |     66 |          0.4  |                 0.17 |
| clear_lowmid_h0         | pooled(pct)       | 50-75% |     70 |          0.47 |                 0.21 |
| clear_lowmid_h0         | pooled(pct)       | >=75%  |    231 |          0.7  |                 0.42 |
| clear_lowmid_h0         | bolton_summit_cam | <25%   |     28 |          0.16 |                 0    |
| clear_lowmid_h0         | bolton_summit_cam | 25-50% |     15 |          1.61 |                 0.2  |
| clear_lowmid_h0         | bolton_summit_cam | 50-75% |     19 |          5.72 |                 0.11 |
| clear_lowmid_h0         | bolton_summit_cam | >=75%  |     70 |         16.66 |                 0.41 |
| clear_lowmid_h0         | btv_echo_cam      | <25%   |    113 |          3.33 |                 0.08 |
| clear_lowmid_h0         | btv_echo_cam      | 25-50% |     44 |         12.92 |                 0.18 |
| clear_lowmid_h0         | btv_echo_cam      | 50-75% |     41 |         16.09 |                 0.29 |
| clear_lowmid_h0         | btv_echo_cam      | >=75%  |    137 |         32.67 |                 0.41 |
| clear_lowmid_h0         | wcax_tower_sunset | <25%   |      6 |         15.98 |                 0    |
| clear_lowmid_h0         | wcax_tower_sunset | 25-50% |      7 |         21.97 |                 0    |
| clear_lowmid_h0         | wcax_tower_sunset | 50-75% |     10 |         33.98 |                 0.1  |
| clear_lowmid_h0         | wcax_tower_sunset | >=75%  |     24 |         80.54 |                 0.5  |
| relative_humidity_2m@h1 | pooled(pct)       | <60%   |    249 |          0.65 |                 0.35 |
| relative_humidity_2m@h1 | pooled(pct)       | 60-75% |    135 |          0.43 |                 0.21 |
| relative_humidity_2m@h1 | pooled(pct)       | 75-90% |     92 |          0.36 |                 0.17 |
| relative_humidity_2m@h1 | pooled(pct)       | >=90%  |     39 |          0.17 |                 0    |
| relative_humidity_2m@h1 | bolton_summit_cam | <60%   |     29 |         22.04 |                 0.41 |
| relative_humidity_2m@h1 | bolton_summit_cam | 60-75% |     40 |          8.42 |                 0.4  |
| relative_humidity_2m@h1 | bolton_summit_cam | 75-90% |     35 |          6.26 |                 0.17 |
| relative_humidity_2m@h1 | bolton_summit_cam | >=90%  |     28 |          0.15 |                 0    |
| relative_humidity_2m@h1 | btv_echo_cam      | <60%   |    194 |         24.93 |                 0.33 |
| relative_humidity_2m@h1 | btv_echo_cam      | 60-75% |     85 |          7.6  |                 0.14 |
| relative_humidity_2m@h1 | btv_echo_cam      | 75-90% |     48 |          6.04 |                 0.19 |
| relative_humidity_2m@h1 | btv_echo_cam      | >=90%  |      9 |          2.53 |                 0    |
| relative_humidity_2m@h1 | wcax_tower_sunset | <60%   |     26 |         69.88 |                 0.42 |
| relative_humidity_2m@h1 | wcax_tower_sunset | 60-75% |     10 |         27.01 |                 0.1  |
| relative_humidity_2m@h1 | wcax_tower_sunset | 75-90% |      9 |         23.48 |                 0.11 |
| relative_humidity_2m@h1 | wcax_tower_sunset | >=90%  |      2 |          7.32 |                 0    |

## clear low/mid corridor (>=50% of path points): by high cloud overhead
| high_over_h0   |   days |   median_pct |   top25 |
|:---------------|-------:|-------------:|--------:|
| (-1, 10]       |    268 |         0.66 |    0.36 |
| (10, 40]       |     13 |         0.49 |    0.08 |
| (40, 70]       |     11 |         0.65 |    0.45 |
| (70, 101]      |     16 |         0.81 |    0.56 |

## models, sunset cameras pooled, leave-one-month-out, target = best-score percentile
| features                                 | model   |   n |     R2 |   spearman |   AUC(top 25%) |
|:-----------------------------------------|:--------|----:|-------:|-----------:|---------------:|
| (a) climatology (train mean)             | -       | 517 | -0.008 |     -0.207 |          0.392 |
| (b) stored 3-point path + overhead       | ridge   | 517 |  0.336 |      0.543 |          0.709 |
| (b) stored 3-point path + overhead       | gbm     | 517 |  0.299 |      0.529 |          0.713 |
| (c) dense blanket (engineered)           | ridge   | 517 |  0.348 |      0.558 |          0.727 |
| (c) dense blanket (engineered)           | gbm     | 517 |  0.288 |      0.539 |          0.715 |
| (c') dense blanket (all grid points)     | ridge   | 517 |  0.375 |      0.597 |          0.754 |
| (c') dense blanket (all grid points)     | gbm     | 517 |  0.31  |      0.555 |          0.742 |
| (d) blanket + stored + humidity/temp/dew | ridge   | 517 |  0.352 |      0.568 |          0.735 |
| (d) blanket + stored + humidity/temp/dew | gbm     | 517 |  0.322 |      0.56  |          0.723 |

## per camera, model (d) gbm
|                   |   n |    R2 |   spearman |   AUC(top 25%) |
|:------------------|----:|------:|-----------:|---------------:|
| bolton_summit_cam | 133 | 0.363 |      0.59  |          0.761 |
| btv_echo_cam      | 336 | 0.301 |      0.545 |          0.705 |
| wcax_tower_sunset |  48 | 0.353 |      0.592 |          0.749 |

## sunrise ridge LOMO (47 days, 3 months)
{'n': 47, 'R2': -0.001, 'spearman': 0.378, 'AUC(top 25%)': 0.643}

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