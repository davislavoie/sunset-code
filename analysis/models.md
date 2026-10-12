# Cloud models compared, 1 h before sunset (517 sunset camera-days; photo checks on the 160 vision days)

AUC = leave-one-month-out ridge, top-25 % day. 'photo cover' is the vision model's cloud_cover on the 1h-pre photo.

| model                 |   n |   missing % |   rho photo cover vs total_over |   rho photo horizon_clear vs low_far |   rho score vs total_over |   rho score vs low_far |   AUC low/mid/high |   AUC + pressure levels |   AUC pressure levels only |
|:----------------------|----:|------------:|--------------------------------:|-------------------------------------:|--------------------------:|-----------------------:|-------------------:|------------------------:|---------------------------:|
| best_match            | 517 |           0 |                           0.761 |                               -0.501 |                    -0.421 |                 -0.494 |              0.701 |                   0.712 |                      0.706 |
| gfs_hrrr              | 517 |           0 |                           0.761 |                               -0.501 |                    -0.421 |                 -0.494 |              0.701 |                   0.712 |                      0.706 |
| ecmwf_ifs025          | 517 |           0 |                           0.695 |                               -0.504 |                    -0.463 |                 -0.45  |              0.728 |                   0.728 |                      0.704 |
| gem_hrdps_continental | 517 |           0 |                           0.692 |                               -0.548 |                    -0.443 |                 -0.482 |              0.728 |                   0.73  |                      0.725 |
| icon_seamless         | 517 |           0 |                           0.705 |                               -0.441 |                    -0.45  |                 -0.433 |              0.755 |                   0.766 |                      0.743 |

## Two models together (low/mid/high near/far/over from each)

|                                       |   AUC |
|:--------------------------------------|------:|
| gem_hrdps_continental + icon_seamless | 0.761 |
| best_match + icon_seamless            | 0.754 |
| gfs_hrrr + icon_seamless              | 0.754 |
| ecmwf_ifs025 + icon_seamless          | 0.751 |
| ecmwf_ifs025 + gem_hrdps_continental  | 0.748 |
| best_match + ecmwf_ifs025             | 0.735 |
| ecmwf_ifs025 + gfs_hrrr               | 0.735 |
| best_match + gem_hrdps_continental    | 0.73  |
| gem_hrdps_continental + gfs_hrrr      | 0.73  |
| best_match + gfs_hrrr                 | 0.702 |