#!/usr/bin/env python3
"""Generate the T1 item 6 Monte Carlo `klt sim` requests (nominal + negative control).

Stdlib only. `python3 -I sim/mc/gen_mc.py [--check]` writes (or checks) one
`request_<row>.json` and `request_<row>_ctl.json` per campaign in sim/mc/.
The 45-corner PVT-FULL grid comes from `sim/pvt_full.py` (the repo's one encoding
of spec/target-spec.md), on the PDK's `mos_<corner>_mismatch` sections so
per-instance mismatch is live.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "capture_window"))
sys.path.insert(0, str(HERE.parent))
import gen_t19  # noqa: E402  (T-19 bench constants and measurement cards)
import pvt_full  # noqa: E402  (the one PVT-FULL corner-bundle definition)
LIBM = pvt_full.LIB_MOS


def corners(supplies=("vddio",)) -> dict:
    """The PVT-FULL grid on the PDK's `mos_*_mismatch` sections (per-instance mismatch live)."""
    return pvt_full.corners(supplies, style="explicit", mismatch=True)


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
                    "osdi_preload": pvt_full.osdi_preload()},
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


# T-19 receiver capture window (#138): swept-offset single transient, see capture_window/gen_t19.py.
# One-sided aperture limit (a width; the row has no lower bound) with target_sigma 7, the one-sided
# reading of the 14 sigma peak-to-peak used for the other STAT rows (README, Assumptions).
ROWS["t19"] = {
    "dir": "capture_window",
    "netlist": "tb_t19.cir", "ctl_netlist": "tb_t19_ctl.cir", "n": 20, "n_ctl": 20, "seed": 4430, "seed_ctl": 4431,
    "supplies": ("vdd_rx",), "timeout_s": 60,
    "steps": [{"name": "cw", "analysis": {"kind": "tran", "args": f"5p {gen_t19.ns(gen_t19.T_END_PS)} 0 20p"},
               "alter": {},
               "measurements": [{"name": k, "spice": v, "unit": "s" if k in ("dr", "df") else "V"}
                                for k, v in gen_t19.steps().items()]}],
    "top": [{"name": "t19_aperture_ps", "expr": "(cw.ys-cw.xs)*1000+(cw.df-cw.dr)*1e12", "unit": "ps",
             "limits": {"max": 150, "target_sigma": 7}},
            {"name": "t19_setup_ps", "expr": f"-((cw.xs-{gen_t19.DELTA_PS / 2000})*1000+cw.dr*1e12)", "unit": "ps"},
            {"name": "t19_hold_ps", "expr": f"(cw.ys-{gen_t19.DELTA_PS / 2000})*1000+cw.df*1e12", "unit": "ps"}],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    bad = 0
    for row in ROWS:
        for ctl in (False, True):
            p = HERE / ROWS[row].get("dir", ".") / f"request_{row}{'_ctl' if ctl else ''}.json"
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
