# signoff

`block-manifest.json` declares the block (`sg13g2-aib`, `mixed-signal`) and an
`evidence` map (today only `1.analog`). `block-manifest.signoff.json` is the committed verdict of
record: the output of `klt signoff --manifest` for that manifest. Every T1 row
(22: 11 items x analog and digital partitions) reads `unmet` / `no_evidence`
except those with cited evidence: `1.analog` is `met` (sources exist, netlists
fresh; no spec row). The honest state is `unmet` until evidence is cited.

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
- each checker passes a self-test, including a seeded-bad input it must
  reject, before it is trusted (`scripts/ci/test_checkers.py`).

## What CI does not check

- that any evidence is true, or that a record's numbers are right;
- that any design meets the spec;
- anything needing the PDK, ngspice or klayout: no workflow installs them.
