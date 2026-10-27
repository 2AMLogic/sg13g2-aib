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
| `aib_rx_data` | single-ended receiver, two inverters, no hysteresis | T-10, T-11 |
| `aib_tx_clk` | clk/clkb forwarded-clock driver: two `aib_tx_data` | T-04 |
| `aib_rx_clk` | clk/clkb forwarded-clock receiver: two `aib_rx_data` | T-04 |
| `aib_pad_esd` | diode pair + rail clamp at the pad, series resistor, secondary diodes | T-24, T-25 |

Each cell is a `.sch` plus `.sym`; the `.spice` next to it is derived with
`klt netlist`, never raw `xschem`. `xschemrc` carries the PDK search path.

**What this directory claims: the sources exist and the netlists are fresh.** Every
size is a first-cut placeholder and nothing here has been simulated, so no spec
row is claimed met. `w` is the total width over `ng` fingers; every finger is at or above the
0.15 um minimum (`XMp` 28u/28, `XMn` 14u/14, `Mclamp` 40u/20). Known open point: an inverter receiver's threshold moves with
the `mos_sf`/`mos_fs` corners and mismatch, so T-10 may need a different receiver;
the Monte Carlo testbench decides. Simulation, layout, LVS and the I/O-cell
assembly are separate issues. The forwarded-clock alignment (DLL) is out of scope.

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
