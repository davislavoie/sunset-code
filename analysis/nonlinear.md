# A model that bends vs the live line (2872 shots, 481 camera-days, leave-one-month-out, same rows for every model)


## AUC (top 25 %)

| model                               |   01_2h_pre |   02_1h_pre |   03_45m_pre |   04_30m_pre |   05_15m_pre |   06_5m_pre |   mean |
|:------------------------------------|------------:|------------:|-------------:|-------------:|-------------:|------------:|-------:|
| live line (icon+goes)               |       0.752 |       0.753 |        0.766 |        0.766 |        0.804 |       0.897 |  0.789 |
| line + sky shape                    |       0.736 |       0.745 |        0.758 |        0.761 |        0.797 |       0.896 |  0.782 |
| trees, live inputs                  |       0.727 |       0.72  |        0.756 |        0.746 |        0.813 |       0.89  |  0.775 |
| trees, live + sky shape + raw cloud |       0.721 |       0.736 |        0.739 |        0.746 |        0.801 |       0.888 |  0.772 |
| trees pooled over horizons          |       0.725 |       0.734 |        0.76  |        0.753 |        0.805 |       0.866 |  0.774 |
| blend: live line + pooled trees     |       0.745 |       0.75  |        0.771 |        0.766 |        0.812 |       0.893 |  0.79  |

## AUC top-10%

| model                               |   01_2h_pre |   02_1h_pre |   03_45m_pre |   04_30m_pre |   05_15m_pre |   06_5m_pre |   mean |
|:------------------------------------|------------:|------------:|-------------:|-------------:|-------------:|------------:|-------:|
| live line (icon+goes)               |       0.647 |       0.652 |        0.651 |        0.65  |        0.686 |       0.815 |  0.683 |
| line + sky shape                    |       0.633 |       0.646 |        0.645 |        0.646 |        0.681 |       0.818 |  0.678 |
| trees, live inputs                  |       0.633 |       0.635 |        0.664 |        0.65  |        0.702 |       0.808 |  0.682 |
| trees, live + sky shape + raw cloud |       0.638 |       0.653 |        0.65  |        0.659 |        0.694 |       0.811 |  0.684 |
| trees pooled over horizons          |       0.625 |       0.65  |        0.665 |        0.649 |        0.692 |       0.791 |  0.679 |
| blend: live line + pooled trees     |       0.638 |       0.653 |        0.663 |        0.654 |        0.691 |       0.812 |  0.685 |

## spearman

| model                               |   01_2h_pre |   02_1h_pre |   03_45m_pre |   04_30m_pre |   05_15m_pre |   06_5m_pre |   mean |
|:------------------------------------|------------:|------------:|-------------:|-------------:|-------------:|------------:|-------:|
| live line (icon+goes)               |       0.601 |       0.631 |        0.647 |        0.672 |        0.76  |       0.867 |  0.697 |
| line + sky shape                    |       0.582 |       0.617 |        0.634 |        0.66  |        0.751 |       0.865 |  0.685 |
| trees, live inputs                  |       0.543 |       0.597 |        0.65  |        0.664 |        0.753 |       0.851 |  0.677 |
| trees, live + sky shape + raw cloud |       0.564 |       0.62  |        0.633 |        0.673 |        0.742 |       0.851 |  0.681 |
| trees pooled over horizons          |       0.572 |       0.616 |        0.658 |        0.671 |        0.736 |       0.799 |  0.676 |
| blend: live line + pooled trees     |       0.599 |       0.636 |        0.667 |        0.686 |        0.762 |       0.852 |  0.7   |

## MAE (percentile pts, lower is better)

| model                               |   01_2h_pre |   02_1h_pre |   03_45m_pre |   04_30m_pre |   05_15m_pre |   06_5m_pre |   mean |
|:------------------------------------|------------:|------------:|-------------:|-------------:|-------------:|------------:|-------:|
| live line (icon+goes)               |      18.673 |      17.833 |       17.613 |       17.106 |       13.96  |       9.935 | 15.853 |
| line + sky shape                    |      18.897 |      17.968 |       17.747 |       17.332 |       14.135 |      10.113 | 16.032 |
| trees, live inputs                  |      19.576 |      18.135 |       17.291 |       16.95  |       13.904 |      10.524 | 16.063 |
| trees, live + sky shape + raw cloud |      18.859 |      17.612 |       17.606 |       16.603 |       14.335 |      10.756 | 15.962 |
| trees pooled over horizons          |      18.549 |      17.405 |       16.984 |       16.666 |       14.823 |      12.974 | 16.234 |
| blend: live line + pooled trees     |      18.406 |      17.28  |       16.976 |       16.516 |       14.023 |      10.807 | 15.668 |

## What the pooled trees use (permutation importance, drop in R2, in-sample)

|              |   importance |
|:-------------|-------------:|
| cur_pct      |       0.2802 |
| max_pct      |       0.0635 |
| goes_fan     |       0.0578 |
| icon_low     |       0.0459 |
| weather      |       0.0448 |
| icon_weather |       0.0377 |
| goes_near    |       0.0369 |
| icon_mid     |       0.03   |
| icon_canvas  |       0.0288 |
| metar_west   |       0.0204 |
| goes_far     |       0.0192 |
| ceil         |       0.0172 |
| h            |       0.0171 |
| goes_over    |       0.0123 |
| icon_high    |       0.0092 |
| lit_canvas   |       0.0064 |
| cover_mid    |       0.0047 |
| BTV_cover    |       0.0021 |
| lowdeck      |       0      |

## Outcome by GOES fan cloud, 1 h pre (mean percentile, share of top-25 % days)

| fan_band   |   n |   mean_pct |   top25 |
|:-----------|----:|-----------:|--------:|
| 0-10       |  73 |       0.73 |    0.59 |
| 10-30      |  42 |       0.71 |    0.45 |
| 30-50      |  60 |       0.59 |    0.32 |
| 50-70      |  53 |       0.53 |    0.23 |
| 70-90      |  88 |       0.44 |    0.17 |
| 90-100     | 164 |       0.33 |    0.08 |

## Outcome by KBTV ceiling, 1 h pre

| ceil_band   |   n |   mean_pct |   top25 |
|:------------|----:|-----------:|--------:|
| <3k         |  39 |       0.23 |    0.05 |
| 3-6k        |  82 |       0.39 |    0.16 |
| 6-12k       | 124 |       0.44 |    0.16 |
| none <12k   | 235 |       0.62 |    0.37 |