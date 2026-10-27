# layout

I/O cell and I/O column stream for T1 item 2 (layout, analog partition). Rows: T-22
(55 um pitch), T-23 (area per wire), DR-0007 (pitch, pad), DR-0010 (column and skew
matching).

**Status of this stream: it exists, regenerates, and passes structural checks. It is not
DRC, LVS or extraction evidence.** Those are separate issues (#39, #40, #42).

The digital partition's routed stream (`klt place-and-route` of the synthesized data path) is
in [`pnr/`](pnr/README.md).

## Files

| File | What |
|---|---|
| `gen_io_column.py` | the generator; the only source of the stream |
| `aib_io_column.gds` | committed stream, written by the generator (no timestamps, byte-reproducible) |
| `check_io_column.py` | structural checks: unit cell 55 x 100 um, column length, mirror symmetry about the column centre, gap-free abutment, no device shape under the pad opening |
| `record_stats.py` | writes `stats/`: `klt stats` JSON per cell and `stats/t22-t23.json` |
| `attest_item2.py` | writes `../signoff/attest/item2-analog.json` after regenerating and checking |

Provenance: every shape comes from `gen_io_column.py`; nothing is hand-drawn. Device
type, W, L, ng and the net on each terminal are repeated from `design/*.spice` in the
generator, and the run aborts if they disagree with those netlists.

## Regenerate

From the repo root, with the pinned grader (`signoff/KLT_VERSION`):

```bash
K="uvx --from klayout-tools==$(cat signoff/KLT_VERSION)"
$K python -I layout/gen_io_column.py -o layout/aib_io_column.gds
$K klt diff layout/aib_io_column.gds <(git show HEAD:layout/aib_io_column.gds)   # equal after a clean regenerate
$K python -I layout/check_io_column.py layout/aib_io_column.gds
python3 -I layout/record_stats.py
$K python -I layout/attest_item2.py            # rewrites signoff/attest/item2-analog.json
```

CI has no klayout stack wired for this, so the generator run is not CI-checked; CI re-grades
the manifest, which re-hashes the committed stream against the citation. The generator
needs only `klayout` (it ships in the klt environment) and the repo's `design/` netlists;
no PDK install is read.

## What is drawn

Cells: `aib_io_tx` and `aib_io_rx` (unit cells, 55 x 100 um, each with its own pad, the
`aib_pad_esd` structure and the `aib_tx_data` driver or `aib_rx_data` receiver),
`aib_io_tx_clk` / `aib_io_rx_clk` (the clk and clkb cells: two unit cells abutted),
`aib_io_column_tx` / `aib_io_column_rx` (24 slots each) and the top `aib_io_column` (the
TX column then the RX column).

- **Assembly choice.** The bond pad is the `PAD` of `aib_pad_esd`. The driver output is on
  `PAD`; the receiver input is on `PADI`, behind the series resistor. The TX cell leaves
  `PADI` on the secondary diodes only. No assembled I/O-cell schematic exists yet; LVS
  (#40) needs one.
- **Column (DR-0010).** Slots 0..23: spare, 10 data wires, clk, clkb, 10 data wires,
  spare. Odd slots are mirrored about their own vertical centre line, so neighbours abut
  mirror-to-mirror and the column is mirror-symmetric about its centre (slot k and slot
  23-k); `check_io_column.py` verifies that layer by layer. clk and clkb sit at the centre.
  The shared `OE`/`PUN`/`PD` controls and the `VDDIO`/`VSS` rails run across each cell edge to
  edge on Metal3 and join by abutment. The cells carry no clock input in the analog
  partition (the DDR registers are in the digital data path), so the "balanced clock tree"
  here is only the central placement of the clk/clkb cells; their `DIN` stubs are mirror
  images of each other. Any clock tree to the data path belongs to the digital flow.
- **Length (DR-0007).** 20 data wires span 20 x 55 = 1100 um. The column is 24 slots =
  1320 um because it adds the two AIB spare wires (DR-0003) and the clk/clkb pair.
- **Pad (DR-0007).** Passivation opening 40 x 40 um (>= 30 um), TopMetal1 2 um beyond it,
  a Metal3-Metal5 landing stack beneath. The pad occupies the top 44 um of the cell; every
  device is below it (y < 54 um), so nothing sits under the pad. The pad is inside the 55 x
  100 um box, so T-23 is measured with the pad included, which is the conservative reading.
- **Routing.** Devices are placed by hand-chosen rows in the generator; nets are routed
  by a deterministic maze router on a 0.8 um grid (Metal2 vertical, Metal3 horizontal).
  The unit cells route to completion (no unrouted terminal), and a connectivity trace over
  the metal stack finds no short between the labelled nets `PAD`, `VDDIO`, `VSS`, `OE`,
  `PUN`, `PD` and `DIN`/`DOUT`. That trace is not LVS: opens and wrong connections are not
  excluded.

## Measured, and what is not

`stats/t22-t23.json` (from `klt stats` of the drawn cells, labelled layout-measured and
pre-extraction): unit-cell pitch 55.0 um, abutted pair 110.0 um (55.0 um each), area per
wire 5500 um2 (55 x 100 um bounding box, pad included). T-22 and T-23 sit exactly at
their limits; they are met, with no margin, and the 80 um fallback is not invoked. The
bounding box of a cell that is defined to be 55 x 100 um (the `prBoundary`) says the
cell was drawn to that box; the contents are what must fit, and they do (every drawn
shape is inside it).

Not established by this stream, each its own issue: DRC (#39), LVS (#40), ERC (#41),
extracted parasitics and skew (#42, #44), the ESD level T-25 (diode and clamp drawn at
the schematic sizes, but supply and discharge-path metal widths are not sized for 0.5 A,
and the deck has no pad or ESD coverage, 2AMLogic/klayout-tools#3854), T-24 pad
capacitance. `klt drc --deck sg13g2` on the unit cells reports 0 violations, but that deck
is unreleased and partial (12 stream layers unchecked, pad and latch-up rules not
modelled), so it is a smoke result, not evidence.

Tool gaps met: `klt signoff --attest` has no item 2 producer
(2AMLogic/klayout-tools#4188, #4221), so `attest_item2.py` writes the envelope;
the PDK PCell library cannot be loaded from the release tarball, so devices are drawn
from base layers (#4236); no symmetry or abutment check exists (#4237). `klt gen-compose`
was not tried for the column.
