# sim/dc-static

DC static characteristics of the I/O cell, PVT-FULL (T1 item 5, analog; family of #42).
One `klt sim` request, `request.json`, 45 corners: 5 MOS corners x VDDIO 1.08/1.20/1.32 V
x -40/27/125 C (`klt sim --dry-run` reports `unit_count: 45`). Each process corner is a
bundle of the matching MOS, poly-resistor and diode sections, because the cells use `rppd`
and the antenna diodes as well as the thin-oxide MOS devices.

**Status: testbenches and request only. No record exists yet.** The 45-corner batch
submit failed (see "Batch run" below), so nothing was graded and no `records/<stamp>/`
was written. A failed submit is not a result.

## Rows and measurements

All step measurements carry `limits` straight from `spec/target-spec.md`; the spec is
not relaxed. Names are `<step>.<measurement>` in the report.

| Row | Step(s) | Measurement | Bound |
|---|---|---|---|
| T-06 | `drv_nl`, `drv_ld` | `t06_voh_droop_v` (VDDIO - V(pad), driving high), `t06_vol_v` | <= 0.1 V, unloaded and at 1 mA |
| T-08 | `drv_ld` | `t08_rout_up_ohm`, `t08_rout_dn_ohm` (chord resistance at 1 mA) | 40-80 ohm |
| T-07, T-28 | `lk_0`, `lk_5`, `lk_10` | `t07_t28_ipin_a`: pin current, driver tristated, pulls off, pad at 0, VDDIO/2, VDDIO | <= 1 uA |
| T-28 | `pu_on`, `pd_on` | `t28_rpu_ohm`, `t28_rpd_ohm` at VDDIO/2 | 10-20 kohm |
| T-24 | `cap_0`, `cap_5`, `cap_10` | `t24_cpin_ff`: imaginary admittance / (2 pi 500 MHz) at pad = 0, VDDIO/2, VDDIO | <= 100 fF |
| T-11 | `rx_up`, `rx_dn` + derived | `t11_hyst_mv` = abs(up trip - down trip) | <= 60 mV |

Test conditions chosen here, not given by the spec (flagged for ratification):

- **1 mA DC load** for T-06/T-08. The spec gives no load current. 0.1 V / 1 mA = 100 ohm, so
  the T-08 80 ohm bound implies the T-06 droop bound.
- **1 uA** for T-07 and the T-28 tristate leakage. T-07 says "no DC path to a termination"
  and T-28 gives no leakage number; 1 uA is above leakage and below any termination.
  T-07's structural half is the netlists: the only resistors on `PAD` are the weak
  pulls (`XRpu`, `XRpd`, each behind a gated switch) and the ESD series resistor,
  which leads to the receiver gates.
- **T-24 is an extracted-capacitance estimate** from the model small-signal admittance at
  500 MHz, labelled as such. The PDK `bondpad` is an empty placeholder, so no bond pad
  is in it; post-layout PEX is out of scope. It covers the whole pin: ESD, tristated
  driver drains and receiver.
- **T-11** is a structural check: a DC sweep of a memoryless inverter pair cannot show
  hysteresis unless the cell has positive feedback, which is what this detects.

Pin assembly: driver and primary ESD stage on `PAD`, receiver behind the ESD series
resistor on `PADI`. The assembly itself is another issue.

Scope: every row here is `BOTH` (channel and test configuration); no channel model is used.

## Files

- `tb_dc_static.cir` top level; `.include`s the cells from `design/` and the benches.
- `tb_drive.cir` (T-06/T-08), `tb_pin.cir` (T-07/T-24/T-28), `tb_rx_hyst.cir` (T-11).
- `request.json` the one request. `options.fail_on_diagnostic: ["nonconvergence"]` grades
  a corner whose operating point did not converge as `inconclusive`, never pass/fail.

## Reproduce

```bash
sim/harness/common/fetch-pdk.sh && source sim/harness/env.sh
SG13G2_TOOLS_CACHE=$PWD/sim/build/cache sim/harness/common/build-osdi.sh
klt sim sim/dc-static/request.json --dry-run            # 45 units, backend batch
klt sim sim/dc-static/request.json --format json --report-out /tmp/dc-static-report.json
```

The second command goes to the batch fleet. A record is a new `records/<stamp>/` directory
holding the report; never edit an earlier one.

## Batch run

Submit `klt-sim-1f8fa18f7a9f` (2026-10-27) failed on all 45 units: the fleet runner image
is klt 0.7.0 and rejects the request ("request is missing required field: analysis")
because it predates `analysis_steps[]`. The client reported
`runner_request_features.missing: ["analysis_steps"]`. Per the host rule the grid was not
run locally. Needs a runner image with `analysis_steps` (klayout-tools#3516 and siblings),
or a rewrite as one request per analysis kind, which departs from the one-request shape
of #52.

## Known finding from a single local probe (not a result)

One corner (tt, 1.20 V, 27 C) was run locally as a debug probe and is not recorded.
The driver does not drive: in this PDK the `w` of `sg13_lv_*` is the **total** width and
`ng` the finger count, so `aib_tx_data` `XMp` (`w=1u ng=28`) and `XMn` (`w=1u ng=14`) are
36 nm and 71 nm per finger, below the model minimum, and the pad floats at the first
operating point. The first `op` then fails to converge, which is why
`fail_on_diagnostic` is set. Cell netlists are out of scope here (#35); filed separately.
