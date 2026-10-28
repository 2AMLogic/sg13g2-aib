# layout/erc

`klt erc` supply evidence for T1 item 11 (power delivery, structural), one run per partition.
Pinned klt: `signoff/KLT_VERSION`. Structural result about the die; valid for both the modeled
channel and the loopback test configuration, and makes no channel claim.

| Partition | Layout (top) | Spec | Report | Supplies |
|---|---|---|---|---|
| analog | `layout/aib_io_column.gds` (`aib_io_column`) | `io_cells.erc-spec.json` | `io_cells.erc-report.json` | VDDIO, VSS |
| digital | `layout/pnr/.klt/place-and-route/aib_datapath.gds` (`aib_datapath`) | `aib_datapath.erc-spec.json` | `aib_datapath.erc-report.json` | VDD, VSS |

Result: each supply resolves to one island; no `erc.unconnected_net`, `erc.supply_short`,
`erc.unlabelled_conductor` or `erc.missing_tie`; no `erc_coverage.skipped` entry.

## Reading the evidence honestly

- **No `roles`.** No routed layer is owned by a single supply (both rails share the strap and
  metal layers), so `supply_unlabelled_islands` is `{}` as unmeasured, not as measured clean.
- **N-well taps are asserted, not derived.** SG13G2 draws the n-well tap as Activ in NWell and
  outside pSD. A tie can narrow a tap only by intersecting layers, so the n-well tie uses
  `tap_boxes` generated from the stream by `gen_specs.py` (reported as `checked_by_assertion`).
  The p-substrate tie uses `tap_requires` over the complement of NWell
  (`checked_by_well_assertion`). Without the boxes the n-well tie is `degenerate_tap_declaration`.
  Regenerate the specs after any change to either stream.
- **Reports are `--findings-only`.** Antenna tables are not computed, so `klt erc` exits 4
  (`status: not_checked`) while `erc_status` is `clean`; item 11 grades `erc_status`.
- **Seeded check.** Clearing every Via2 shape in a scratch copy of the I/O column makes the
  analog spec report 313 `erc.missing_tie` findings, so the spec measures what it claims.
- **Digital row stays `unmet`** (`no_pdn`): the routed result has no tapcell master. See
  `signoff/README.md`.

## Reproduce

```bash
K="uvx --from klayout-tools==$(cat signoff/KLT_VERSION)"
$K python -I layout/erc/gen_specs.py
$K klt erc --validate-spec layout/erc/io_cells.erc-spec.json
$K klt erc layout/aib_io_column.gds layout/erc/io_cells.erc-spec.json --top aib_io_column \
  --deck sg13g2 --findings-only --omit-antenna-tables --compact --format json \
  > layout/erc/io_cells.erc-report.json    # exit 4 is expected
$K klt erc --check layout/erc/io_cells.erc-report.json
```

The digital run is the same with `aib_datapath` and its GDS.
