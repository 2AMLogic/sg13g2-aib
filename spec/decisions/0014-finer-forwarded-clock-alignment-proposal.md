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
| `2AMLogic/sg13g2-dll`, main | `e1a0747` | `spec/` holds a stub README and, relevant to this question, the consumer-requirements record `spec/decisions/0002-consumer-requirements-aib.md`, status *proposed*; the tree also holds `spec/decisions/0003-sim-harness-reuse.md`, not used here |
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

## Sampling-margin budget re-derived (T-20)

The chain in [target-spec.md](../target-spec.md) §Timing budget, in ps at 1 Gb/s:
400 (far-end eye) − 150 (capture aperture, T-19) − 30 (data-to-clock skew, T-16) −
62.5 (placement, T-21) − 50 (clock-path jitter, T-21) = **107.5 ps = 0.1075 UI**. Only
the placement line depends on the step count; the other four are the same for 16 and
32 positions. So for a candidate with placement error *p* (ps) and the other lines
unchanged, margin = 170 − *p* ps, and T-20 (≥ 100 ps) holds for *p* ≤ 70 ps. T-21's
own bound (62.5 ps) is 7.5 ps tighter than T-20 needs; the slack is in the budget, not
in T-21.

| Candidate | Placement *p* = half step + spacing | Margin = 170 − *p* | Against T-20 (≥ 100 ps) |
|---|---|---|---|
| 16 positions, zero spacing error (T-21 as written) | 62.5 ps | 107.5 ps (0.1075 UI) | inside by 7.5 ps |
| 16 positions, sibling 2 % (40 ps) | 102.5 ps | 67.5 ps (0.0675 UI) | under by 32.5 ps |
| 32 positions, zero spacing, zero residual | 31.25 ps | 138.75 ps (0.13875 UI) | inside by 38.75 ps |
| 32 positions, sibling 1 % (20 ps) | 51.25 ps | 118.75 ps (0.11875 UI) | inside by 18.75 ps |
| 32 positions, sibling 2 % (40 ps) | 71.25 ps | 98.75 ps (0.09875 UI) | **under by 1.25 ps** |
| 32 positions, sibling 5 % (100 ps) | 131.25 ps | 38.75 ps (0.03875 UI) | under by 61.25 ps |

Two readings follow, both from the table and neither a result:

- With the sibling's 2 % spacing target at 32 positions the margin is about 0.099 UI,
  just under the T-20 target of 0.10 UI, and the calibration residual (open
  definition 2) would come on top of it. 32 positions with a 2 % spacing error does
  **not** close T-20 by itself. T-20 alone allows spacing error plus calibration
  residual up to 38.75 ps; T-21's placement bound allows 31.25 ps. The 2 % figure
  (40 ps) is over both.
- The jitter line is 0.050 UI for **all** contributors in the clock path (forwarded
  clock, buffers, DLL), of which T-21 gives the DLL 0.030 UI (30 ps). The sibling's
  2 ps rms × 14 = 28 ps fits that 30 ps with 2 ps to spare (definition caveat in open
  definition 3). The other 0.020 UI (20 ps) is not split among contributors by any
  row; it is not re-derived here and is an unknown. Any excess over 50 ps in total
  moves the margin one for one, and the 7.5 ps of T-20 slack at 16 zero-error
  positions is the only buffer; a 32-position line with a small spacing error has more.

Lines unchanged by the candidate: far-end eye, capture aperture, data-to-clock skew.
Lines that move: placement (the step and spacing terms, plus a calibration residual
if one is counted), and jitter if a longer or interpolated chain adds to it.

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
4. **Calibration versus lock, and corner coverage.** The sibling's row 5 (static
   phase error) is not a requirement here (D-12) because alignment is found by
   sweeping. Two further comparisons:
   - *Lock time.* The sibling's row 7 target is ≤ 1 µs from enable (fallback ≤ 5 µs),
     graded from its worst false-lock start state; T-21 allows ≤ 10 µs. The sibling's
     number is inside T-21 by 10× at the target and 2× at its fallback, for an 8-tap
     line. T-21 does not define "locked"; the sibling's predicate (1 % of T over 64
     cycles and a 5 mV control-voltage window) is its own. Lock time for a 32-tap or
     interpolated line is not argued by either side: unknown.
   - *Corner coverage.* The sibling grades spacing (row 4, post-layout), static
     error (row 5) and lock time (row 7) over its 45 corners (5 MOS × 3 supply ×
     3 temperature, on a 3.3 V rail), but jitter (row 6) at **3** corners only
     (tt/3.3 V/27 °C, ss/2.97 V/125 °C, ff/3.63 V/−40 °C). T-21 is PVT-FULL, 45
     points of this repo's 1.2 V product (DR-0012), for every sub-limit including
     jitter. The two 45-point sets differ in rail, so even the matching counts do not
     cover the same conditions; the jitter gap is 42 points; the 3.3 V/1.2 V
     interface (Gaps) decides which set applies. Open.

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
- **Validation.** (Plan: "Bounded validation plan" above.) No simulation of any candidate exists. The sibling states that an
  `hv` delay cell reaching 1 GHz is unsimulated (PR #8 DR-001, "Unverified risk"),
  and matched post-layout extraction of tap spacing is unverified. The consumer
  rows T-19/T-21 would need `SIM-MC` that is not yet scoped.
- **Duty-cycle correction (G3)** remains conditional on T-17 and is not touched.

## Bounded validation plan (future work; nothing here is authorized or run)

Ordered, each step gated on the one before. Sizes are counts, or **unknown** where no
basis exists; none is a quote.

1. **Analysis only, no simulator.** Extend the table above into a
   worksheet: per-position placement error from the sibling's recorded spacing
   figures (once PR #8 or its successor records per-position data), a stated
   calibration residual, and the jitter split. Cost: hand or spreadsheet work, no
   corners. Output: the largest spacing error plus residual that holds T-20, with
   the 38.75 ps and 31.25 ps limits above as the check. Unknown: per-position data
   does not exist yet.
2. **Definitions reconciled in text** (open definitions 1–4): spacing versus
   placement, residual, one jitter estimator, lock predicate. Cost: a sibling
   exchange per `2am/REUSE.md`; no simulation.
3. **Single-corner behavioural check** (one `klt sim` unit, local): the 16- and
   32-position placement-error arithmetic against a behavioural delay line with
   injected spacing error, tt/1.2 V/27 °C. Size: two position counts × a handful of
   injected-error values, a few runs. Does not test a circuit.
4. **Corner sweep of the sibling's cell, if one exists**: spacing and jitter over
   the 45-point set of DR-0012 for the interface option chosen. Size: 45 corners ×
   positions (16 or 32) for spacing (a `klt sim` corner request, batch backend);
   jitter by transient noise is the expensive part and its cost per corner is
   **unknown** (the sibling limited itself to 3 corners because of it).
5. **Monte Carlo of spacing** for the statistical T-19/T-21 reading (DR-0013):
   sample count and runtime **unknown**; `SIM-MC` is not yet scoped here.
6. **Post-layout extracted re-run** of steps 4 and 5: only after layout exists in
   the sibling; layout size and extraction cost **unknown**.

Steps 3 to 6 need their own authorization. Steps 1 and 2 are analysis and
correspondence only, but this record still does not start them.

## Decision

Proposed, for independent ratification: **keep T-20 and T-21 unchanged and carry
the 32-position bound only as a reference comparison** (what a finer alignment would
have to meet, not a requirement and not a topology). T-21 (16 steps) and D-4 are
unchanged until a human ratifies a change through DR-0001; nothing here adopts 32
positions as the working requirement. Until a candidate meets the bound in a simulation at PVT-FULL, the
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
