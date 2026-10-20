# DR-0014: finer forwarded-clock alignment (proposal)

**Status**: **proposed**. Not ratified; ratification follows the process in
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge. **Rows**:
T-20, T-21, D-4, D-5 are *named*, none is changed. This record is documentation only.

## Context

T-21 asks for a step of at most 1/8 UI (16 steps per forwarded-clock period) and a
worst-case placement error of at most 0.0625 UI (half a step plus phase-spacing
error). Half of a 1/8 UI step is already 0.0625 UI, so the row passes only with
**zero** spacing error ([dll-interface.md](../dll-interface.md) D-5). The sibling
DLL canary's draft does not give zero spacing error. The ruling on #9 keeps the
timing target and asks for a finer-alignment proposal to be compared, not decided.

This record compares candidates against the unchanged T-20 / T-21 and names what
is unknown. **It is budget arithmetic, not feasibility evidence, and it selects no
topology.** All figures below are hand arithmetic from tables; nothing here is
simulated.

## Pinned sources

| Source | Pin | State at the pin |
|---|---|---|
| This repo, ratified baseline | `7a0f57e` (merge of PR #8) | T-20, T-21, DR-0006, DR-0011 accepted |
| `2AMLogic/sg13g2-dll`, main | `e1a0747` | `spec/` holds only a stub README and the consumer-requirements record `spec/decisions/0002-consumer-requirements-aib.md`, status *proposed* |
| `2AMLogic/sg13g2-dll`, PR #8 | head `f947de6`, open | proposes `spec/target-spec.md` and DR-001..004; ratification is the sibling's human merge and is **independent of, and unchanged by,** this record |

PR #8 at `f947de6` is a proposal, so every sibling number below is a *proposed*
number. Re-read both pins before relying on any row; this record's figures go stale
when either moves.

## Arithmetic (target: 1 Gb/s DDR, clock 500 MHz, UI = 1000 ps, clock period 2000 ps)

Placement error is taken **as T-21 defines it**: half a step plus phase-spacing error.

| Positions per clock period | Nominal step | Half step | Left of the 62.5 ps allocation for spacing error (and anything else) |
|---|---|---|---|
| 8 | 250 ps (1/4 UI) | 125 ps | none: half a step alone exceeds 62.5 ps (this is T-21's *fallback* grade) |
| 16 (T-21 today) | 125 ps (1/8 UI) | 62.5 ps | **0 ps** |
| 32 (uniform) | 62.5 ps (1/16 UI) | 31.25 ps | **31.25 ps** = 0.03125 UI = 1.5625 % of the period |

32 positions is the existing stretch-column step of T-21 (≤ 1/16 UI) and D-4, pulled
forward to the target rate; the stretch column itself is untouched. The 31.25 ps
is the whole remainder: it must hold the spacing error **and** any calibration
residual (below). Doubling the count does not by itself meet the budget; it only
makes a non-zero spacing error possible.

Against the sibling's proposed spacing figures, taken as a percentage of a 2000 ps
period and added to a 31.25 ps half step:

| Sibling spacing error (percent of period) | In ps at 2000 ps | Placement error at 32 positions | Against 62.5 ps |
|---|---|---|---|
| 2 % (PR #8 target column) | 40 ps | 71.25 ps | **over** by 8.75 ps |
| 1 % (PR #8 stretch column) | 20 ps | 51.25 ps | inside, 11.25 ps left |
| 5 % (PR #8 fallback column) | 100 ps | 131.25 ps | over |

At 16 positions any non-zero spacing error is over. This is a draft-against-proposal
reading, with the caveats in the next section; it says what would have to be true,
not that it is.

## Open definitions (must be reconciled before any fit is claimed)

1. **Adjacent-step spacing versus absolute phase placement.** The sibling's row 4
   bounds each *adjacent-tap spacing* against T/8 (so a DNL-style figure for an
   8-tap line); its row 5 bounds the *static* error of the last tap against one
   period. T-21 bounds the *placement* error of the selected position against the
   ideal sampling instant. Three different quantities:
   - If calibration (AIB 1.2 §3.2.3.3) sweeps the positions and picks the best one,
     the worst case is set by the *largest adjacent gap*: half of it is an
     alternative reading of "half a step plus spacing error" that would loosen the
     spacing budget (a spacing error up to one full step would then fit). T-21 as
     ratified adds the full spacing error to half the step; this record keeps that
     reading and records the alternative as a question for a future record, not as
     an adopted relaxation.
   - Accumulated (INL-like) phase error across positions matters if the code is
     held while temperature or supply drifts after calibration, or if monotonicity
     is not guaranteed. T-21 does not say.
   - The sibling's spacing row is a mean over 64 cycles of a *locked, ideal-input*
     run; its Monte Carlo spacing is "a separate recorded result", not graded. T-21
     is a PVT-FULL row, and T-19/T-13..T-16 are statistical (DR-0013). Whether
     spacing mismatch is a corner effect or a tail (14 σ) quantity is undecided.
2. **Calibration residual.** The 31.25 ps remainder has no line for the calibration
   step's own resolution (the decision granularity of the sweep that picks a
   position, and a one-code dither). T-21 and the DR-0006 allocation do not list
   one. Unknown; must be given a value or shown to be inside the spacing term.
3. **Jitter definition.** T-21 allows 0.03 UI peak-to-peak DLL-added jitter (30 ps),
   which at 14 σ is about 2.1 ps rms. The sibling proposes 2 ps rms by a
   transient-noise method with its own estimator (PR #8 "Jitter method"). 2 ps rms
   × 14 is 28 ps, inside by 2 ps. The two must be shown to use one definition
   (bandwidth, estimator, 14 σ) before the margin is claimed; the sibling's own
   record says the same (`0002`, "Jitter"). A finer step does not change this line
   but a longer or interpolated chain may add to it: unmeasured.
4. **Calibration versus lock.** The sibling's row 5 (static phase error) is not a
   requirement here (D-12) because alignment is found by sweeping.

## Candidates compared (none selected)

| | A. 16 positions (T-21 today) | B. 32 uniform taps from one delay line | C. fewer taps plus a finer interpolation stage (or equivalent), 32 effective positions | D. relax T-21 |
|---|---|---|---|---|
| Meets the T-21 numbers | only with zero spacing error | with spacing error ≤ 31.25 ps less calibration residual | same bound on the *effective* position error | not applicable |
| Taps/cells vs sibling's proposed 8 (16 stretch) | 2× (1×) | 4× (2×) cells and tap loads | 8 or 16 taps plus an added stage; the stage is outside the sibling's scope | none |
| Lock/false-lock argument | sibling's DR-003 is argued for 8 taps; 16 is argued in its stretch only | longer chain for the same period: delay-range limit and start-up state need a new argument | the lock loop is unchanged; the interpolator adds its own linearity question | none |
| New circuit class in this repo | no | no (if the sibling provides it) | yes: interpolation sits outside the DLL canary's scope, and this repo may not design a DLL | no |
| Cost | n/a | cell count, tap-load and power scale with tap count; the sibling's 5 mW is for 8 taps. **Unmeasured, no figure available** | interpolator area, power, linearity and jitter: **unmeasured** | none |
| Status | fails with any real spacing | open | open | **rejected** (below) |

D is rejected here, not weighed: agents do not relax a ratified row to make a result
pass (CLAUDE.md), and the ruling preserves T-20 and T-21.

## Gaps and named unknowns

- **Frequency and range.** T-21 needs lock around 500 MHz (±20 %: 400–600 MHz), the
  sibling's *fallback* operating point. PR #8 `f947de6` row 1/2 grades ±20 % around
  1 GHz and ±10 % around its 500 MHz fallback. Its record `0002` partly accepts
  500 MHz ±20 %, but PR #8's row does not carry it as I read it. Open (originally G1,
  `2AMLogic/sg13g2-dll#10`).
- **Rail and interface.** The sibling proposes 3.3 V thick-oxide (PR #8 DR-001); this
  repo's clock path and data interface are 1.2 V (T-01, DR-0012, D-10). A 1.2 V → 3.3 V
  conversion in and a 3.3 V → 1.2 V conversion out of the alignment block would add
  delay, duty-cycle distortion, supply sensitivity and jitter that none of T-17,
  T-21 or the DR-0006 allocation counts. **No level conversion is authorized or
  costed by this record**, and the 1.2 V option is the sibling's stated revisit
  trigger, not this repo's request. Open (G4).
- **False lock.** The sibling's three-part exclusion (PR #8 DR-003) is argued for 8
  taps. A 32-tap or interpolated line needs it restated; unreviewed here.
- **Validation.** No simulation of any candidate exists. The sibling states that an
  `hv` delay cell reaching 1 GHz is unsimulated (PR #8 DR-001, "Unverified risk"),
  and matched post-layout extraction of tap spacing is unverified. The consumer
  rows T-19/T-21 would need `SIM-MC` that is not yet scoped.
- **Duty-cycle correction (G3)** remains conditional on T-17 and is not touched.

## Decision

Proposed, for independent ratification: **keep T-20 and T-21 unchanged and adopt,
as the working requirement for the alignment contract, the 32-position
comparison above** (a reference for what a finer alignment must meet, not a
topology). Until a candidate meets the bound in a simulation at PVT-FULL, the
alignment block remains an ideal block in RTL and testbenches (dll-interface.md,
"consumes: edge") and **no fit is claimed**.

## Not authorized by this record

Numerical ratification, any change to T-20/T-21 or an accepted record,
circuit/RTL/layout work, a simulation campaign, spending, a `consumes:` edge or a
`reuse.lock.json` change, level-conversion, a DLL or interpolator design in this
repo, and any change to the sibling's PR #8. This record has not posted on the
sibling; a gap filed there (finer-than-8 positions at the 500 MHz point, one jitter
definition, spacing as a per-position figure) follows `2am/REUSE.md` once this
proposal is reviewed.

## Alternatives rejected

- **Relaxing T-21** (D above): barred.
- **Treating "32 positions" as a closed fit** because 31.25 ps remains: it is only
  budget space, with the spacing term, calibration residual and jitter definition
  all open.
- **Adopting the sibling's 3.3 V rail by implication**: it would import an
  unbudgeted level conversion into the clock path.
