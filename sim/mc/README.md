# sim/mc

Monte Carlo campaigns for the **STAT** rows of `spec/target-spec.md` (T1 item 6, analog;
DR-0013). Simulated, pre-layout; post-layout re-runs follow #37.

| Row | Status | Where |
|---|---|---|
| T-10 receiver threshold | **recorded, passes** | `records/20261123T092848Z-t10/` (the #398 adoption: the supply-referenced cell; supersedes the failing `20261108T035315Z-t10/`, which stays as append-only evidence) |
| T-13, T-14 TX skew | not done | #136 |
| T-15 RX data-to-data skew (CH) | **recorded, passes** | `records/20261123T093311Z-t15/` (the #398 re-run on the split cells; supersedes `20261120T202400Z-t15/`) |
| T-16 RX data-to-clock skew (CH) | **recorded, passes** | `records/20261123T093311Z-t16/` (the #398 re-run on the split cells; supersedes `20261120T202400Z-t16/`) |
| T-19 capture window | **recorded, fails on the adopted cell** | `records/20261123T094302Z-t19/` (the #398 re-run; the pre-adoption pass `20261112T082047Z-t19/` stays as append-only evidence; #190 tracks the fix) |

The manifest declares all six under `spec_rows."6.analog"`; the two open rows (T-13, T-14) are declared
`gap`s, and since the #398 adoption T-19 is the one recorded failure (the adopted cell's slow
asymmetric output edge widens the capture aperture past the 150 ps row at the low-supply ss/sf
corners; #190 tracks the output-stage work), so item 6 / analog reads on that failure plus the
declared gap set — T-10, T-15 and T-16 pass.

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

Each committed `report.json.gz` holds one entry per corner and draw. `gen_per_corner.py` reads
the T-10 failing record and the two T-15/T-16 re-run records and regenerates [`per_corner.md`](per_corner.md) -- per corner, the
draw count, mean, sample sigma (n-1, as `klt`), margin-ranked worst draw and draws outside the
row's limits, with the pooled totals cross-checked against the record (`--check` in CI;
`klt yield` itself pools the corners and cannot answer this).

## T-10

Bench `tb_t10.cir` sweeps the RX input as a fraction of VDDIO and measures the crossing
of the receiver output at VDDIO/2; `t10_offset_mv` is that crossing minus VDDIO/2. Limits
are the row's +-60 mV with `target_sigma` 3 (the row says 3 sigma mismatch). 45 corners x
120 draws = 5400 samples; seed 4410. Negative control: the input-pair NMOS 4x narrower
(`tb_t10_ctl.cir`), 900 draws, seed 4411, detected. Since the #398 adoption the design cell
is the supply-referenced stage; the nominal request also carries `rx_up.ivdd_a` (|i(VDDIO)|
at the crossing, i.e. input at VDDIO/2) so the same committed record measures the standing
divider + tail current (the design note in `design/README.md` quotes it).

`tb_t10_ctl.cir` is generated, not hand-copied (#202): `gen_mc.py` takes `tb_t10.cir`, inlines
`design/aib_rx_data.spice` in place of its `.include`, and narrows the input-pair NMOS
(`XMnp` `w=1u ng=2` -> `w=0.25u ng=1`) as the one seeded degradation — the same defect the
#386 study's control seeded on the same cell. The control's other devices are copied from the
design cell, so a change to them is carried into the control and `gen_mc.py --check` fails
until it is regenerated. A resize of `XMnp` itself moves the substitution's anchor and stops
the generator with a message naming it: what "4x narrower" means has to be restated on the
new device, not guessed. One stated deviation, carried by the study and by `gen_mc.py`: the
control's DC sweep widens to `Vfr 0.15 0.95`, because the degraded cell crosses at
fr 0.66-0.75 over the grid, outside the committed 0.3-0.7 window; the nominal bench keeps
the committed window.

**Result (2026-11-23, `records/20261123T092848Z-t10/`, the #398 adoption): T-10 PASSES.**
On the adopted supply-referenced cell, pooled over the grid the offset has mean +2.7 mV and
sigma 9.6 mV (sigma-to-spec 5.96, lower confidence bound 5.85 against 3; sample-size verdict
sufficient, required 183); **0 of 5400 draws and 0 of 45 corners outside +-60 mV**, worst
draw +42.3 mV, and the distribution reads consistent with normal (Anderson-Darling) where
the inverter cell's was not. Per-corner means -2.4..+10.8 mV, per-corner sigma 7.5-10.8 mV
(about twice the inverter cell's: the mirror's mismatch adds); worst mean+3sigma corner
`ff/1.200V/125C` at +41.3 mV, 18.7 mV of headroom — the per-corner table is in
[per_corner.md](per_corner.md). Negative control detected (0 of 900 degraded draws in
limit). The same record's `rx_up.ivdd_a` gives the standing supply current: at
tt / 1.2 V / 27 C the 120 draws span 64.0-94.2 uA (mean 81.3 uA, midpoint power 97.6 uW per
receiver; 2.15 mW across the 20+2 data and spare lanes); across the 45-corner grid the 5400
draws span 34.6-185.4 uA (per-corner means 36.6-152.5 uA, grand mean 84.7 uA). Mismatch coverage: MOS only — the divider's
`rppd` pair carries no independent resistor-pair mismatch in this model set (documented in
the record and the design note).

The superseded 2026-11-08 record (the #35 inverter cell) read mean +34.9 mV, sigma 22.6 mV,
13 of 45 corners with out-of-limit draws, binding `sf/1.320V/125C` — a systematic N/P
strength-ratio corner shift no re-centring of that topology closed (the #386 study's
finding). It stays committed as append-only evidence; the spec row and its limits are
untouched.

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
The 2026-11-20 re-run (#385) kept these counts and seeds; its zero-failure verdict
(`clopper-pearson-zero-failures`) asks 183 on both rows, far below what is recorded, and both
controls are detected again. One of the T-16 nominal shards was lost to an S3 upload failure on
first submit (300 units, `lost_shard`) and was recovered with `klt sim --resume`; the collected
report carries all 1800 draws.

**Results (2026-11-20 re-run, #385): both pass the 7-sigma gate** on the current cells (`main`
at `7a7c5b9`, after the TX predriver NOR widening of `89d803b` / #164 and the `aib_pad_esd`
`XResd` `l=1u` shortening of `e47bb80` / #332, the two resizes aimed at this quantity). Pooled over the grid, T-15 has mean -1.8 ps and sigma 5.4 ps (sigma-to-spec 10.8,
lower confidence bound 10.3 against 7; no draw outside +-60 ps, worst -20.7 ps); T-16 has mean
-0.7 ps and sigma 3.4 ps (sigma-to-spec 8.6, lower bound 8.3 against 7; no draw outside +-30 ps,
worst -15.1 ps). The 2026-11-10 means (+31.9 / +16.6 ps) moved to the means above, but the two runs
also differ in other inputs: the SS and FF diode sections changed from `dio_tt` to `dio_ss` and
`dio_ff` in all four requests, and the ngspice engine moved from 46 to 47. The comparison shows
the current cells pass under the current setup; it does not isolate how much of the improvement
came from the resizes. The distributions are still skewed and the normality test
still rejects, so the empirical tail is the quantity to read: it is empty. `klt yield` pools
the 45 corners as for T-10; the per-corner reading is in [per_corner.md](per_corner.md): T-15's
margin-ranked worst draw sits at `sf/1.080V/-40C`, T-16's at `ss/1.080V/27C` -- the low-supply
corners bind on both rows, and no corner holds an out-of-limit draw. The 2026-11-10 records
stay untouched (append-only); the re-run supersedes them. The limits are not relaxed. These
are CH results only; the L2 loopback does not observe RX-input skew, so no TC value is recorded
here. PR #374's pad-diode change was open at run time and is not covered; if it merges, one
more re-run is a follow-up, not a reason to hold this one.

**2026-11-23 re-run (#398, `records/20261123T093311Z-t15/`, `...-t16/`): both rows still pass
the 7-sigma gate on the split cells** — the data lanes on the adopted supply-referenced
receiver, the clock pair through `lane_clk` on the committed inverter. At the recorded counts
and seeds, T-15 reads mean -1.3 ps / sigma 5.4 ps (sigma-to-spec 10.9, lower bound 10.4;
worst draw -18.6 ps; control yield drops 1.0 -> 0.263, detected) and T-16 mean -0.3 ps /
sigma 3.4 ps (sigma-to-spec 8.7, lower bound 8.4; worst draw -15.1 ps; control 0 of 900,
detected) — within a fraction of a sigma of the #385 records, exactly what the #386 study's
t16-mixed leg predicted for the split. The RX-pin T-16 value is not the receiver-output
margin; the two-edge DDR disposition at the receiver outputs is recorded in
`design/README.md` from the clock-path record.

## T-19 (receiver capture window, BOTH)

Bench `capture_window/tb_t19.cir` (generated by `capture_window/gen_t19.py`; `gen_t19.py --check` and
`test_t19.py` keep it fresh, and CI runs `test_t19.py` -- `gen_mc.py --check` covers the two T-19
requests, not the netlists): `design/aib_rx_data.spice` as drawn driving D of the PDK
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

**2026-11-23 re-run (#398, `records/20261123T094302Z-t19/`): T-19 FAILS on the adopted cell.**
On the supply-referenced receiver, at the same counts and seeds, 151 of 900 draws fall outside
the 150 ps one-sided limit and 8 of 45 corners have mean apertures over it (worst readable
`ss/1.080V/27C`, 442.1 ps: setup 163.2, hold 278.9 — the hold side dominates); at
`ss/1.080V/-40C` the capture boundary leaves the bench's -400..+100 ps sweep window, so the row
is unmeasurable there without a wider sweep. The mechanism is the adopted stage's asymmetric
output edge — the same mechanism the clock-path t02 separations quantify (data fall-vs-rise
output-delay mismatch up to +624 ps at that corner) — keeping the D pin moving long after its
50 % crossing through the half-width restore inverter. The #386 study did not measure T-19; this
re-run is the row's first record on the adopted cell and its recorded cost, tracked for #190's
rise/fall symmetry work (the one STAT row item 6 / analog now fails on). The receiver-output
two-edge disposition (design/README.md) still closes on the separations at every corner, and at
every corner where this record's window contains the boundary the measured rising-setup and
falling-hold fit inside them (worst phase-window width 599 ps at `ss/1.080V/27C`); the row's
own 150 ps budget is what the adopted cell misses. The pre-adoption record stays committed as
append-only evidence; nothing was tuned.

## Assumptions for ratification (not in the spec)

- The skew and capture rows (open, #136 to #138) read "14 sigma peak-to-peak" as a signed
  lane-to-lane difference with limits +-bound and `target_sigma` 7.
- T-19 (#138) is a one-sided width limit (150 ps) graded at `target_sigma` 7, the one-sided reading of the same
  14 sigma peak-to-peak; the negedge flop (same cell, inverted clock) is not run as a second measurement and
  no posedge/negedge difference was estimated; setup and hold are quantised to the 10 ps sweep step
  (about 4.1 ps rms on the aperture).
