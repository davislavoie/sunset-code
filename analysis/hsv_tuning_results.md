# HSV tuning and cloud contrast vs My ranking (btv_echo_cam, 116 days, script `hsv_tuning.py`)

Four zoomed-in days left out. Histogram rebuild of the current score vs the pipeline's: r = 1.0000.
Each row: 5-fold cross-validation over days, 20 random splits; the variant is picked on 4 folds (the current
score is always a candidate) and judged on the 5th. Mean abs diff is after the soft cap, refitted per fold.

| change                                                                        |   cv rho |   cv mean abs diff | picked most                                |
|:------------------------------------------------------------------------------|---------:|-------------------:|:-------------------------------------------|
| current score                                                                 |    0.753 |             13.255 | nan                                        |
| crop: top 40-70 % of the frame                                                |    0.75  |             13.327 | current (99/100)                           |
| pink saturation floor                                                         |    0.746 |             13.569 | pink s>=36 (80/100)                        |
| pink value floor                                                              |    0.773 |             12.805 | pink v>=128 (84/100)                       |
| pink hue starts later                                                         |    0.75  |             13.385 | pink from 150 (70/100)                     |
| grey-pink penalty                                                             |    0.751 |             13.355 | current (80/100)                           |
| pink sub-band weights                                                         |    0.771 |             12.843 | [4.5, 9, 12, 12] (56/100)                  |
| all of the above together                                                     |    0.768 |             13.059 | top 50%, pink s>=36, v>=96 (79/100)        |
| HSV x (1 + w * colorfulness)                                                  |    0.771 |             13.945 | w=0.6 (38/100)                             |
| HSV x (1 + w * hue_spread)                                                    |    0.816 |             11.907 | w=0.5 (62/100)                             |
| HSV x (1 + w * sat_spread)                                                    |    0.748 |             13.56  | w=-0.2 (72/100)                            |
| HSV x (1 + w * v_spread_col)                                                  |    0.757 |             13.392 | w=0.2 (90/100)                             |
| HSV x (1 + w * v_range_sky)                                                   |    0.753 |             13.243 | w=-0.1 (62/100)                            |
| HSV x (1 + w * lit_vs_cloud)                                                  |    0.802 |             12.033 | w=0.4 (92/100)                             |
| HSV x (1 + w * local_contrast_col)                                            |    0.737 |             13.749 | w=0.1 (54/100)                             |
| HSV x (1 + w * edge_col)                                                      |    0.752 |             13.456 | w=-0.1 (51/100)                            |
| HSV x (1 + w * warm_cool)                                                     |    0.806 |             13.112 | w=0.6 (75/100)                             |
| any one contrast measure (measure and w picked in the folds)                  |    0.789 |             12.554 | hue_spread w=0.4 (69/100)                  |
| pink value floor + hue spread + lit contrast (all picked in the folds)        |    0.866 |             10.049 | pink v>=128, hue w=0.4, lit w=0.3 (51/100) |
| shipped: pink v>=128 x (0.36 + 2.5 hue spread) x (0.93 + 0.0086 lit contrast) |    0.87  |              9.896 | shipped (100/100)                          |
| current, all 116 days in sample                                               |    0.755 |             13.13  | soft cap k = 55.4                          |
| shipped, all 116 days in sample                                               |    0.872 |              9.789 | soft cap k = 66.9                          |

## Contrast measures on their own (best frame of the day)

| measure            |   rho with your score |   rho with the HSV score |   rho with what HSV misses |
|:-------------------|----------------------:|-------------------------:|---------------------------:|
| colorfulness       |                 0.449 |                    0.395 |                      0.013 |
| hue_spread         |                 0.253 |                    0.157 |                      0.146 |
| sat_spread         |                 0.269 |                    0.495 |                     -0.335 |
| v_spread_col       |                -0.076 |                    0.137 |                     -0.298 |
| v_range_sky        |                 0.055 |                    0.248 |                     -0.293 |
| lit_vs_cloud       |                 0.223 |                    0.006 |                      0.305 |
| local_contrast_col |                -0.065 |                    0.007 |                     -0.084 |
| edge_col           |                -0.15  |                   -0.004 |                     -0.193 |
| warm_cool          |                 0.732 |                    0.751 |                     -0.039 |
