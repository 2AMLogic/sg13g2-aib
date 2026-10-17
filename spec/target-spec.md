# Target specification

Ratified by the merge of the pull request that closes issue #2 (see
[`README.md`](README.md) and [DR-0001](decisions/0001-spec-structure-and-ratification.md)).
Scope tags, verification codes and reference pins are defined in
[`README.md`](README.md). **No conformance claim is made.** "AIB 1.2" below is the
public AIB Gen1 revision pinned in `README.md`; a citation names the section a
number or requirement was read from. Where a row says *not defined by AIB 1.2*,
the value is this repo's own choice and the reason is given.

**1 UI** is the minimum interval between data changes on a wire (AIB 1.2 §4.1,
bullet list under Table 17). For DDR it is half a clock period: 1 Gb/s per wire
is a 500 MHz forwarded clock and a 1000 ps UI. Rows given in UI scale with the
rate; absolute values are in the "at 1 Gb/s" column.

## PVT-FULL: the corner set every recorded analog result carries

| Axis | Values | Source |
|---|---|---|
| MOS process | `mos_tt`, `mos_ss`, `mos_ff`, `mos_sf`, `mos_fs` | the corner names in PDK `libs.tech/ngspice/models/cornerMOSlv.lib` (PSP103, thin-oxide devices) |
| I/O supply (VDDIO) | 1.08 V, 1.20 V, 1.32 V (nominal 1.2 V ±10 %) | PDK-io liberty corner files `sg13g2_io_{slow_1p08V,typ_1p2V,fast_1p32V}_*`; see DR-0012 for what is and is not stated in the PDK docs |
| Temperature | −40 °C, 27 °C, 125 °C | the issue proposes −40 … +125 °C; PDK-io liberty corners are at −40, 25 and 125 °C |

**Worst-case pairs** for timing rows: slow = `mos_ss` / 1.08 V / 125 °C; fast =
`mos_ff` / 1.32 V / −40 °C. Skew-class rows also need `mos_sf` and `mos_fs`
(unmatched N/P speed moves the duty cycle and the driver edge asymmetry). A full
grid is 5 × 3 × 3 = 45 corners and goes to `klt sim` as one multi-corner
request (batch fleet; never a hand-run loop).

Rows marked **STAT** are statistical: they need `SIM-MC` (mismatch and process
Monte Carlo) because #3 item 6 depends on whether the tail meets the row. They
are reported as mean, sigma and the tail used, not as a single corner value.

## Table 1: rate, channel, signalling

| ID | Parameter | Target | Fallback | Stretch | Verification | PVT | AIB 1.2 basis | Scope |
|---|---|---|---|---|---|---|---|---|
| T-01 | Rate per wire (DDR) | 1 Gb/s (500 MHz forwarded clock; UI 1000 ps) | 500 Mb/s (250 MHz; UI 2000 ps) | 2 Gb/s (1 GHz; UI 500 ps) | `SIM`: eye at far-end RX over the channel model meets T-14 at the rate; `MEAS` (TC) later | PVT-FULL | §1.3.1.2, Table 2: AIB 1.2 sets a *minimum* operating data rate of no more than 2 Gb/s for the DDR configuration and no maximum; it does not define 1 Gb/s as a rate. The target and fallback are this repo's choice (DR-0002) | CH + TC (BOTH) |
| T-02 | Data exchange format | DDR (data on both clock edges); SDR path present as a test mode | DDR only | — | `RTL` for the format, `SIM` for the timing | PVT-FULL | §2.1.3.1–2.1.3.2, Figures 16–17 | BOTH |
| T-03 | Data wires per direction (N) | 20 TX + 20 RX (one balanced channel) | 8 + 8 (below the AIB 1.2 channel minimum; a test-vehicle size only) | 40 + 40 | `LAYOUT`, `RTL` | n/a (structural) | §1.3.4.1 Table 4: balanced channels at ≤ 55 µm bump pitch carry 20–80 data signals per direction in steps of 20 | CH (the channel) ; TC covers whatever subset the shuttle seat holds (DR-0003) |
| T-04 | Forwarded clock | one forwarded clock per direction, **quasi-differential** (clk + clkb pair, both driven and received) | single-ended clock + on-die complement at the RX | — | `RTL`, `SIM` (clk/clkb crossing at RX over PVT-FULL) | PVT-FULL | §2.1.6.3, Figures 20–21 | BOTH |
| T-05 | Spare wires and redundancy | 2 spare wires per channel; shift redundancy: a faulty wire reroutes two positions toward the spares in both chiplets | none (no spares) | — | `RTL` (mux function, all single-fault positions, 20 × 2 cases per direction), `SIM` (mux added load/delay inside T-12/T-13) | PVT-FULL for the delay; n/a for the function | §3.3.1, Figures 43–44; §3.3.1.1 neighbor-cell capability | CH for the repair claim; **TC covers the mux function only** (no assembly exists to produce an open or short; DR-0003) |
| T-06 | Signal levels | full-rail CMOS at VDDIO: VOH ≥ VDDIO − 0.1 V at DC, VOL ≤ 0.1 V (thin-oxide devices only; no 3.3 V devices in the data path) | — | reduced swing below VDDIO | `SIM` | PVT-FULL | **Deviates**: §4.1 Table 17 specifies a 0.7–0.9 V output swing; this repo signals at the full VDDIO swing (1.2 V nominal) because the reduced-swing baseline was rejected for the 1 Gb/s target (DR-0004) | BOTH |
| T-07 | Termination | none (unterminated, point-to-point) | — | — | `SIM` | PVT-FULL | §1.3.4 context; the AIB 1.2 signalling is unterminated (no termination parameter exists in Table 17) | BOTH |
| T-08 | Driver output impedance | 40 Ω to 80 Ω at VOH/VOL operating points, all PVT-FULL | 30 Ω to 120 Ω | 40–60 Ω | `SIM` (DC I–V of driver at both rails) | PVT-FULL | not defined by AIB 1.2. Chosen to source-match the 50 Ω channel (channel-model.md §Derived quantities) within ±40 % so reflections at the unterminated far end are bounded; DR-0004 | BOTH |
| T-09 | Overshoot / undershoot at the receiver pin | ≤ 0.25 × VOS peak (0.3 V at VOS = 1.2 V) and ≤ 0.4 ns above that level, both polarities | ≤ 0.35 × VOS | — | `SIM` over the channel model (CH); `SIM` over the loopbacks (TC) | PVT-FULL | §4.2 Table 18: VOA = 0.25·VOS, TOD ≤ 0.4 ns (same for under-shoot). Applied with this repo's own VOS (T-06), not AIB 1.2's | CH and TC, each in its own setup. **TC is expected to fail the CH limit** with a wire-bond loopback; that is a documented property of that configuration, not a spec relaxation (test-configuration.md) |
| T-10 | Receiver threshold | VDDIO/2 within ±60 mV (±5 % of VDDIO at 1.2 V; arithmetic) at all PVT-FULL corners **including 3σ mismatch** | ±80 mV | — | `SIM-MC` | PVT-FULL | not defined by AIB 1.2. The AIB 1.2 eye-height mask is ±90 mV around the midpoint (§4.1 Table 17, VEH); the 3σ threshold offset must lie inside the ±90 mV eye with margin (±60 mV target leaves 30 mV; ±80 mV fallback leaves 10 mV) | BOTH. **STAT** |
| T-11 | Receiver hysteresis | none by design; if added, ≤ 60 mV (below the ±90 mV VEH) | ≤ 90 mV | — | `SIM` | PVT-FULL | not defined by AIB 1.2; bound derived from VEH (§4.1 Table 17) | BOTH |

## Table 2: channel, timing, I/O cell

| ID | Parameter | Target | Fallback | Stretch | Verification | PVT | AIB 1.2 basis | Scope |
|---|---|---|---|---|---|---|---|---|
| T-12 | Channel model | **CH-3MM-RC**: 3 mm line, R = 5.5 Ω/mm, C = 0.20 pF/mm, L = 0.5 nH/mm, far-end load 0.1 pF, defined in [`channel-model.md`](channel-model.md) and `channel/channel_rc.cir` | **CH-1MM**: 1 mm (same per-mm values) | **CH-5MM**: 5 mm | `SIM` | PVT-FULL, plus channel R/C ±20 % (DR-0005) | not defined by AIB 1.2 (its Table 17 has a "Trace" column of eye width only; §1.3.2 gives no trace model) | **CH only.** No test uses it as silicon |
| T-13 | Data-to-data skew, TX output (UI at near-side output) | ≤ 0.04 UI (40 ps at 1 Gb/s) | ≤ 0.08 UI | ≤ 0.04 UI (20 ps at 2 Gb/s) | `SIM-MC` over PVT-FULL; `PEX` after layout | PVT-FULL incl. `mos_sf`, `mos_fs` | §2.1.3.3 Table 7 (tDS 0.04 UI near-side output) | BOTH. **STAT** |
| T-14 | Data-to-clock skew, TX output | ≤ 0.02 UI (20 ps at 1 Gb/s) | ≤ 0.04 UI | ≤ 0.02 UI (10 ps at 2 Gb/s) | `SIM-MC`; `PEX` | PVT-FULL incl. `mos_sf`, `mos_fs` | §2.1.3.3 Table 7 (tDCS 0.02 UI) | BOTH. **STAT** |
| T-15 | Data-to-data skew, RX input (after the channel) | ≤ 0.06 UI (60 ps at 1 Gb/s) | ≤ 0.12 UI | ≤ 0.06 UI | `SIM` over the channel model; `SIM-MC` for the array | PVT-FULL | §2.1.3.3 Table 7 (tDS 0.06 UI far-side input) | CH (the channel adds skew); the TC value is reported separately and is not the channel's. **STAT** |
| T-16 | Data-to-clock skew, RX input | ≤ 0.03 UI (30 ps at 1 Gb/s) | ≤ 0.06 UI | ≤ 0.03 UI | `SIM` over the channel model; `SIM-MC` | PVT-FULL | §2.1.3.3 Table 7 (tDCS 0.03 UI) | CH. **STAT** |
| T-17 | Forwarded-clock duty-cycle distortion at TX output | ±3 % (DDR) | ±5 % | ±3 % | `SIM` | PVT-FULL incl. `mos_sf`, `mos_fs` | §2.1.6.5 Table 8 (tFDCD: DDR ±3 %, SDR ±10 %) | BOTH |
| T-18 | Eye at the far-end RX input (width) | ≥ 0.40 UI valid window, ≥ ±90 mV eye height around VDDIO/2 | ≥ 0.30 UI | ≥ 0.40 UI | `SIM` (eye over PRBS-7 at the rate, channel model) | PVT-FULL | §4.1 Table 17 (tEW far end 0.40 UI; VEH ±90 mV). The AIB 1.2 near-end width (0.56 UI) and trace consumption (0.1 UI) are reported alongside | CH |
| T-19 | Receiver capture window (setup + hold aperture), including mismatch | ≤ 0.15 UI (150 ps at 1 Gb/s) | ≤ 0.25 UI | ≤ 0.15 UI (75 ps at 2 Gb/s) | `SIM-MC` of the RX capture flop/latch plus input stage | PVT-FULL | not defined by AIB 1.2 (it defines the eye at the pin, not the capture aperture). Allocation in §Timing budget below; DR-0006 | BOTH. **STAT** |
| T-20 | Sampling-margin budget (the DDR capture window left after all uncertainty) | ≥ 0.10 UI (100 ps at 1 Gb/s) at every PVT-FULL corner | ≥ 0.05 UI | ≥ 0.10 UI | `ANALYSIS` fed by T-16, T-19, T-21, and the DLL interface (dll-interface.md); `SIM` end-to-end confirms | PVT-FULL | not defined by AIB 1.2 (derived; §Timing budget) | CH for the claim; TC value reported separately |
| T-21 | Forwarded-clock alignment (RX sampling-clock placement) | step ≤ 1/8 UI (125 ps at 1 Gb/s, i.e. 16 steps per clock period); worst-case placement error (half a step plus phase-spacing error) ≤ 0.0625 UI; range ≥ one forwarded-clock period (2 ns at 1 Gb/s); lock ≤ 10 µs; DLL-added jitter ≤ 0.03 UI peak-to-peak | step ≤ 1/4 UI (8 steps per period); placement error ≤ 0.125 UI; jitter ≤ 0.05 UI p-p | step ≤ 1/16 UI | `SIM` of the interface contract (dll-interface.md); compared against the sibling | PVT-FULL | §2.1.6.7 (optional DLL phase selection), §3.2.3 (calibration, which an absent DLL shall still perform as if present); step, range, lock and jitter values are *not defined by AIB 1.2* (DR-0011) | BOTH |
| T-22 | I/O cell pitch | 55 µm | 80 µm | 40 µm | `LAYOUT` (`klt` bounding box of the unit cell and its abutment) | n/a (geometric) | §1.3.4.1 Table 4 and §4.1 note: ≤ 55 µm bump pitch is the low-density class AIB 1.2 sizes its timing against. Floor from PDK-lay Pad.aR + Pad.bR = 38.4 µm; the PDK's own I/O cells are 80 µm wide (PDK-io LEF) | BOTH (the same cell is in both) |
| T-23 | Area per wire (**simulated / pre-layout estimate**; replaced by the extracted-layout figure when layout exists) | ≤ 5500 µm² per data wire, I/O cell only (55 µm × 100 µm) | ≤ 14400 µm² (80 µm × 180 µm, the PDK I/O cell footprint) | ≤ 3200 µm² (40 µm × 80 µm) | `ANALYSIS` now; `LAYOUT` (`klt stats`) when the cell exists | n/a (geometric) | not defined by AIB 1.2. Depth chosen so a 20-wire column is 20 × 55 µm = 1.1 mm long | BOTH |
| T-24 | Pad plus ESD capacitance seen by the pin (total at the receiver pin, excluding the channel) | ≤ 100 fF | ≤ 200 fF | ≤ 50 fF | `SIM` (extracted-capacitance estimate now; `PEX` after layout) | PVT-FULL (capacitance is bias dependent) | AIB 1.2 §4.1 states a 0.5 fF near-end microbump load for its own timing, which excludes the ESD device; no PDK bond-pad model exists (PDK-esd `bondpad` is an empty placeholder subcircuit); DR-0008 | BOTH (CH uses the value inside the far-end load, T-12) |
| T-25 | ESD protection target | **Proposed target equals AIB 1.2 Table 19 at 55 µm pitch: CDM ≥ 70 V and 0.5 A discharge current**; a *human-body-model class* is not specified (AIB 1.2 does not define one) | the PDK's own `sg13g2_io` pad cells at 80 µm pitch (T-22 fallback), protection level as the PDK's ESD documents state; those documents are not in PDK `v0.3.0` `libs.doc` (DR-0008) | CDM ≥ 70 V at ≤ 40 µm pitch | `LAYOUT` (clamp + diode area and current-path width by `klt`), `SIM` (diode/clamp transient at the 0.5 A pulse), `MEAS` (none planned; no ESD tester access is in scope) | n/a | §4.3 Table 19 | BOTH for the cell. Which pads of the shuttle part face the package, and so need more than this level, is decided in DR-0008 |
| T-26 | Energy per bit, TX + RX (**simulated**) | ≤ 1 pJ/bit | ≤ 2 pJ/bit | ≤ 0.5 pJ/bit (not reachable at full swing on `CH-3MM-RC`: DR-0004) | `SIM`: integrated supply energy of the full channel (TX, channel model, RX, clock share) over PRBS-7 at the rate, divided by bits delivered | PVT-FULL; reported at tt/1.2 V/27 °C as the headline and at the worst-case supply corner | not defined by AIB 1.2 | CH (the channel capacitance sets it). The TC figure with bond-pad loads is a different, larger number and is reported separately; it is not a channel claim. **Simulated; no measurement exists** |
| T-27 | Latency, sequential part (TX input register to RX output register) | TX ≤ 1.5 clock cycles (3 UI) and RX ≤ 1.5 clock cycles (3 UI), sequential delay only | — | — | `RTL` (cycle accounting) | n/a | §2.1.7 Table 9: the DDR-capable (Plus) configuration allows 1.5 clock cycles (3 UI) each way, the base SDR configuration 1 cycle (1 UI); analog delays are excluded | BOTH |
| T-28 | Tristate and weak pulls on every pin | tristate on all outputs; selectable weak pull-up / pull-down / none, 10–20 kΩ equivalent | tristate only | — | `SIM` (leakage, pull strength), `RTL` (control) | PVT-FULL | §2.1.4; §2.1.5 | BOTH |
| T-29 | Test and loopback modes | on-die loopback L1 and wire-bond loopback L2 as defined in test-configuration.md; both selectable per wire group | L1 only | — | `RTL`, `SIM` | PVT-FULL | not defined by AIB 1.2 (it has JTAG-style test provisions in §5 that this repo does not adopt; the issue's scope is loopback) | TC |
| T-30 | Signoff | DRC + LVS clean with the I/O column included, post-layout re-verified | — | — | `LAYOUT` (`klt drc`, `klt lvs`, `klt signoff`), `PEX` | n/a | not defined by AIB 1.2 | BOTH |

## Timing budget (the basis of T-20)

Everything in UI of the 1 Gb/s target (1 UI = 1000 ps). The far-end valid eye is
0.40 UI (AIB 1.2 §4.1 Table 17, tEW far end). The sampling clock has to land inside
it, and everything below shares it. This is an *allocation proposal*: each line
is a verified row, and the sum is what T-20 checks, not an independent claim.

| Contribution | UI | ps at 1 Gb/s | Row |
|---|---|---|---|
| Far-end valid eye | 0.400 | 400 | T-18 (AIB 1.2) |
| − receiver capture aperture | 0.150 | 150 | T-19 |
| − data-to-clock skew at RX input | 0.030 | 30 | T-16 (AIB 1.2) |
| − alignment placement error (half a step of 1/8 UI plus phase-spacing error, worst case) | 0.0625 | 62.5 | T-21 |
| − forwarded-clock + DLL jitter, peak-to-peak (all contributors in the block's clock path) | 0.050 | 50 | T-21 |
| **= margin left** | **0.1075** | **107.5** | **T-20 ≥ 0.10 UI** |

The margin line closes by 7.5 ps at the target. The fallback rate (UI 2000 ps)
doubles every absolute figure and costs nothing in the UI budget. The 2 Gb/s
stretch halves the absolute values and is not shown to close on these allocations
(a 75 ps aperture and a 31 ps step are both demanding on this node); that is why
the stretch must not drive the architecture (CLAUDE.md, DR-0002).

The jitter allocation is peak-to-peak at 14 σ (≈ 1e-12 tail); 0.03 UI of it is
the DLL's (dll-interface.md), i.e. about 2.1 ps rms at 1 Gb/s.

## What this spec does not cover

- The interposer or package, and anything above the physical wires (README
  scope).
- A DLL or duty-cycle corrector design (scope discipline; dll-interface.md).
- Any claim that the block meets the AIB specification. None is made.
