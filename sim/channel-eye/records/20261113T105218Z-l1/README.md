# L1 on-die loopback, PVT-FULL x the route's +-20 % R/C (135 corners)

The `SIM` leg of **T-29** for loopback **L1**, and the first record of the L1 electrical
configuration. Decision record: [DR-0019](../../../../spec/decisions/0019-t29-loopback-selection.md).
Issue #176. Written by `sim/channel-eye/run_channel_eye.sh l1`; append-only, do not edit.

**Scope: TC (test configuration). Nothing here is a CH claim.** `record.json`'s
`claim_scope` says so, and `measurements/row-evidence.json` scopes every entry citing
this record `TC`.

## What was simulated

`tb_l1.cir`: the four-lane `tb_body.inc` bench (data A, its complement B, and the
clk/clkb forwarded-clock pair), each lane `aib_tx_data` -> `aib_pad_esd` -> link ->
`aib_pad_esd` -> `aib_rx_data`, `.include`d from `design/`, never copied. The link is the
L1 **on-die route**: the channel model's RC ladder (`spec/channel/channel_rc.cir`,
`chan_rlc`, `len_mm = 3`) with its inductance removed (`l_mm = 0`) per DR-0009 "Limits",
and with the route's R and C scaled by `kr_l1` / `kc_l1`.

Grid: 135 corners = PVT-FULL (5 `mos_*` x 1.08/1.20/1.32 V x -40/27/125 C) x **three R/C
points**, `kr_l1 = kc_l1 =` 0.8, 1.0, 1.2 — the ±20 % band `spec/test-configuration.md`
allows the route to land in. R and C are zipped (they move together), so the band is three
corners per PVT point, never folded into nominal. `klt sim --backend batch`, 20 jobs of 7
units; `klt.stderr` carries the job ids.

## Results (135/135 corners, `klt sim` exit 0, every corner `pass`)

| Row | Graded | Verdict | Worst observed | Limit |
|---|---|---|---|---|
| T-01 | yes | **pass** (270/270) | `dout` edge count 64.0 on both data lanes at every corner | 63.5-64.5 per PRBS-7 period |
| T-09 | yes | **pass** (2160/2160) | over/undershoot 0.0053 x VOS (`t09_under_a`, `mos_ss`/1.08 V/-40 C/0.8 R-C); dwell above the level 0.0 s everywhere | <= 0.25 x VOS, <= 0.4 ns dwell |
| T-26 | no (report-only) | reported (540 measurements) | 0.308 pJ/bit (`mos_ss`/-40 C/0.8) to 0.691 pJ/bit (`mos_ff`/125 C/1.2) | — |

T-01 and T-09 are the rows `test-configuration.md` marks `yes` for L1 among those this
bench measures, so they are the ones graded. **T-26 is report-only here** because the
matrix says energy per bit is "not measured by this repo's plan" in L1; the figure is
**simulated** and is not a T-26 claim. Energy rises monotonically with the route's C
(0.31-0.58 / 0.34-0.64 / 0.37-0.69 pJ/bit at 0.8 / 1.0 / 1.2), which is the expected
behaviour and a cross-check that the R/C axis really took effect.

T-15, T-16 and T-18 are **not requested**: `test-configuration.md` gives L1 "no direct
observation" of RX-input skew and "no (error count, not eye)" for the far-end eye.

## Declared gaps — read before citing this record

- **The route does not exist in layout.** `layout/gen_io_column.py` has no TopMetal2
  loopback route, so the ±20 % band swept here is the *declared* emulation tolerance, not
  an extracted one. `test-configuration.md` requires the band to be confirmed by
  `klt extract` / `klt pex` on the real route (with an added explicit capacitor if the
  route's own C is short of the model's). That check is owed and filed as **#182**. This
  record shows the L1 configuration behaves across the admissible band; it does **not**
  show that a route as drawn lands inside it.
- **The route's inductance is not reproduced** (`l_mm = 0`, DR-0009 "Limits"). A real
  TopMetal2 line has inductance; this bench does not model it.
- **The far-end term is the model's.** `tb_l1.cir` keeps `chan_rlc`'s default
  `cfar = 0.1 pF`, exactly as `tb_ch.cir` does, on top of the real cells' own pin
  capacitance. Both benches therefore over-count the receiver-side load by that term.
- **`l1 = 1` in the RTL is not this.** `rtl/aib_datapath.v`'s `l1` input is a digital
  select with no I/O cell in the path. Exercising the configuration recorded here needs
  `l1 = 0` (DR-0019); the port name is filed as **#181**.
- **No silicon.** T-29 is TC-scoped: what a part could show. Every number here is
  simulated.
- **Not the clock cells.** As in every bench in this family, the clk/clkb lanes are two
  `aib_tx_data` / `aib_rx_data` instances, not `aib_tx_clk` / `aib_rx_clk`
  (`tb_body.inc` explains why).

## Files

| File | What |
|---|---|
| `record.json` | the summary `run_channel_eye.sh` wrote: corner count, per-row verdicts, binding corners, PDK pin |
| `rows.json` | `channel_eye_post.py`'s per-row roll-up of `report.json.gz` |
| `report.json.gz` | the full `klt sim` report, 135 corners x 22 measurements |
| `request.json` | the request as submitted (a copy of `request_l1_1g.json`) |
| `tb_l1.cir`, `tb_body.inc`, `prbs7_stim.inc` | the netlist and includes as run |
| `klt.stderr` | the run's stderr, with the fleet bucket redacted; the batch job ids are here |
