# signoff

`block-manifest.json` declares the block (`sg13g2-aib`, `mixed-signal`) and an
`evidence` map (today: item 1 / digital only). `block-manifest.signoff.json` is the committed verdict of
record: the output of `klt signoff --manifest` for that manifest. T1 has 22 rows
(11 items x analog and digital partitions); every row without cited evidence
reads `unmet` / `no_evidence`, and only item 1 / digital reads `met`.

The grader version is pinned in one place, `signoff/KLT_VERSION`; the CI
workflow reads it too. Do not use a dev-build `klt` to generate the record.

## Regenerate

From the repo root (`klt signoff` exits 3 while rows are unmet; that is expected):

```bash
cd signoff
uvx --from "klayout-tools==$(cat KLT_VERSION)" klt signoff \
  --manifest block-manifest.json --format json > block-manifest.signoff.json
```

Commit the result. Never hand-edit the record.

## Item 1 / digital attestation

The pinned grader (0.7.0) has no `--attest` flag; item 1 is graded from an
artifact-anchored `generic` envelope. `attest/item1-digital.inventory.json`
lists the RTL sources and the `klt synthesize` request, report, script and
netlist (`design/synth/`) with sha256 each. `attest/item1-digital.attest.json`
declares `t1_item: 1` and pins the inventory's hash; the manifest key
`1.digital` cites it with the same hash. `scripts/ci/check_design_sources.py
--regenerate` rewrites all three; then regenerate the record (above).

## What CI checks (`.github/workflows/ci.yml`)

- the pinned grader re-grades the manifest (exit 0 or 3 only) and the output
  matches the committed record byte for byte, so a hand-edited record fails;
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
