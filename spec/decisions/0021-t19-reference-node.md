# DR-0021: Reference T-19's capture aperture to the RX pins

**Status**: **proposed**. Ratification requires a human merge under
[DR-0001](0001-spec-structure-and-ratification.md).
**Rows**: T-19 and T-20. This decision amends [DR-0006](0006-timing-budget.md)
by naming the reference node for the 0.150 UI capture aperture. The T-20
allocation gives 0.1075 UI against a requirement of ≥ 0.10 UI at 1 Gb/s.

## Context

T-18 measures the valid eye at the RX data pin, and T-16 grades data-to-clock
skew at the RX pins. DR-0006 budgeted T-19 between that eye and the sampling
flop, but left its reference node implicit. Issue #177 arose when the original
clock-path simulation found 397.4 ps and 602.6 ps between opposite-direction
edges at the RX **outputs** at `mos_sf`/1.08 V/−40 °C. The 102.6 ps displacement
from 500 ps (0.103 UI) includes the transmitter, pads, channel and receiver.

Two receiver designs enter the evidence. The November 12–13 records used
two-inverter cells for both data and clock. In #398 the data path adopted a
supply-referenced receiver. The two clock legs kept the inverter as
`aib_rx_inv`. The November 23 records characterize this split.

## Pinned sources

All timing results here are **simulated, pre-layout**. The channel-eye and
clock-path records use the modeled CH-3MM-RC channel (scope CH). The T-19
Monte Carlo benches drive the RX pad and the flop clock with ideal 100 ps
edges. Their cell-level results apply to CH or TC only at the stated slew.

| Receiver | Source in this repository | Evidence |
|---|---|---|
| Adopted (`4b73f7c`) | `design/aib_rx_data.spice`, `design/aib_rx_clk.spice`, `design/README.md` | Supply-referenced data path, inverter clock legs and the output-stage disposition |
| Adopted | `sim/mc/records/20261123T094302Z-t19/` | D-pin aperture, per-draw results, sweep saturation and recorded failure |
| Adopted | `sim/clock-path/records/20261123T091724Z/`, `sim/channel-eye/records/20261123T093440Z-ch/` | Edge separations at the RX outputs and T-16/T-18 at the pins |
| Earlier inverter (`8107ae0`) | `sim/mc/records/20261112T082047Z-t19/` | D-pin aperture and per-draw pad-to-D delays for the matched-cell calculation |
| Earlier inverter | `sim/clock-path/records/20261113T095936Z/`, `sim/channel-eye/records/20261111T235838Z-ch/` | The original 0.103 UI observation and its pin-side comparison |

## Decision

### 1. T-19's aperture is referred to the RX pins

Grade the setup and hold window at the data and forwarded-clock pins
(`rxa`, `rxc`/`rxcb`). This includes the delays from those pins to the
flop's D and sampling-clock inputs. T-18 checks the 0.40 UI eye at the data
pin. T-16 checks eight data-to-clock intervals at the pins, including
opposite-direction edges. On the adopted receiver's channel-eye run, T-18
passes 1845/1845 checks and T-16 passes 360/360. T-17 already accounts for
TX clock duty-cycle distortion. Charging the whole 0.103 UI observed across
the earlier lane to T-19 would count effects upstream of the RX pins twice.

### 2. One sampling phase must satisfy both data polarities and both clock edges

Let a valid window open at time zero and close at `W` at the data pin. A
clock edge at time `x` at its pin reaches the sampling flop at `x + c_e`,
where `c_e` is the delay for that clock edge. The opening and closing data
edges reach D at `d_open` and `W + d_close`. For a given pairing the setup
and hold requirements at the flop therefore give

```
x ≥ t_su + d_open − c_e
x ≤ W − (t_h + c_e − d_close)
```

Use the data delays `d_r`, `d_f` and the clock delays `c_r`, `c_f` for their
respective rising and falling edges, including the sampling clock path to
the active flop. These are the two pin-referred requirements for each pairing.
Use the flop's setup and hold for that pairing in its row.

| Data bit (opens / closes) | Sampling clock | Setup from opening edge | Hold to closing edge |
|---|---|---|---|
| 1 (rise / fall) | rise | `t_su + d_r − c_r` | `t_h + c_r − d_f` |
| 1 (rise / fall) | fall | `t_su + d_r − c_f` | `t_h + c_f − d_f` |
| 0 (fall / rise) | fall | `t_su + d_f − c_f` | `t_h + c_f − d_r` |
| 0 (fall / rise) | rise | `t_su + d_f − c_r` | `t_h + c_r − d_r` |

T-21 sets one phase for both clock edges. With nominal DDR spacing at the
pins (pin-side skew and duty distortion have their own rows), `x` must lie
in the intersection of all four intervals. Thus the aperture at each draw is
the **maximum setup column plus the maximum hold column**, which can come
from different rows. A common data-to-clock delay offset moves the required
phase. Moving the phase cannot widen the intersection.

**Earlier matched-cell case.** The historical calculation assumes
`c_r = d_r`, `c_f = d_f` and the same flop setup and hold in every row. With
`Δ_rx = d_r − d_f`, the largest setup and hold each gain `|Δ_rx|`.
For positive Δ_rx the falling-clock 1 sets setup and the rising-clock 1
sets hold. For negative Δ_rx the rising-clock 0 sets setup and the
falling-clock 0 sets hold. This gives **`t_su + t_h + 2·|Δ_rx|`** for the
earlier inverter model. The adopted supply-referenced data path and inverter
clock path require the separate delays above.

### 3. T-19 evidence for the adopted receiver and the earlier inverter

Both T-19 records use 20 mismatch draws at each of 45 PVT corners. The bench
measures rising-data setup and falling-data hold on one posedge
`sg13g2_dfrbpq_1`, with an ideal clock at the flop. The aperture in each
`report.json.gz` is `t19_aperture_ps` at the D-pin 50 % crossing.

| Simulated result at 1 Gb/s | Earlier inverter (Nov 12) | Adopted receiver (Nov 23) |
|---|---|---|
| Largest recorded D-pin aperture | 68.60 ps | **541.2365 ps** |
| D-pin draws over 150 ps | 0 of 900 | **151 of 900** |
| D-pin σ-to-spec (target 7) | 9.78 | 0.47 |
| RX-pin aperture | 99.52 ps worst, 0 of 900 over 150 ps, under the matched-cell assumptions | Open pending split-path evidence |

On the **adopted receiver**, eight corner means exceed 150 ps. The worst
readable mean is 442.1 ps at `ss`/1.08 V/27 °C, dominated by hold.
At `ss`/1.08 V/−40 °C the capture boundary leaves the −400 to +100 ps sweep
window for some draws. The recorded maximum and failure count describe that
sweep. A wider sweep at this corner is needed to bound the aperture.
The characterization report records T-19 as **fail** on this D-pin evidence.
The bench supplies data delays but omits the inverter clock legs and the
other capture pairings needed for a pin-referred result.

For the **earlier inverter only**, applying decision 2 draw by draw gives
`t19_aperture_ps + 2·abs(cw.dr − cw.df)` with all delays in ps. Δ_rx ran from
−1.44 to +19.52 ps. The pin-referred mean was 42.5 ps and the worst was
**99.52 ps** at `sf`/1.08 V/125 °C (60.48 + 2 × 19.52), about 50 ps below
150 ps. This historical estimate uses row 1's measured setup and hold for
the other three pairings and assumes the clock delays match the data delays
in each draw. The setup and hold thresholds each carry the 10 ps sweep's
±5 ps quantisation.

### 4. The earlier 0.103 UI observation motivates a slew measurement

In the November 13 CH-3MM-RC clock-path record, the TX-pad contribution was
20.7 ps at `mos_sf`/1.08 V/−40 °C. The approximately 82 ps left after that
subtraction spans the channel, pad structures and receiver. In the November
12 inverter Monte Carlo record, Δ_rx at the same corner was 10.54–19.11 ps.
Combining those figures leaves **63–71 ps** unattributed across the two
benches. The Monte Carlo bench used an ideal 100 ps input ramp, and neither
historical record measured the channel's slew at the RX pin. #198 tracks
that slew measurement and attribution. As a sensitivity check on the historical
matched-cell model, substituting an 82 ps receiver asymmetry would give about
233 ps (68.6 + 2 × 82). Neither record establishes that attribution.

The November 23 clock-path record gives end-to-end separations for the
adopted split. For example, `t02_df_cf` reaches −139.5 ps at the RX outputs
at `mos_ss`/1.08 V/−40 °C. These separations inform phase placement.
A pin-referred T-19 result needs setup and hold across all four pairings
at representative data and clock slews, either by sweeping their relative
phase at the RX pins or by measuring the separate delays and flop boundaries
in decision 2 at the same operating condition and mismatch draw.

### 5. #190 carries the adopted output-stage revision and T-19 re-run

The adopted stage's asymmetric output drives the hold-dominated D-pin
failure. As recorded in `design/README.md`, #190 owns the output-stage
revision and T-19 re-run. That work has a measured failure to address
independently of #198's historical slew question. Check the revision's
impact on T-10 threshold, T-11 hysteresis and T-24 input capacitance
(which also loads the channel for T-12). A sizing change propagates
to the layout, LVS references and signoff evidence under T-30.

### 6. Timing allocations and verification

T-19 retains its target/fallback/stretch limits of 0.150/0.250/0.150 UI.
T-02 grades the exchange format in RTL. T-04 grades the forwarded-clock
arrangement with the netlist connectivity check. Their analog edge
separations and crossing levels are report-only (DR-0026, DR-0027).

## Alternatives rejected

- **Add a receiver budget line or charge the loss to T-21.** The pin reference
  includes the receiver paths within T-19. A new line over 0.0075 UI would
  take the allocated T-20 margin below its requirement. A single T-21 phase
  can place the sampling edge only within the intersection in decision 2.
- **Use one pairing, or halve the loss by re-centring an alternating pattern.**
  Either choice can miss the pairing that sets the opposite bound. Even in
  the matched-cell case the full DDR stream pays the asymmetry on both sides.
- **Use the earlier inverter's passing margin or the full 0.103 UI for the
  adopted data receiver.** The former assumes matching clock and data delays
  at 100 ps slew. The latter includes pre-pin effects. The current D-pin
  failure and the two distinct receiver paths require their own evidence.
- **Add a numerical analog bound to T-02 or T-04.** Their graded criteria
  are format and connectivity. T-16, T-19 and T-20 carry the DDR timing limits.

## Consequences

The T-19 `SIM-MC` result used in the budget must cover both sampling edges
and report the aperture at the RX pins. The adopted design has a recorded
D-pin failure and an open pin-referred result. #190 tracks the hardware
revision and re-run. The November 12 passing estimate remains historical
evidence for the inverter receiver.

The DR-0006 allocation leaves **0.1075 UI**, or 107.5 ps at 1 Gb/s.
T-20 remains **not-yet-measured** in `measurements/characterization-report.md`.
Its verification requires the pin-referred T-19 result and the other timing
inputs, including the separate T-21 DLL evidence in
[DR-0020](0020-dll-recomparison-t21.md).
