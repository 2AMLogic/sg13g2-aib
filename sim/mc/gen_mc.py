#!/usr/bin/env python3
"""Generate the T1 item 6 Monte Carlo `klt sim` requests (nominal + negative control).

Stdlib only. `python3 -I sim/mc/gen_mc.py [--check]` writes (or checks) one
`request_<row>.json` and `request_<row>_ctl.json` per campaign in sim/mc/, plus the
T-10 control bench `tb_t10_ctl.cir` (see `tb_t10_ctl`). The 45-corner PVT-FULL grid comes
from `sim/pvt_full.py` (the repo's one encoding of spec/target-spec.md), on the PDK's
`mos_<corner>_mismatch` sections so
per-instance mismatch is live.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE / "capture_window"))
sys.path.insert(0, str(HERE.parent))
import gen_t19  # noqa: E402  (T-19 bench constants and measurement cards)
import pvt_full  # noqa: E402  (the one PVT-FULL corner-bundle definition)
import gen_common  # noqa: E402  (write_or_check and the seeded-defect substitution)
LIBM = pvt_full.LIB_MOS


def corners(supplies=("vddio",)) -> dict:
    """The PVT-FULL grid on the PDK's `mos_*_mismatch` sections (per-instance mismatch live)."""
    return pvt_full.corners(supplies, style="explicit", mismatch=True)


# row id -> (netlist, control netlist, analysis step list, MC n, seed)
ROWS = {}


def request(row: str, ctl: bool) -> dict:
    spec = ROWS[row]
    steps = spec.get("ctl_steps") if ctl else None
    if steps is None:
        steps = spec["steps"]
    return {
        "engine": "ngspice",
        "netlist": spec["ctl_netlist"] if ctl else spec["netlist"],
        "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
        "corners": corners(spec.get("supplies", ("vddio",))),
        "monte_carlo": {"n": spec["n_ctl" if ctl else "n"], "seed": spec["seed_ctl" if ctl else "seed"], "vary": "mismatch"},
        "analysis_steps": steps,
        "measurements": spec["top"],
        "options": {"stage_model_inputs": True, "fail_on_diagnostic": ["nonconvergence"],
                    "timeout_s": spec.get("timeout_s", 10), "keep_artifacts": False,
                    "osdi_preload": pvt_full.osdi_preload()},
        "backend": "batch",
        "batch": {"capacity_wait_s": 1800},
    }


ROWS["t10"] = {
    "netlist": "tb_t10.cir", "ctl_netlist": "tb_t10_ctl.cir", "n": 120, "n_ctl": 20, "seed": 4410, "seed_ctl": 4411,
    "steps": [{"name": "rx_up", "analysis": {"kind": "dc", "args": "Vfr 0.3 0.7 0.0005"}, "alter": {},
               "measurements": [
                   {"name": "vth_frac", "spice": ".meas dc vth_frac WHEN v(dnorm)=0.5 RISE=1", "unit": "frac"},
                   {"name": "vddio_v", "expr": "v(vddio)[0]", "unit": "V"},
                   {"name": "ivdd_a", "spice": ".meas dc ivdd_a FIND i(vddio) AT=0.5", "unit": "A"}]}],
    # The degraded cell (input-pair NMOS 4x narrower) crosses at fr 0.66-0.75 over the grid
    # (#386 study, records/20261121T091822Z-mc), outside the committed 0.3-0.7 window, so the
    # control widens its sweep; the nominal bench keeps the committed window. One stated
    # deviation, carried by the study and now by this row.
    "ctl_steps": [{"name": "rx_up", "analysis": {"kind": "dc", "args": "Vfr 0.15 0.95 0.0005"}, "alter": {},
                   "measurements": [
                       {"name": "vth_frac", "spice": ".meas dc vth_frac WHEN v(dnorm)=0.5 RISE=1", "unit": "frac"},
                       {"name": "vddio_v", "expr": "v(vddio)[0]", "unit": "V"}]}],
    "top": [{"name": "t10_offset_mv", "expr": "(rx_up.vth_frac-0.5)*rx_up.vddio_v*1000", "unit": "mV",
             "limits": {"min": -60, "max": 60, "target_sigma": 3}}],
}


# T-10 negative control bench. tb_t10.cir includes design/aib_rx_data.spice as drawn; the
# control inlines a copy of that cell instead and narrows its input-pair NMOS, which is the
# one seeded degradation the control exists to detect. Derived from the design cell rather
# than hand-copied (#202) so a resize of the receiver cannot leave the control on the old
# device sizes while still claiming to isolate the narrowing. Since the #398 adoption the
# design cell is the supply-referenced stage (the #386 study's rx__vref); its input-pair NMOS
# (Mnp, gate PAD) is the degraded device, the same defect the study's control seeded.
T10_CTL_HEADER = """\
* T-10 negative control: the receiver's input-pair NMOS is made 4x narrower
* (w=0.25u ng=1 instead of w=1u ng=2), a seeded design degradation that must move the
* threshold out of the +-60 mV bound. A bench copy, not design evidence; the
* design cell is NOT included here.
"""
T10_INCLUDE = ".include ../../design/aib_rx_data.spice"
T10_NMOS = "XMnp d1 PAD s1 VSS sg13_lv_nmos w={} l=0.5u ng={} m=1"


def tb_t10_ctl() -> str:
    """tb_t10.cir with the design cell inlined in place of its .include and the receiver's
    input-pair NMOS narrowed from w=1u ng=2 to w=0.25u ng=1. The other devices are
    copied verbatim, so they follow design/aib_rx_data.spice."""
    what = "tb_t10_ctl.cir"
    cell = "\n".join(line for line in (ROOT / "design" / "aib_rx_data.spice").read_text().splitlines()
                     if not line.startswith("*"))     # the design cell's own comments and PININFO
    cell = gen_common.seed(cell, T10_NMOS.format("1u", 2), T10_NMOS.format("0.25u", 1), what)
    lines = (HERE / "tb_t10.cir").read_text().splitlines()
    head = 0
    while head < len(lines) and lines[head].startswith("*"):
        head += 1                                     # the nominal header; the control has its own
    return T10_CTL_HEADER + gen_common.seed("\n".join(lines[head:]), T10_INCLUDE, cell, what) + "\n"


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


def outputs() -> dict:
    """path -> text for every file this script writes."""
    out = {}
    for row in ROWS:
        for ctl in (False, True):
            p = HERE / ROWS[row].get("dir", ".") / f"request_{row}{'_ctl' if ctl else ''}.json"
            out[p] = json.dumps(request(row, ctl), indent=2) + "\n"
    out[HERE / "tb_t10_ctl.cir"] = tb_t10_ctl()
    return out


def main() -> int:
    return gen_common.write_or_check(outputs(), description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main())
