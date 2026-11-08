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


def corners() -> dict:
    proc = []
    for c in ("tt", "ss", "ff", "sf", "fs"):
        proc.append({"name": c, "sections": [
            {"lib": LIBM, "section": f"mos_{c}_mismatch"},
            {"lib": "libs.tech/ngspice/models/cornerRES.lib", "section": RES[c]},
            {"lib": "libs.tech/ngspice/models/cornerDIO.lib", "section": "dio_tt"}]})
    return {"process": proc, "supply_v": {"vddio": [1.08, 1.2, 1.32]},
            "temperature_c": [-40, 27, 125]}


# row id -> (netlist, control netlist, analysis step list, MC n, seed)
ROWS = {}


def request(row: str, ctl: bool) -> dict:
    spec = ROWS[row]
    return {
        "engine": "ngspice",
        "netlist": spec["ctl_netlist"] if ctl else spec["netlist"],
        "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
        "corners": corners(),
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
