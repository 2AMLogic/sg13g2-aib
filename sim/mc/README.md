# sim/mc

Monte Carlo campaigns for the **STAT** rows of `spec/target-spec.md` (T1 item 6, analog;
DR-0013). Simulated, pre-layout; post-layout re-runs follow #37.

| Row | Status | Where |
|---|---|---|
| T-10 receiver threshold | **recorded, fails** | `records/20261108T035315Z-t10/` |
| T-13, T-14 TX skew | not done | #136 |
| T-15, T-16 RX skew (CH; TC reported separately) | not done | #137 |
| T-19 capture window | not done | #138 |

The manifest declares all six under `spec_rows."6"`; the five open rows are declared
`gap`s, so item 6 / analog stays `unmet` (reason `check_failed`: T-10 fails its limit).

## Method

`gen_mc.py` writes one nominal and one negative-control `klt sim` request per row
(`--check` for staleness; CI runs it). Each request is the 45-corner PVT-FULL grid with
`mos_<corner>_mismatch` process sections (the PDK's per-instance mismatch sections),
`monte_carlo.vary: mismatch`, a recorded seed, and goes to the batch fleet; the
negative control is a bench copy of the cell with a seeded degradation. The two reports
are joined by `klt yield-samples` and graded by `klt yield`:

```bash
python3 -I sim/mc/gen_mc.py --check
cd sim/mc && uvx --from "klayout-tools[yield]==$(cat ../../signoff/KLT_VERSION)" klt sim request_t10.json \
  --backend batch --wait-for-capacity 600 --max-units-per-job 348 -o <work> --report-out report.json.gz
# same for request_t10_ctl.json; gunzip both, then, from the directory holding them:
klt yield-samples report.json --negative-control report_ctl.json --description "<defect>" --measurement t10_offset_mv --format json > samples.json
klt yield samples.json --format json > yield.json
```

`klt yield` needs the `yield` extra (`klayout-tools[yield]`), which resolves for 0.9.0 in a
throwaway `uvx` environment.

## T-10

Bench `tb_t10.cir` sweeps the RX input as a fraction of VDDIO and measures the crossing
of the receiver output at VDDIO/2; `t10_offset_mv` is that crossing minus VDDIO/2. Limits
are the row's +-60 mV with `target_sigma` 3 (the row says 3 sigma mismatch). 45 corners x
120 draws = 5400 samples (the sample-size verdict asked for 5178 at +-0.01 yield CI);
seed 4410. Negative control: first-stage NMOS 4x narrower (`tb_t10_ctl.cir`), 900 draws,
seed 4411, detected.

**Result: T-10 fails.** Pooled over the grid the offset has mean +34.9 mV and sigma
22.6 mV (sigma-to-spec 1.11 against 3); 16 % of draws fall outside +-60 mV, worst 94.6 mV in the 20-draw pilot. Most of the mean is the systematic
corner shift (N/P strength ratio), not mismatch. The spec is not relaxed; the cell is #35's. Note
`klt yield` pools the 45 corners ("a worst-case envelope rather than a distribution anyone
sampled"); a per-corner reading is not in this record.

## Assumptions for ratification (not in the spec)

- The skew and capture rows (open, #136 to #138) read "14 sigma peak-to-peak" as a signed
  lane-to-lane difference with limits +-bound and `target_sigma` 7.
