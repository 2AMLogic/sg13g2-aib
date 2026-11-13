#!/usr/bin/env python3
"""Generate the sim/dc-static `klt sim` requests from one description.

Stdlib only. `python3 -I sim/dc-static/gen_dc_static.py [--check]` writes (or
checks) the three committed requests in sim/dc-static/:

  request.json           the T1 item 5 dc-static set on tb_dc_static.cir
  request_2kv.json       the same set on the DR-0018 variant tb_dc_static_2kv.cir
  request_esd_diode.json the DR-0018 pad-diode extraction on tb_esd_diode.cir

`request_2kv.json` used to be a hand copy of `request.json` with the netlist
swapped (#203): nothing checked that the 12 steps stayed equal, so a step or a
limit edited for item 5 could leave the 2kv re-run measuring the old set. Both
now come from DC_STEPS below. The ESD-diode request is three step shapes over
the five DUTs of tb_esd_diode.cir, not 35 hand-written blocks.

All 45-corner requests share one PVT-FULL grid: 5 MOS corners x VDDIO
1.08/1.20/1.32 V x -40/27/125 C (sim/dc-static/README.md). Unlike sim/mc the
MOS sections are the plain `mos_<corner>` ones — these are not Monte Carlo
runs, so per-instance mismatch is not wanted.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

LIBM = "libs.tech/ngspice/models/cornerMOSlv.lib"
LIBR = "libs.tech/ngspice/models/cornerRES.lib"
LIBD = "libs.tech/ngspice/models/cornerDIO.lib"
# The cells use rppd and the antenna diodes as well as thin-oxide MOS, so each
# process corner is a bundle of the matching MOS, resistor and diode sections.
RES = {"tt": "res_typ", "ss": "res_wcs", "ff": "res_bcs", "sf": "res_typ", "fs": "res_typ"}
OSDI = [f"$PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/osdi/{m}.osdi"
        for m in ("psp103", "psp103_nqs", "r3_cmc", "mosvar")]
# Host rule (one submit may wait for fleet capacity rather than fail) and
# sim/dc-static/README.md "Run both with --wait-for-capacity 600".
CAPACITY_WAIT_S = 600

OP = {"kind": "op", "args": ""}
AC500 = {"kind": "ac", "args": "lin 1 500meg 500meg"}
AC1K = {"kind": "ac", "args": "lin 1 1k 1k"}
# Pad bias as a fraction of VDDIO: 0, VDDIO/2, VDDIO. The tag is the fraction
# in tenths, which is what the step and measurement names carry.
PAD_BIAS = (("0", 0), ("5", 0.5), ("10", 1))


def corners() -> dict:
    proc = [{"name": c, "sections": [{"lib": LIBM, "section": f"mos_{c}"},
                                     {"lib": LIBR, "section": RES[c]},
                                     {"lib": LIBD, "section": "dio_tt"}]}
            for c in ("tt", "ss", "ff", "sf", "fs")]
    return {"process": proc, "supply_v": {"vddio": [1.08, 1.2, 1.32]},
            "temperature_c": [-40, 27, 125]}


def meas(name: str, expr: str, unit: str, **limits) -> dict:
    m = {"name": name, "expr": expr, "unit": unit}
    if limits:
        m["limits"] = limits
    return m


def step(name: str, analysis: dict, alter: dict, measurements: list) -> dict:
    return {"name": name, "analysis": analysis, "alter": alter, "measurements": measurements}


# --- the item 5 dc-static set (tb_dc_static.cir and the DR-0018 2kv variant) ---
# Limits come straight from spec/target-spec.md; see README "Rows and
# measurements" for the row -> step mapping.
VOH = meas("t06_voh_droop_v", "v(vddio)-v(pad_h)", "V", max=0.1)
VOL = meas("t06_vol_v", "v(pad_l)", "V", max=0.1)
IPIN = meas("t07_t28_ipin_a", "abs(i(vacp))", "A", max=1e-06)
CPIN = meas("t24_cpin_ff", "vecmax(imag(-i(vacp)))/(2*pi*500e6)*1e15", "fF", max=100)

DC_STEPS = [
    # T-06 unloaded, then T-06/T-08 at the 1 mA Builder-chosen load.
    step("drv_nl", OP, {"Ih": 0, "Il": 0}, [VOH, VOL]),
    step("drv_ld", OP, {"Ih": 0.001, "Il": 0.001},
         [VOH, VOL,
          meas("t08_rout_up_ohm", "(v(vddio)-v(pad_h))/1e-3", "ohm", min=40, max=80),
          meas("t08_rout_dn_ohm", "v(pad_l)/1e-3", "ohm", min=40, max=80)]),
    # T-07/T-28 tristate leakage, pulls off, at the three pad biases.
    *[step(f"lk_{tag}", OP, {"Vpf": v, "Vpunf": 1, "Vpdf": 0}, [IPIN]) for tag, v in PAD_BIAS],
    # T-28 weak pulls, one at a time, at VDDIO/2.
    step("pu_on", OP, {"Vpf": 0.5, "Vpunf": 0, "Vpdf": 0},
         [meas("t28_rpu_ohm", "0.5*v(vddio)/i(vacp)", "ohm", min=10000.0, max=20000.0)]),
    step("pd_on", OP, {"Vpf": 0.5, "Vpunf": 1, "Vpdf": 1},
         [meas("t28_rpd_ohm", "-0.5*v(vddio)/i(vacp)", "ohm", min=10000.0, max=20000.0)]),
    # T-24 pin capacitance at the three pad biases.
    *[step(f"cap_{tag}", AC500, {"Vpf": v, "Vpunf": 1, "Vpdf": 0, "Vacp.ac": 1}, [CPIN])
      for tag, v in PAD_BIAS],
    # T-11 hysteresis: the two sweep directions, combined by the top measurement.
    step("rx_up", {"kind": "dc", "args": "Vfr 0 1 0.001"}, {},
         [{"name": "vth_up", "spice": ".meas dc vth_up WHEN v(dnorm)=0.5 RISE=1", "unit": "frac"},
          {"name": "vddio_v", "expr": "v(vddio)[0]", "unit": "V"}]),
    step("rx_dn", {"kind": "dc", "args": "Vfr 1 0 -0.001"}, {},
         [{"name": "vth_dn", "spice": ".meas dc vth_dn WHEN v(dnorm)=0.5 FALL=1", "unit": "frac"}]),
]
DC_TOP = [meas("t11_hyst_mv", "abs(rx_up.vth_up-rx_dn.vth_dn)*rx_up.vddio_v*1000", "mV", max=60)]

# --- the DR-0018 pad-diode extraction (tb_esd_diode.cir) ---
# DUT letter -> the rail the diode is referenced to, which fixes the forward
# direction: a "vdd" device (anode on the pad) conducts with the pad above
# VDDIO, so it is biased at Vf=1 and the overdrive is positive; a "vss" device
# (cathode on the pad) is biased at Vf=0 with a negative overdrive.
ESD_DUTS = {"a": "vdd",   # diodevdd_2kv
            "b": "vss",   # diodevss_2kv
            "c": "vdd",   # diodevdd_4kv
            "d": "vss",   # diodevss_4kv
            "e": "vdd"}   # dpantenna 4.5u x 4.5u, the DR-0017 XDp1 baseline
ESD_OVERDRIVE = (("2v", 2.0), ("3v", 3.0))


def esd_bias(dut: str, value) -> dict:
    """All five pad-bias sources, with only `dut` carrying `value`."""
    return {f"Vf{d}": (value if d == dut else 0) for d in ESD_DUTS}


def esd_overdrive(dut: str, volts: float) -> dict:
    """All five forward-overdrive sources, with only `dut` carrying `volts`."""
    return {f"Vo{d}": (volts if d == dut else 0) for d in ESD_DUTS}


def esd_steps() -> list:
    steps = []
    for dut in ESD_DUTS:  # pad capacitance vs bias, one ac stimulus per step
        for tag, v in PAD_BIAS:
            steps.append(step(f"cap_{dut}_{tag}", AC500,
                              {**esd_bias(dut, v), f"Vac{dut}.ac": 1},
                              [meas(f"cpad_{dut}_{tag}_ff",
                                    f"vecmax(imag(-i(vac{dut})))/(2*pi*500e6)*1e15", "fF")]))
    for dut, rail in ESD_DUTS.items():  # forward current and dynamic resistance
        fwd_bias = 1 if rail == "vdd" else 0
        sign = 1 if rail == "vdd" else -1
        for tag, volts in ESD_OVERDRIVE:
            alter = {**esd_bias(dut, fwd_bias), **esd_overdrive(dut, sign * volts)}
            steps.append(step(f"fwd_{dut}_{tag}", OP, dict(alter),
                              [meas(f"ifwd_{dut}_{tag}_a", f"abs(i(vac{dut}))", "A")]))
            steps.append(step(f"rdyn_{dut}_{tag}", AC1K, {**alter, f"Vac{dut}.ac": 1},
                              [meas(f"rdyn_{dut}_{tag}_ohm", f"1/real(-i(vac{dut}))", "ohm")]))
    return steps


def request(netlist: str, steps: list, top: list = None, osdi: bool = True) -> dict:
    r = {"engine": "ngspice", "netlist": netlist,
         "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
         "corners": corners(),
         "analysis_steps": steps}
    if top is not None:
        r["measurements"] = top
    # fail_on_diagnostic grades a corner whose operating point did not converge
    # as inconclusive, never pass/fail.
    r["options"] = {"stage_model_inputs": True, "fail_on_diagnostic": ["nonconvergence"],
                    "timeout_s": 60, "keep_artifacts": False}
    if osdi:
        r["options"]["osdi_preload"] = OSDI
    r["backend"] = "batch"
    r["batch"] = {"runner_version_check": "warn", "capacity_wait_s": CAPACITY_WAIT_S}
    return r


def requests() -> dict:
    return {
        "request.json": request("tb_dc_static.cir", DC_STEPS, DC_TOP),
        "request_2kv.json": request("tb_dc_static_2kv.cir", DC_STEPS, DC_TOP),
        # The ESD bench instantiates the library diodes directly; it includes no
        # design/ cell, so it needs no OSDI compact models.
        "request_esd_diode.json": request("tb_esd_diode.cir", esd_steps(), osdi=False),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if a committed request is stale, writing nothing")
    args = ap.parse_args()
    bad = 0
    for name, req in requests().items():
        p = HERE / name
        text = json.dumps(req, indent=2) + "\n"
        if args.check:
            if not p.exists() or p.read_text() != text:
                print(f"STALE: {p.name} (run python3 -I sim/dc-static/{Path(__file__).name})",
                      file=sys.stderr)
                bad = 1
        else:
            p.write_text(text)
    return bad


if __name__ == "__main__":
    sys.exit(main())
