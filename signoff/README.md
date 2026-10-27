# signoff

`block-manifest.json` declares the block (`sg13g2-aib`, `mixed-signal`) and the
evidence it cites. `block-manifest.signoff.json` is the committed verdict of
record: the output of `klt signoff --manifest` for that manifest. Of the 22 T1
rows (11 items x analog and digital partitions), `1.analog`, `2.analog` and item 9 (both
partitions) read `met` (see "Attest item 1", "Item 2 (layout)" and "Item 9 attestation"); every
other row reads `unmet` / `no_evidence`, which is the honest state until evidence is cited. Evidence paths
resolve against the working directory, so always grade from the repo root.

The grader version is pinned in one place, `signoff/KLT_VERSION`; the CI
workflow reads it too. Do not use a dev-build `klt` to generate the record.

## Regenerate

From the repo root (`klt signoff` exits 3 while rows are unmet; that is expected):

```bash
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff \
  --manifest signoff/block-manifest.json --format json > signoff/block-manifest.signoff.json
```

Commit the result. Never hand-edit the record.

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

## What CI checks (`.github/workflows/ci.yml`)

- the pinned grader re-grades the manifest (exit 0 or 3 only) and the output
  matches the committed record byte for byte, so a hand-edited record fails;
- each item-9 envelope re-attests with `--check` (inventoried file hashes, pins
  and the committed cold-start outcome; the cold-start commands themselves are
  skipped, they need the PDK, ngspice and Icarus);
- each evidence directory (`spec design rtl verification sim layout
  measurements`) has a `README.md`;
- each `sim/**/records/<stamp>/record.json` has `record`, `utc_stamp` and
  `pdk.release_tag`, and contains no absolute path;
- `sim/` records (files under a `records/` or `corners/` directory) are
  append-only against the PR base, or the pre-push SHA on a push: added
  files pass, modified, deleted or renamed ones fail;
- each checker passes a self-test, including a seeded-bad input it must
  reject, before it is trusted (`scripts/ci/test_checkers.py`).

## What CI does not check

- that any evidence is true, or that a record's numbers are right;
- that any design meets the spec;
- anything needing the PDK, ngspice or klayout: no workflow installs them.
