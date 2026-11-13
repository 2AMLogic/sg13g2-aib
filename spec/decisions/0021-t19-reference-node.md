# DR-0021: T-19's aperture is referred to the RX pin, which puts the input stage's rise/fall asymmetry inside T-19

**Status**: **proposed**. Not ratified; ratification follows
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge.
**Rows**: T-19 and T-20 are *named and interpreted*; **neither value is
changed**. T-16, T-17 and T-18 are cited. **Amends**:
[DR-0006](0006-timing-budget.md) by naming the node T-19's aperture is referred
to, which DR-0006 left unstated. No target, fallback or stretch value moves, no
budget line is added or re-weighted, and **T-20 stays at 0.1075 UI allocated
against a ≥ 0.10 UI requirement**.

## Context

`target-spec.md`'s timing budget chains T-18 (eye at the RX input), T-19 (capture
aperture), T-16 (data-to-clock skew at the RX input) and T-21 (alignment), and
closes T-20 at 0.1075 UI — 7.5 ps of slack at the 1 Gb/s target. DR-0006 set
T-19 at 0.150 UI but never said **at which node** the aperture is measured. The
T-19 row's verification wording, "`SIM-MC` of the RX capture flop/latch plus
input stage", implies the input stage is inside the number, but the spec does not
say so in words.

Issue #54's clock-path record made that silence expensive. Measuring the DDR data
edge against the forwarded clock's edges at the **RX outputs** — the nodes a
capture flop would see — it found the two alternate DDR half-periods at
**397.4 ps and 602.6 ps** instead of 500 ps at `mos_sf`/1.08 V/−40 °C:
**0.103 UI** of static off-centring, before any jitter or mismatch. Same-direction
edges track to under 0.01 ps, because the data lane and the clock lane are the
same cells on the same channel; the opposite-direction pairs do not cancel.

That term sits between the last pin-referred graded row and the capture node. If
T-19 is referred to the pin it is inside T-19's 0.150 UI; if T-19 is referred to
the flop input it is charged to nothing. The spec has to pick one, or T-20 cannot
be re-derived from results.

## Pinned sources

| Source | Pin | What was read |
|---|---|---|
| `sim/clock-path/records/20261113T095936Z/` | `main` @ `8107ae0` | T-02 at the RX outputs 397.4 / 602.6 ps, 0.103 UI (`README.md` 70–71, 79); T-17 worst DCD −1.036 % (28); T-04 crossing at the pins −19.2…+9.1 mV, at the outputs −646.1 mV at `mos_sf`/**1.32 V**/−40 °C (48) |
| `sim/mc/records/20261112T082047Z-t19/` | `main` @ `8107ae0` | T-19 **pass**: aperture worst draw 68.60 ps of 150, σ-to-spec 9.78 of 7, 900 mismatch draws; per-draw `cw.dr` / `cw.df` pad-to-D delays from `report.json.gz`; `tb_t19.cir`, `record.json` |
| `sim/channel-eye/records/20261111T235838Z-ch/` | `main` @ `8107ae0` | T-16 **pass 360/360**, T-18 **pass 1845/1845** (`rows.json`); per-corner T-16 values from `report.json.gz` |
| `design/aib_rx_data.spice`, `design/aib_rx_clk.spice` | `main` @ `8107ae0` | the two-inverter receiver; `aib_rx_clk` is two instances of the same cell |
| `sim/channel-eye/gen_channel_eye.py` | `main` @ `8107ae0` | T-16 and T-18 probe nodes and limits (`EYE_WIN_PS = 400`) |

Every record here is **simulated**; the clock-path and channel-eye records are
scope **CH** on the declared channel CH-3MM-RC, and the T-19 record is a
pre-layout cell property. There is no die-to-die assembly to measure, so nothing
below is a silicon result.

## What the graded pin-referred rows already cover

This decides whether the term is genuinely uncharged.

- **T-18 is pin-referred and is a real width criterion.** Its eye is measured on
  `v(rxa)`, the RX pin. `t18_eye_windows_open` counts, over 20 phase offsets, the
  **0.40 UI-wide** windows (`EYE_WIN_PS = 400`) whose eye height stays ≥ 90 mV,
  and requires at least one. It passes 1845/1845.
- **T-16 is pin-referred and *does* bound opposite-direction edges.** All **eight**
  of its measurements carry the 470–530 ps limit, including the opposite-direction
  pairs `t16_dr_cf_{long,short}` and `t16_df_cr_{long,short}`; it passes 360/360
  (8 × 45). At `mos_sf`/1.08 V/−40 °C — the corner that binds the clock-path
  figure — those intervals measure **482.1, 490.2, 500.9 and 510.0 ps**, within
  18 ps of nominal. The row's binding draw over the grid is `t16_dr_cf_long` =
  480.9 ps at `mos_ss`/−40 °C.

So the pin is **not** where the off-centring appears: there the opposite-direction
data-to-clock interval is bounded to 500 ± 30 ps by a graded, passing row. What
is charged to **no** row is whatever the receiver adds between the pin and the
capture node.

## Decision

### 1. T-19's aperture is referred to the RX pin

T-19 is the setup + hold aperture **referred to the RX pin** (`rxa`, `rxc`/`rxcb`)
— the same node T-16 and T-18 are graded at — and therefore includes the RX input
stage (`aib_rx_data`), not only the capture flop or latch. `target-spec.md`'s
T-19 row and the Timing budget section are edited to say so.

This is the reading the row's existing "plus input stage" wording already
implied; it is now stated. It leaves **no node between the last pin-referred
graded row and the capture flop uncharged**, and it changes no number.

### 2. The quantity inside T-19 is the receiver's own pad-to-D asymmetry, and no clock placement can absorb it

Let the receiver's pin-to-flop delay be `d_r` for a rising edge and `d_f` for a
falling one, and let **Δ_rx = d_r − d_f**. The clock receiver is the same cell
(`aib_rx_clk` is two instances of `aib_rx_data`), so the clock sees the same
`d_r`/`d_f`.

A 1 UI-wide valid window is bounded by one edge in and one edge out, of opposite
directions: a `1` bit opens on a data rise and closes on a data fall, a `0` bit
the reverse. In DDR each is sampled by a rising *or* a falling clock edge
depending on the pattern phase, so over a data stream **all four pairings occur**.
Referring the flop's own `t_su`/`t_h` back to the pin through `d_r`/`d_f`:

| bit | opens / closes | sampling clock edge | pin-referred setup | pin-referred hold |
|---|---|---|---|---|
| `1` | rise / fall | rise | `t_su` | `t_h + Δ_rx` |
| `1` | rise / fall | fall | `t_su + Δ_rx` | `t_h` |
| `0` | fall / rise | fall | `t_su` | `t_h − Δ_rx` |
| `0` | fall / rise | rise | `t_su − Δ_rx` | `t_h` |

The binding pin-referred aperture is therefore **`t_su + t_h + |Δ_rx|`** — and
Δ_rx lands on the **hold** side in row 1 and on the **setup** side in row 2. A
single sampling-clock position cannot trade one against the other: shifting the
clock earlier to relieve row 1's hold side tightens row 2's setup side by exactly
the same amount. **Re-centring buys nothing, so no part of Δ_rx may be credited
to T-21**, whose 0.0625 UI line is quantization and spacing error — a different
quantity.

This is why a *halved* figure is rejected. One can arrive at half of a measured
asymmetry by looking at only two of the four pairings and quoting the per-side
margin after optimal re-centring. That is an artefact of a bench whose stimulus
is a fixed alternating pattern: rows 2 and 4 above follow from the same `d_r`,
`d_f` without a new simulation, and they remove the trade.

**The quantity is Δ_rx, not the clock-path record's end-to-end 0.103 UI.** The
102.6 ps measured at the RX outputs is the asymmetry of the whole lane — TX cell,
TX pad, channel, two `aib_pad_esd` instances and receiver. Its pre-pin part is
T-17's and is bounded at the pin by T-16; only the receiver's own share belongs
inside a pin-referred T-19. Charging the end-to-end figure to T-19 would
double-count T-16's and T-17's terms.

### 3. On the evidence that exists, T-19 still passes pin-referred — worst draw 80.0 ps of 150 ps

**A T-19 result exists and passes**, contrary to the premise of #177 that none
does. `sim/mc/records/20261112T082047Z-t19/` drives `aib_rx_data` into the D pin
of `sg13g2_dfrbpq_1` over 900 mismatch draws on the 45-corner grid: aperture
mean 27.6 ps, σ 12.5 ps, **worst draw 68.60 ps against the 150 ps limit**,
σ-to-spec 9.78 against a target of 7, empirical yield 900/900, negative control
detected. Its worst process corner is `sf` (mean 40.7, max 68.6) — the skew
corner, as this finding predicts.

That result is reported **referred to the D pin**, so by decision 1 it no longer
answers the row as defined. It does not need a new simulation to do so: the record
carries the pad-to-D delays `cw.dr` and `cw.df` **per draw**, so the pin-referred
aperture is `t19_aperture_ps + |cw.dr − cw.df|` draw by draw. Computed over all
900 draws of the committed `report.json.gz`:

| quantity | over 900 draws | at `sf`/1.08 V/−40 °C (20 draws) |
|---|---|---|
| Δ_rx = `cw.dr − cw.df` | −1.44 … **+19.52** ps, mean 7.45, σ 3.70 | 10.54 … **19.11** ps |
| aperture, D-referred | … **68.60** ps | 35.37 … 68.60 ps |
| **aperture, pin-referred** | mean 35.0, **max 80.00** ps | — |

**0 of 900 draws exceed the 150 ps limit pin-referred.** The worst pin-referred
draw is 80.00 ps at `sf`/1.08 V/−40 °C (aperture 63.54 + Δ_rx 16.46). So
referring T-19 to the pin does **not** break the row on the evidence committed to
`main`; it leaves about 70 ps of the 150 ps allocation.

This derivation is stated here, not written into `measurements/row-evidence.json`
or the characterization report. Recorded results are append-only, and
re-reporting a row pin-referred is new analysis that belongs in its own recorded
derivation (filed as **#198**), not in a spec-decision PR. The evidence mapping's
`basis` line already discloses that the committed figure is "at the D-pin 50 %
crossing", so the mismatch with the row is visible rather than hidden.

### 4. The clock-path record's "~82 ps, dominantly `aib_rx_data`" attribution is contradicted, and the residue is unexplained

This is the part the decision cannot settle, and it is recorded as open rather
than resolved.

The clock-path record attributes the 102.6 ps, less T-17's 20.7 ps at the TX pad,
to "~82 ps … dominantly by `aib_rx_data`". That is a subtraction over an interval
that also contains the channel and two `aib_pad_esd` instances. The T-19 record
**measures the receiver per-stage**, and at the same corner gives Δ_rx ≤ 19.11 ps.
T-17's 20.7 ps plus that is **≈ 31–40 ps of the measured 102.6 ps: roughly
63–71 ps is unaccounted for by any per-stage measurement on `main`.**

The two benches differ in the edge the pad sees. The T-19 bench drives the pad
with an **ideal 100 ps linear ramp** (`tb_t19.cir`: `Vpn … pwl(…)` with 0.1 ns
transitions into `Bpad pad 0 V = v(pn)*v(vdd_rx)`); the clock-path bench drives
the receiver through `aib_tx_clk` → `aib_pad_esd` → CH-3MM-RC → `aib_pad_esd` →
`aib_rx_clk`. A receiver's rise/fall asymmetry is slew-dependent, and the T-19
record states this limit itself: its claim scope holds "only to the extent the
edge arriving at the RX pad has the declared 100 ps slew; the slew sensitivity is
not measured here". **Neither record measures the slew at the RX pad** — both
reports were searched for a slew, rise- or fall-time measurement and have none.

So the candidates are: the receiver's asymmetry is far larger at the channel's
actual slew; `aib_pad_esd` contributes; the channel contributes; or the
attribution is wrong. **None is eliminated, and this record adopts neither the
~82 ps figure nor the 19 ps one as the operating value.** Filed as **#198**:
measure the pad slew, re-measure `d_r`/`d_f` at it, separate the residue, and
re-report T-19 pin-referred.

The consequence for the row's verdict is stated plainly: **pin-referred T-19
passes at the recorded 100 ps pad slew with ~70 ps of margin, and its verdict at
the channel's actual slew is not established.** If the receiver's share there
were near the ~82 ps the clock-path record assumes, the pin-referred aperture
would be ≈ 68.6 + 82 ≈ 151 ps — at the limit. That is why #198 gates the row and
not merely the arithmetic.

### 5. The resize follow-up stays filed, contingent on #198

**#190** (size `aib_rx_data` for rise/fall symmetry) stays open, but as the
*remedy* conditional on #198's measurement rather than a presumed necessity: on
the per-stage evidence that exists, Δ_rx ≤ 19.5 ps and no resize is justified.
Per `CLAUDE.md` it is not done here, and it is larger than the comparable #142 TX
predriver fix — `layout/gen_io_column.py` asserts the schematic sizes against its
`RX_DEVICES` table (`chk_mos`), so the GDS, LVS references and signoff manifests
regenerate (T-30); the first inverter sets **T-10**/**T-11**; and its input is a
pad node, so its gate capacitance is inside **T-24** and feeds T-12's far-end
load.

### 6. Nothing else moves

T-02 and T-04 stay report-only; no numeric bound is invented for either. T-16,
T-17, T-18, T-20 and T-21 keep their values. T-19 keeps 0.150 / 0.250 / 0.150 UI.
This record adds no row and no budget line.

## Alternatives rejected

- **Refer T-19 to the flop input and add a new budget line for the receiver.**
  Rejected: T-20 has 0.1075 UI against a ≥ 0.10 UI requirement, so any new line
  above 0.0075 UI takes T-20 below it. Agents do not relax the ratified spec to
  make results pass (`CLAUDE.md`), and this is the form that relaxation would
  take. Referring to the pin needs no new line at all.
- **Refer T-19 to the flop input and charge the term to T-21.** Rejected by the
  derivation in decision 2: Δ_rx appears on the setup side and the hold side for
  different pairings, so sampling-clock placement cannot absorb any of it.
- **Charge the clock-path record's end-to-end 0.103 UI to T-19.** Rejected: it
  double-counts T-17's TX-pad term and the pin-side term T-16 already bounds, and
  it is contradicted as a receiver figure by the per-stage measurement
  (decisions 2 and 4). It would also have put T-19 at ≈ 171 ps — failing a row
  that passes — on the strength of a subtraction.
- **Charge half of a measured asymmetry.** Rejected, with the argument in
  decision 2: the halving depends on only two of the four (bit, clock-edge)
  pairings.
- **Adopt Δ_rx ≤ 19.5 ps as the settled operating value and declare the matter
  closed.** Rejected: it is measured at an ideal 100 ps pad ramp, and the record
  that produced it says its slew sensitivity is unmeasured. Treating it as the
  operating value would bury the 63–71 ps the two records disagree about.
- **Resize `aib_rx_data` now.** Rejected: on the per-stage evidence there is
  nothing to fix, and the resize moves T-10/T-11, T-24 and the whole layout and
  signoff flow (decision 5). It waits on #198.
- **Grade T-02 against a numeric bound so the term is caught by its own row.**
  Rejected: T-02 is the DDR *format* row, the numeric capture budget lives in
  T-19 and T-20, and adding a bound to a report-only row after ratification is a
  spec change this finding does not need.
- **Leave the reference node implicit and rely on the row's "plus input stage"
  wording.** Rejected: that wording is what produced the ambiguity. The
  verification column says what is simulated; the budget needs the node the
  aperture is *measured to*, stated as such.

## Consequences

- T-19 is now a pin-referred row, so its `SIM-MC` must drive the input stage from
  the pin and report the aperture referred to **that** node. A D-referred figure
  does not answer the row — which the committed result is, so it is re-reported
  under #198. The derivation in decision 3 shows the existing record already
  contains what that re-report needs.
- **T-19's worst corner is a skew corner** (`sf`: aperture mean 40.7 / max 68.6 ps,
  Δ_rx mean 12.1 / max 19.5 ps), not the classic slow/fast pair. This is already
  observed, not predicted.
- T-20's allocation and verdict are unchanged, and T-20's `ANALYSIS` now re-derives
  T-19's contribution from merged records rather than from an allocation alone.
- **The open item is the pad slew, not the sizing.** #198 measures it and separates
  the 63–71 ps residue; #190 is the remedy if the answer is large. The next trigger
  is #198's record, which re-fires decision 3's arithmetic against a measured Δ_rx
  at the operating slew.
- `spec/dll-interface.md` and [DR-0020](0020-dll-recomparison-t21.md) are
  untouched: the DLL-side T-20 shortfall recorded there is a separate finding on
  the T-21 lines, and this record does not restate it.
