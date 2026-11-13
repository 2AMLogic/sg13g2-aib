# DLL interface: what forwarded-clock alignment needs

This repo has no `consumes:` edge. It **specifies** what the receive side needs
from a clock-alignment block and compares that against the SG13G2 DLL canary; it
does not design a DLL or a duty-cycle corrector (scope discipline, CLAUDE.md;
`2am/REUSE.md`). Decision: [DR-0011](decisions/0011-dll-interface-and-consumes-proposal.md).

**What was compared, and to what depth.** The canary is
`2AMLogic/sg13g2-dll` at commit **`da166a6`** (main HEAD on 2026-10-17). At that
commit its `spec/` holds only a README stub and its draft target table lives in
the repo README, marked DRAFT and pre-spec. So the comparison below is
*draft against draft*: the "canary" column quotes that README table, nothing in
the canary has been simulated, and whether its output phases give the resolution
needed here was **not traced** beyond what the README says. Re-compare against the
canary's ratified spec when one exists (record the commit then).

**A newer comparison exists.** The canary's table has since moved into its own
`spec/target-spec.md`, and the re-comparison against it is
[below](#re-comparison-2026-11-13-381d989), pinned at `381d989`. The `da166a6`
table in the next section is kept as history and is **superseded** where the two
disagree — including two of its Fit verdicts, which were read from the wrong
column.

## Why AIB says this exists

AIB 1.2 treats both blocks as optional adapter features whose absence does not
remove the calibration step:

- Duty-cycle correction on the transmit clock, "if necessary for meeting the
  clock duty-cycle specification under all conditions of voltage and
  temperature": §2.1.6.6, Figure 24.
- A DLL for phase selection on the received forwarded clock, "if necessary to
  ensure correct data sampling under all conditions of voltage and temperature":
  §2.1.6.7, Figure 25.
- Calibration runs as if both were present: §3.2.3, §3.2.3.3.

This spec needs the receive-side phase placement (T-21), and needs correction on
the transmit side only if T-17 (±3 % DCD for DDR, AIB 1.2 §2.1.6.5 Table 8) cannot
be met by the TX clock path itself.

## Requirement table, with the `da166a6` comparison (2026-10-17)

**History.** The "Fit" column below is the 2026-10-17 reading against the canary's
README draft. It is retained unedited; the current reading is the
[2026-11-13 re-comparison](#re-comparison-2026-11-13-381d989), which corrects the
column alignment (D-4 and D-7 change verdict) and restates G1–G5.

Rate points: target = 1 Gb/s DDR (clock 500 MHz), fallback = 500 Mb/s (250 MHz),
stretch = 2 Gb/s (1 GHz). UI at the target is 1000 ps (T-01).

| # | Parameter | Requirement: target | fallback | stretch | AIB 1.2 basis | `sg13g2-dll` @ `da166a6` (README draft) | Fit |
|---|---|---|---|---|---|---|---|
| D-1 | Clock frequency the block locks at | 500 MHz | 250 MHz | 1 GHz | §1.3.1.2 Table 2 (rate floors only) | input clock **1 GHz** / 500 MHz / 2 GHz | **Gap G1**: our target (500 MHz) is the canary's *fallback* point; our fallback (250 MHz) is below any canary point; the canary's target matches only our *stretch* |
| D-2 | Lock range around that frequency | ±20 % | ±10 % | ±40 % | not defined by AIB 1.2 (spread covers rate sweeps in characterization) | ±20 % around the *1 GHz* target; ±10 % at the 500 MHz fallback; ±40 % stretch | part of **G1**: ±20 % around 1 GHz is 800 MHz–1.2 GHz and excludes 500 MHz; only the canary's fallback (±10 %) lies on our target frequency |
| D-3 | Phase placement range | ≥ one forwarded-clock period (2 ns at 500 MHz; 4 ns at 250 MHz) | same | same | §2.1.6.7 (phase selection); range not defined by AIB 1.2 | a delay line locked to one period (README description) | Fits by construction when locked at our frequency; **not stated as a requirement** in the canary |
| D-4 | Phase resolution (step) | ≤ 1/8 UI = T/16: **16 steps per clock period** | ≤ 1/4 UI: 8 steps | ≤ 1/16 UI: 32 steps | not defined by AIB 1.2; derived (target-spec timing budget) | output phases **8** / 4 / 16 evenly spaced over one period | **Gap G2**: our target needs the canary's *stretch* count; the canary's target (8) meets only our fallback |
| D-5 | Phase-spacing error (counted inside the placement error ≤ 0.0625 UI) | with a 16-step line: ≤ 0.0625 UI total including half a step, i.e. the spacing error must be ≈ 0 | placement ≤ 0.125 UI | — | derived | ≤ 2 % of the period / ≤ 5 % / ≤ 1 % | **Gap G2** (continued): 2 % of a 2 ns period is 40 ps = 0.04 UI; with half a step (0.0625 UI) the placement error is about 0.10 UI, not 0.0625. The budget margin falls from 0.1075 UI to about 0.07 UI: above the T-20 *fallback* (0.05 UI), below its target (0.10 UI). A draft-versus-draft finding, not a simulation result |
| D-6 | Lock time from enable | ≤ 10 µs | ≤ 50 µs | — | not defined by AIB 1.2; calibration runs once at link bring-up and is not on the data path (§3.2.3) | ≤ 1 µs / ≤ 5 µs | **Fits** with margin |
| D-7 | Added jitter (DLL contribution) | ≤ 0.03 UI peak-to-peak, about 2.1 ps rms at 1 Gb/s (14 σ) | ≤ 0.05 UI p-p (about 3.5 ps rms) | ≤ 0.03 UI at 500 ps UI: about 1.1 ps rms | AIB 1.2 §4.1 requires the chiplet's jitter to include all contributors; the split is derived (timing budget) | rms, simulated: ≤ 2 ps / ≤ 5 ps / ≤ 1 ps | **Fits at the target, barely**: the canary's 2 ps rms is inside our 2.1 ps rms; confirm the two use the same jitter definition (bandwidth, rms vs 14 σ). The canary's fallback (5 ps rms ≈ 0.07 UI p-p) exceeds ours |
| D-8 | False lock | none from any start state | same | — | not defined by AIB 1.2 (a false-locked sampling clock breaks capture) | none from any start state at any corner | **Fits** |
| D-9 | Duty-cycle correction (transmit clock), only if T-17 needs it | corrects input DCD of ±10 % to ±3 % at the output | ±5 % to ±3 % | ±15 % to ±3 % | §2.1.6.5 Table 8 (output limit ±3 % DDR); the ±10 % input is the AIB receive-domain-clock figure used as an upstream-quality proxy; DCC itself is optional (§2.1.6.6) | **not in scope** of the canary (its README scope: delay line, phase detector, charge pump, filter, start-up, taps) | **Gap G3**, conditional: needed only if the TX clock path alone cannot hold T-17 in simulation; to be decided before layout |
| D-10 | Rail and devices | VDDIO 1.2 V ±10 % (1.08–1.32 V), thin-oxide devices, −40…+125 °C | same | same | target-spec PVT-FULL | "device flavor and rail to ratify" | **Open (G4)**: the canary has not chosen; our requirement is stated so it can |
| D-11 | Interface | input: the received forwarded clock after clk/clkb to single-ended conversion; output: phase taps (not a selected clock), selection by a digital code in this repo; no on-die lock indicator is *required* by this repo's rows, one is desirable for calibration (§3.2.3.3) | | | §2.1.3.2, §2.1.6.3, Figure 25 | taps and buffers are in canary scope; a lock indicator is not listed | **Gap G5**, minor: lock-status output is not in the canary's README scope |
| D-12 | Static phase error (output vs input) | not required: alignment is relative and found by sweeping the placement (calibration) | — | — | §3.2.3.3 | ≤ 2 % / 5 % / 1 % of period | not a requirement here; no conflict |

## Re-comparison 2026-11-13: `381d989`

The canary is `2AMLogic/sg13g2-dll` at commit **`381d989`** (main HEAD on
2026-11-13T09:39:25Z). The trigger below fired: the sibling's draft table moved
out of its README into `spec/target-spec.md`. This section is the re-comparison.
It **adds** to the `da166a6` comparison above, which stays as history; where the
two disagree, this section is the current reading and the one above is
superseded.

**This section produces no simulation.** T-21's `SIM` half — simulated evidence of
this interface contract — remains a **declared gap** after it, and nothing here
closes, relaxes or marks T-21 covered. What is delivered is T-21's other half,
"compared against the sibling", pinned.

### Pinned sources

| Source | Pin | State at the pin |
|---|---|---|
| This repo, `main` | `70b7d23` | T-20, T-21 ratified; DR-0014 *proposed*; `sim/clock-path/` **not in the tree** |
| `2AMLogic/sg13g2-dll`, `main` | `381d989` (2026-11-13T09:39:25Z) | `spec/target-spec.md` present, status **"proposed — ratification candidate"**; ratification issue `sg13g2-dll#41` **open** |
| `2AMLogic/sg13g2-dll`, `spec/decisions/0002-consumer-requirements-aib.md` | same pin | this repo's G1–G5, with dispositions |
| `2AMLogic/sg13g2-dll`, `spec/decisions/0007-rail-1p2v-thin-oxide.md` | same pin | rail ruling (operator, 2026-10-20) and the G1 / G2 / G4 / G5 calls |
| `2AMLogic/sg13g2-dll`, `sim/bench-rows.json`, `sim/corners.json` | same pin | `"dut": "standin"`; corner set status `proposed-pending-human-merge` |

**Every sibling number below is a *proposed* number.** The sibling's spec is a
ratification candidate, its corner set is "proposed-pending-human-merge", and
`sg13g2-dll#41` is open. Re-read both pins before relying on any row.

### Which sibling column applies (the correction this re-comparison makes)

The sibling's columns are keyed to **its own** `f0`: 1 GHz target, 500 MHz
fallback, 2 GHz stretch (its row 1). This repo's rate points are keyed to its own:
1 Gb/s DDR target is a **500 MHz** forwarded clock, 500 Mb/s fallback is 250 MHz,
2 Gb/s stretch is 1 GHz (T-01). The two sets do not line up column-to-column:

| This repo's point | Forwarded clock | Sibling column at that frequency |
|---|---|---|
| **target** (1 Gb/s) | 500 MHz | the sibling's **fallback** column |
| **fallback** (500 Mb/s) | 250 MHz | **no sibling column** — below its lowest point |
| **stretch** (2 Gb/s) | 1 GHz | the sibling's **target** column |

The `da166a6` table above quoted the sibling's **target**-column numbers next to
this repo's target. That was the wrong column: at 500 MHz the applicable numbers
are the sibling's fallback column, which is looser on every row. Two verdicts
above change as a result — D-4 (step) and D-7 (jitter), noted per row below.

### The five T-21 numbers

Everything in UI of this repo's 1 Gb/s target: 1 UI = 1000 ps, forwarded-clock
period T = 2000 ps. "Sibling" = the **fallback** column of `spec/target-spec.md`
@ `381d989` unless a row says otherwise.

| T-21 number | This repo's target | Sibling value, and the column it is quoted from | Status there | Verdict |
|---|---|---|---|---|
| **Step** (phase resolution) | ≤ 1/8 UI = 125 ps, i.e. T/16 — 16 steps per clock period | **4 phases even over T** (row 3, fallback, 500 MHz) → step T/4 = **500 ps = 0.50 UI** | proposed; row 3 is graded "n/a (structural)" and is **specified only** — `sim/phase/` holds no recorded result at this pin | **Gap (G2), 4× too coarse.** Supersedes the `da166a6` reading of "8 at target": 8 is the sibling's *target*-column count at 1 GHz, which is this repo's *stretch* frequency |
| **Worst-case placement error** (half a step plus spacing error) | ≤ 0.0625 UI = 62.5 ps | half a step = **0.25 UI**, plus systematic phase-spacing error ≤ 5 % T = 100 ps = **0.10 UI** (row 4, fallback). Random mismatch: row 4 states Monte Carlo is "a separate recorded result with **no limit**" and that "a consumer must budget random mismatch separately" | proposed; specified only | **Not derivable as a worst case** — the random term is unbounded in the sibling's spec, so no worst-case total exists. The *derivable* part alone is ≥ 0.35 UI against a 0.0625 UI budget: **Gap** |
| **Range** | ≥ one forwarded-clock period (2 ns at 500 MHz) | the "Locked" predicate pins the last tap (tap N) at a delay of **exactly 1 × T**, and the 4 taps span that period; lock range **±20 % around 500 MHz** = 400–600 MHz (row 2, fallback, per 0002 G1 accepted in 0007) | proposed; specified only | **Fits**, with one note: "one period" is held only to the column's lock tolerance, **±5 % of T** at the fallback column (±2 % at target). A strict "≥ one period" reading is met inside that tolerance, not absolutely |
| **Lock time** | ≤ 10 µs from enable | **≤ 5 µs** (row 7, fallback) | proposed; specified only — `sim/lock-time/` holds no recorded result at this pin | **Fits** with 2× margin |
| **DLL-added jitter** | ≤ 0.03 UI peak-to-peak = 30 ps (≈ 2.1 ps rms at 14 σ) | **≤ 5 ps rms, simulated** (row 6, fallback) → 70 ps p-p = **0.07 UI** at the same 14 σ conversion | proposed, and **no number exists yet**: `sim/bench-rows.json` marks row 6 `status: blocked`, "blocked_on: noise-method decision record" | **Gap, 2.3× over.** Supersedes the `da166a6` reading "Fits at the target, barely": the ≤ 2 ps rms that fitted is the sibling's *target*-column limit at 1 GHz, not the limit at 500 MHz |

### Definition mismatches, stated rather than converted away

- **rms versus peak-to-peak.** The sibling's row 6 limit is an **rms** figure; T-21
  and the timing budget are **peak-to-peak**. The 14 σ Gaussian conversion used
  above is this repo's (`target-spec.md` § Timing budget, which states the jitter
  allocation is peak-to-peak at 14 σ; DR-0013 for the statistical rows that use the
  same tail) and is the one the sibling's 0002 proposed sharing. DR-0019 would
  ratify that definition for the T-13/T-14 skew rows, but it is **not on `main`** —
  it is in open PR #168 — so it is named here as a pending claim, not cited as
  evidence. It is an assumption about the distribution, not an
  identity: a jitter distribution with a non-Gaussian tail breaks it in the
  unsafe direction. The sibling's own jitter method section says the figure is
  "simulated added jitter, thermal-noise class", underestimates 1/f, and does not
  capture supply noise unless injected — so even the rms number is not the whole
  peak-to-peak contributor T-21 budgets.
- **Corner coverage.** The sibling's corner set (`sim/corners.json`: 5 MOS × 3
  supply × 3 temperature = 45, at −40/27/125 °C and 1.08/1.20/1.32 V) is the
  **same grid** as this repo's PVT-FULL, so a sibling row graded "all 45" carries
  PVT-FULL coverage. **Row 6 does not**: it is graded at 3 corners only
  (tt/1.20 V/27 °C, ss/1.08 V/125 °C, ff/1.32 V/−40 °C), because ngspice
  transient noise is expensive. T-21 asks for PVT-FULL. A 3-corner jitter number
  is not a PVT-FULL result and must not be read as one.
- **Systematic-only spacing versus worst-case placement.** Row 4 bounds the
  **systematic** (corner, end-cell, load) spacing error and explicitly carries
  **no limit** on the Monte Carlo result. T-21's placement error is a worst case
  over everything. The two are not the same quantity and cannot be compared
  without the consumer-side mismatch budget the sibling's row 4 asks for — which
  this repo has not allocated (it is the question DR-0014 and #9 hold open).
  For scale, and as a non-spec reading: the sibling's `sim/delay-sizing`
  Monte Carlo probe (`20261107T224325Z-mc/`, ss/1.08 V/125 °C, 1 GHz, n = 32,
  mismatch-only, ideal bias, no extraction) reports a per-tap step σ of 8.2–15.1 ps
  (candidate A) and 12.5–16.9 ps (candidate B) against a ~125 ps nominal step. That
  is a delay-cell sizing probe on an open loop, **not** a spec-row result and not a
  layout-matching result; it is quoted only to show the random term is the same
  order as the whole 62.5 ps placement budget, not to fill the row.
- **Nothing is simulated yet.** `sim/bench-rows.json` @ `381d989` records
  `"dut": "standin"` for every row, and no `results/` or `records/` directory
  exists under `sim/phase`, `sim/lock-time`, `sim/false-lock`, `sim/jitter` or
  `sim/power`. The sibling's recorded results at this pin (`cp-currents`,
  `delay-sanity`, `delay-sizing`, `harness-example`, `pfd-fit`,
  `lock-detector-smoke`, `supervisor-smoke`, `pdk-smoke`) are device- and
  block-level probes or harness examples, not graded spec rows. **Every row
  above is therefore "specified only", at no corners.**

### This repo's other two rate points

- **Fallback (500 Mb/s, 250 MHz clock): not derivable.** The sibling has no
  250 MHz point and 0002 declined one (its G1 disposition accepts 500 MHz ±20 %
  and declines a single range spanning 500 MHz and 1 GHz as a 2:1 span). Every
  fallback-rate number in T-21 is therefore unanswered by the sibling at this
  pin — not a fit, and not a gap against a stated value, but **no counterpart**.
- **Stretch (2 Gb/s, 1 GHz clock)**: the sibling's target column applies — 8
  phases, T/8 = 125 ps = 0.25 UI against a T-21 stretch step of ≤ 1/16 UI
  = 31.25 ps. A gap, recorded for completeness only: the stretch must not drive
  the architecture (CLAUDE.md, DR-0002).

### Sibling rows with no counterpart here

Listed so they are not mistaken for fits:

| Sibling row | Value | Here |
|---|---|---|
| row 5, static phase error | ≤ 2 % T / 5 % / 1 % | **Not a requirement here** (D-12): alignment is relative and found by sweeping the placement during calibration |
| row 10, power | ≤ 5 mW / 10 mW / 2 mW | **Not a requirement here**: this repo budgets the alignment block's power nowhere, because it does not instantiate one |
| row 11, signoff | DRC + LVS clean, post-layout re-verified | **Not a requirement on this interface**: this repo's signoff rows cover its own blocks |
| row 12 grading, 20 fF tap load | every tap drives 20 fF to VSS | **Noted, not required**: 0007 decision 7 chose 20 fF partly by reading D-11. If this repo ever states a tap load, it replaces 20 fF only through a new sibling record |

### Consequence for the budget (arithmetic, not a change)

Substituting the fallback-column numbers into the T-20 timing-budget allocation
(`target-spec.md` § Timing budget) does two things. The 0.0625 UI placement line
becomes ≥ 0.35 UI, costing ≥ 0.2875 UI. The DLL's share of the 0.050 UI clock-path
jitter line goes from 0.03 UI to 0.07 UI — `target-spec.md` § Timing budget gives
the DLL 0.03 of that 0.050, so the forwarded clock's own 0.02 UI share stays and is
**not** absorbed — costing a further 0.04 UI. Together that is about **0.33 UI
removed from a 0.1075 UI margin**, i.e. a negative margin of roughly −0.22 UI
(linear sum). **The sibling's fallback column, as specified at `381d989`, does
not close T-20 at this repo's target.** That is hand arithmetic
from two tables, in the same spirit as DR-0014 — not a simulation, not a
feasibility claim, and **not a change to any T-row or D-row value**. The
shortfalls it names are recorded in
[DR-0020](decisions/0020-dll-recomparison-t21.md) and filed on the sibling.

## Gaps filed on the sibling, and their state

Filed on `2AMLogic/sg13g2-dll` as one issue carrying this requirement table
(consumers are the sibling's spec, `2am/REUSE.md`): **G1** lock frequency and range
centered on 500 MHz and 250 MHz; **G2** 16 evenly spaced phases per period with a
spacing error small enough for D-5; **G3** whether a duty-cycle corrector is in
scope (conditional); **G4** rail and devices, 1.2 V ±10 % thin-oxide; **G5** a
lock-status output. Filed as `2AMLogic/sg13g2-dll#10`, now **closed**.

State at `381d989` (2026-11-13), each citing the sibling record that settles it:

| Gap | State at the pin | Settled by | Effect here |
|---|---|---|---|
| **G1** lock frequency and range | **Partly accepted; 500 MHz half closed, 250 MHz half unresolved.** The 500 MHz point carries ±20 % (400–600 MHz) and row 2's fallback column changed from ±10 % to ±20 %. A single continuous range spanning 500 MHz and 1 GHz is **declined** (a 2:1 span needs a range-select and its own false-lock argument). No 250 MHz point was added or proposed | `0002` G1 row; `0007` decision 3 | D-1 and D-2 **fit at this repo's target** (500 MHz ±20 %), via the sibling's *fallback* column. This repo's own **fallback rate point (250 MHz) has no sibling counterpart** and is re-filed |
| **G2** 16 phases per period | **Declined at target.** 8 phases at its target and 16 at its stretch are kept; the 16-at-target ask "is met only by the stretch column". The record adds that this repo's DR-0014 shows 16 steps does not close this repo's budget either, "so the next move is theirs" | `0002` G2 row; `0007` decision 4 | **Open and wider than recorded in the `da166a6` table.** At this repo's target the applicable column is the sibling's fallback — **4** phases, step 0.50 UI — not the 8 previously quoted. Re-filed with the column correction. The "next move is theirs" point is this repo's to answer and belongs to #9 and DR-0014, not here |
| **G3** duty-cycle correction | **Declined (out of scope).** "A corrector is a separate block"; the sibling's README Scope now names duty-cycle correction of the input clock as not in scope, and the record says "revisit only if the consumer's simulation shows it is needed" | `0002` G3 row and § "G3 — duty-cycle correction"; sibling `README.md` § Scope | D-9 stays **conditional and unanswered**. Whether this repo needs a corrector turns on whether its own TX clock path holds T-17 — and **that evidence is pending #54**: `sim/clock-path/` is not in this repo's `main` at `70b7d23` (PR #178 open). Until #54 lands, D-9 / G3 is *pending*, not "not triggered" |
| **G4** rail and devices | **Accepted.** 1.2 V thin-oxide (`sg13_lv_nmos` / `sg13_lv_pmos`) throughout, nominal 1.20 V, ±10 % (1.08–1.32 V), no SiGe HBT; spec row 9 | `0007` decisions 1 and 5 (operator ruling 2026-10-20) | **D-10 fits.** The sibling's corner set (`sim/corners.json`: 5 MOS × 3 supply × 3 temperature = 45, −40/27/125 °C) is the same grid as this repo's PVT-FULL. Closed |
| **G5** lock-status output | **Accepted.** Added as spec row 12 and an interface item, with a ±128-input-cycle lag definition in both directions, graded in every row-8 run | `0002` G5 row; `0007` decision 6 | **D-11 fits**, and better than D-11 asked for (D-11 called a lock indicator desirable, not required). Closed |

Re-filed at this pin as `2AMLogic/sg13g2-dll#72`: the 250 MHz half of G1, the
column-corrected G2 (4 phases at 500 MHz, not 8), the unbounded random-mismatch
term that makes the placement error not derivable, and the fallback-column jitter
limit. Recorded here as [DR-0020](decisions/0020-dll-recomparison-t21.md).
**No requirement in this file was relaxed to produce a fit.**

## `consumes:` edge: proposal only

Proposed, **not made**: a `consumes` edge from `2AMLogic/sg13g2-aib` to
`2AMLogic/sg13g2-dll` for forwarded-clock alignment, with a pinned
`reuse.lock.json` entry, **once G1 and G2 close in the sibling's ratified spec**.
Today the target rows do not fit (G1, G2), so adopting it would record a
dependency this repo's own timing budget cannot yet close on. Editing the
manifest (`repos.yml`) or `reuse.lock.json` is an operator decision and is out
of this issue's scope. Until then the alignment block is a contract in this
file, and RTL and testbenches treat it as an ideal block that meets D-1…D-8 so
the interface is exercised before any silicon is chosen.

## Re-comparison trigger

Re-compare, and add a new dated section to this file, when: the sibling
ratifies its spec; the sibling's table changes; or this repo changes any
of T-01, T-16, T-17, T-19, T-20, T-21.

| Fired | Trigger | Section |
|---|---|---|
| 2026-10-17 | first comparison | the `da166a6` table above |
| 2026-11-13 | the sibling's draft table moved into `spec/target-spec.md` and `0007` ruled on G1, G2, G4, G5 | the `381d989` re-comparison above |

**Next expected trigger**: the sibling merging `sg13g2-dll#41` (ratification),
which turns every proposed number above into a ratified one, or a disposition on
`sg13g2-dll#72`.
