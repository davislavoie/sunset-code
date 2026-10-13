# Cloud-top height toward the sun (517 sunset camera-days, 120 of them ranked by you)

GOES-East cloud-top height (ABI-L2-ACHAC, ~10 km pixels, top layer only), 1 h before sunset (h1) and at sunset (h0). top = median height of the zone's cloud tops (km); high / mid / low = share of the zone with tops at 6 km+ / 2-6 km / under 2 km. Zones: overhead (15 km), near fan (5-40 km toward the sun), far fan (80-300 km).

## Spearman with the outcome

|              |   HSV score (all cameras) |   your score (btv, ranked days) |
|:-------------|--------------------------:|--------------------------------:|
| top_over@h1  |                    -0.234 |                          -0.054 |
| high_over@h1 |                    -0.271 |                          -0.1   |
| mid_over@h1  |                    -0.156 |                           0.119 |
| low_over@h1  |                     0.217 |                           0.069 |
| top_near@h1  |                    -0.193 |                          -0.071 |
| high_near@h1 |                    -0.275 |                          -0.111 |
| mid_near@h1  |                    -0.173 |                           0.116 |
| low_near@h1  |                     0.19  |                           0.065 |
| top_far@h1   |                    -0.224 |                          -0.068 |
| high_far@h1  |                    -0.317 |                          -0.078 |
| mid_far@h1   |                    -0.213 |                          -0.02  |
| low_far@h1   |                     0.22  |                           0.067 |
| top_over@h0  |                    -0.226 |                           0.01  |
| high_over@h0 |                    -0.277 |                          -0.032 |
| mid_over@h0  |                    -0.133 |                           0.172 |
| low_over@h0  |                     0.142 |                           0.03  |
| top_near@h0  |                    -0.186 |                           0.059 |
| high_near@h0 |                    -0.292 |                          -0.031 |
| mid_near@h0  |                    -0.16  |                           0.114 |
| low_near@h0  |                     0.139 |                          -0.032 |
| top_far@h0   |                    -0.276 |                          -0.048 |
| high_far@h0  |                    -0.314 |                          -0.075 |
| mid_far@h0   |                    -0.178 |                          -0.041 |
| low_far@h0   |                     0.209 |                          -0.043 |

## KBTV METAR 1 h before sunset (Spearman)

|               |   HSV score (all cameras) |   your score (btv, ranked days) |
|:--------------|--------------------------:|--------------------------------:|
| metar_cover   |                    -0.489 |                          -0.03  |
| metar_ceiling |                     0.449 |                           0.055 |
| metar_base    |                     0.345 |                           0.044 |

## Satellite layers vs the photo's cloud type (vision model, 160 camera-days)

Mean share of the near fan (5-40 km toward the sun) per layer, and median top (km), by what the photo shows.

| cloud_type   |   high_near@h1 |   mid_near@h1 |   low_near@h1 |   top_near@h1 |   days |
|:-------------|---------------:|--------------:|--------------:|--------------:|-------:|
| clear        |           0.07 |          0.05 |          0.12 |          2.4  |     27 |
| high_thin    |           0.29 |          0.16 |          0.05 |          6.93 |     23 |
| low_thick    |           0.44 |          0.39 |          0.11 |          5.48 |     11 |
| mid_broken   |           0.41 |          0.32 |          0.15 |          5.78 |     65 |
| mixed        |           0.56 |          0.25 |          0.16 |          6.8  |      7 |
| overcast     |           0.65 |          0.31 |          0.03 |          6.79 |     27 |

## Satellite's main layer vs hand labels from the photos (39 camera-days)

| layer   |   clear |   high |   low |   mid |
|:--------|--------:|-------:|------:|------:|
| clear   |      11 |      0 |     1 |     0 |
| high    |       1 |      3 |     0 |     2 |
| low     |       0 |      3 |     3 |     6 |
| mid     |       3 |      2 |     1 |     3 |

Agree on 51% (mixed labels count as misses).


## By kind of sky 1 h before sunset (mean percentile; 0.5 is an average day)

| sky                            |   days |   hsv_pct |   ranked_days |   your_pct |
|:-------------------------------|-------:|----------:|--------------:|-----------:|
| clear                          |     13 |      0.69 |             2 |       0.48 |
| mixed                          |    157 |      0.58 |            42 |       0.59 |
| low bank far toward the sun    |     12 |      0.57 |             5 |       0.34 |
| mostly clear                   |    135 |      0.54 |            29 |       0.5  |
| high cloud near, far side open |    200 |      0.4  |            42 |       0.44 |

## Leave-one-month-out, 1 h before sunset

| features                                | model   |   n |     R2 |   spearman |   AUC(top 25%) |
|:----------------------------------------|:--------|----:|-------:|-----------:|---------------:|
| cloud mask (what's live)                | ridge   | 517 |  0.282 |      0.518 |          0.756 |
| cloud mask (what's live)                | gbm     | 517 |  0.211 |      0.474 |          0.719 |
| cloud mask + height                     | ridge   | 517 |  0.277 |      0.509 |          0.754 |
| cloud mask + height                     | gbm     | 517 |  0.196 |      0.47  |          0.716 |
| height only                             | ridge   | 517 |  0.256 |      0.494 |          0.747 |
| height only                             | gbm     | 517 |  0.173 |      0.448 |          0.709 |
| cloud mask + METAR                      | ridge   | 517 |  0.305 |      0.569 |          0.772 |
| cloud mask + METAR                      | gbm     | 517 |  0.268 |      0.529 |          0.722 |
| cloud mask + height + METAR             | ridge   | 517 |  0.292 |      0.556 |          0.761 |
| cloud mask + height + METAR             | gbm     | 517 |  0.261 |      0.529 |          0.725 |
| cloud mask, your score                  | ridge   | 120 | -0.043 |     -0.076 |          0.393 |
| cloud mask + height, your score         | ridge   | 120 | -0.044 |     -0.324 |          0.287 |
| cloud mask + METAR, your score          | ridge   | 120 | -0.057 |     -0.132 |          0.404 |
| cloud mask + height + METAR, your score | ridge   | 120 | -0.042 |     -0.372 |          0.259 |

## Notes on the hand labels (written by hand after the run; a rerun drops this section)

Labelled blind from the 02_1h_pre thumbnails: 39 btv_echo_cam / bolton_summit_cam days picked across the kinds of sky
(bolton 2026-05-19 dropped, black frame). The photo shows the cloud *base*; the satellite reads the *top* of the top layer.

- Fog and flat grey decks read as high. Bolton 2026-09-28 (summit in fog): 100% high, tops 7.3 km. btv 2026-03-06
  (flat overcast): tops 10.8 km. The deck is low but the system is deep, or a higher layer hides it.
- Lumpy grey decks read as mid. 6 of 12 photo-"low" days come out mid with tops 2.3-3.8 km (btv 2025-10-08, 2025-12-12,
  2026-01-07, 2026-04-05, 2026-10-09). That's stratocumulus with a low base and its top above the 2 km cut-off, so the bins
  disagree on definition more than on what's there. Counting low and mid as one group, agreement goes from 51% to 69%
  (27 of 39); clear days match 11 of 12.
- Thin cirrus gets placed too low. btv 2025-10-10 (streaky cirrus across the sun) is near-fan mid at 3.5 km. btv 2026-04-07
  (milky veil) is 1.9 km. btv 2026-06-29 (haze or veil) comes out clear. Semi-transparent cirrus is where the height
  retrieval is weakest.
- Small cumulus is missed. Bolton 2026-07-08 and 2026-07-15 show broken puffy cloud near the sun, but the satellite has no
  cloud in any zone. Those clouds are smaller than the ~10 km pixels.
