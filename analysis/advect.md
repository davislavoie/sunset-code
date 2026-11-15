# Cloud mask moved forward to sunset with the wind (3407 pre shots read)

The cloud that will sit in a zone at sunset is now upwind of it by wind x (time to sunset). For every pre shot
of the sunset cameras, the GOES-East clear-sky mask (ABI-L2-ACMC) from the latest scan landed by the capture
time (ai_analysis/goes.py, as live) is read, and the zones (ai_analysis.goes.zone_masks: near 5-40 km, far
80-300 km, fan 5-300 km, sun bearing +/-30 deg) are evaluated around the camera moved upwind by
speed x dt, the sun azimuth kept. The wind is Open-Meteo's historical forecast at the hour nearest the capture
(the same source as aloft.py; direction = where it blows from, km/h). Two steering choices, fixed in advance:

  adv700_<zone>   700 hPa wind
  advtop_<zone>   by the stored far-zone cloud-top height (goes_top_far): under 2 km 850 hPa, 2-6 km 700 hPa,
                  6 km and up 500 hPa, 700 hPa when it's missing
  rev*_<zone>     the same with the wind reversed (sanity check only)
  *_<zone>_in     share of the displaced zone that fell inside the downloaded window (under 60% -> missing)

As goes.py: wcax_tower_sunset (3 km from btv_echo_cam) is read around btv_echo_cam's position with its own sun
azimuth, so the two cameras share a window. Each window is kept as a compressed .npz (mask as int8 + the
fixed-grid x/y and projection) so the features can be recomputed without downloading.

## Verdict

- Projection check: the displaced mask beats both persistence and the reversed wind (higher Spearman and lower MAE against the sunset value) in 12 of 12 horizon/steering/zone rows (8 of 8 for far and fan). Mean Spearman over the far/fan rows: persistence 0.937, displaced 0.950, reversed 0.872; mean MAE 0.087 / 0.073 / 0.122.
- live+adv700 far: mean AUC gain +0.001 vs mean shuffled 95% +0.002; beats the shuffle on 1 of 6 horizon fits.
- live+adv700 fan: mean AUC gain +0.001 vs mean shuffled 95% +0.002; beats the shuffle on 2 of 6 horizon fits.
- live+advtop far: mean AUC gain +0.002 vs mean shuffled 95% +0.002; beats the shuffle on 3 of 6 horizon fits.
- live+advtop fan: mean AUC gain +0.002 vs mean shuffled 95% +0.002; beats the shuffle on 2 of 6 horizon fits.
- live+adv700 change: mean AUC gain +0.001 vs mean shuffled 95% +0.002; beats the shuffle on 3 of 6 horizon fits.
- live+sky+adv700 far: mean AUC gain -0.002 vs mean shuffled 95% +0.003; beats the shuffle on 0 of 4 horizon fits.
- live+sky+adv700 fan: mean AUC gain -0.002 vs mean shuffled 95% +0.004; beats the shuffle on 0 of 4 horizon fits.
- live+sky+advtop far: mean AUC gain -0.002 vs mean shuffled 95% +0.002; beats the shuffle on 0 of 4 horizon fits.
- live+sky+advtop fan: mean AUC gain -0.001 vs mean shuffled 95% +0.003; beats the shuffle on 0 of 4 horizon fits.
- live+sky+adv700 change: mean AUC gain -0.002 vs mean shuffled 95% +0.003; beats the shuffle on 0 of 4 horizon fits.
- Overall: no candidate's gain clears the shuffled 95% on most horizons: the projected mask adds nothing over the live line's current goes_fan beyond noise.
- DMW: C14 (IR cloud-drift) vectors within 300 km at 1.5 h before sunset, median 60 over the 8 times (min 10); see the table for the other bands.

## Coverage per horizon

| label      |   pre shots |   read |   adv700 value read |   adv700_far kept |   adv700_fan kept |   advtop_far kept |   advtop_fan kept |   adv700_far dropped (<60% in window) |   advtop_far dropped |   median dt h |
|:-----------|------------:|-------:|--------------------:|------------------:|------------------:|------------------:|------------------:|--------------------------------------:|---------------------:|--------------:|
| 01_2h_pre  |         576 |    570 |                 570 |               568 |               568 |               543 |               543 |                                     2 |                   27 |         1.958 |
| 02_1h_pre  |         575 |    569 |                 569 |               569 |               569 |               569 |               569 |                                     0 |                    0 |         0.958 |
| 03_45m_pre |         576 |    570 |                 570 |               570 |               570 |               570 |               570 |                                     0 |                    0 |         0.708 |
| 04_30m_pre |         574 |    567 |                 567 |               567 |               567 |               567 |               567 |                                     0 |                    0 |         0.458 |
| 05_15m_pre |         573 |    566 |                 566 |               566 |               566 |               566 |               566 |                                     0 |                    0 |         0.208 |
| 06_5m_pre  |         572 |    565 |                 565 |               565 |               565 |               565 |               565 |                                     0 |                    0 |         0.041 |

Steering level picked by cloud-top height (advtop):

| label      |   500hPa |   700hPa |   850hPa |
|:-----------|---------:|---------:|---------:|
| 01_2h_pre  |      251 |      235 |       84 |
| 02_1h_pre  |      255 |      227 |       87 |
| 03_45m_pre |      254 |      224 |       92 |
| 04_30m_pre |      258 |      232 |       77 |
| 05_15m_pre |      246 |      265 |       55 |
| 06_5m_pre  |      241 |      267 |       57 |

Reader check: this script's undisplaced fan vs the stored goes_fan at the same shot: Spearman 1.000, MAE 0.001 (3407 shots; wcax is read around btv_echo_cam here, around its own spot live). Download: 721 KB per scan on average, 3113 windows downloaded, the rest shared with another camera.

## Sanity check: does the displaced mask predict the zone's cloud at sunset?

Truth: the stored zone value at the 07_sunset capture (else the capture nearest sunset, within 20 min). persist = today's zone value at the shot; displaced = the zone moved upwind by wind x dt; reversed = moved downwind.

| horizon   | steering   | zone   |   n |   rho persist |   MAE persist |   rho displaced |   MAE displaced |   rho reversed |   MAE reversed | displaced best   |
|:----------|:-----------|:-------|----:|--------------:|--------------:|----------------:|----------------:|---------------:|---------------:|:-----------------|
| 01_2h_pre | 700        | near   | 569 |         0.72  |         0.18  |           0.756 |           0.15  |          0.593 |          0.239 | True             |
| 01_2h_pre | 700        | far    | 567 |         0.912 |         0.106 |           0.927 |           0.091 |          0.825 |          0.149 | True             |
| 01_2h_pre | 700        | fan    | 567 |         0.915 |         0.103 |           0.928 |           0.089 |          0.828 |          0.146 | True             |
| 01_2h_pre | top        | near   | 569 |         0.72  |         0.18  |           0.771 |           0.142 |          0.572 |          0.249 | True             |
| 01_2h_pre | top        | far    | 542 |         0.916 |         0.107 |           0.936 |           0.088 |          0.809 |          0.156 | True             |
| 01_2h_pre | top        | fan    | 542 |         0.92  |         0.103 |           0.938 |           0.085 |          0.816 |          0.153 | True             |
| 02_1h_pre | 700        | near   | 568 |         0.819 |         0.131 |           0.829 |           0.118 |          0.734 |          0.183 | True             |
| 02_1h_pre | 700        | far    | 568 |         0.958 |         0.071 |           0.967 |           0.059 |          0.927 |          0.093 | True             |
| 02_1h_pre | 700        | fan    | 568 |         0.96  |         0.068 |           0.968 |           0.058 |          0.931 |          0.09  | True             |
| 02_1h_pre | top        | near   | 568 |         0.819 |         0.131 |           0.853 |           0.112 |          0.711 |          0.188 | True             |
| 02_1h_pre | top        | far    | 568 |         0.958 |         0.071 |           0.968 |           0.059 |          0.918 |          0.098 | True             |
| 02_1h_pre | top        | fan    | 568 |         0.96  |         0.068 |           0.969 |           0.057 |          0.922 |          0.094 | True             |

## Spearman with the outcome (pct) per horizon

|            |   adv700_far |   adv700_fan |   adv700_near |   advtop_far |   advtop_fan |   advtop_near |   adv700_fan_change |   goes_fan |   goes_far |
|:-----------|-------------:|-------------:|--------------:|-------------:|-------------:|--------------:|--------------------:|-----------:|-----------:|
| 01_2h_pre  |       -0.518 |       -0.527 |        -0.424 |       -0.505 |       -0.512 |        -0.427 |              -0.027 |     -0.525 |     -0.514 |
| 02_1h_pre  |       -0.496 |       -0.504 |        -0.436 |       -0.494 |       -0.501 |        -0.445 |               0.039 |     -0.508 |     -0.501 |
| 03_45m_pre |       -0.493 |       -0.502 |        -0.423 |       -0.492 |       -0.501 |        -0.425 |              -0.001 |     -0.501 |     -0.491 |
| 04_30m_pre |       -0.489 |       -0.494 |        -0.445 |       -0.49  |       -0.495 |        -0.444 |               0.017 |     -0.495 |     -0.487 |
| 05_15m_pre |       -0.507 |       -0.518 |        -0.493 |       -0.508 |       -0.518 |        -0.493 |               0.007 |     -0.516 |     -0.507 |
| 06_5m_pre  |       -0.517 |       -0.525 |        -0.491 |       -0.518 |       -0.525 |        -0.497 |              -0.016 |     -0.526 |     -0.518 |

## Forecast test (extra.report: live line + the new input, leave-one-month-out, 30 shuffles)

| set                    | horizon    |   n |   spearman |   AUC top-25% |   AUC top-10% |    MAE |   AUC gain |   shuffled 95% |
|:-----------------------|:-----------|----:|-----------:|--------------:|--------------:|-------:|-----------:|---------------:|
| live                   | 01_2h_pre  | 461 |      0.528 |         0.708 |         0.597 | 20.206 |    nan     |        nan     |
| live+adv700 far        | 01_2h_pre  | 461 |      0.539 |         0.712 |         0.611 | 19.819 |      0.005 |          0.006 |
| live+adv700 fan        | 01_2h_pre  | 461 |      0.538 |         0.711 |         0.607 | 19.803 |      0.004 |          0.004 |
| live+advtop far        | 01_2h_pre  | 461 |      0.544 |         0.715 |         0.618 | 19.722 |      0.007 |          0.003 |
| live+advtop fan        | 01_2h_pre  | 461 |      0.544 |         0.714 |         0.613 | 19.715 |      0.006 |          0.004 |
| live+adv700 change     | 01_2h_pre  | 461 |      0.538 |         0.711 |         0.607 | 19.803 |      0.004 |          0.003 |
| live                   | 02_1h_pre  | 487 |      0.6   |         0.739 |         0.616 | 18.318 |    nan     |        nan     |
| live+adv700 far        | 02_1h_pre  | 487 |      0.603 |         0.74  |         0.622 | 18.229 |      0.001 |          0.001 |
| live+adv700 fan        | 02_1h_pre  | 487 |      0.603 |         0.74  |         0.618 | 18.22  |      0.001 |          0.003 |
| live+advtop far        | 02_1h_pre  | 487 |      0.602 |         0.74  |         0.623 | 18.255 |      0.002 |          0.001 |
| live+advtop fan        | 02_1h_pre  | 487 |      0.604 |         0.741 |         0.62  | 18.24  |      0.002 |          0.001 |
| live+adv700 change     | 02_1h_pre  | 487 |      0.603 |         0.74  |         0.618 | 18.22  |      0.001 |          0.001 |
| live                   | 03_45m_pre | 488 |      0.596 |         0.733 |         0.602 | 18.193 |    nan     |        nan     |
| live+adv700 far        | 03_45m_pre | 488 |      0.593 |         0.731 |         0.601 | 18.183 |     -0.002 |          0.001 |
| live+adv700 fan        | 03_45m_pre | 488 |      0.594 |         0.731 |         0.6   | 18.161 |     -0.002 |          0.001 |
| live+advtop far        | 03_45m_pre | 488 |      0.594 |         0.733 |         0.604 | 18.186 |     -0     |          0.003 |
| live+advtop fan        | 03_45m_pre | 488 |      0.595 |         0.734 |         0.604 | 18.159 |      0     |          0.003 |
| live+adv700 change     | 03_45m_pre | 488 |      0.594 |         0.731 |         0.6   | 18.161 |     -0.002 |          0.004 |
| live                   | 04_30m_pre | 485 |      0.614 |         0.746 |         0.632 | 17.738 |    nan     |        nan     |
| live+adv700 far        | 04_30m_pre | 485 |      0.612 |         0.744 |         0.634 | 17.743 |     -0.002 |          0.002 |
| live+adv700 fan        | 04_30m_pre | 485 |      0.612 |         0.744 |         0.633 | 17.726 |     -0.001 |          0.004 |
| live+advtop far        | 04_30m_pre | 485 |      0.612 |         0.745 |         0.635 | 17.762 |     -0.001 |          0.003 |
| live+advtop fan        | 04_30m_pre | 485 |      0.612 |         0.745 |         0.633 | 17.75  |     -0.001 |          0.002 |
| live+adv700 change     | 04_30m_pre | 485 |      0.612 |         0.744 |         0.633 | 17.726 |     -0.001 |          0.002 |
| live                   | 05_15m_pre | 484 |      0.677 |         0.787 |         0.671 | 15.929 |    nan     |        nan     |
| live+adv700 far        | 05_15m_pre | 484 |      0.677 |         0.786 |         0.678 | 15.967 |     -0     |          0.002 |
| live+adv700 fan        | 05_15m_pre | 484 |      0.677 |         0.788 |         0.675 | 15.94  |      0.001 |          0.001 |
| live+advtop far        | 05_15m_pre | 484 |      0.677 |         0.787 |         0.679 | 15.971 |      0.001 |          0.001 |
| live+advtop fan        | 05_15m_pre | 484 |      0.677 |         0.789 |         0.676 | 15.96  |      0.002 |          0.003 |
| live+adv700 change     | 05_15m_pre | 484 |      0.677 |         0.788 |         0.675 | 15.94  |      0.001 |          0.003 |
| live                   | 06_5m_pre  | 483 |      0.757 |         0.87  |         0.791 | 13.15  |    nan     |        nan     |
| live+adv700 far        | 06_5m_pre  | 483 |      0.759 |         0.873 |         0.802 | 13.26  |      0.002 |          0.002 |
| live+adv700 fan        | 06_5m_pre  | 483 |      0.759 |         0.872 |         0.793 | 13.151 |      0.002 |          0.001 |
| live+advtop far        | 06_5m_pre  | 483 |      0.759 |         0.873 |         0.802 | 13.26  |      0.002 |          0.001 |
| live+advtop fan        | 06_5m_pre  | 483 |      0.758 |         0.871 |         0.793 | 13.169 |      0.001 |          0.001 |
| live+adv700 change     | 06_5m_pre  | 483 |      0.759 |         0.872 |         0.793 | 13.151 |      0.002 |          0.001 |
| live+sky               | 02_1h_pre  | 486 |      0.644 |         0.747 |         0.625 | 17.081 |    nan     |        nan     |
| live+sky+adv700 far    | 02_1h_pre  | 486 |      0.643 |         0.745 |         0.627 | 17.13  |     -0.002 |          0.003 |
| live+sky+adv700 fan    | 02_1h_pre  | 486 |      0.645 |         0.746 |         0.626 | 17.108 |     -0.001 |          0.005 |
| live+sky+advtop far    | 02_1h_pre  | 486 |      0.645 |         0.746 |         0.629 | 17.128 |     -0.001 |          0.002 |
| live+sky+advtop fan    | 02_1h_pre  | 486 |      0.646 |         0.747 |         0.628 | 17.101 |     -0.001 |          0.004 |
| live+sky+adv700 change | 02_1h_pre  | 486 |      0.645 |         0.746 |         0.626 | 17.108 |     -0.001 |          0.003 |
| live+sky               | 03_45m_pre | 487 |      0.665 |         0.756 |         0.629 | 16.729 |    nan     |        nan     |
| live+sky+adv700 far    | 03_45m_pre | 487 |      0.662 |         0.754 |         0.627 | 16.791 |     -0.003 |          0.002 |
| live+sky+adv700 fan    | 03_45m_pre | 487 |      0.662 |         0.754 |         0.626 | 16.789 |     -0.003 |          0.004 |
| live+sky+advtop far    | 03_45m_pre | 487 |      0.662 |         0.755 |         0.628 | 16.784 |     -0.002 |          0.001 |
| live+sky+advtop fan    | 03_45m_pre | 487 |      0.663 |         0.755 |         0.628 | 16.765 |     -0.002 |          0.004 |
| live+sky+adv700 change | 03_45m_pre | 487 |      0.662 |         0.754 |         0.626 | 16.789 |     -0.003 |          0.002 |
| live+sky               | 04_30m_pre | 482 |      0.669 |         0.764 |         0.651 | 16.632 |    nan     |        nan     |
| live+sky+adv700 far    | 04_30m_pre | 482 |      0.666 |         0.761 |         0.648 | 16.677 |     -0.003 |          0.003 |
| live+sky+adv700 fan    | 04_30m_pre | 482 |      0.666 |         0.762 |         0.649 | 16.665 |     -0.003 |          0.002 |
| live+sky+advtop far    | 04_30m_pre | 482 |      0.665 |         0.761 |         0.649 | 16.688 |     -0.004 |          0.003 |
| live+sky+advtop fan    | 04_30m_pre | 482 |      0.666 |         0.762 |         0.649 | 16.673 |     -0.003 |          0.002 |
| live+sky+adv700 change | 04_30m_pre | 482 |      0.666 |         0.762 |         0.649 | 16.665 |     -0.003 |          0.003 |
| live+sky               | 05_15m_pre | 483 |      0.728 |         0.798 |         0.691 | 15.027 |    nan     |        nan     |
| live+sky+adv700 far    | 05_15m_pre | 483 |      0.726 |         0.796 |         0.693 | 15.136 |     -0.002 |          0.003 |
| live+sky+adv700 fan    | 05_15m_pre | 483 |      0.726 |         0.797 |         0.692 | 15.079 |     -0.001 |          0.004 |
| live+sky+advtop far    | 05_15m_pre | 483 |      0.726 |         0.796 |         0.693 | 15.151 |     -0.001 |          0.001 |
| live+sky+advtop fan    | 05_15m_pre | 483 |      0.728 |         0.798 |         0.693 | 15.09  |      0.001 |          0.003 |
| live+sky+adv700 change | 05_15m_pre | 483 |      0.726 |         0.797 |         0.692 | 15.079 |     -0.001 |          0.003 |

### Mean gain in AUC top-25%

| set                    |   horizons |   mean_gain |   mean_shuffled_95 |   beats_shuffle |
|:-----------------------|-----------:|------------:|-------------------:|----------------:|
| live+adv700 far        |          6 |       0.001 |              0.002 |               1 |
| live+adv700 fan        |          6 |       0.001 |              0.002 |               2 |
| live+advtop far        |          6 |       0.002 |              0.002 |               3 |
| live+advtop fan        |          6 |       0.002 |              0.002 |               2 |
| live+adv700 change     |          6 |       0.001 |              0.002 |               3 |
| live+sky+adv700 far    |          4 |      -0.002 |              0.003 |               0 |
| live+sky+adv700 fan    |          4 |      -0.002 |              0.004 |               0 |
| live+sky+advtop far    |          4 |      -0.002 |              0.002 |               0 |
| live+sky+advtop fan    |          4 |      -0.001 |              0.003 |               0 |
| live+sky+adv700 change |          4 |      -0.002 |              0.003 |               0 |


## Feasibility: GOES derived motion winds (ABI-L2-DMWC)

Files per hour by band (the band is in the name, `-M6C14_`), and size:

| hour           | band   |   files |   median_KB |
|:---------------|:-------|--------:|------------:|
| 2026-10-07 20Z | C02    |       4 |     385.154 |
| 2026-10-07 20Z | C07    |       4 |     101.497 |
| 2026-10-07 20Z | C08    |       4 |     235.153 |
| 2026-10-07 20Z | C09    |       4 |     145.834 |
| 2026-10-07 20Z | C10    |       4 |     130.359 |
| 2026-10-07 20Z | C14    |       4 |     259.517 |
| 2026-10-07 21Z | C02    |       4 |     316.072 |
| 2026-10-07 21Z | C07    |       4 |     123.857 |
| 2026-10-07 21Z | C08    |       4 |     237.074 |
| 2026-10-07 21Z | C09    |       4 |     146.087 |
| 2026-10-07 21Z | C10    |       4 |     128.756 |
| 2026-10-07 21Z | C14    |       4 |     260.005 |

Variables per wind vector in `OR_ABI-L2-DMWC-M6C14_G19_s20262802101178_e20262802103551_c20262802109245.nc`: lat, lon, time, wind_speed, wind_direction, pressure, temperature, local_zenith_angle, solar_zenith_angle, DQF (5705 vectors, speed m s-1, pressure hPa); plus per-file summaries (vector counts per layer, cloud-top pressure stats).

Good-quality (DQF 0) vectors within 300 km of Burlington, latest file of each band landed by 1.5 h before sunset (4 cloudy and 4 clear days by the 1h-pre GOES fan cloud at btv_echo_cam). Cell: total (low >= 700 hPa / mid 400-700 / high < 400):

| day        |   fan cloud | UTC   | C02           | C07       | C08           | C09         | C10       | C14           |
|:-----------|------------:|:------|:--------------|:----------|:--------------|:------------|:----------|:--------------|
| 2025-12-15 |       0.832 | 19:43 | 0 (0/0/0)     | 0 (0/0/0) | 1 (0/0/1)     | 0 (0/0/0)   | 0 (0/0/0) | 30 (0/23/7)   |
| 2026-07-28 |       0.999 | 22:52 | 0 (0/0/0)     | 0 (0/0/0) | 148 (0/0/148) | 0 (0/0/0)   | 0 (0/0/0) | 158 (0/0/158) |
| 2025-05-22 |       1     | 22:51 | 17 (17/0/0)   | 0 (0/0/0) | 56 (0/0/56)   | 0 (0/0/0)   | 0 (0/0/0) | 99 (1/21/77)  |
| 2026-09-12 |       0.968 | 21:38 | 7 (7/0/0)     | 0 (0/0/0) | 92 (0/0/92)   | 4 (0/0/4)   | 0 (0/0/0) | 100 (4/3/93)  |
| 2026-05-22 |       0.054 | 22:51 | 53 (53/0/0)   | 0 (0/0/0) | 59 (0/0/59)   | 0 (0/0/0)   | 0 (0/0/0) | 63 (24/0/39)  |
| 2026-05-18 |       0.035 | 22:46 | 7 (7/0/0)     | 0 (0/0/0) | 16 (0/0/16)   | 14 (0/1/13) | 6 (0/6/0) | 10 (2/2/6)    |
| 2026-08-21 |       0.02  | 22:18 | 116 (116/0/0) | 0 (0/0/0) | 17 (0/0/17)   | 47 (0/0/47) | 1 (0/1/0) | 28 (8/2/18)   |
| 2026-08-03 |       0.045 | 22:45 | 149 (149/0/0) | 0 (0/0/0) | 0 (0/0/0)     | 19 (0/17/2) | 2 (0/2/0) | 58 (29/24/5)  |