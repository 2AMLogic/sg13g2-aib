# layout/pnr: routed `aib_datapath` (T1 item 2, digital)

`klt place-and-route` of the item 1 gate-level netlist (`design/synth/`, run
`run-2080128096d444afaa0672134a2e026a`, N = 20) onto `sg13g2_stdcell`, floorplan through
detailed route, with a `power` block. **P&R-tool output. It is not DRC, LVS or signoff timing
evidence**: DRC of this stream is in [`../records/`](../README.md#drc-records) (`klt drc`, not
this tool's own route DRC), LVS belongs to #40, STA corners to #43.

| File | What |
|---|---|
| `request.json` | the `klt place-and-route` request (the committed flow; `seed` 1) |
| `request.report.json` | the `--format json` report, verbatim |
| `.klt/place-and-route/aib_datapath.gds` | routed GDS (DEF merged with the stdcell GDS views) |
| `.klt/place-and-route/aib_datapath.v` | as-built routed gate-level verilog (CTS buffers, antenna repair included) |
| `.klt/place-and-route/aib_datapath.def` | routed DEF |
| `.klt/place-and-route/aib_datapath_route.spef`, `.sdf` | extracted parasitics and the SDF written from them |
| `.klt/place-and-route/pnr_*.tcl` | the generated OpenROAD stage scripts |

The OpenROAD checkpoints (`*.odb`), the 6 MB parasitics deck, per-corner metrics and logs are
not committed. The report still names them; they regenerate. The report's `*_path` fields hold
the absolute path of the worktree that produced it; the files sit at the repo paths above.

## Measured (report `status: ok`, `stage_reached: route`, `openroad 26Q3-1510-g6cb3f2b704`, klt 0.8.0)

Request corner `slow_1p08V_125C`, clock `clk` at 2.0 ns (T-01, 500 MHz; `rx_clk` is not
constrained, `klt place-and-route` takes one clock).

| Quantity | Value |
|---|---|
| die / core area | 26841.9 / 23442 um^2 (57.4 % utilization) |
| routed wirelength | 20674 um |
| `route_drc_violation_count` / `antenna_violation_count` | 0 / 0 (OpenROAD's own route DRC, not `klt drc`) |
| `setup_violation_count` / `hold_violation_count` | 0 / 0 |
| worst setup / hold slack over the 6 shipped liberty corners | 0.494 ns / 0.141 ns |
| `power.pdn` / `power.global_connect` | true / true |
| `power.tapcell_master` / `endcap_master` | null / null (the library ships neither) |

Slacks are the tool's estimates from global-route parasitics. The post-route SPEF pass
(`spef_sta`) annotated 241 of 421 design nets (`annotation_complete: false`), so its slack
(0.509 ns) is a cross-check only, and the SPEF/SDF are not timing signoff.

**Item 11 (digital) will not read `met` from this run**: the grader asks for a named
`power.tapcell_master` and this library has none. Not weakened locally; the gap is already tracked upstream as
`2AMLogic/klayout-tools#4199` (item 11 grades a built PDN `no_pdn` on a tapless library).

## Reproduce and check

```bash
export PDK_ROOT=<path containing ihp-sg13g2>
K="uvx --from klayout-tools==$(cat signoff/KLT_VERSION)"
$K klt place-and-route layout/pnr/request.json --pdk ihp-sg13g2 --format json > layout/pnr/request.report.json
$K klt place-and-route --check layout/pnr/request.report.json layout/pnr/request.json --pdk ihp-sg13g2          # cheap: exit 0
$K klt place-and-route --check layout/pnr/request.report.json layout/pnr/request.json --pdk ihp-sg13g2 --rerun  # full
$K python -I layout/attest_item2_digital.py     # rewrites signoff/attest/item2-digital.json
```

Recorded results (2026-10-27): the cheap `--check` exits 0 (input and deck hashes match). The
full `--rerun` ran once (about 3.5 min) and exits 0, status `match`; the rerun's GDS, verilog,
DEF and SPEF are byte-identical to the committed ones (the SDF differs only in its header).
After altering the netlist the cheap `--check` exits 3 (`provenance.input.content_hash` drifted).

The wrapper `~/.local/bin/openroad` runs a container and mounts only a `$PDK_ROOT`, so export
it as above or the first stage fails with "cannot read file".

Re-run after the T-05 remap settles (#29): the netlist, and so this stream, changes.
