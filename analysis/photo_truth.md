# Cloud sources vs the photo (147 camera-days, 1 h before sunset)

Truth: vision-model cloud cover read off the photo, mean of two prompts (they agree at rho 0.87). 51% of these photos read >= 60 % cloudy, 6% <= 20 %.

## Agreement with the photo

| source      |   rho vs photo |   rho vs prompt A |   rho vs prompt B |   AUC cloudy (>=60) vs not |   AUC clear (<=20) vs cloudy (>=60) |
|:------------|---------------:|------------------:|------------------:|---------------------------:|------------------------------------:|
| goes_over   |           0.77 |              0.74 |              0.76 |                       0.86 |                                0.89 |
| goes_near   |           0.78 |              0.75 |              0.75 |                       0.9  |                                0.89 |
| goes_far    |           0.68 |              0.68 |              0.65 |                       0.87 |                                0.9  |
| goes_fan    |           0.7  |              0.69 |              0.66 |                       0.87 |                                0.9  |
| icon_low    |           0.67 |              0.67 |              0.65 |                       0.83 |                                0.9  |
| icon_mid    |           0.62 |              0.6  |              0.61 |                       0.8  |                                0.89 |
| icon_high   |           0.28 |              0.26 |              0.28 |                       0.63 |                                0.69 |
| icon_total  |           0.72 |              0.7  |              0.68 |                       0.86 |                                0.94 |
| BTV_cover   |           0.77 |              0.75 |              0.75 |                       0.88 |                                0.94 |
| metar_path  |           0.63 |              0.65 |              0.54 |                       0.86 |                                0.9  |
| metar_west  |           0.7  |              0.71 |              0.63 |                       0.88 |                                0.93 |
| BTV_ceiling |           0.75 |              0.73 |              0.73 |                       0.86 |                                0.94 |

## By the cloud base the model saw (prompt B)

| cloud_base       |   n |   photo |   goes_fan |   icon_low |   icon_mid |   icon_high |   metar_west |   BTV_ceiling |
|:-----------------|----:|--------:|-----------:|-----------:|-----------:|------------:|-------------:|--------------:|
| low              |  66 |   50.04 |       0.56 |       0.27 |       0.38 |        0.23 |         0.34 |      19795.5  |
| mid              |  39 |   49.74 |       0.43 |       0.21 |       0.23 |        0.31 |         0.21 |      23705.1  |
| none             |   1 |    0    |       0.85 |       0    |       0.73 |        0.94 |         0.5  |      20000    |
| touching_horizon |  41 |   84.88 |       0.89 |       0.64 |       0.73 |        0.43 |         0.75 |       7904.88 |