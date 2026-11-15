# Three satellite ideas for the forecast: trend, thickness, motion (2026-11-14)

None of them is wired in. Each was scored with `extra.py`: the live line (`icon+goes+band`, and with the
sky read on the 1h-15m shots) with and without the new input, leave-one-month-out on the same shots, next
to what a shuffled input scores by chance. Export of 2026-10-15, about 490 sunset camera-days. Candidate
sets were fixed before any result was seen.

| idea | what it is | mean gain in AUC top-25% | shuffled 95% | write-up |
|---|---|---|---|---|
| Trend | this shot's GOES cloud minus the previous shot's | 0.000 to +0.002 | 0.002 to 0.003 | `trend.md` |
| Thickness | GOES cloud optical depth by zone (`ABI-L2-CODC`) | -0.001 to +0.002 | 0.002 to 0.003 | `thickness.md` |
| Motion | the cloud mask moved upwind by forecast wind x time to sunset | +0.001 to +0.002 | 0.002 | `advect.md` |

## Why motion and trend can't help: the ceiling

The live line was given the actual GOES cloud at the `07_sunset` capture (`goes_fan`), as if the cloud
position at sunset were known perfectly:

| horizon | gain in AUC top-25% from the true sunset cloud |
|---|---|
| 2 h | +0.021 |
| 1 h | +0.009 |
| 45 min | +0.003 |
| 30 min | +0.004 |
| 15 min | +0.001 |
| 5 min | +0.003 |

Cloud toward the sun 2 h out already tracks the cloud at sunset at rho 0.92 (0.96 at 1 h), so any method
that predicts where the cloud will be is capped at about +0.02 at 2 h and close to nothing later. The
projection in `advect.py` does work (it beats persistence and the reversed wind in 12 of 12 checks); there
is just little left to gain. GOES derived motion winds (`ABI-L2-DMWC`) have vectors near Burlington at
every time sampled (median 60 within 300 km, as few as 10) but were not built on, for the same reason.

## Why thickness can't go live as is

The optical-depth product switches from its day algorithm to its night one when the sun is 8 degrees up,
which falls between the 1 h and 30 min shots. From 30 min on, clear pixels have no value, nothing reads
20 or more, and "thin" just means "cloudy", so the same field measures different things at different
shots. Only the 2 h and 1 h shots measure thickness as intended, and there it adds nothing over the live
inputs.

## What this points to

The skill still missing is not where the cloud is or how thick the satellite thinks it is. More labelled
days (My ranking) and better banger calls are the open levers; see the notes in the session of 2026-11-14.
