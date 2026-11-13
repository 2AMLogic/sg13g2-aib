# sim/mc

Monte Carlo campaigns for the **STAT** rows of `spec/target-spec.md` (T1 item 6, analog;
DR-0013). Simulated, pre-layout; post-layout re-runs follow #37.

| Row | Status | Where |
|---|---|---|
| T-10 receiver threshold | **recorded, fails** | `records/20261108T035315Z-t10/` |
| T-13, T-14 TX skew | not done | #136 |
| T-15 RX data-to-data skew (CH) | **recorded, fails** | `records/20261110T113631Z-t15/` |
| T-16 RX data-to-clock skew (CH) | **recorded, fails** | `records/20261110T113631Z-t16/` |
| T-19 capture window | **recorded, passes** | `records/20261112T082047Z-t19/` |

The manifest declares all six under `spec_rows."6.analog"`; the two open rows (T-13, T-14) are declared
`gap`s, so item 6 / analog stays `unmet` (reason `check_failed`: T-10, T-15 and T-16 fail their limits; T-19 is cited and passes).

## Method

`gen_mc.py` writes one nominal and one negative-control `klt sim` request per row, and the
T-10 control bench `tb_t10_ctl.cir` (`--check` for staleness; CI runs it). Each request is the
45-corner PVT-FULL grid of `sim/pvt_full.py` with `mos_<corner>_mismatch` process sections (the
PDK's per-instance mismatch sections), `monte_carlo.vary: mismatch`, a recorded seed, and goes to
the batch fleet; the negative control is a bench copy of the cell with a seeded degradation. The
two reports are joined by `klt yield-samples` and graded by `klt yield`:

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

`tb_t10_ctl.cir` is generated, not hand-copied (#202): `gen_mc.py` takes `tb_t10.cir`, inlines
`design/aib_rx_data.spice` in place of its `.include`, and narrows the first-stage NMOS
(`XMi1n` `w=1u ng=2` -> `w=0.25u ng=1`) as the one seeded degradation. The control's other three
devices are copied from the design cell, so a change to them is carried into the control and
`gen_mc.py --check` fails until it is regenerated — the control used to inline the sizes by hand,
which would have left it on the old cell after a receiver resize (#190). A resize of `XMi1n`
itself moves the substitution's anchor and stops the generator with a message naming it: what
"4x narrower" means has to be restated on the new device, not guessed. The generated file is
byte-identical to the bench the record cites
(`records/20261108T035315Z-t10/tb_t10_ctl.cir`), so the recorded result is unchanged.

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

## T-19 (receiver capture window, BOTH)

Bench `capture_window/tb_t19.cir` (generated by `capture_window/gen_t19.py`, `gen_mc.py --check` and
`test_t19.py` keep it fresh): `design/aib_rx_data.spice` as drawn driving D of the PDK
`sg13g2_dfrbpq_1` (the flop `design/synth/` maps the RX capture register to, vendored verbatim as
`capture_window/sg13g2_dfrbpq_1.inc`). One transient sweeps the data edge across the clock edge in
10 ps steps, first rising data (setup), then falling data (hold); the flop output flips at the first
failing / first capturing cycle and a staircase source reads the offset back. A klt netlist body cannot
carry a `.control` loop, so this is a swept-offset transient, not a bisection. Aperture = setup + hold at the
D-pin 50 % crossing, per draw, on one posedge flop instance; the sweep window (-400..+100 ps) is wider than
every measured edge. Measured cost is about 12 s of ngspice per unit. Limit: one-sided 150 ps with
`target_sigma` 7. 45 corners x 20 draws = 900 samples (the 20-draw pilot verdict asked for 183), seed 4430;
negative control: the flop clock edge ramps over 1500 ps instead of 100 ps, 900 samples, seed 4431, detected.
Both ran on the batch fleet (`--backend batch --wait-for-capacity 600 --max-units-per-job 58`).

**Result: T-19 holds in simulation, pre-layout.** Pooled over the grid the aperture has mean 27.6 ps and
sigma 12.5 ps (sigma-to-spec 9.8 against 7); worst draw 68.6 ps (sf, 1.08 V, -40 C); 900 of 900 draws under
150 ps. The control alone fails the gate (sigma-to-spec 2.6; 12 draws over 150 ps, 72 outside the sweep
window and counted as failed). The distribution is not normal, so the empirical yield and the worst draw are the
tail used. `klt yield` pools the 45 corners as for T-10. The manifest pin for this citation is the hash of
`samples.json` (the document `yield.json` names), which is what `klt signoff` compares for a passing
yield report.

This is a cell property from ideal 100 ps edges at the flop and the input stage: it holds for the modeled
channel (CH) and for the wire-bond loopback (TC) only as far as the edge slew arriving at the RX pad matches;
the slew sensitivity is not measured and no separate TC value is recorded. The aperture is not widened by a
pure delay change (supply, D load): setup and hold move together, so the control degrades the clock edge instead.

## Assumptions for ratification (not in the spec)

- The skew and capture rows (open, #136 to #138) read "14 sigma peak-to-peak" as a signed
  lane-to-lane difference with limits +-bound and `target_sigma` 7.
- T-19 (#138) is a one-sided width limit (150 ps) graded at `target_sigma` 7, the one-sided reading of the same
  14 sigma peak-to-peak; the negedge flop (same cell, inverted clock) is not run as a second measurement and
  no posedge/negedge difference was estimated; setup and hold are quantised to the 10 ps sweep step
  (about 4.1 ps rms on the aperture).
