# measurements

`characterization-report.md` is the T1 item 8 aggregate: one row for each of
T-01..T-30 of `spec/target-spec.md` (measured value, binding corner, status,
record link) and a digital Fmax / area / power table. Rows with no recorded
value read `not-yet-measured`; that is a gap, not a pass. Read the header of the
report before reading item 8 `met` as anything more than "the aggregate exists
and no recorded row fails".

Item 8 does not read `met` today. T-10, T-15 and T-16 each have a committed
`klt yield` record whose verdict is `fail`, so the envelope is `status: fail` and
`8.analog` / `8.digital` read `unmet` / `check_failed`. That is the report
following the records; no spec target, limit or comparator was changed and no
record was touched to produce it.

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

Adding the entry is not left to memory. The generator refuses to run — writing
and under `--check` — unless every `(file, row)` pair `signoff/block-manifest.json`
cites under `evidence."5.analog"` and `evidence."6.analog"` is graded by an entry
citing a file in that same record directory. So citing a record for signoff and
forgetting it here is a hard error rather than a row that quietly reads
`not-yet-measured` (issue #230). Two practical consequences:

- Cite the record directory the manifest cites. A sibling digest in it
  (`rows.json`, `yield.json`) is fine and usually easier to grade than the raw
  `klt sim` envelope, but a *superseded* run in a different directory is not.
- Grade a row from **every** record the manifest cites for it. T-15 and T-16 are
  cited under both `5.analog` (PVT) and `6.analog` (Monte Carlo); a row with one
  failing record is a failing row, and the passing record does not stand in for it.

Grading only a `fail` count is not enough where a record can also report a row
without limits (`verdict: reported`, as the clock-path record does for T-02 and
T-04): grade the record's own `verdict` alongside the count.
