# HSV tuning and cloud contrast vs My ranking (btv_echo_cam, 2026-10-12)

Follows `my_rank.md`. Script: `hsv_tuning.py` (full table in `hsv_tuning_results.md`). 116 ranked days (the four
zoomed-in days are left out). Day score = best non-excluded frame. Every number below is 5-fold cross-validation
over days, 20 random splits: settings picked on 4 folds, judged on the 5th, soft cap refitted on the 4 folds.

## Verdict

Changed. Two things beat the current score out of sample, and together they beat it by a lot:

1. **Pink only counts at half brightness or more** (`v >= 128`). That drops the dim grey-purple / mauve dusk cloud.
2. **Cloud colour contrast multiplier**: `score x (0.36 + 2.5 x hue spread) x (0.93 + 0.0086 x lit contrast)`
   - *hue spread*: circular spread of the hues of the coloured pixels (0 = one flat colour; orange and pink
     together is high). This is the "colour contrast in the cloud".
   - *lit contrast*: mean brightness of the coloured pixels minus the rest of the sky (lit cloud against dark
     cloud / plain sky).
3. Soft cap constant refitted for the new scale: `100 x (1 - e^(-raw / 66.9))` (was 55.3).

| | ρ with your score | mean abs diff |
|---|---|---|
| current score | 0.753 | 13.3 |
| pink v >= 128 alone | 0.773 | 12.8 |
| hue spread multiplier alone | 0.816 | 11.9 |
| lit contrast multiplier alone | 0.802 | 12.0 |
| **all three, every setting picked inside the folds** | **0.866** | **10.0** |
| edited `sunset_process.py` run on every frame (in sample) | 0.872 (was 0.756) | 9.8 (was 13.1) |
| scored on the frame *you* picked each day | 0.878 (was 0.754) | |

The gain holds on the last 40 % of days when the cap is fitted on the first 60 % (ρ 0.869 → 0.929). The two pieces
help more together than apart (pink floor 0.773 + hue spread 0.816 → 0.850 combined), because once the dim mauve
is gone the hue spread is measuring real orange-against-pink skies rather than grey.

`rank_sunset`'s flow is unchanged: same masks, same per-band score, same top half; the pink mask gets a value floor,
and the contrast factor multiplies the sum before the soft cap. `scoring.js` matches (tests added), and the
Ranking explained page and score breakdown show the contrast factor.

## What didn't help

| change | cv ρ | |
|---|---|---|
| crop the top 40 / 55 / 60 / 65 / 70 % instead of 50 % | 0.750 | half picked 99 of 100 times |
| pink saturation floor 28-60 instead of 20 | 0.746 | |
| pink starting at hue 150 or 160 | 0.750 | |
| penalty for dull pink-hue pixels (s 8-19) | 0.751 | |
| pink split into 4 sub-bands with their own weights | 0.771 | about the same as the value floor, more knobs |

Horizon: a fixed different crop doesn't help, so the views with the horizon low in the frame stay a known miss.
The preset view isn't recorded with the frame, so a per-preset ratio wasn't possible.

Contrast measures that didn't add anything: overall colourfulness (Hasler-Süsstrunk), saturation spread, brightness
spread of the coloured pixels, sky brightness range, local contrast and edge strength inside the coloured areas.
Texture/edges *lower* agreement slightly: busy cloud isn't what you reward, colour against colour and lit against
dark is. On their own none of the contrast measures rank days well (hue spread ρ 0.25, lit contrast 0.22); they
work as a correction to the HSV score (ρ with what the HSV score misses: 0.15 and 0.31).

## Days that moved most (your score / old / new)

Closer: 2025-12-02 22 / 58 / 4, 2026-04-14 25 / 68 / 34, 2026-03-08 14 / 59 / 38, 2026-10-09 79 / 54 / 82,
2025-05-16 86 / 54 / 71. Further: 2025-06-29 64 / 65 / 80, 2025-11-06 28 / 27 / 42, 2026-06-04 15 / 36 / 47,
2026-04-17 42 / 37 / 23.

## Caveats

- The best frame of the day now matches your pick on 78 % of days (was 91 %): the contrast term sometimes prefers a
  neighbouring shot. The day score still agrees better, and so does the score of your own pick (above).
- Tuned on one camera (btv_echo_cam); the other cameras' scores move too. Check them once some days are ranked there.
- Stored scores keep the old formula until rescored (`python -m ai_judge rescore --camera all`); not run. The zoomed-day
  -40 offset in `backend.py` is unchanged.
