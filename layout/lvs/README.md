# layout/lvs: LVS for T1 item 4 (both partitions)

`klt lvs` (klt 0.8.0, `signoff/KLT_VERSION`, engine `klayout` with the `sg13g2` extraction deck) of the
drawn I/O cells against the item 1 analog netlists, and of the routed data path against its as-built
gate-level netlist.

| Partition | Result | Row |
|---|---|---|
| Digital (`aib_datapath`) | `status: match`, `power_connectivity.status: match` | `4.digital` reads `met` |
| Analog, whole stream (`aib_io_column`: 24 TX + 24 RX units) | `status: match`, 2928 / 2928 devices, 341 / 341 nets, 101 / 101 pins | `4.analog` reads `met`, citing `aib_io_column.report.json` |
| Analog, per cell (`aib_io_tx`, `aib_io_rx`, `aib_io_tx_clk`, `aib_io_rx_clk`) | `status: match` on all four (stream regenerated, issue #70; the earlier stream was `mismatch`) | not cited: item 4 takes one report per partition (2AMLogic/klayout-tools#4354) |

Issue #40 recorded the analog result as a mismatch and did not change the generator. Issue #70 fixed the
generator (below) and re-ran all four compares against the same, unchanged reference netlists; the
reports here are those re-runs. The item 1 sources, `gen_reference.py` and the P&R flow are unchanged.

## Files

| File | What |
|---|---|
| `gen_reference.py` | writes the assembled reference netlists from `design/*.spice`; `--check` compares to the committed files; `--diagnostic` writes the `*.diag.ref.spice` set |
| `<cell>.ref.spice` | reference for `aib_io_tx`, `aib_io_rx`, `aib_io_tx_clk`, `aib_io_rx_clk`; each header carries the sha256 of every `design/*.spice` it was built from |
| `<cell>.request.json`, `<cell>.report.json` | the `klt lvs` request and its `--format json` report, verbatim |
| `aib_io_column.ref.spice`, `aib_io_column.request.json`, `aib_io_column.report.json` | the whole analog stream (all 48 units) against one generated reference; this is the report `4.analog` cites |
| `<cell>.diag.*` | the same against the diagnostic reference (below). **Not a result reference.** |
| `aib_datapath.gate.spice`, `aib_datapath.extract.report.json` | layout side of the digital compare: `klt extract --abstract-cells 'sg13g2_*' --def-net-names` of the routed GDS |
| `digital.request.json`, `digital.report.json` | digital request and report, verbatim |
| `neg/` | negative controls: digital (the as-built netlist with one gate input rewired) and analog column (`aib_io_column.rewired.ref.spice`: one clamp finger gate moved from `VSS` to `VDDIO`), each with its report |

Provenance: the reference netlists are generated, not hand-written; `design/*.spice` is read only, so the
item 1 hashes are unchanged. Assembly follows `layout/README.md` ("Assembly choice"): the pad is the
`PAD` of `aib_pad_esd`; TX leaves `PADI` on the secondary diodes and `Mn2` only; RX takes its input on
`PADI`, behind the series resistor.

## Reproduce

From the repo root (`klt lvs` and `--check` resolve the relative paths in a request/report against the
current directory, so run them from `layout/lvs/`):

```bash
K="uvx --from klayout-tools==$(cat signoff/KLT_VERSION)"
python3 -I layout/lvs/gen_reference.py --check
export PDK_ROOT=<path containing ihp-sg13g2>              # digital only
cd layout/lvs
$K klt lvs aib_io_tx.request.json --format json > aib_io_tx.report.json      # exit 0: match
$K klt lvs digital.request.json --format json > digital.report.json          # exit 0: match
$K klt lvs --check digital.report.json                                        # exit 0
$K klt lvs --check aib_io_tx.report.json --rerun                              # exit 0 (the report is reproduced)
```

The digital layout netlist is regenerated with:

```bash
$K klt extract ../pnr/.klt/place-and-route/aib_datapath.gds --deck sg13g2 --top aib_datapath \
  --abstract-cells 'sg13g2_*' --def-net-names --pdk ihp-sg13g2 -o aib_datapath.gate.spice --format json \
  > aib_datapath.extract.report.json
```

Recorded results (2026-10-27): cheap `--check` exits 0 on all 5 result reports and on the 4 diagnostic
reports. Full `--check --rerun` exits 0 on the four analog result reports. For the digital report it
exits 1, because `--rerun` re-reads the reference as plain-element SPICE and cannot replay
`gate-level-verilog` (2AMLogic/klayout-tools#4353). The digital rerun was instead done by hand: the
request was run again and `status`, `mismatch_count`, `category_counts`, `counts`, `power_connectivity`
and `mismatches` are identical to the committed report, with equal layout and reference hashes.

## Digital

Reference `aib_datapath.v` (the as-built netlist, with CTS buffers and antenna repair), not the pre-P&R
`aib_datapath_synth.v`, because those cells exist only in the former. The layout side is abstracted to
standard-cell black boxes (3172 instances), so the compare covers signal connectivity between cells,
not transistors. Results:

- `status: match`; `power_connectivity.status: match` with `expected_nets` `{VDD: VDD, VSS: VSS}`,
  `finding_count: 0`, `unchecked_expected_pins: []`.
- Residual warnings, listed with the claim: `topology.power_only_pruned` (the filler cells
  `SG13G2_FILL_1`, `SG13G2_FILL_2` were removed from the layout side before comparing) and
  `topology.top_level_pins_anchored` (125 top-level pin names declared on both sides were anchored by
  name). The layout side exposes 421 pins (every net with a DEF name); the Verilog reference declares 125
  ports, so only those are anchored.
- Reach: `power_connectivity` checks per-instance pin-to-net, not rail continuity. The library ships no
  tap cells, so item 11 still does not read `met` (`layout/pnr/README.md`, 2AMLogic/klayout-tools#4199).
- Negative control (`neg/`): rewiring one mux input in a copy of the as-built netlist gives
  `status: mismatch` (klt exit 3). The committed report also fails `--check` (exit 3, `reference_sha256`
  drifted) when its reference is swapped for the rewired file.

## Analog

Device recognition (the question the issue asked first): the `sg13g2` deck extracts every device in the
drawn cells, including the ESD structure. For `aib_io_tx`: `dantenna` 1, `dpantenna` 2, `rppd` 3, and the
clamp NMOS fingers among 45 `nfet`. No device is left unrecognised, so no deck gap is filed for the ESD
devices. The drawn layout does not carry labels on the datatype the deck reads by default (the generator
writes datatype 1), so the requests pass `layout.label_layers`; with it the pins extract as named
(TX: `DIN OE PAD PD PUN VDDIO VSS`).

The compare on the stream drawn for #40 reported `mismatch` on all four cells (that run is in git history, commit `1226ed8`). Two differences between the drawn layout and the item 1
schematic explain it; each was isolated by a *diagnostic* reference (`gen_reference.py --diagnostic`)
that changes only that difference, and with both applied all four cells report `match` (`*.diag.report.json`,
`device` counts equal on both sides: 89, 33, 178, 66). The diagnostic is a localisation, not a result:
nothing is claimed against it.

1. **`PADI` is the `VSS` net in the extracted layout.** In both cell types the extracted second terminal
   of the series resistor, the anode of the `PADI` diode, the drain of the grounded-gate NMOS, and (RX)
   the gates of the receiver input stage are on `VSS`. In the schematic `PADI` is a separate net; in RX it
   is the receiver input. In the layout as extracted, the receiver input is tied to `VSS`. The cause is not
   localised here (a short, or the deck reading a connection that the generator's own connectivity trace,
   which covers only the labelled nets, does not examine).
2. **Finger width convention.** The item 1 netlists carry total `w` with `ng` fingers (the IHP
   model derives a finger as `w/ng`). The generator draws `w` per finger for every device with `ng > 1`
   except `Mp`, `Mn` and `Mclamp`: the eight TX logic devices (`Mnd1p`, `Mnd2p`, `Mnd1n`, `Mnd2n`, `Mnr1p`,
   `Mnr2p`, `Mnr1n`, `Mnr2n`) and the four RX devices (`Mi1p`, `Mi1n`, `Mi2p`, `Mi2n`), all `ng = 2`. Those
   are drawn twice as wide as simulated.

Both were fixed in `layout/gen_io_column.py` (issue #70); the reference netlists were not touched:

1. Cause: the clamp's bulk tap and the secondary diode `Dp2` were placed on the same router node, so
   the tap's `VSS` Metal1 overlapped the `Dp2` plate (`PADI`). `Dp2` and `Mn2` moved right, clear of the
   tap. `layout/check_io_column.py` now fails on this merge in the old stream (resistor end on a rail,
   found from the wire connectivity of unlabelled shapes too).
2. The generator table carries the finger width for every device and the self-check compares
   `w * ng` with the netlist `w` for all of them (it was three devices).

The `*.diag.*` files are the localisation recorded against the old stream. They are kept as the
record of that diagnosis and no longer reproduce (`--check` reports drift on the layout hash); they
are not evidence about the current stream.

Column compare (issue #40, the `4.analog` citation): `aib_io_column.request.json` extracts the top
cell (the TX column then the RX column; spares and the clk/clkb pair are ordinary units) and compares
it to a reference of 24 TX and 24 RX units on shared `OE`/`PUN`/`PD`/`VDDIO`/`VSS`, built by the same
`gen_reference.py` from the same item 1 netlists. Result: `status: match`, devices 2928/2928, nets
341/341, pins 101/101; warnings `device.geometry_not_compared`, `device.placeholder_value` (the
`rppd` value is not compared, as in the cell reports) and 45 `topology` entries (listed in the report).
`--check` exits 0 and `--check --rerun` exits 0. The negative control (`neg/`) reports `mismatch`
(exit 3, one `device.unmatched`) when one clamp finger gate is moved in the reference.

Limit of the column compare: klt names the repeated pins `DIN`, `DIN$1`, ... and `PAD`, `PAD$1`, ... in
its own extraction order, not slot order, and which `DIN$i` shares a unit with which `PAD$k` was read
once from the extracted column netlist and fixed in `gen_reference.py` (`PAD_OF_DIN`, `PAD_OF_DOUT`).
That is bookkeeping between identical units, not an electrical claim, and it is klt's numbering, not a
stable contract (`klt extract --help`); if a later `klt` renumbers, the column compare mismatches and
the table is re-read. Slot position, mirroring and which pad belongs to which wire are not tested by
this compare, because the units are interchangeable to LVS. The cell-level reports test each unit's wiring.

Not covered, and so not claimed:

- The resistor value and `L`/`W` are not compared: the `rppd` card in a `subckt-call` reference carries
  a placeholder `R`, and a resistor's `L`/`W` are secondary parameters (`device.placeholder_value`,
  `device.geometry_not_compared` warnings in every analog report).
- A second engine (`netgen`) was not run.
- `klt signoff` item 4 accepts one report per partition (2AMLogic/klayout-tools#4354), so the four
  per-cell reports cannot be cited together; the column report is cited instead.
