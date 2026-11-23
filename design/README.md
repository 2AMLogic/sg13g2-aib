# design

## synth/: gate-level netlist of `aib_datapath` (T1 item 1, digital)

`klt synthesize` of `rtl/aib_datapath.v` (N = 20, the module default) onto
`sg13g2_stdcell` at the slow corner `slow_1p08V_125C` (exact shipped point:
1.08 V, 125 C). One corner only: a corner changes cell sizing, and timing is
item 5, not this item. No timing, area or power claim is made from it.

| File | What |
|---|---|
| `synth/aib_datapath.synth.json` | the `klt synthesize` request |
| `synth/aib_datapath.report.json` | the report it produced (verbatim) |
| `synth/.klt/synthesize/<run_id>/` | the run's netlist `aib_datapath_synth.v`, `.ys` script |

**Revision.** Synthesized from `main` @ `a800088`. `rtl/shift_redundancy.v`
(last commit `42fa21ca9fa178a70b06cea249bd5a17eb8eec13`) is the pre-decision
T-05 remap; `aib_datapath` does not instantiate it, so the netlist does not
contain the mux. Re-synthesize after #29 / PR #32 settles; that is a new,
dated artifact (a new `run_id`, a new inventory hash).

**Regenerate and check** (needs the PDK and `yosys`; see `signoff/README.md`):

```bash
export PDK_ROOT=<path containing ihp-sg13g2>
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt synthesize \
  design/synth/aib_datapath.synth.json --pdk ihp-sg13g2 --format json \
  > design/synth/aib_datapath.report.json
# keep only the new design/synth/.klt/synthesize/<run_id>/ (drop *.log), delete older run dirs
python3 -I scripts/ci/check_design_sources.py --regenerate
```

Consistency of a committed report with a fresh run:
`klt synthesize <request> --pdk ihp-sg13g2 --check <report> --rerun` (exit 0 = match).
A re-run writes a new `.klt/synthesize/run-*` directory; delete it.

## Analog I/O-cell sources (T1 item 1, analog)

Analog design sources for the I/O-cell partition (T1 item 1, analog). Thin-oxide
SG13G2 devices only (T-06), unterminated outputs (T-07).

| Cell | Role | Spec rows it is built toward |
|---|---|---|
| `aib_tx_data` | tristate full-swing data driver, selectable weak pull-up / pull-down | T-06, T-07, T-08, T-28 |
| `aib_rx_data` | single-ended supply-referenced data receiver, no hysteresis (the #398 adoption; see below) | T-10, T-11 |
| `aib_tx_clk` | clk/clkb forwarded-clock driver: two `aib_tx_data` | T-04 |
| `aib_rx_clk` | clk/clkb forwarded-clock receiver: two `aib_rx_inv` | T-04 |
| `aib_rx_inv` | single-ended inverter receiver, no hysteresis — the committed receiver both clock legs keep | T-04 |
| `aib_pad_esd` | diode pair + rail clamp at the pad, series resistor, secondary diodes | T-24, T-25 |

Each cell is a `.sch` plus `.sym`; the `.spice` next to it is derived with
`klt netlist`, never raw `xschem`. `xschemrc` carries the PDK search path.

**What this directory claims: the sources exist and the netlists are fresh.** The output
stage and the primary ESD diode were sized in issue #130 against the dc-static PVT-FULL run
(`sim/dc-static/records/20261108T004350Z/`); every other size not named below is still a
first-cut placeholder. `w` is the total width over `ng` fingers; every finger is at or above
the 0.15 um minimum.

Sizing set in #130 (details and probe table in `sim/dc-static/README.md`):

- `aib_tx_data`: `XMp` 54u/54 and `XMn` 22u/22 each drive PAD through a series `rppd`
  (`XRsp`, `XRsn`, `w=10u l=0.5u`, about 18 ohm). The MOS Ron alone spreads 2.1-2.4x over
  PVT-FULL, wider than T-08's 2x window, so no width closes it; the poly leg compresses it.
- `aib_tx_data` (#142): the predriver NOR pull-up `XMnr1p`/`XMnr2p` is 8u/ng=4 (was 4u/ng=2).
  The fall edge charged the 22u `XMn` gate through two series PMOS and ran about 41 ps slower
  than the rise; balanced, the data-to-clock offset (T-16) closes at 45/45 corners.
- `aib_pad_esd`: `XDp1` is 4.5u x 4.5u (was 10u x 10u) because the wider driver and the
  primary diode do not both fit T-24. **T-25 (ESD level) is not evaluated**: no ESD-transient
  simulation exists. DR-0017 states the trade and what would reverse it.
- `aib_pad_esd` (#251): `XResd` is `w=2u l=1u` (was `l=2u`). The channel-bench T-16 margin at the
  declared kr = kc = 1.2 corner was 1.331 ps; with this change the worst margin over PVT-FULL x the four
  (kr, kc) spread pairs is 19.92 ps. T-08 (min margin bound 42.86 ohm) and T-24 (worst 96.42 fF) are unchanged
  in the dc-static runs. **T-25 is still not evaluated** and `XResd` is the receiver-isolation element, so the
  halved resistance is an unmeasured ESD cost. `design/aib_pad_esd_2kv.spice` keeps `l=2u` until #196 decides
  the diode. Evidence: `sim/channel-eye/records/20261118T220000Z-t16-sizing/README.md`. The committed
  layout draws `Resd` at this netlist size since the #387 regeneration (2 um wide, 1 um long;
  DRC `layout/records/20261120T202314Z`). The LVS is a connectivity match
  on the layout and records `device.geometry_not_compared` for `rppd`, so it cannot
  distinguish the two resistor lengths; the drawn size rests on the generator table, which
  the CI evidence job now compares against this netlist on every push
  (`python3 -I layout/gen_io_column.py --check`).

Known open point: T-25 (ESD level) remains unevaluated; DR-0017 states the trade and
what would reverse it. The forwarded-clock alignment (DLL) is out of scope.

## Receive split (#398): the data lanes take the supply-referenced receiver

`aib_rx_data` is the **supply-referenced input stage** selected by the #386 sizing study
(study cell `rx__vref`, `sim/rx-threshold-study/cand_cells.inc`, device sizes adopted
verbatim): an NMOS input pair (the pad vs `vrn`, a matched `rppd` VDDIO/2 divider —
`Rdiv1`/`Rdiv2`, 0.5 um x 48 um each), a PMOS mirror load (`Mlp` diode-connected, `Mln`
4 um/0.25 um ng=4), a ~100 uA tail (`Mtail` 2 um/0.5 um, gate VDDIO), and a restore
inverter at half the committed width (`Mi2` 2 um/1 um, l=0.13 um, ng=1). Comparing the pad
against a divider that tracks the same supply turns the PVT N/P strength skew — the
mechanism that put 13 of 45 corners outside +-60 mV on the committed inverter cell — into a
near common-mode current change.

**Why the split.** The study measured the candidate in both clock legs
(`records/20261121T104210Z-clk/`, variant c): at the binding corner `mos_ss/1.080V/-40C`
the opposite-edge separations invert (`t02_cr_df` +624 ps relative to 500 ps), ~8x the
committed cell's worst, because the stage's output slew is asymmetric (d1 charges through
the mirror but discharges through the input pair). So `aib_rx_clk` keeps the committed
inverter in both legs — as its own cell `aib_rx_inv` now, with the sizes unchanged from the
cell as first committed (#35) — and `aib_rx_data` carries the adopted stage for the data
lanes (and the spares, which are data-lane spares). The study's variant-d measured exactly
this split; the landed re-run reproduces it (below).

**Recorded results on the landed split** (all simulated, pre-layout, batch fleet; the
records are the evidence, this note quotes them):

| Quantity | Result | Record |
|---|---|---|
| T-10 threshold, 45 corners x 120 draws, seed 4410 | `klt yield` **pass**, +-60 mV / 3 sigma; pooled mean +2.7 mV, sigma 9.6 mV, worst draw +42.3 mV; **0 of 5400 draws and 0 of 45 corners outside the limits**; sigma-to-spec 5.96 (lower bound 5.85); control (input-pair NMOS 4x narrower) detected, 0/900 | `sim/mc/records/20261123T092848Z-t10/` |
| T-11 hysteresis | <= 1.7 uV (binding `sf/mixed/125C`), pass 45/45 | `sim/dc-static/records/20261123T091724Z/` |
| T-24 pin capacitance | 76.3-92.4 fF over the three biases (binding 92.4 fF at VDDIO, `ss/mixed/125C`), pass 45/45 | same |
| T-15 / T-16 RX-input skew (mismatch) | pass, unchanged by the split (T-16 pooled mean -0.3 ps, sigma 3.4 ps, worst -15.1 ps vs -30) | `sim/mc/records/20261123T093311Z-t15/`, `...-t16/` |
| T-16 at the nominal channel | pass 45/45 (binding +9.5 ps-class margins, `mos_sf/mixed/-40C`), with T-01/T-09/T-18/T-26 | `sim/channel-eye/records/20261123T093440Z-ch/` |
| t02 clock-path separations | the split's cost: `t02_cr_df` 586.8-1089.8 ps, `t02_df_cf` -139.5..392.1 ps at the RX outputs | `sim/clock-path/records/20261123T091724Z/` |
| T-19 capture aperture | **FAILS on the adopted cell**: 151/900 draws over 150 ps, 8 corner means 156-442 ps (hold-dominated), window saturation at `ss/1.080V/-40C`; #190 carries the fix | `sim/mc/records/20261123T094302Z-t19/` |

**Costs the ratification sees** (all simulated, labelled as such):

- **Standing divider + tail current.** Measured on the committed T-10 request itself
  (`rx_up.ivdd_a`, |i(VDDIO)| at the switching point, i.e. with the input at the threshold
  — at VDDIO/2 by construction of the bench): at tt / 1.2 V / 27 C the 120 draws span
  **64.0-94.2 uA, mean 81.3 uA** — midpoint DC power **1.2 V x 81.3 uA = 97.6 uW per
  receiver**. Over the 45-corner grid the mean spans 34.6-185.4 uA (mismatch live). This is
  the architecture's standing cost, ~0.7-0.8 mW across the 20+2 data lanes at 1.2 V;
  rail-idle power would need a rail-input measurement, which this record is not.
- **Energy per bit (T-26, SIMULATED).** The split raises the lane energy per bit
  `t26_energy_per_bit_simulated_j` from 0.354-0.634 pJ/bit (the same-day pre-split record
  `sim/channel-eye/records/20261123T001529Z-ch/`) to **0.387-0.741 pJ/bit** (+9.4 % at the
  low end, +17.0 % at the high end, over the same 45 corners); the RX lane's own energy
  rises from 0.845-2.24 pJ to 5.12-18.4 pJ per 127-bit integration (0.0403-0.145 pJ/bit),
  the divider + tail current dominating. Labelled SIMULATED; no measurement exists.
- **Mismatch coverage.** The committed T-10 Monte Carlo varies MOS mismatch only
  (`mos_*_mismatch` sections); the divider is a pair of corner-section `rppd` resistors
  with **no independent resistor-pair mismatch in this model set** — the same coverage as
  the pre-adoption record and the study. Documented here and in the record.

**Two-edge timing disposition (the DDR sampling decision).** A passing T-16 at the RX pins
does not establish margin at the receiver outputs, so the four signed t02 separations were
read per corner from the landed clock-path record (all values at the RX **outputs**;
`t02_dr_cr` a, `t02_df_cf` b, `t02_cr_df` c, `t02_cf_dr` d; UI 1000 ps, nominal 500 each).
With one legal forwarded-clock phase phi per operating condition — both clock edges shifted
together, the alignment's one degree of freedom — the DDR margins are
min(a+phi, c-phi) on the rising-data eye and min(b+phi, d-phi) on the falling-data eye:

- A common phase exists at **all 45 corners**; the required phi* spans **+80.7..+327.4 ps**
  of added clock delay relative to nominal center alignment (the DLL/interface budget the
  spec's forwarded-clock alignment question carries; DR-0020/#195 compare it against the
  sibling SG13G2 DLL canary).
- The **falling-data eye binds at every corner** (the adopted stage's late falling edge:
  data fall-vs-rise output-delay mismatch up to +624.1 ps at `mos_ss/1.080V/-40C`).
- Limiting corner **`mos_ss/1.080V/-40C`**: phi* = +327.4 ps leaves **762.4 ps** of
  rising-eye margin and **187.9 ps** of falling-eye margin (the grid's worst; the best
  corner keeps 481.6 ps).
- **Decision: the output stage stays as adopted, and the T-19 cost is recorded, not
  hidden.** By the issue's stated test — one legal phase per operating condition against the
  existing budget, read from the four separations — the phase exists at all 45 corners and the
  binding 188.0 ps clears the 150 ps budget with 37.9 ps. The T-19 re-run on the adopted cell
  (`sim/mc/records/20261123T094302Z-t19/`) adds the measured aperture: **the T-19 row itself
  fails** (151 of 900 draws over 150 ps; 8 of 45 corners' means 156-442 ps, hold-dominated;
  at `ss/1.080V/-40C` the capture boundary leaves the bench's sweep window), because the same
  asymmetric output edge that shifts the t02 separations keeps the D pin moving through the
  half-width restore inverter. Cross-checking the two records corner by corner: at every corner
  where T-19's window contains the boundary, the measured rising-setup and falling-hold fit
  inside the separation margins (worst phase-window width 599 ps at `ss/1.080V/27C`), so the
  phase choice stands; the row's own 150 ps budget is what the cell misses. **#190 (rise/fall
  symmetry of this cell) carries the output-stage revision and the T-19 re-run that closes
  it**; the worst mixed-lane falling-data separation (t02_df_cf = -139.5 ps, the ordering
  inversion) is included in the four separations above.

#190's rise/fall symmetry question now applies to this data path: the disposition above is
the pre-#190 reading, and a #190 resize re-measures it. The spec's T-10 row, its +-80 mV
fallback, the manifest's row set and every limit are untouched by this adoption.

## Regenerate and check

From the repo root, with the pinned grader (`signoff/KLT_VERSION`):

```bash
K="uvx --from klayout-tools==$(cat signoff/KLT_VERSION) klt"
$K netlist --rcfile design/xschemrc design/aib_tx_data.sch -o design/aib_tx_data.spice          # write
$K netlist --rcfile design/xschemrc design/aib_tx_data.sch -o design/aib_tx_data.spice --check  # exit 0 = fresh
```

xschem writes absolute `** sch_path:` comments; strip the checkout prefix after
writing so the committed file is repo-relative (`--check` ignores those
comments). Re-attest with the recipe in `signoff/README.md`.
