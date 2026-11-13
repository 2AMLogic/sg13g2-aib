# signoff

`block-manifest.json` declares the block (`sg13g2-aib`, `mixed-signal`) and the
evidence it cites. `block-manifest.signoff.json` is the committed verdict of
record: the output of `klt signoff --manifest` for that manifest. Of the 22 T1
rows (11 items x analog and digital partitions), item 1 (both partitions), `2.analog`, `2.digital`, `3.analog`, `3.digital`, `4.analog`, `4.digital`, `5.digital`, `7.digital`, `11.analog`, `11.digital` and items 9
and 10 (both partitions) read `met` (see "Item 3 (DRC)", "Item 4 (LVS)", "Item 1 / digital attestation", "Attest item 1 (analog)",
"Item 2 (layout, analog)", "Item 2 (layout, digital)", "Item 5 / digital evidence", "Item 7 / digital evidence", "Item 11 (power delivery)", "Item 9 attestation" and "Item 10 attestation"); `6.digital` reads `not_applicable`, `6.analog` `unmet` / `check_failed` (see "Item 6")
and `5.analog` `unmet` / `partial_coverage` (see "Item 5 / analog evidence");
`7.analog` reads `unmet` / `check_failed` (see "Item 7 / analog evidence" — the cited `klt pex`
runs extracted the cells and graded nothing, which is not the same as a spec row failing);
`8.analog` and `8.digital` read `unmet` / `check_failed` (see "Item 8" — three recorded rows
fail, so the aggregate's envelope is `status: fail`; that is the report following the records,
not a spec target being missed by the report);
every other row reads
`unmet` / `no_evidence`, which is the honest state until evidence is cited. Evidence paths resolve
against the working directory, so always grade from the repo root.

The grader version is pinned in one place, `signoff/KLT_VERSION`; the CI
workflow reads it too. Do not use a dev-build `klt` to generate the record.

## Regenerate

From the repo root (`klt signoff` exits 3 while rows are unmet; that is expected):

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff \
  --manifest signoff/block-manifest.json --format json > signoff/block-manifest.signoff.json
```

Run it from the repo root, as CI does: the grader opens each `file` in the
manifest relative to the working directory, not the manifest's directory, so
the manifest's `file` paths are repo-root-relative. Run from anywhere else,
item 1 grades `unmet` / `unreadable_evidence`. Commit the result. Never
hand-edit the record.

## Item 6 (Monte Carlo)

`6.digital` is a `not_applicable` outcome: `scripts/ci/gen_item6_digital.py --regenerate`
derives `item6/digital-spec.json` (a ratified JSON row list for the five deterministic
digital rows) from `spec/target-spec.md` and writes `item6/digital-statement.json`; the
manifest binds both by hash. `6.analog` cites the `klt yield` reports under
`sim/mc/records/` with `rows`, and `spec_rows."6"` declares all six STAT rows; rows
without a campaign are declared gaps (see `sim/mc/README.md`), so analog stays `unmet`.

## Item 1 / digital attestation

Item 1 is graded from an artifact-anchored `generic` envelope written by
`scripts/ci/check_design_sources.py`. `attest/item1-digital.inventory.json`
lists the RTL sources and the `klt synthesize` request, report, script and
netlist (`design/synth/`) with sha256 each. `attest/item1-digital.attest.json`
declares `t1_item: 1` and pins the inventory's hash; the manifest key
`1.digital` cites it with the same hash. `scripts/ci/check_design_sources.py
--regenerate` rewrites all three; then regenerate the record (above).

## Attest item 1 (analog)

`attest/item1-analog.inventory.json` lists the design sources and derived
netlists; `attest/item1-analog.json` is the envelope `klt signoff --attest 1`
produced from it (needs klt >= 0.8.0, so the pin). The freshness commands are
`local_only` because CI has no xschem or PDK. Regenerate after any `design/`
edit, then re-cite the new `content_hash` in the manifest and regenerate the record:

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff --attest 1 \
  --inventory signoff/attest/item1-analog.inventory.json -o signoff/attest/item1-analog.json
```

The manifest cites the envelope under `1.analog` with the inventory file's sha256.

## Item 2 (layout, analog)

`layout/attest_item2.py analog` writes `attest/item2-analog.json` through
`klt signoff --attest 2`: it first regenerates `layout/aib_io_column.gds` into a scratch
directory, requires the same geometry digest as the committed stream and a passing
`layout/check_io_column.py`, and only then passes klt that digest (`--hash-kind geometry`);
klt builds the envelope. The manifest cites it under `2.analog` with the
stream's sha256 (`provenance.input.content_hash`). The envelope is not DRC, LVS or
extraction evidence; see `layout/README.md`. Regenerate after any `layout/` change, then
re-cite the hash and regenerate the record:

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/attest_item2.py analog [--check]
```

## Item 2 (layout, digital)

`layout/attest_item2.py digital` writes `attest/item2-digital.json` through
`klt signoff --attest 2`, anchored on the routed GDS `layout/pnr/.klt/place-and-route/aib_datapath.gds` (the P&R report
itself is item 11 evidence, so item 2 cannot cite it). It refuses to write unless
`layout/pnr/request.report.json` is `ok`, `stage_reached: route`, `power.pdn: true`. The manifest
cites it under `2.digital` with the stream's sha256. Regenerate after re-running P&R
(`layout/pnr/README.md`), then re-cite the hash and regenerate the record:

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/attest_item2.py digital [--check]
```

## Item 3 (DRC)

`layout/records/<stamp>/drc_{analog,digital}.json` are verbatim `klt drc --deck sg13g2 --format json`
reports, one per partition, from the pinned grader and cited under `3.analog` / `3.digital` with
the input stream's sha256. `claims."3"` in the manifest quotes `coverage.layers_in_stream_without_rules`,
`coverage.rules_skipped` and `coverage.deck_scope` per partition and discloses the unmodeled pad,
latch-up and ESD rules. A re-run adds a new stamped directory and a re-cited manifest; old
records stay. Re-check with `klt drc --check <report>`.

## Item 4 (LVS)

`4.digital` cites the `klt lvs` report `layout/lvs/digital.report.json` directly (an `lvs`-kind
check: `status: match` and `power_connectivity.status` not `mismatch`; here both are `match`).
`4.analog` cites `layout/lvs/aib_io_column.report.json`, one `klt lvs` of the whole analog stream
(top `aib_io_column`, 48 I/O units, 3360 devices) against a generated reference; it is `status: match`
and reads `met`. Item 4 takes one report per partition (2AMLogic/klayout-tools#4354), so the four
per-cell reports (all `match`, issue #70) are not cited; they localise, the column report is the claim.
`power_connectivity` is `unchecked` there, because the `subckt-call` reference carries its own power pins
and they take part in the ordinary compare. Details, the
two layout differences behind the earlier mismatch, and the commands are in
[`layout/lvs/README.md`](../layout/lvs/README.md). The report's relative paths resolve against the
current directory, so `--check` runs from `layout/lvs/`; the grader runs from the repo root and
re-hashes the same files. Re-run after any change to `layout/pnr/` or `design/`, then regenerate the record.

## Item 5 / analog evidence

`5.analog` cites three `klt sim` reports as a list, each naming the `rows` it covers, and
`spec_rows."5.analog"` declares the **full** analog `SIM` row set — 21 rows, 13 covered and
8 declared gaps. The item reads **`unmet` / `partial_coverage`** with `failed_rows: []` and
`uncovered_rows: []`: every cited envelope passes and every covered row is genuinely covered,
but declared gaps remain.

Six of those gaps are **pending** — a measurement not yet made, which closes when the work is
done; progress toward T1 is tracked in #3, not here. **T-02 and T-04 are standing gaps**:
DR-0022 decided that T-02's `SIM` leg is a pointer to where the timing is graded (T-16, T-19,
T-20) and that T-04's is report-only by design, because the specification states no clk/clkb
crossing requirement. Neither closes through verification work — only a future revision of the
specification, or a consumer stating a requirement, would give T-04 a bound (DR-0022,
"Consequences"). So **closing the pending gap issues does not by itself make this item read
`met`**, and whether it can while two standing gaps are declared is an open accounting
question, tracked in #216. Do not settle it by deleting a row from the declared set.

| envelope | rows | result |
|---|---|---|
| `sim/dc-static/records/20261112T001207Z/report.json` | T-06, T-07, T-08, T-11, T-24, T-28 | 45/45 corners pass |
| `sim/channel-eye/records/20261111T235838Z-ch/report.json` | T-01, T-09, T-15, T-16, T-18, T-26 | 45/45 corners pass (CH, simulated) |
| `sim/clock-path/records/20261113T095936Z/report.json` | T-17 | 45/45 corners pass (CH) |

The declared row set is every row in `spec/target-spec.md` whose verification column has a
plain `SIM` leg and that is not owned by item 5 / digital or item 6 (`SIM-MC`: T-10, T-13,
T-14, T-19). **Re-derive it from the spec table** when a row changes — see `sim/README.md`
("Item 5 / analog: the declared row set") for the 8 gaps and their issues.

### Two citation rules this item depends on

Both were verified on 2026-11-13 against the pinned grader (0.9.0) with scratch copies of the
manifest; nothing in the checkout was written.

- **Only the CH channel-eye record is cited, not the TC one.** `sim/channel-eye/records/20261110T083756Z-tc/`
  carries the same row ids from the test configuration (bond-pad loaded loopback). Citing both
  would mix a modeled-die-to-die-channel claim with a test-configuration one under one item.
  `spec/test-configuration.md` keeps the two apart, so item 5 carries the CH claim only. This is
  a reading of that document, not a grader rule.
- **A `.json.gz` citation grades `unmet` / `unreadable_evidence`.** The channel-eye and
  clock-path records hold `report.json.gz`; a decompressed `report.json` was added beside each
  (byte-identical content, no re-run — the `.gz` is untouched, so the `sim/` append-only check
  passes) and that is what is cited. Filed upstream as `2AMLogic/klayout-tools#5452`. If a later
  pin fixes it, the citations can move back to the `.gz` and the copies be dropped.

### The declared row set is load-bearing, not decorative

The grader does **not** infer the row set. Verified against 0.9.0:

- Omitting a gap entry — or omitting `spec_rows."5.analog"` entirely — makes item 5 / analog
  read **`met`** on the 13 covered rows, with the 8 real gaps silently absent and
  `uncovered_rows` empty. Nothing flags the omission. This is why the full set is committed
  and must be re-derived from the spec table rather than edited by hand.
- The `rows` list on a citation is checked **only where the envelope's measurements carry
  `spec_row` tags** — not on every envelope. The channel-eye and clock-path reports are tagged
  (`T-01, T-09, T-15, T-16, T-18, T-26` and `T-02, T-04, T-17`), and under them a wrong `rows`
  entry is caught: listing a report-only row (T-02, whose measurements carry `limits: null`)
  under the passing clock-path envelope returns `uncovered_rows: ["T-02"]`, not coverage, and
  so does claiming a row that envelope has no measurements for (probed with T-05). **The
  dc-static report's measurements carry no `spec_row` field, and under it the grader accepts
  whatever `rows` says**: the same two probes moved to the dc-static citation both return
  `uncovered_rows: []` with `row_sources` `asserted`. So a row can be listed under an untagged
  envelope that does not measure it and nothing fails.
- `detail.row_sources` is what tells the two apart: `derived` where the grader matched the row
  against the envelope's own measurement names, `asserted` where it did not. **An `asserted`
  entry means "the grader did not check this row — verify it by hand", not "checked and
  covered".** Under `5.analog` the six `asserted` rows are exactly the dc-static ones, and they
  are covered on this manifest's word rather than the grader's check. Each was read against
  `sim/dc-static/records/20261112T001207Z/report.json` by hand; all have bounded, passing
  measurements over the envelope's 45/45 corners:

  | row | measurements | bound |
  | --- | --- | --- |
  | T-06 | `drv_{nl,ld}.t06_vol_v`, `drv_{nl,ld}.t06_voh_droop_v` | `max` 0.1 V |
  | T-07 | `lk_{0,5,10}.t07_t28_ipin_a` | `max` 1 uA |
  | T-08 | `drv_ld.t08_rout_{up,dn}_ohm` | 40-80 ohm |
  | T-11 | `t11_hyst_mv` | `max` 60 mV |
  | T-24 | `cap_{0,5,10}.t24_cpin_ff` | `max` 100 fF |
  | T-28 | `pu_on.t28_rpu_ohm`, `pd_on.t28_rpd_ohm`, `lk_*.t07_t28_ipin_a` | 10-20 kohm |

  Re-check this table by hand whenever a dc-static row's `rows` entry changes: the grader will
  not do it. The gap is filed upstream as `2AMLogic/klayout-tools#5462`.

## Item 5 / digital evidence

`attest/item5-digital/` holds the verbatim `klt` envelopes, cited as a list under
`5.digital` (the grader requires both kinds): three `klt functional-verification` runs
(`fv_shift_redundancy` 41/41, `fv_datapath_n20` and `fv_datapath_n8` 8/8) and two
`klt sta` runs (`sta_clk`, `sta_rx_clk`), each over `slow_1p08V_125C` and
`fast_1p32V_m40C` at a 2.0 ns period (T-01, 500 MHz). Requests live in
`verification/klt/` and `design/synth/aib_datapath.sta_*.json`.

- The two negative controls (`fv_neg_shift_edge`, `fv_neg_extra_stage`) are committed
  but **not cited**: they must fail (klt exit 3), and do (39/41, 6/8).
- STA is `geometry_source: netlist_estimate` (the `klt synthesize` netlist, ideal wires,
  no SPEF). It is not post-route; re-run after #38. The netlist predates the T-05 mux
  decision (#29 / PR #32), so it does not contain the mux; re-synthesize and re-run
  both after that merges.
- `klt sta` takes one `clock_port`, and the datapath has two clocks, so there is one
  request per clock. In each, the registers on the other clock are `unclocked` and
  the outputs have no output delay, so every envelope reports
  `constraint_completeness: incomplete` (180 unconstrained endpoints, 80 unclocked
  registers) while `timing_status` is `constrained`. The grader reads the latter.
  The completeness gap is a real limit of this evidence: no I/O budget is
  invented here, and the TX-to-RX path across the two clocks is not timed.
- `klt functional-verification` carries no provenance block, so the manifest pins no
  `content_hash` on these entries. The runner reduces the three absolute scratch
  paths in `environment` to file names; nothing else is edited.

Regenerate (needs `uv`, `iverilog`, `openroad`, and `PDK_ROOT`), then regenerate the record:

```bash
PDK_ROOT=<path containing ihp-sg13g2> python3 verification/klt/run_evidence.py
```

## Item 7 / analog evidence

`7.analog` reads `unmet` / `check_failed`, citing the four `klt pex --extract-only` reports in
`layout/pex/records/20261113T130842Z/`. **`check_failed` here does not mean a spec row failed
post-layout — no spec row was measured post-layout at all.** It means the cited `klt pex` runs
report `status: "not_checked"`: they extracted the drawn I/O cells (cleanly, with
`body_bias: "biased"` and the input hash equal to the committed `layout/aib_io_column.gds`) and
graded nothing, because `klt pex` cannot simulate an sg13g2 extraction. The deck writes the
pad/ESD antenna diode as a bare `D` card naming `dpantenna`, which the PDK defines only as a
`.subckt`, so ngspice stops at netlist load. Reproduced in
`layout/pex/records/20261113T130846Z/` and filed upstream as
[2AMLogic/klayout-tools#5491](https://github.com/2AMLogic/klayout-tools/issues/5491); the full
account, including the two alternatives that were rejected rather than used, is in
[`../layout/pex/README.md`](../layout/pex/README.md). Two further gaps found in the same
bring-up are filed there too: #5492 (a dropped `options.osdi_preload`, worked around by naming
a backend) and #5493 (one `--top` per run cannot express a link testbench, which is why the
`channel-eye` and `clock-path` rows have no bench here).

The citation is deliberate: it is a true `klt pex` report about this layout, and `check_failed`
naming it leads a reader to the reports, where `no_evidence` would have hidden that the
extraction exists. `spec_rows."7.analog"` declares all 21 rows as gaps with the reason — the
13 rows `5.analog` grades plus its 8 carried-forward gaps, with the same trackers (#216, #192,
#193, #194, #195, #196, #176). Today's grader does not consume `spec_rows` for item 7 (only
items 5 and 6), so that block is a declaration in the manifest rather than something the record
rolls up; it is kept so the gap list is machine-readable in one place.

## Item 7 / digital evidence

`attest/item7-digital/fv_post_route.json` is the existing cocotb suite
(`verification/test_datapath.py`, unchanged) run through `klt functional-verification` on
the **post-route** netlist with the routed SDF annotated (8/8). It is cited under `7.digital`.
Inputs, pinned by sha256 in `run_evidence.py` (the run refuses if either changes):
`layout/pnr/.klt/place-and-route/aib_datapath.v` `a27bec23…` and `aib_datapath_route.sdf`
`3e8edd07…`, plus the `sg13g2_stdcell` Verilog models from `PDK_ROOT`. The SDF is one corner,
`slow_1p08V_125C` (1.08 V, 125 C), the binding corner; klt's `corner: max` selects its
min:typ:max column. There is no second SDF, so no fast-corner post-route run exists.

- **Negative control** (`fv_neg_post_route_timing`, committed, **not cited**; klt exit 3, 1/8):
  the same run on a copy of the SDF in which every delay of the mux driving `tx_wire[0]`
  is 12 ns, longer than the 10 ns test period. It fails for that reason (round trips lose
  bit-exactness and the TX marker never reaches the wire); only `l1_ignores_rx_wire` still passes.
- **Derived SDF.** `aib_datapath_route.tb.sdf` is the routed SDF with one mechanical edit:
  every `(INSTANCE ...)` is prefixed with `dut`, because the bench instantiates the netlist as
  `dut` and klt annotates at the bench top. `aib_datapath_route.tb.neg_timing.sdf` adds the
  inflated arc. `run_evidence.py` regenerates both from the committed SDF. Both are kept as
  committed evidence inputs and pinned by sha256 in the manifest's `derived_inputs."7.digital"`
  block, with the routed SDF they derive from (a separate key because the grader reads every
  `evidence` entry as an envelope). `python3 -I scripts/ci/check_item7_sdf.py` (PDK-free, run in CI)
  fails if the routed SDF is not the pinned one, if regeneration does not reproduce the committed
  bytes, or if the committed bytes differ from the pins. If a P&R re-run changes the routed SDF,
  re-cite `PNR_SHA256`, the SDFs and the pins together. The routed SPEF and DEF from the same
  P&R run (read by no item) are pinned the same way under `derived_inputs."pnr.digital"`;
  `python3 -I scripts/ci/check_pnr_pins.py` fails if either differs from its pin, so a re-run
  re-cites those too.
- **Bench.** `verification/tb_datapath_postroute.v` is `tb_datapath.v` with `N` fixed at 20
  (klt rejects `request.parameters` together with `options.sdf`, and the routed netlist has no
  `N`) and no parameter list (klt's SDF wrapper needs a plain `module` declaration). It also holds
  `tx_d0`/`tx_d1` for 1 ns after the clock edge. The suite moves them on the edge; the routed clock
  tree delays the edge at the registers, so without the hold the stimulus races it (observed: the
  latency tests never saw their marker). That is a declared input-hold assumption of the bench,
  not a result about the netlist, and it is not timed by any STA here.
- **Dropped by the simulator** (recorded in the envelope's `environment.sdf.dropped`): all 159
  `TIMINGCHECK` sections (Icarus does not implement them, so setup/hold/recovery/width limits are
  **not** checked against the SDF; the evidence is delay-annotated function, not timing closure), and
  41 `INTERCONNECT` entries from bit-selected top-level inputs, all zero-delay. `annotated: true`,
  `partial: true`.
- Not shown: skew across a real I/O column, the TX-to-RX channel (zero-delay wire, `rx_clk` a fixed
  quarter cycle behind `clk`), or any fast-corner behaviour.

Regenerate with the Item 5 command (it now also writes this directory).

## Item 8 (characterization report)

`measurements/characterization-report.md` is generated by
`scripts/ci/gen_characterization_report.py` from the 30 spec rows, the committed
records named in `measurements/row-evidence.json`, and the STA / place-and-route
reports. `attest/item8.json` is a bare `generic` envelope (`t1_item: 8`) whose
`provenance.input.content_hash` is the report's sha256; the manifest cites the
same envelope and hash under `8.analog` and `8.digital`. `status: pass` means no
recorded row fails. Rows without a record read `not-yet-measured` in the report;
`met` does not say they pass. The script also checks (`--check`, run in CI) that
the report, envelope and manifest hash agree. Regenerate after any change to a
cited record or the mapping, then re-cite the hash and regenerate the record.

The generator also refuses to run — writing and under `--check` — when this
manifest cites per-row evidence the map does not grade. Every `(file, row)` pair
under `evidence."5.analog"` and `evidence."6.analog"` must have an entry in
`row-evidence.json` citing a file in that same record directory (a `rows.json` or
`yield.json` digest beside a `klt sim` envelope counts). So the manifest is the
single list of which rows have a record and the map only says how each is graded;
a record cited for signoff can no longer be missing from the aggregate, which is
how 13 rows — three of them recorded failures — read `not-yet-measured` here
while already being cited for item 5 and item 6 (issue #230). The map may still
carry extra entries the manifest does not cite; the check is one-directional.

**Item 8 currently reads `unmet` / `check_failed`, and that is the honest state.**
T-10, T-15 and T-16 each have a committed `klt yield` record whose verdict is
`fail`, so the envelope is `status: fail` and the aggregate says so. No spec
target, limit or comparator was changed, and no record under `sim/*/records/` was
touched, to produce it. The `met` reading it replaced was an artefact of those
records never being read.

## Item 9 attestation

`attest/item9-{analog,digital}.inventory.json` list the testbenches, the
cold-start command and the tool/PDK pins; `attest/item9-{analog,digital}.json`
are the envelopes `klt signoff --attest` wrote from them. The manifest cites each
envelope under `9.analog` / `9.digital` with the inventory's
`provenance.input.content_hash`. Never hand-write an envelope. From the repo root,
after the PDK and OSDI models are built (`sim/README.md`, "Reproduce"):

```bash
for p in analog digital; do
  uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff --attest 9 \
    --inventory signoff/attest/item9-$p.inventory.json -o signoff/attest/item9-$p.json
done
```

Then update the two `content_hash` values in the manifest and regenerate the
record. The analog cold start (`run_smoke.sh`) writes a new
`sim/pdk-smoke/records/<UTC>/` on every run: delete the untracked directory
before committing. The digital cold start calls `/usr/bin/python3` by absolute
path because `uvx` puts its own `python3`, without cocotb, first on `PATH`.
Both cold starts are `local_only`, so CI skips them under `--check`.

Inventories cover only the benches that exist today; extend them (and re-attest)
as new benches land.

## Item 10 attestation

`attest/item10.inventory.json` lists the hygiene artifacts (README, LICENSE, the
CI workflow) and the PDK-free checks (`scripts/ci/test_checkers.py`,
`scripts/ci/check_evidence_format.py`); `attest/item10.json` is the envelope
`klt signoff --attest 10` wrote from it. One envelope is cited under both
`10.analog` and `10.digital`, with the inventory's `content_hash`. The RTL
benches are not repeated here: they are the item 9 cold start and run in the CI
`rtl` job. From the repo root:

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff --attest 10 \
  --inventory signoff/attest/item10.inventory.json -o signoff/attest/item10.json
```

Then update the two `content_hash` values for item 10 in the manifest and
regenerate the record.

Re-attest as the last step, after `README.md` and `.github/workflows/ci.yml`
are final: both are hashed into the envelope, so any later edit to either
makes the CI `--check` exit 3 (`drifted`).

## What CI checks (`.github/workflows/ci.yml`)

- the pinned grader re-grades the manifest (exit 0 or 3 only) and the output
  matches the committed record byte for byte, so a hand-edited record fails;
- each item-9 envelope re-attests with `--check` (inventoried file hashes, pins
  and the committed cold-start outcome; the cold-start commands themselves are
  skipped, they need the PDK, ngspice and Icarus);
- the item-10 envelope re-attests with `--check`, re-running its two checkers;
- each evidence directory (`spec design rtl verification sim layout
  measurements`) has a `README.md`;
- each `sim/**/records/<stamp>/record.json` has `record`, `utc_stamp` and
  `pdk.release_tag`, and contains no absolute path;
- `sim/` records (files under a `records/` or `corners/` directory) are
  append-only against the PR base, or the pre-push SHA on a push: added
  files pass, modified, deleted or renamed ones fail;
- `scripts/ci/check_design_sources.py`: every inventory file re-hashes, the RTL
  sources match the synthesis report's input hash, the netlist matches its
  `netlist_sha256`, and the envelope and manifest pin the current inventory;
  edited RTL or a stale netlist fails. It does not re-hash the standard-cell
  liberty (no PDK on the runner); `klt synthesize --check <report> [--rerun]`
  covers that locally (`design/README.md`);
- each checker passes a self-test, including a seeded-bad input it must
  reject, before it is trusted (`scripts/ci/test_checkers.py`).

## Item 11 (power delivery)

`11.analog` cites `layout/erc/io_cells.erc-report.json` plus item 4's analog LVS report and
reads `met`. `11.digital` cites `layout/erc/aib_datapath.erc-report.json`, the digital LVS report
and the P&R response (`layout/pnr/request.report.json`), and reads `met` (klt 0.9.0). The
standard-cell library ships no tapcell or endcap master, so the routed result has `power.pdn: true`,
`power.tapcell_master: null` and no tapcells; klt 0.9.0 (`2AMLogic/klayout-tools#4199`, fixed by
klayout-tools PR #4250) grades that as `met` when the P&R response states `power.tapless: true`,
which `klt place-and-route` 0.9.0 emits for `sg13g2_stdcell`. Under klt 0.8.0 the row read
`no_pdn`. Getting to `met` took three steps, none of which changes the P&R request or relaxes a
check: the P&R report was regenerated under 0.9.0 (same request; the routed GDS, DEF and
netlist reproduce byte-identically), the digital `klt erc` spec's stackup names were changed to
the PDK's own `Metal1`..`TopMetal2` (0.9.0 matches `power.straps[].layer` against them exactly;
`layout/erc/gen_specs.py`), and the ERC report was re-run. Evidence and caveats:
`layout/erc/README.md`.

## Re-pin to klt 0.9.0

The pin went from 0.8.0 to 0.9.0. Besides item 11 (digital), 0.9.0 binds the item 1 analog
envelope to every file in its input set, and the committed envelope had been generated from an
older `design/aib_pad_esd.sch` / `.spice`, which 0.8.0 did not detect (`klt signoff --attest 1
--check` on 0.8.0 already reported drift). `1.analog` therefore read `stale_evidence` until the
envelope was regenerated and the manifest re-cited with the new input-set digest. The
`item2-analog` and `item2-digital` envelopes were rewritten for the new `klt_version`, then
rebuilt with `klt signoff --attest 2` (see issue 120), which populates `klayout_version`. The
`signoff/attest/` envelopes not named here were not regenerated; they still record the klt that
produced them — except `item9-digital.json`, which issue #217 regenerated under 0.9.0 when
`verification/run_tb.py` changed, so it now records `klt_version: 0.9.0`. A `--check` of a
0.8.0-produced envelope under the 0.9.0 pin passes (`item9-analog.json` still does), so
`klt_version` is recorded provenance here, not something the re-attest compares.

## What CI does not check

- that any evidence is true, or that a record's numbers are right;
- that any design meets the spec;
- anything needing the PDK, ngspice or klayout: no workflow installs them.
