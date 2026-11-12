# sim/mc

Monte Carlo campaigns for the **STAT** rows of `spec/target-spec.md` (T1 item 6, analog;
DR-0013). Simulated, pre-layout; post-layout re-runs follow #37.

| Row | Status | Where |
|---|---|---|
| T-10 receiver threshold | **recorded, fails** | `records/20261108T035315Z-t10/` |
| T-13 data-to-data skew (TX output) | **recorded, fails** | `records/20261112T080126Z-t13/` |
| T-14 data-to-clock skew (TX output) | **recorded, fails** | `records/20261112T080126Z-t14/` |
| T-15 RX data-to-data skew (CH) | **recorded, fails** | `records/20261110T113631Z-t15/` |
| T-16 RX data-to-clock skew (CH) | **recorded, fails** | `records/20261110T113631Z-t16/` |
| T-19 capture window | not done | #138 |

The manifest declares all six under `spec_rows."6.analog"`; the one open row (T-19) is a declared
`gap`, so item 6 / analog stays `unmet` (reason `check_failed`: T-10, T-13, T-14, T-15 and T-16 fail their limits).

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

## T-15, T-16 (RX-input skew, CH)

Single-edge benches over `spec/channel/channel_rc.cir` (CH-3MM-RC, nominal channel), the
`sim/channel-eye` lane (`edge_lane.inc`: TX, pad ESD, channel, pad ESD, RX, 5 fF on DOUT) as
subject. `tb_t15.cir`: lane A rises and complement lane B falls together; skew is B's falling
minus A's rising mid-rail crossing of the RX pad node. `tb_t16.cir`: lane A rises, the
center-aligned clock pair (`rxc - rxcb`) rises 500 ps later; the graded quantity is data-to-clock
delay minus the nominal 0.5 UI. Measured cost is about 0.5 s (T-15) and 0.7 s (T-16) of ngspice
per unit, against about 22 s per corner for the PRBS bench. Limits +-60 ps / +-30 ps, `target_sigma` 7
(signed difference; see below). 45 corners, seeds 4415 / 4420, negative-control seeds 4416 / 4421.
Both supplies of every block move together on the grid (`vdd_*` in lockstep, as the channel-eye grid).

N from the `klt yield` sample-size verdict of a 20-draw pilot (confidence 0.95, CI half-width
0.01): T-15 needs 170 (900 recorded, the pilot run itself); T-16 needs 1318 (`required_n` in `record.json` and `yield.json`), so 40 draws per corner
(1800) were run (verdict sufficient, observed half-width 0.0088). Negative control: an extra 500 fF
at the degraded lane's receiver input (`edge_lane_deg.inc`, not design evidence), 900 samples each,
detected for both rows. Both rows ran on the batch fleet (`--backend batch --wait-for-capacity 600`).

**Results: both fail the 7-sigma gate.** Pooled over the grid, T-15 has mean +31.9 ps and sigma 11.4 ps
(sigma-to-spec 2.47 against 7; 0.4 % of draws outside +-60 ps, worst 62.6 ps); T-16 has mean +16.6 ps
and sigma 6.6 ps (sigma-to-spec 2.03 against 7; 3.6 % outside +-30 ps, worst 37.1 ps). The mean is
mostly systematic (rise/fall asymmetry across the channel and receiver, not mismatch), the
distributions are skewed and the normality test rejects, so the empirical tail is the quantity to
read. `klt yield` pools the 45 corners as for T-10. The limits are not relaxed. These are CH
results only; the L2 loopback does not observe RX-input skew, so no TC value is recorded here.

## T-13, T-14 (TX-output skew, CH and TC)

Single-edge benches at the TX pad node (near-side output: `aib_tx_data` / `aib_tx_clk` plus `aib_pad_esd`;
no channel, no receiver). `tb_t13.cir`: lane A rises and complement lane B falls together; skew is B's
falling minus A's rising mid-rail crossing. `tb_t14.cir`: lane A rises, the center-aligned `aib_tx_clk` pair
(`padc - padcb`) rises 500 ps later; the graded quantity is data-to-clock delay minus the nominal 0.5 UI.
Limits +-40 ps / +-20 ps (0.04 / 0.02 UI at 1 Gb/s), `target_sigma` 7, definition ratified in DR-0019.
45 corners, supplies of each block in lockstep, seeds 4413 / 4418, negative-control seeds 4414 / 4419.
N: a 20-draw pilot (900 samples) gave a `klt yield` required N of 183 for both rows, so the pilot is the
recorded run (verdict sufficient). Negative control: an extra 2 pF on one pad (`tb_t13_ctl.cir`,
`tb_t14_ctl.cir`, not design evidence), 0 of 900 pass, detected. Both ran on the batch fleet
(`--wait-for-capacity 600`); job ids are in each `record.json`.

**Results: both fail the 7-sigma gate** (no draw is outside the limit; the row fails on the tail). T-13: mean +2.5 ps,
sigma 6.2 ps, sigma-to-spec 6.08 (lower bound 5.79) against 7, worst draw 18.3 ps. T-14: mean +1.0 ps, sigma 3.3 ps,
sigma-to-spec 5.75 (lower bound 5.48) against 7, worst 14.4 ps. Distributions are not normal; pooled grid as for T-10.
The limits are not relaxed. Scope: the CH value is the TX output before the channel; for TC the on-die array skew
is what the shmoo observes, and this single-lane-pair spread is not that array measurement.

## Assumptions for ratification (not in the spec)

- The skew and capture rows (T-13 to T-16 ratified in DR-0019; T-19 open, #138) read "14 sigma peak-to-peak" as a signed
  lane-to-lane difference with limits +-bound and `target_sigma` 7.
