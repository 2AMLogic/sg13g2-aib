# signoff

`block-manifest.json` declares the block (`sg13g2-aib`, `mixed-signal`) and the
evidence it cites. `block-manifest.signoff.json` is the committed verdict of
record: the output of `klt signoff --manifest` for that manifest. Of the 22 T1
rows (11 items x analog and digital partitions), item 1 (both partitions), `2.analog`, `2.digital`, `3.analog`, `3.digital`, `4.digital`, `5.digital` and items 9
and 10 (both partitions) read `met` (see "Item 3 (DRC)", "Item 4 (LVS)", "Item 1 / digital attestation", "Attest item 1 (analog)",
"Item 2 (layout, analog)", "Item 2 (layout, digital)", "Item 5 / digital evidence", "Item 9 attestation" and "Item 10 attestation"); every other row reads
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

klt 0.8.0 has no `--attest 2`, so `layout/attest_item2.py` writes
`attest/item2-analog.json`: it regenerates `layout/aib_io_column.gds` into a scratch
directory, requires the same geometry digest as the committed stream and a passing
`layout/check_io_column.py`, and only then writes the envelope (a `provenance.regeneration`
claim with `hash_kind: geometry`). The manifest cites it under `2.analog` with the
stream's sha256 (`provenance.input.content_hash`). The envelope is not DRC, LVS or
extraction evidence; see `layout/README.md`. Regenerate after any `layout/` change, then
re-cite the hash and regenerate the record:

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/attest_item2.py [--check]
```

## Item 2 (layout, digital)

`layout/attest_item2_digital.py` writes `attest/item2-digital.json`, a `generic` envelope
anchored on the routed GDS `layout/pnr/.klt/place-and-route/aib_datapath.gds` (the P&R report
itself is item 11 evidence, so item 2 cannot cite it). It refuses to write unless
`layout/pnr/request.report.json` is `ok`, `stage_reached: route`, `power.pdn: true`. The manifest
cites it under `2.digital` with the stream's sha256. Regenerate after re-running P&R
(`layout/pnr/README.md`), then re-cite the hash and regenerate the record:

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/attest_item2_digital.py [--check]
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
`4.analog` cites nothing and reads `unmet` / `no_evidence`: the four per-cell reports are all
`match` (issue #70), but item 4 takes one report per partition (2AMLogic/klayout-tools#4354). Details, the
two layout differences behind the earlier mismatch, and the commands are in
[`layout/lvs/README.md`](../layout/lvs/README.md). The report's relative paths resolve against the
current directory, so `--check` runs from `layout/lvs/`; the grader runs from the repo root and
re-hashes the same files. Re-run after any change to `layout/pnr/` or `design/`, then regenerate the record.

## Item 5 / digital evidence

`attest/item5-digital/` holds the verbatim `klt` envelopes, cited as a list under
`5.digital` (the grader requires both kinds): three `klt functional-verification` runs
(`fv_shift_redundancy` 81/81, `fv_datapath_n20` and `fv_datapath_n8` 8/8) and two
`klt sta` runs (`sta_clk`, `sta_rx_clk`), each over `slow_1p08V_125C` and
`fast_1p32V_m40C` at a 2.0 ns period (T-01, 500 MHz). Requests live in
`verification/klt/` and `design/synth/aib_datapath.sta_*.json`.

- The two negative controls (`fv_neg_shift_edge`, `fv_neg_extra_stage`) are committed
  but **not cited**: they must fail (klt exit 3), and do (79/81, 6/8).
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

## What CI does not check

- that any evidence is true, or that a record's numbers are right;
- that any design meets the spec;
- anything needing the PDK, ngspice or klayout: no workflow installs them.
