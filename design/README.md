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

**What this directory claims: the sources exist and the netlists are fresh.** The output
stage and the primary ESD diode were sized in issue #130 against the dc-static PVT-FULL run
(`sim/dc-static/records/20261108T004350Z/`, T-06/T-07/T-08/T-11/T-24/T-28 pass at 45/45); every
other size is still a first-cut placeholder. `w` is the total width over `ng` fingers; every
finger is at or above the 0.15 um minimum.

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
  layout still draws `Resd` 2 um x 2 um (`ESD_RES` in `layout/gen_io_column.py:129`) — the
  geometry of the completed DR-0017 regeneration (#140, PR #148; DRC
  `layout/records/20261110T082915Z`, LVS `layout/lvs/README.md` "Issue #140") — so this
  `l=1u` netlist size is the one change it does not cover. That LVS is a connectivity match
  on the layout and records `device.geometry_not_compared` for `rppd`, so it cannot
  distinguish the two resistor lengths; the drawn size rests on the generator table.

Known open point: an inverter receiver's threshold moves with
the `mos_sf`/`mos_fs` corners and mismatch, so T-10 may need a different receiver;
the Monte Carlo testbench decides. Layout, LVS and the I/O-cell
assembly are separate issues. The DR-0017 regeneration they owed is complete (#140, PR #148):
its DRC (`layout/records/20261110T082915Z`) and LVS (`layout/lvs/README.md` "Issue #140") evidence
covers the netlists as of that regeneration, with `Resd` drawn 2 um x 2 um (`ESD_RES`,
`layout/gen_io_column.py:129`); the LVS is a connectivity match that does not compare `rppd`
geometry, so the drawn size is attested by the generator table, not by the LVS.
The later `XResd l=1u` change above is not in the committed layout yet. The forwarded-clock
alignment (DLL) is out of scope.

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
