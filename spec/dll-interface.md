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

## Requirement table, with comparison

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

## Gaps to file on the sibling

Filed on `2AMLogic/sg13g2-dll` as one issue carrying this requirement table
(consumers are the sibling's spec, `2am/REUSE.md`): **G1** lock frequency and range
centered on 500 MHz and 250 MHz; **G2** 16 evenly spaced phases per period with a
spacing error small enough for D-5; **G3** whether a duty-cycle corrector is in
scope (conditional); **G4** rail and devices, 1.2 V ±10 % thin-oxide; **G5** a
lock-status output. Filed as `2AMLogic/sg13g2-dll#10`.

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

Re-compare, and add a new row of commits to this file, when: the sibling
ratifies its spec; the sibling's draft table changes; or this repo changes any
of T-01, T-16, T-17, T-19, T-20, T-21.
