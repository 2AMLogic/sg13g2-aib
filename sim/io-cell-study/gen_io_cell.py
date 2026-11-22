#!/usr/bin/env python3
"""Generate the sim/io-cell-study `klt sim` request from one description.

Stdlib only. `python3 -I sim/io-cell-study/gen_io_cell.py [--check]` writes (or checks) the
committed request, request.json, for tb_io_cell.cir (issue #196: the PDK `sg13g2_io` pad cells
as the AIB pin).

The grid is the PVT-FULL one from `sim/pvt_full.py` (5 MOS corners x VDDIO 1.08/1.20/1.32 V x
-40/27/125 C = 45 units) with one addition: the PDK I/O cells are built from thick-oxide
`sg13_hv_*` devices as well as the thin-oxide ones, so each process bundle also carries the
matching `cornerMOShv.lib` section. The check in scripts/ci/check_corner_bundles.py reads the
`cornerMOSlv.lib` / resistor / diode sections only, so the extra hv section is outside what it
grades. The cell's own `iovdd` is not a swept source: tb_io_cell.cir derives it from VDDIO, and
the steps alter `Vkiov` to pick the mode (see the bench header).

Nothing here is graded: no `limits` anywhere, so the report carries ranges and the record's
`rows` is empty by construction (--allow-empty-rows in run_io_cell.sh). The grading against
T-24's two columns and T-08 is done in the study record, from those ranges.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pvt_full  # noqa: E402  (the one PVT-FULL corner-bundle definition)
import gen_common  # noqa: E402  (the one write-or-check implementation)

LIB_HV = pvt_full.MODELS + "cornerMOShv.lib"
CAPACITY_WAIT_S = 600
OP = {"kind": "op", "args": ""}
AC500 = {"kind": "ac", "args": "lin 1 500meg 500meg"}

# mode -> Vkiov (iovdd = Vddio x Vkiov); see tb_io_cell.cir
MODES = {"p": 2.75,   # the PDK-characterised 3.3 V iovdd point
         "a": 1.0}    # iovdd = VDDIO, the AIB 1.2 V signalling level (not PDK-characterised)
# pad-bias tag -> (Vpf, Vpg), fractions of VDDIO and of iovdd
BIAS_VDDIO = (("0", (0, 0)), ("5", (0.5, 0)), ("10", (1, 0)))
BIAS_IOVDD = (("g5", (0, 0.5)), ("g10", (0, 1)))
CAP_DUTS = {"a": "IOPadInOut4mA", "b": "IOPadInOut16mA", "c": "IOPadInOut30mA", "d": "IOPadIn"}
DRV_CELLS = ("4", "16", "30")
IDRV = 1e-3          # the same 1 mA load sim/dc-static uses for T-08


def corners() -> dict:
    c = pvt_full.corners(("vddio",), style="explicit")
    for entry in c["process"]:
        corner = entry["name"]
        entry["sections"].insert(1, {"lib": LIB_HV, "section": pvt_full.mos_section(corner)})
    return c


def meas(name: str, expr: str, unit: str) -> dict:
    return {"name": name, "expr": expr, "unit": unit}


def step(name: str, analysis: dict, alter: dict, measurements: list) -> dict:
    return {"name": name, "analysis": analysis, "alter": alter, "measurements": measurements}


def steps() -> list:
    out = []
    for mode, k in MODES.items():
        biases = BIAS_VDDIO + (BIAS_IOVDD if mode == "p" else ())
        for dut in CAP_DUTS:
            for tag, (pf, pg) in biases:
                out.append(step(f"cap_{dut}_{mode}_{tag}", AC500,
                                {"Vkiov": k, "Vpf": pf, "Vpg": pg, f"Vac{dut}.ac": 1},
                                [meas(f"cpad_{dut}_{mode}_{tag}_ff",
                                      f"vecmax(imag(-i(vac{dut})))/(2*pi*500e6)*1e15", "fF")]))
        loads = {}
        ms = []
        for c in DRV_CELLS:
            loads.update({f"Ih{c}": IDRV, f"Il{c}": IDRV})
            ms += [meas(f"rout_up_{c}_{mode}_ohm", f"(v(iovdd)-v(pad_h{c}))/{IDRV}", "ohm"),
                   meas(f"rout_dn_{c}_{mode}_ohm", f"v(pad_l{c})/{IDRV}", "ohm"),
                   meas(f"voh_{c}_{mode}_v", f"v(pad_h{c})", "V"),
                   meas(f"vol_{c}_{mode}_v", f"v(pad_l{c})", "V")]
        out.append(step(f"drv_{mode}", OP, {"Vkiov": k, **loads}, ms))
        for lvl, v in (("lo", 0), ("hi", 1)):
            out.append(step(f"rx_{lvl}_{mode}", OP, {"Vkiov": k, "Vrf": v},
                            [meas(f"p2c_{lvl}_{mode}_frac", "v(p2c_r)/v(vddio)", "frac")]))
    return out


def request() -> dict:
    return {"engine": "ngspice", "netlist": "tb_io_cell.cir",
            "models": {"pdk": "ihp-sg13g2", "lib": pvt_full.LIB_MOS},
            "corners": corners(),
            "analysis_steps": steps(),
            "options": {"stage_model_inputs": True, "fail_on_diagnostic": ["nonconvergence"],
                        "timeout_s": 200, "keep_artifacts": False,
                        "osdi_preload": pvt_full.osdi_preload()},
            "backend": "batch", "batch": {"capacity_wait_s": CAPACITY_WAIT_S}}


def main() -> int:
    outputs = {"request.json": json.dumps(request(), indent=2) + "\n"}
    return gen_common.write_or_check(outputs, base=HERE, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main())
