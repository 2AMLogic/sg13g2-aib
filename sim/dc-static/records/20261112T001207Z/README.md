# Hand-built dc-static record: the #142 re-check the signoff cites

Kind: **simulated**. One `klt sim` report over the dc-static bench, PVT-FULL (45 corners:
5 MOS corners x VDDIO 1.08/1.20/1.32 V x -40/27/125 C), `status: pass` with 45/45 corners
passing and 810/810 measurements passing, none inconclusive. Batch job
`klt-sim-f611a9ac49eb`; ngspice 46 through klayout-tools 0.9.0 (`5dbbad05`, KLayout
0.30.13) against PDK `ihp-sg13g2` 0.3.0. Same `request.json` (the `gen_dc_static.py`
output) as the two earlier item 5 records of this family; it is the re-check that the
#142 predriver change did not move any dc-static verdict.

## Why there is no `record.json`

This directory was produced **by hand, before the shared batch-and-record harness
existed** (`sim/harness/batch_record.sh`; #228 moved the family onto it, and
`sim/dc-static/README.md` tells both stories). The hand procedure captured only the
fleet's report, so the directory holds **only `report.json`** — no `request.json` copy,
no bench files, no scrubbed `klt.stderr`, and no graded `record.json`. The record is
evidence and is kept exactly as produced; nothing was back-filled. The entry point for
the next run is `sim/dc-static/run_dc_static.sh nominal|2kv|esd-diode`.

## What cites it

`report.json` — not a `record.json` — is what the signoff chain cites for six spec rows,
T-06, T-07, T-08, T-11, T-24 and T-28 (all 45/45 corners pass):
`signoff/block-manifest.json`, `signoff/block-manifest.signoff.json`, the dc-static row
of `signoff/README.md`, and the six row entries of `measurements/row-evidence.json`.
`sim/harness/test_batch_record.sh` (case 8) drives this same `report.json` through the
shared post-processor and checks the row map reproduces the six rows, their 45-corner
counts and T-24's binding corner.
