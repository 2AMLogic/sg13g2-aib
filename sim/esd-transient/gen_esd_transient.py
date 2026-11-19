#!/usr/bin/env python3
"""Generate the sim/esd-transient `klt sim` request from one description.

Stdlib only. `python3 -I sim/esd-transient/gen_esd_transient.py [--check]` writes (or
checks) the committed request, request.json, for tb_esd_transient.cir (issue #196: the
T-25 SIM leg, the 0.5 A ESD discharge transient, DR-0029).

T-25's grid column is n/a: this is a single-configuration bench, not a grid. The corners
object is the PVT-FULL bundle restricted to its nominal point (mos_tt, 1.20 V, 27 C --
`pvt_full.corners` with the documented single-corner overrides; the vddio source is not a
corner axis because the tran steps alter it between powered and unpowered). The run is
local (`backend: "local"`, one unit); no `--wait-for-capacity` and no fleet are involved.

Two tran steps alter Vddio between powered (1.2 V) and unpowered (0 V, the discharge
case); both pulse polarities fire inside each step and the per-measurement time windows
separate them (see the bench header). Pulse shape and the pass bounds below are fixed by
DR-0029 before the run; they are not edited after it.

Graded T-25 measurements, per step:
  - peak |V(PAD)| and peak |V(PADI)| per polarity (the clamp-path impedance and the
    isolation the secondary stage must absorb);
  - the protected-branch current per polarity (the XResd + secondary-stage branch);
  - the recovery ratio per polarity: |V(PAD)| 1 ns after the crest over its own peak
    (derived, top level: the node discharges through the clamp path -- about 2 time
    constants of R_path*C_node, R_path from DR-0018's measured forward resistance and
    C_node from T-24 -- not a node stuck at its peak).

The three mc_ steps carry no `spec_row`: they are the model check (the conduction models
the transient credits, measured at the sizes the committed netlist uses), reported, not
graded. The `pad_late_*_v` measurements feed the derived recovery ratios and grade nothing
themselves (no spec_row, and no `t25_` prefix for the runner's row map); each derived
ratio carries T-25 and its bound.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pvt_full  # noqa: E402  (the one PVT-FULL corner-bundle definition)
import gen_common  # noqa: E402  (the one write-or-check implementation)

# The DUT is instantiated twice (see the bench header): the voltage
# measurements read the floating-PADI instance (pad_t / padi_f), the
# protected-branch current the metered instance (i(vmeas_padi), an upper
# bound because the meter pins PADI at 0 V).
# Measurement windows in the 55 ns transient: window A covers the positive pulse
# (crest at t = 1.2 ns), window B the negative pulse (crest at t = 51.2 ns); the late
# windows start 1 ns after the crest (DR-0029's recovery bound).
MASK_A = "(time ge 0.8n)*(time le 4n)"
MASK_B = "(time ge 50.8n)*(time le 54n)"
LATE_A = "(time ge 2.2n)*(time le 3n)"
LATE_B = "(time ge 52.2n)*(time le 53n)"
I_PADI = "i(vmeas_padi)"
TRAN = {"kind": "tran", "args": "1p 55n 0 5p"}
# DR-0029 s5 bounds, stated before the run.
MAX_VPAD_POS = 7.0      # V, positive-pulse peak |V(PAD)|
MAX_VPAD_NEG = 3.0      # V, negative-pulse peak |V(PAD)|
MAX_VADI = 3.5          # V, |V(PADI)| either polarity
MAX_IPADI = 0.05        # A, protected-branch peak (10 % of the 0.5 A pulse)
MAX_RELIEF = 0.40       # ratio, |V(PAD)| 1 ns after its crest over its own peak


def meas(name: str, expr: str, unit: str, limits: dict, graded: bool = True) -> dict:
    m = {"name": name, "expr": expr, "unit": unit}
    if graded:
        m["spec_row"] = "T-25"
        m["limits"] = limits
    return m


def tran_step(name: str, alter: dict) -> dict:
    """One supply state, both pulse polarities, DR-0029 bounds."""
    return {
        "name": name,
        "analysis": TRAN,
        "alter": alter,
        "measurements": [
            meas("t25_vpad_pos_pk_v", f"vecmax(abs(v(pad_t))*{MASK_A})", "V",
                 {"max": MAX_VPAD_POS}),
            meas("t25_vpad_neg_pk_v", f"vecmax(abs(v(pad_t))*{MASK_B})", "V",
                 {"max": MAX_VPAD_NEG}),
            meas("t25_vadi_pos_pk_v", f"vecmax(abs(v(padi_f))*{MASK_A})", "V",
                 {"max": MAX_VADI}),
            meas("t25_vadi_neg_pk_v", f"vecmax(abs(v(padi_f))*{MASK_B})", "V",
                 {"max": MAX_VADI}),
            meas("t25_ipadi_pos_pk_a", f"vecmax(abs({I_PADI})*{MASK_A})", "A",
                 {"max": MAX_IPADI}),
            meas("t25_ipadi_neg_pk_a", f"vecmax(abs({I_PADI})*{MASK_B})", "A",
                 {"max": MAX_IPADI}),
            # feeds the derived recovery ratio; grades nothing itself
            meas("pad_late_pos_v", f"vecmax(abs(v(pad_t))*{LATE_A})", "V",
                 None, graded=False),
            meas("pad_late_neg_v", f"vecmax(abs(v(pad_t))*{LATE_B})", "V",
                 None, graded=False),
        ],
    }


def mc_step(name: str, alter: dict, analysis: dict) -> dict:
    """One DC sweep of a model-check DUT; reported, never graded."""
    return {"name": name, "analysis": analysis, "alter": alter,
            "measurements": []}


def steps() -> list:
    out = [tran_step("pwr", {"Vddio": 1.2}),
           tran_step("unpwr", {"Vddio": 0}),
           # Diode model check, powered and unpowered rail: first sweep voltage at which
           # the diode carries 0.5 A (the voltages where |i| >= 0.5 keep their value,
           # elsewhere a sentinel 1000 is added; the in-window minimum is the first
           # crossing).
           mc_step("mc_dio_fwd", {"Vddio": 1.2, "Vmc2r": 1.2},
                   {"kind": "dc", "args": "Vmc2 0 8 0.01"}),
           mc_step("mc_dio_fwd_novdd", {"Vddio": 0, "Vmc2r": 0},
                   {"kind": "dc", "args": "Vmc2 0 8 0.01"}),
           # XMn1's drain-body junction, negative-pulse direction (a positive pulse
           # reverse-biases it): sweep down, so the first crossing is the largest
           # (least negative) voltage with |i| >= 0.5 -- sentinel -1000 outside.
           mc_step("mc_xmn1_neg", {"Vddio": 0},
                   {"kind": "dc", "args": "Vmc1 0 -4 -0.01"}),
           ]
    # The mc_ measurements are appended to their steps so the resolved names are
    # <step>.<name> and carry no spec_row; the sweep-source branch current i(vN) is
    # saved by ngspice for a dc sweep. Each value is the first sweep point at which
    # the swept source carries 0.5 A.
    mc = {"mc_dio_fwd": ("mc_idiode_500ma_v",
                         "vecmin(v(pad_mc2)*(abs(i(vmc2)) ge 0.5)"
                         " + 1000*(abs(i(vmc2)) lt 0.5))"),
          "mc_dio_fwd_novdd": ("mc_idiode_novdd_500ma_v",
                               "vecmin(v(pad_mc2)*(abs(i(vmc2)) ge 0.5)"
                               " + 1000*(abs(i(vmc2)) lt 0.5))"),
          "mc_xmn1_neg": ("mc_ixmn1_neg_500ma_v",
                          "vecmax(v(pad_mc1)*(abs(i(vmc1)) ge 0.5)"
                          " - 1000*(abs(i(vmc1)) lt 0.5))")}
    for step in out:
        if step["name"] in mc:
            name, expr = mc[step["name"]]
            step["measurements"].append({"name": name, "expr": expr, "unit": "V"})
    return out


def derived() -> list:
    """The DR-0029 recovery ratios: late-window |V(PAD)| over its own peak, per step
    and polarity. Top level (like dc-static's t11_hyst_mv), graded T-25; names carry
    the step because top-level measurement names are globally unique."""
    out = []
    for step in ("pwr", "unpwr"):
        for tag in ("pos", "neg"):
            out.append({
                "spec_row": "T-25",
                "name": f"t25_{step}_{tag}_relief",
                "expr": (f"abs({step}.pad_late_{tag}_v)"
                         f"/abs({step}.t25_vpad_{tag}_pk_v)"),
                "unit": "ratio",
                "limits": {"max": MAX_RELIEF},
            })
    return out


def request() -> dict:
    return {
        "engine": "ngspice",
        "netlist": "tb_esd_transient.cir",
        "models": {"pdk": "ihp-sg13g2", "lib": pvt_full.LIB_MOS},
        "corners": pvt_full.corners((), style="explicit", only=("tt",),
                                    supply_v=[], temperature_c=[27]),
        "analysis_steps": steps(),
        "measurements": derived(),
        "options": {"stage_model_inputs": True, "fail_on_diagnostic": ["nonconvergence"],
                    "timeout_s": 120, "keep_artifacts": False,
                    "osdi_preload": pvt_full.osdi_preload()},
        "backend": "local",
    }


def main() -> int:
    outputs = {"request.json": json.dumps(request(), indent=2) + "\n"}
    return gen_common.write_or_check(outputs, base=HERE, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main())
