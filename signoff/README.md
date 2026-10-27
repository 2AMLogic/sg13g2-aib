# signoff

`block-manifest.json` declares the block (`sg13g2-aib`, `mixed-signal`) and the
evidence it cites. `block-manifest.signoff.json` is the committed verdict of
record: the output of `klt signoff --manifest` for that manifest. Of the 22 T1
rows (11 items x analog and digital partitions), items 9 and 10 read `met` for
both partitions (see "Item 9 attestation" and "Item 10 attestation"); every other row reads `unmet` /
`no_evidence`, which is the honest state until evidence is cited. Evidence paths
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
- each checker passes a self-test, including a seeded-bad input it must
  reject, before it is trusted (`scripts/ci/test_checkers.py`).

## What CI does not check

- that any evidence is true, or that a record's numbers are right;
- that any design meets the spec;
- anything needing the PDK, ngspice or klayout: no workflow installs them.
