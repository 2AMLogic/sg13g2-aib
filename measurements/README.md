# measurements

`characterization-report.md` is the T1 item 8 aggregate: one row for each of
T-01..T-30 of `spec/target-spec.md` (measured value, binding corner, status,
record link) and a digital Fmax / area / power table. Rows with no recorded
value read `not-yet-measured`; that is a gap, not a pass. Read the header of the
report before reading item 8 `met` as anything more than "the aggregate exists
and no recorded row fails".

Do not edit the report. It is generated from committed records and
`row-evidence.json` (row id to record, field, corner, comparator). When a record
for a row lands, add an entry there, then from the repo root:

```bash
python3 -I scripts/ci/gen_characterization_report.py           # rewrites the report and signoff/attest/item8.json
python3 -I scripts/ci/gen_characterization_report.py --check   # what CI runs
```

Re-cite the printed sha256 under `8.analog` and `8.digital` in
`signoff/block-manifest.json` and regenerate the signoff record
(`signoff/README.md`, "Item 8"). `--check` fails when the report, the envelope or
the manifest citation is stale.
