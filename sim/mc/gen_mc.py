#!/usr/bin/env python3
"""Generate the T1 item 6 Monte Carlo `klt sim` requests (nominal + negative control).

Stdlib only. `python3 -I sim/mc/gen_mc.py [--check]` writes (or checks) one
`request_<row>.json` and `request_<row>_ctl.json` per campaign in sim/mc/.
The 45-corner PVT-FULL grid (spec/target-spec.md) is built from the PDK's
`mos_<corner>_mismatch` sections so per-instance mismatch is live.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIBM = "libs.tech/ngspice/models/cornerMOSlv.lib"
RES = {"tt": "res_typ", "ss": "res_wcs", "ff": "res_bcs", "sf": "res_typ", "fs": "res_typ"}
OSDI = [f"$PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/osdi/{m}.osdi"
        for m in ("psp103", "psp103_nqs", "r3_cmc", "mosvar")]


def corners(supplies=("vddio",)) -> dict:
    proc = []
    for c in ("tt", "ss", "ff", "sf", "fs"):
        proc.append({"name": c, "sections": [
            {"lib": LIBM, "section": f"mos_{c}_mismatch"},
            {"lib": "libs.tech/ngspice/models/cornerRES.lib", "section": RES[c]},
            {"lib": "libs.tech/ngspice/models/cornerDIO.lib", "section": "dio_tt"}]})
    return {"process": proc, "supply_v": {k: [1.08, 1.2, 1.32] for k in supplies},
            "temperature_c": [-40, 27, 125]}


# row id -> (netlist, control netlist, analysis step list, MC n, seed)
ROWS = {}


def request(row: str, ctl: bool) -> dict:
    spec = ROWS[row]
    return {
        "engine": "ngspice",
        "netlist": spec["ctl_netlist"] if ctl else spec["netlist"],
        "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
        "corners": corners(spec.get("supplies", ("vddio",))),
        "monte_carlo": {"n": spec["n_ctl" if ctl else "n"], "seed": spec["seed_ctl" if ctl else "seed"], "vary": "mismatch"},
        "analysis_steps": spec["steps"],
        "measurements": spec["top"],
        "options": {"stage_model_inputs": True, "fail_on_diagnostic": ["nonconvergence"],
                    "timeout_s": spec.get("timeout_s", 10), "keep_artifacts": False,
                    "osdi_preload": OSDI},
        "backend": "batch",
        "batch": {"runner_version_check": "warn", "capacity_wait_s": 1800},
    }


ROWS["t10"] = {
    "netlist": "tb_t10.cir", "ctl_netlist": "tb_t10_ctl.cir", "n": 120, "n_ctl": 20, "seed": 4410, "seed_ctl": 4411,
    "steps": [{"name": "rx_up", "analysis": {"kind": "dc", "args": "Vfr 0.3 0.7 0.0005"}, "alter": {},
               "measurements": [
                   {"name": "vth_frac", "spice": ".meas dc vth_frac WHEN v(dnorm)=0.5 RISE=1", "unit": "frac"},
                   {"name": "vddio_v", "expr": "v(vddio)[0]", "unit": "V"}]}],
    "top": [{"name": "t10_offset_mv", "expr": "(rx_up.vth_frac-0.5)*rx_up.vddio_v*1000", "unit": "mV",
             "limits": {"min": -60, "max": 60, "target_sigma": 3}}],
}


EDGE_SUPPLIES = ("vdd_atx", "vdd_arx", "vdd_btx", "vdd_brx", "vdd_ctx", "vdd_crx")


def edge_step(meas_card: str, name: str) -> list:
    return [{"name": "edge", "analysis": {"kind": "tran", "args": "2p 5n 0 5p"}, "alter": {},
             "measurements": [{"name": name, "spice": meas_card, "unit": "s"}]}]


# Single-edge RX-input skew benches (#137). The skew is the signed difference of two lane
# crossings of the RX input at mid-rail (data lane A rising vs complement lane B falling for
# T-15; data A rising vs the center-aligned clock csig=rxc-rxcb rising for T-16). Limits are the
# row's bound with target_sigma 7 each side (sim/mc/README.md, "Assumptions for ratification").
ROWS["t15"] = {
    "netlist": "tb_t15.cir", "ctl_netlist": "tb_t15_ctl.cir", "n": 20, "n_ctl": 20, "seed": 4415, "seed_ctl": 4416,
    "supplies": EDGE_SUPPLIES,
    "steps": edge_step(".meas tran skew TRIG v(dsa) VAL=0 RISE=1 TARG v(dsb) VAL=0 FALL=1", "skew"),
    "top": [{"name": "t15_skew_ps", "expr": "edge.skew*1e12", "unit": "ps",
             "limits": {"min": -60, "max": 60, "target_sigma": 7}}],
}
ROWS["t16"] = {
    "netlist": "tb_t16.cir", "ctl_netlist": "tb_t16_ctl.cir", "n": 40, "n_ctl": 20, "seed": 4420, "seed_ctl": 4421,
    "supplies": EDGE_SUPPLIES,
    "steps": edge_step(".meas tran dly TRIG v(dsa) VAL=0 RISE=1 TARG v(csig) VAL=0 RISE=1", "dly"),
    "top": [{"name": "t16_dev_from_half_ui_ps", "expr": "(edge.dly-0.5e-9)*1e12", "unit": "ps",
             "limits": {"min": -30, "max": 30, "target_sigma": 7}}],
}


# Single-edge TX-output skew benches (#136). Same measurement as T-15/T-16 but at the TX pad node
# (near-side output: driver + pad ESD, no channel, no receiver). T-13: lane A rises vs complement lane
# B falls; T-14: data A rises vs the center-aligned clock pair (padc - padcb) rises 500 ps later.
# Limits are the row's bound (0.04 / 0.02 UI at 1 Gb/s = 40 / 20 ps) with target_sigma 7 each side.
ROWS["t13"] = {
    "netlist": "tb_t13.cir", "ctl_netlist": "tb_t13_ctl.cir", "n": 20, "n_ctl": 20, "seed": 4413, "seed_ctl": 4414,
    "supplies": ("vdd_atx", "vdd_btx"),
    "steps": edge_step(".meas tran skew TRIG v(dsa) VAL=0 RISE=1 TARG v(dsb) VAL=0 FALL=1", "skew"),
    "top": [{"name": "t13_skew_ps", "expr": "edge.skew*1e12", "unit": "ps",
             "limits": {"min": -40, "max": 40, "target_sigma": 7}}],
}
ROWS["t14"] = {
    "netlist": "tb_t14.cir", "ctl_netlist": "tb_t14_ctl.cir", "n": 20, "n_ctl": 20, "seed": 4418, "seed_ctl": 4419,
    "supplies": ("vdd_atx", "vdd_ctx"),
    "steps": edge_step(".meas tran dly TRIG v(dsa) VAL=0 RISE=1 TARG v(csig) VAL=0 RISE=1", "dly"),
    "top": [{"name": "t14_dev_from_half_ui_ps", "expr": "(edge.dly-0.5e-9)*1e12", "unit": "ps",
             "limits": {"min": -20, "max": 20, "target_sigma": 7}}],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    bad = 0
    for row in ROWS:
        for ctl in (False, True):
            p = HERE / f"request_{row}{'_ctl' if ctl else ''}.json"
            text = json.dumps(request(row, ctl), indent=2) + "\n"
            if args.check:
                if not p.exists() or p.read_text() != text:
                    print(f"STALE: {p.name}", file=sys.stderr)
                    bad = 1
            else:
                p.write_text(text)
    return bad


if __name__ == "__main__":
    sys.exit(main())
