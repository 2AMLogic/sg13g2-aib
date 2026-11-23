#!/usr/bin/env python3
"""Generate the receiver-threshold sizing-study benches and requests (issue #386).

Stdlib only. `python3 -I sim/rx-threshold-study/gen_rx_threshold.py [--check]`.

T-10 fails on a systematic corner shift (8 of 45 corner means outside +-60 mV,
per-corner sigma 4.9-6.8 mV; `sim/mc/per_corner.md`), so this study screens
first-stage candidates for `aib_rx_data` on the T-10 bench form and confirms the
selected one by Monte Carlo. No `design/` or `layout/` file is touched:
candidates live here as study cells with unique subckt names, and the benches
that need a drop-in `aib_rx_data` inline the selected candidate's text.

Generated files:

  cand_cells.inc          every candidate cell (unique subckt names), study evidence
  prbs7_stim.inc          the channel-eye PRBS-7 stimulus (same bytes as channel-eye's)
  tb_screen.cir           DC screen: every candidate on one pad ramp (nominal offsets)
  tb_mc.cir, tb_mc_ctl.cir  Monte Carlo bench for SELECTED + its seeded control
  tb_hyst.cir             T-11: as-drawn and SELECTED side by side on one ramp
  tb_pin.cir              T-24: two pins (as-drawn vs SELECTED receiver), AC at 3 biases
  tb_clk.cir             clock path three ways (committed / SELECTED / the adoptable
                         split: SELECTED in the data lane, committed in the clock legs),
                         t02 edges
  tb_t16_base.cir, tb_t16_cand.cir, tb_t16_mixed.cir  the channel-eye four-lane bench
                         with the as-drawn receiver, the SELECTED candidate in every
                         lane, and the adoptable split (candidate in lanes A/B only)
  request_screen.json, request_mc.json, request_mc_ctl.json, request_hyst.json,
  request_pin.json, request_clk.json, request_t16_base.json, request_t16_cand.json,
  request_t16_mixed.json

Corner grids come from `sim/pvt_full.py`: the plain `mos_<corner>` sections for
the DC screen and the side-effect legs (no mismatch wanted), the `mos_<c>_mismatch`
sections for the two Monte Carlo requests. The T-16 side-effect requests are
`gen_channel_eye.request("ch")` with the netlist swapped, so the measurement set,
limits and stimulus cannot drift from the committed channel-eye family.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "channel-eye"))
import gen_channel_eye as ce  # noqa: E402  (the T-16 side-effect request form)
import gen_common  # noqa: E402  (write_or_check, seed, the PWL stimulus builders)
import pvt_full  # noqa: E402  (the one PVT-FULL corner-bundle definition)

LIBM = pvt_full.LIB_MOS

# --- the as-drawn receiver (design/aib_rx_data.spice), the baseline of the screen ---
# XMi1p w=2.5u l=0.13u ng=2, XMi1n w=1u l=0.13u ng=2 (P:N width ratio 2.5);
# XMi2p/XMi2n 4u/2u l=0.13u ng=2 is the restore stage every candidate keeps.
STAGE2 = ("4u", 2, "2u", 2, "0.13u")

# Inverter candidates: id -> (wp, wp_ng, wn, wn_ng, l). Stage 2 is STAGE2 for all.
# `w` is the TOTAL width (the PDK device splits it into ng fingers of w/ng), so
# area is w*l whatever ng is. base is the as-drawn cell; r* sweep the P:N ratio,
# l* raise the length at the centring ratio 2.0, a2 halves the finger width at
# ratio 2.0 (same total width and area as r20: a finger-width Vt probe, not an
# area doubling).
INV = {
    "base": ("2.5u", 2, "1u", 2, "0.13u"),
    "r20": ("2.0u", 2, "1u", 2, "0.13u"),
    "r225": ("2.25u", 2, "1u", 2, "0.13u"),
    "r30": ("3.0u", 2, "1u", 2, "0.13u"),
    "r35": ("3.5u", 2, "1u", 2, "0.13u"),
    "l25": ("2.0u", 2, "1u", 2, "0.25u"),
    "l50": ("2.0u", 2, "1u", 2, "0.5u"),
    "a2": ("2.0u", 4, "1u", 4, "0.13u"),
}

# The candidate the Monte Carlo and side-effect legs run. Chosen by the screen
# record records/<stamp>-screen/ (see README): no inverter sizing closes the row,
# vref is the supply-referenced stage that does.
SELECTED = "vref"


def _fmt(x):
    return x if isinstance(x, str) else f"{x}"


def inv_cell(cid: str) -> str:
    """The inverter candidate `cid`: first stage per INV[cid], committed stage 2."""
    wp, png, wn, nng, l = INV[cid]
    return (f"* inverter candidate {cid}: XMi1p w={wp} ng={png}, XMi1n w={wn} ng={nng}, "
            f"both l={l}; restore stage as committed\n"
            f".subckt rx__{cid} PAD DOUT VDDIO VSS\n"
            f"XMi1p M1 PAD VDDIO VDDIO sg13_lv_pmos w={wp} l={l} ng={png} m=1\n"
            f"XMi1n M1 PAD VSS VSS sg13_lv_nmos w={wn} l={l} ng={nng} m=1\n"
            f"XMi2p DOUT M1 VDDIO VDDIO sg13_lv_pmos w={STAGE2[0]} l={STAGE2[4]} ng={STAGE2[1]} m=1\n"
            f"XMi2n DOUT M1 VSS VSS sg13_lv_nmos w={STAGE2[2]} l={STAGE2[4]} ng={STAGE2[3]} m=1\n"
            f".ends")


# The supply-referenced candidate: an NMOS pair with PMOS mirror load compares PAD
# against a VDDIO/2 reference derived from a matched rppd divider, so the PVT N/P
# strength skew that moves an inverter trip point enters as a near common-mode
# current change instead of a threshold shift. The tail (gate at VDDIO, not at the
# divider: a vr-referenced tail gate loses headroom at ss/1.08 V/-40 C) and the
# mirror are sized for a ~100 uA tail: d1 charges through the mirror, so the tail
# current sets both the opposite-edge delay asymmetry and the transient cost of
# the channel benches. The restore inverter is the committed cell's stage 2 at
# half width (the candidate owns its restore stage; DOUT only drives the declared
# 5 fF flop load).
VREF = """\
* supply-referenced candidate: NMOS pair + PMOS mirror load against a matched
* rppd VDDIO/2 divider; restore inverter at half the committed width. Study cell,
* not design evidence.
.subckt rx__vref PAD DOUT VDDIO VSS
XRdiv1 VDDIO vrn VSS rppd w=0.5u l=48u m=1 b=0
XRdiv2 vrn VSS VSS rppd w=0.5u l=48u m=1 b=0
XMtail s1 VDDIO VSS VSS sg13_lv_nmos w=2u l=0.5u ng=2 m=1
XMnp d1 PAD s1 VSS sg13_lv_nmos w=1u l=0.5u ng=2 m=1
XMnn d2 vrn s1 VSS sg13_lv_nmos w=1u l=0.5u ng=2 m=1
XMlp d2 d2 VDDIO VDDIO sg13_lv_pmos w=4u l=0.25u ng=4 m=1
XMln d1 d2 VDDIO VDDIO sg13_lv_pmos w=4u l=0.25u ng=4 m=1
XMi2p DOUT d1 VDDIO VDDIO sg13_lv_pmos w=2u l=0.13u ng=1 m=1
XMi2n DOUT d1 VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1
.ends"""

CANDS = list(INV) + ["vref"]


def cand_text(cid: str) -> str:
    return VREF if cid == "vref" else inv_cell(cid)


# the seeded degradation of the Monte Carlo negative control: the input-side NMOS
# made 4x narrower (the same defect semantics as the committed tb_t10_ctl.cir).
def ctl_seed(cid: str, cell: str) -> str:
    if cid == "vref":
        old = "XMnp d1 PAD s1 VSS sg13_lv_nmos w=1u l=0.5u ng=2 m=1"
        new = "XMnp d1 PAD s1 VSS sg13_lv_nmos w=0.25u l=0.5u ng=1 m=1"
    else:
        wp, png, wn, nng, l = INV[cid]
        old = f"XMi1n M1 PAD VSS VSS sg13_lv_nmos w={wn} l={l} ng={nng} m=1"
        new = f"XMi1n M1 PAD VSS VSS sg13_lv_nmos w=0.25u l={l} ng=1 m=1"
    return gen_common.seed(cell, old, new, f"tb_mc_ctl.cir ({cid})")


def meas(name, unit, row, spice=None, expr=None, **limits):
    d = {"name": name, "unit": unit, "spec_row": row}
    if spice:
        d["spice"] = spice
    if expr:
        d["expr"] = expr
    if limits:
        d["limits"] = limits
    return d


def base_options(timeout_s):
    return {"stage_model_inputs": True, "fail_on_diagnostic": ["nonconvergence"],
            "timeout_s": timeout_s, "keep_artifacts": False,
            "osdi_preload": pvt_full.osdi_preload()}


# --- the DC screen: one bench, one DC sweep, every candidate on the same pad ramp ---
def tb_screen() -> str:
    lines = ["* tb_screen.cir -- GENERATED by gen_rx_threshold.py; do not edit.",
             "* T-10 bench form (sim/mc/tb_t10.cir) with every candidate cell instantiated",
             "* on the same pad ramp: one crossing per candidate per corner, directly",
             "* comparable. Cells are inlined from cand_cells.inc, never .include'd, so the",
             "* record copy is self-contained. Candidates are study cells, not design evidence.",
             "Vddio vddio 0 dc 1.2",
             "Vfr fr 0 dc 0.5",
             "Bpin pad 0 V=v(fr)*v(vddio)"]
    for cid in CANDS:
        lines.append(cand_text(cid))
    for cid in CANDS:
        lines += [f"Xc_{cid} pad do_{cid} vddio 0 rx__{cid}",
                  f"Bdn_{cid} dnorm_{cid} 0 V=v(do_{cid})/v(vddio)"]
    return "\n".join(lines) + "\n"


def request_screen() -> dict:
    step_meas = [{"name": f"vth_{cid}", "spice": f".meas dc vth_{cid} WHEN v(dnorm_{cid})=0.5 RISE=1",
                  "unit": "frac"} for cid in CANDS]
    step_meas.append({"name": "vddio_v", "expr": "v(vddio)[0]", "unit": "V"})
    top = [meas(f"t10_{cid}_mv", "mV", "T-10",
                expr=f"(rx_up.vth_{cid}-0.5)*rx_up.vddio_v*1000") for cid in CANDS]
    return {"engine": "ngspice", "netlist": "tb_screen.cir",
            "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
            "corners": pvt_full.corners(("vddio",), style="explicit"),
            # window 0.15-0.95, wider than the committed T-10 form's 0.3-0.7: the
            # as-drawn cell crosses inside 0.3-0.7 at every corner (the committed
            # record), but ratio candidates shift the crossing (r35 at sf/125C) and
            # the crossing of a candidate outside the window would be an error, not
            # a number. The measured crossing of the as-drawn cell is unchanged by
            # the window (the README checks it against the committed per-corner
            # table).
            "analysis_steps": [{"name": "rx_up", "analysis": {"kind": "dc", "args": "Vfr 0.15 0.95 0.0005"},
                                "alter": {}, "measurements": step_meas}],
            "measurements": top,
            "options": base_options(60),
            "backend": "batch", "batch": {"capacity_wait_s": 600}}


# --- the Monte Carlo pair: SELECTED as aib_rx_data, committed T-10 request shape ---
def _tb_mc(cell: str, header: str) -> str:
    return (header + "\n" + cell + "\n"
            + "Vddio vddio 0 dc 1.2\n"
              "Vfr fr 0 dc 0.5\n"
              "Bpin pad 0 V=v(fr)*v(vddio)\n"
              "Xrx pad dout vddio 0 aib_rx_data\n"
              "Bdn dnorm 0 V=v(dout)/v(vddio)\n")


def tb_mc() -> str:
    cell = cand_text(SELECTED).replace(f"rx__{SELECTED}", "aib_rx_data", 1)
    return _tb_mc(cell, "* tb_mc.cir -- GENERATED by gen_rx_threshold.py; do not edit.\n"
                        "* T-10 bench form with the selected study candidate inlined as aib_rx_data.\n"
                        "* Study cell, not design evidence; design/aib_rx_data.spice is NOT included.")


def tb_mc_ctl() -> str:
    cell = ctl_seed(SELECTED, cand_text(SELECTED)).replace(f"rx__{SELECTED}", "aib_rx_data", 1)
    return _tb_mc(cell, "* tb_mc_ctl.cir -- GENERATED by gen_rx_threshold.py; do not edit.\n"
                        "* T-10 negative control: the selected candidate with its input-side NMOS\n"
                        "* made 4x narrower, the seeded degradation the control exists to detect.\n"
                        "* A bench copy, not design evidence; the design cell is NOT included.")


def _mc_request(netlist, n, seed, sweep="Vfr 0.3 0.7 0.0005"):
    return {"engine": "ngspice", "netlist": netlist,
            "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
            "corners": pvt_full.corners(("vddio",), style="explicit", mismatch=True),
            "monte_carlo": {"n": n, "seed": seed, "vary": "mismatch"},
            "analysis_steps": [{"name": "rx_up", "analysis": {"kind": "dc", "args": sweep},
                                "alter": {}, "measurements": [
                                    {"name": "vth_frac", "spice": ".meas dc vth_frac WHEN v(dnorm)=0.5 RISE=1",
                                     "unit": "frac"},
                                    {"name": "vddio_v", "expr": "v(vddio)[0]", "unit": "V"},
                                    {"name": "ivdd_a", "spice": ".meas dc ivdd_a FIND i(vddio) AT=0.5",
                                     "unit": "A"}]}],
            "measurements": [meas("t10_offset_mv", "mV", "T-10",
                                  expr="(rx_up.vth_frac-0.5)*rx_up.vddio_v*1000",
                                  min=-60, max=60, target_sigma=3)],
            "options": base_options(10),
            "backend": "batch", "batch": {"capacity_wait_s": 1800}}


# --- T-11: the as-drawn receiver and SELECTED side by side on one up/down ramp ---
def tb_hyst() -> str:
    base = inv_cell("base").replace("rx__base", "aib_rx_data__base", 1)
    cand = cand_text(SELECTED).replace(f"rx__{SELECTED}", "aib_rx_data__cand", 1)
    return ("* tb_hyst.cir -- GENERATED by gen_rx_threshold.py; do not edit.\n"
            "* T-11 bench form (sim/dc-static/tb_rx_hyst.cir) with the as-drawn receiver and\n"
            "* the selected candidate on the same pad ramp: one hysteresis number per variant.\n"
            "Vddio vddio 0 dc 1.2\n"
            "Vfr fr 0 dc 0\n"
            "Bpin pad 0 V=v(fr)*v(vddio)\n"
            + base + "\n" + cand + "\n"
            "Xrx_b pad do_b vddio 0 aib_rx_data__base\n"
            "Xrx_c pad do_c vddio 0 aib_rx_data__cand\n"
            "Bdn_b dnorm_b 0 V=v(do_b)/v(vddio)\n"
            "Bdn_c dnorm_c 0 V=v(do_c)/v(vddio)\n")


def request_hyst() -> dict:
    def updn(kind, edge):
        m = [{"name": f"vth_{kind}_b", "spice": f".meas dc vth_{kind}_b WHEN v(dnorm_b)=0.5 {edge}=1",
              "unit": "frac"},
             {"name": f"vth_{kind}_c", "spice": f".meas dc vth_{kind}_c WHEN v(dnorm_c)=0.5 {edge}=1",
              "unit": "frac"}]
        if kind == "up":
            m.append({"name": "vddio_v", "expr": "v(vddio)[0]", "unit": "V"})
        return m
    steps = [{"name": "rx_up", "analysis": {"kind": "dc", "args": "Vfr 0 1 0.001"},
              "alter": {}, "measurements": updn("up", "RISE")},
             {"name": "rx_dn", "analysis": {"kind": "dc", "args": "Vfr 1 0 -0.001"},
              "alter": {}, "measurements": updn("dn", "FALL")}]
    top = [meas(f"t11_hyst_mv__{v}", "mV", "T-11",
                expr=f"abs(rx_up.vth_up_{v}-rx_dn.vth_dn_{v})*rx_up.vddio_v*1000",
                max=60) for v in ("b", "c")]
    return {"engine": "ngspice", "netlist": "tb_hyst.cir",
            "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
            "corners": pvt_full.corners(("vddio",), style="explicit"),
            "analysis_steps": steps, "measurements": top,
            "options": base_options(60),
            "backend": "batch", "batch": {"capacity_wait_s": 600}}


# --- T-24: two complete pins (ESD + tristated TX + receiver), AC at three biases ---
PIN_BIAS = (("0", 0), ("5", 0.5), ("10", 1))
AC500 = {"kind": "ac", "args": "lin 1 500meg 500meg"}


def tb_pin() -> str:
    base = inv_cell("base").replace("rx__base", "aib_rx_data__base", 1)
    cand = cand_text(SELECTED).replace(f"rx__{SELECTED}", "aib_rx_data__cand", 1)
    return ("* tb_pin.cir -- GENERATED by gen_rx_threshold.py; do not edit.\n"
            "* sim/dc-static/tb_pin.cir form with two pins on shared control levels: variant b\n"
            "* carries the as-drawn receiver, variant c the selected candidate. Only the receiver\n"
            "* differs, so the capacitance delta is the candidate's alone. The ESD and TX cells\n"
            "* are included from design/, as in the committed bench; the receivers are inlined.\n"
            "Voef oef 0 dc 0\n"
            "Vdinf dinf 0 dc 0\n"
            "Vpunf punf 0 dc 1\n"
            "Vpdf pdf 0 dc 0\n"
            "Boe oe_p 0 V=v(oef)*v(vddio)\n"
            "Bdin din_p 0 V=v(dinf)*v(vddio)\n"
            "Bpun pun_p 0 V=v(punf)*v(vddio)\n"
            "Bpd pd_p 0 V=v(pdf)*v(vddio)\n"
            "Vddio vddio 0 dc 1.2\n"
            ".include ../../design/aib_pad_esd.spice\n"
            ".include ../../design/aib_tx_data.spice\n"
            + base + "\n" + cand + "\n"
            + "".join(f"Vpf_{v} pf_{v} 0 dc 0\n"
                      f"Bpin_{v} pb_{v} 0 V=v(pf_{v})*v(vddio)\n"
                      f"Vacp_{v} pad_{v} pb_{v} dc 0 ac 0\n"
                      f"Xesd_{v} pad_{v} padi_{v} vddio 0 aib_pad_esd\n"
                      f"Xtx_{v} din_p oe_p pun_p pd_p pad_{v} vddio 0 aib_tx_data\n"
                      f"Xrx_{v} padi_{v} dout_{v} vddio 0 aib_rx_data__{k}\n"
                      for v, k in (("b", "base"), ("c", "cand"))))


def request_pin() -> dict:
    steps, top = [], []
    for tag, v in PIN_BIAS:
        for var in ("b", "c"):
            alter = {"Vpf_b": v, "Vpf_c": v, f"Vacp_{var}.ac": 1}
            steps.append({"name": f"cap_{tag}_{var}", "analysis": AC500, "alter": alter,
                          "measurements": [
                              meas(f"t24_cpin_{tag}_{var}_ff", "fF", "T-24",
                                   expr=f"vecmax(imag(-i(vacp_{var})))/(2*pi*500e6)*1e15",
                                   max=100)]})
    return {"engine": "ngspice", "netlist": "tb_pin.cir",
            "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
            "corners": pvt_full.corners(("vddio",), style="explicit"),
            "analysis_steps": steps,
            "options": base_options(60),
            "backend": "batch", "batch": {"capacity_wait_s": 600}}


# --- the clock path three ways: committed, candidate, and the adoptable split ---
UI_PS, TR_PS, NUI, NEDGE = 1000, 100, 24, 6
END_PS = NUI * UI_PS
CLK_SUPPLIES = ["vdd_tx_b", "vdd_rx_b", "vdd_tx_c", "vdd_rx_c", "vdd_tx_d", "vdd_rx_d"]


def _stim() -> str:
    clk = [(k * UI_PS + UI_PS // 2, 1 if k % 2 == 0 else 0) for k in range(NUI)]
    dat = [(k * UI_PS, 1 if k % 2 == 0 else 0) for k in range(NUI)]
    return ("Vpc pc 0 dc 0 pwl(" + gen_common.pwl(gen_common.level_pwl(clk, TR_PS, END_PS)) + ")\n"
            "Vpd pd_ 0 dc 0 pwl(" + gen_common.pwl(gen_common.level_pwl(dat, TR_PS, END_PS)) + ")")


def tb_clk() -> str:
    rx_base = ("* the committed clock receiver: aib_rx_clk is two aib_rx_data instances\n"
               ".subckt aib_rx_clk__base CLK_PAD CLKB_PAD CLK_O CLKB_O VDDIO VSS\n"
               "Xclk CLK_PAD CLK_O VDDIO VSS aib_rx_data__base\n"
               "Xclkb CLKB_PAD CLKB_O VDDIO VSS aib_rx_data__base\n"
               ".ends\n")
    rx_cand = ("* the study clock receiver: same cell with the selected candidate in both legs\n"
               ".subckt aib_rx_clk__cand CLK_PAD CLKB_PAD CLK_O CLKB_O VDDIO VSS\n"
               "Xclk CLK_PAD CLK_O VDDIO VSS aib_rx_data__cand\n"
               "Xclkb CLKB_PAD CLKB_O VDDIO VSS aib_rx_data__cand\n"
               ".ends\n")
    base = inv_cell("base").replace("rx__base", "aib_rx_data__base", 1)
    cand = cand_text(SELECTED).replace(f"rx__{SELECTED}", "aib_rx_data__cand", 1)
    lane = []
    # three variants: b = committed receiver everywhere (the reference), c = the
    # candidate everywhere, d = the adoptable split -- candidate in the data lane,
    # committed receiver in both clock legs. (The c variant's t02 numbers rule the
    # candidate out of the clock legs; d is the configuration an adoption of the
    # candidate for the data lanes would actually land.)
    for v in ("b", "c", "d"):
        clk_cell = "cand" if v == "c" else "base"
        data_cell = "base" if v == "b" else "cand"
        lane += [f"Vdd_tx_{v} vdd_tx_{v} 0 DC 1.2",
                 f"Vdd_rx_{v} vdd_rx_{v} 0 DC 1.2",
                 f"Bckp_{v} ckp_{v} 0 V=v(pc)*v(vdd_tx_{v})",
                 f"Bckn_{v} ckn_{v} 0 V=(1-v(pc))*v(vdd_tx_{v})",
                 f"Bdd_{v} dd_{v} 0 V=v(pd_)*v(vdd_tx_{v})",
                 f"Boe_{v} oe_{v} 0 V=v(vdd_tx_{v})",
                 f"Xtxc_{v} ckp_{v} ckn_{v} oe_{v} oe_{v} 0 txc_{v} txcb_{v} vdd_tx_{v} 0 aib_tx_clk",
                 f"Xetc_{v} txpc_{v} txc_{v} vdd_tx_{v} 0 aib_pad_esd",
                 f"Xetcb_{v} txpcb_{v} txcb_{v} vdd_tx_{v} 0 aib_pad_esd",
                 f"Xlc_{v} txpc_{v} rxpc_{v} 0 link",
                 f"Xlcb_{v} txpcb_{v} rxpcb_{v} 0 link",
                 f"Xerc_{v} rxpc_{v} rxc_{v} vdd_rx_{v} 0 aib_pad_esd",
                 f"Xercb_{v} rxpcb_{v} rxcb_{v} vdd_rx_{v} 0 aib_pad_esd",
                 f"Xrxc_{v} rxc_{v} rxcb_{v} cko_{v} ckbo_{v} vdd_rx_{v} 0 aib_rx_clk__{clk_cell}",
                 f"Xtxd_{v} dd_{v} oe_{v} oe_{v} 0 txdc_{v} vdd_tx_{v} 0 aib_tx_data",
                 f"Xetd_{v} txpd_{v} txdc_{v} vdd_tx_{v} 0 aib_pad_esd",
                 f"Xld_{v} txpd_{v} rxpd_{v} 0 link",
                 f"Xerd_{v} rxpd_{v} rxd_{v} vdd_rx_{v} 0 aib_pad_esd",
                 f"Xrxd_{v} rxd_{v} ddo_{v} vdd_rx_{v} 0 aib_rx_data__{data_cell}",
                 f"Ccko_{v} cko_{v} 0 5f",
                 f"Cckbo_{v} ckbo_{v} 0 5f",
                 f"Cddo_{v} ddo_{v} 0 5f",
                 f"Bdxo_{v} dxo_{v} 0 V=v(cko_{v})-0.5*v(vdd_rx_{v})",
                 f"Bdd0_{v} ddo0_{v} 0 V=v(ddo_{v})-0.5*v(vdd_rx_{v})"]
    return ("* tb_clk.cir -- GENERATED by gen_rx_threshold.py; do not edit.\n"
            "* sim/clock-path/tb_clock_path.cir form with the path instantiated three times:\n"
            "* variant b on the committed receiver, variant c on the selected candidate in\n"
            "* both clock legs and the data lane, variant d on the adoptable split (the\n"
            "* candidate in the data lane, the committed receiver in the clock legs). Only\n"
            "* t02's opposite-edge separations are measured; the ideal stimulus is shared,\n"
            "* so every path sees identical edges. TX and ESD cells are included from\n"
            "* design/, as in the committed bench; the receivers are inlined.\n"
            ".include ../../spec/channel/channel_rc.cir\n"
            ".include ../../design/aib_tx_clk.spice\n"
            ".include ../../design/aib_tx_data.spice\n"
            ".include ../../design/aib_pad_esd.spice\n"
            ".subckt link txp rxp gnd\n"
            "Xch txp rxp gnd chan_rlc len_mm=3\n"
            ".ends\n"
            + _stim() + "\n"
            + base + "\n" + cand + "\n" + rx_base + rx_cand + "\n".join(lane) + "\n")


def request_clk() -> dict:
    m = []
    for v in ("b", "c", "d"):
        ddo0, dxo = f"v(ddo0_{v})", f"v(dxo_{v})"
        m += [{"name": f"t02_dr_cr__{v}", "unit": "s", "spec_row": "T-02",
               "spice": f".meas tran t02_dr_cr__{v} TRIG {ddo0} VAL=0 RISE={NEDGE} TARG {dxo} VAL=0 RISE={NEDGE}"},
              {"name": f"t02_df_cf__{v}", "unit": "s", "spec_row": "T-02",
               "spice": f".meas tran t02_df_cf__{v} TRIG {ddo0} VAL=0 FALL={NEDGE} TARG {dxo} VAL=0 FALL={NEDGE}"},
              {"name": f"t02_cr_df__{v}", "unit": "s", "spec_row": "T-02",
               "spice": f".meas tran t02_cr_df__{v} TRIG {dxo} VAL=0 RISE={NEDGE} TARG {ddo0} VAL=0 FALL={NEDGE}"},
              {"name": f"t02_cf_dr__{v}", "unit": "s", "spec_row": "T-02",
               "spice": f".meas tran t02_cf_dr__{v} TRIG {dxo} VAL=0 FALL={NEDGE} TARG {ddo0} VAL=0 RISE={NEDGE + 1}"}]
    return {"engine": "ngspice", "netlist": "tb_clk.cir",
            "models": {"pdk": "ihp-sg13g2", "lib": LIBM},
            "corners": pvt_full.corners(CLK_SUPPLIES),
            "analysis": {"kind": "tran", "args": f"2p {NUI}n 0 5p"},
            "measurements": m,
            "options": base_options(1100),
            "backend": "batch", "batch": {"capacity_wait_s": 600}}


# --- T-16 at the nominal channel: the channel-eye bench with the two receivers ---
# The study ran on the pre-#398 receive path (one shared aib_rx_data receiver in all
# four lanes). The adoption split the live sim/channel-eye/tb_body.inc (data lanes on
# the supply-referenced aib_rx_data, clock lanes on aib_rx_inv), and design/aib_rx_data.spice
# is now the adopted cell, so the study benches read this frozen pre-split copy of the
# body and inline the study's own as-drawn inverter (inv_cell("base"), the cell
# design/aib_rx_inv.spice now carries) instead of including a design file that moved.
BODY = HERE / "tb_body_pre398.inc"


def _tb_t16(variant: str) -> str:
    """variant: 'base' (as-drawn, self-check), 'cand' (SELECTED everywhere) or
    'mixed' (SELECTED in the two data lanes, as-drawn receiver in the two clock
    lanes -- the adoptable split the clk leg's variant-c numbers force)."""
    body = BODY.read_text()
    # the as-drawn inverter receiver, inlined: design/aib_rx_data.spice is the adopted
    # supply-referenced cell since #398, so the study's baseline cannot come from design/
    base_inline = inv_cell("base").replace("rx__base", "aib_rx_data", 1) + "\n"
    # inline the four-lane body over the study's own copy of prbs7_stim.inc (the
    # same bytes gen_channel_eye writes, so the record copy is self-contained and
    # the base variant reproduces tb_ch.cir exactly -- checked against the
    # committed channel-eye record in the README)
    head = ("* GENERATED by gen_rx_threshold.py; do not edit.\n"
            "* sim/channel-eye/tb_ch.cir form (CH-3MM-RC, nominal kr = kc = 1, four lanes of\n"
            "* tb_body.inc with the RX-pin probes the t15/t16 cards read). Variant: ")
    incl = (".include ../../spec/channel/channel_rc.cir\n"
            ".include ../../design/aib_tx_data.spice\n"
            ".include ../../design/aib_pad_esd.spice\n")
    link = ".subckt link txp rxp gnd\nXch txp rxp gnd chan_rlc len_mm=3\n.ends\n"
    if variant == "cand":
        cell = cand_text(SELECTED).replace(f"rx__{SELECTED}", "aib_rx_data", 1)
        return (head + "SELECTED candidate\n"
                "* inlined as aib_rx_data; TX and ESD cells included from design/.\n"
                + incl + cell + "\n" + link + body)
    if variant == "mixed":
        # the committed receiver stays in the clock lanes (the as-drawn inverter,
        # inlined below as aib_rx_data); the candidate goes into the two data
        # lanes. Derive a second lane subckt (lane_v, its Xrx on the candidate)
        # from the body's own lane block, so the duplicate tracks the frozen body
        # instead of restating it.
        cell = cand_text(SELECTED).replace(f"rx__{SELECTED}", "aib_rx_data__cand", 1)
        start, end = body.index(".subckt lane din dout rxp vtx vrx"), body.index(".ends lane")
        lane_v = (body[start:end]
                  .replace(".subckt lane din dout rxp vtx vrx",
                           ".subckt lane_v din dout rxp vtx vrx")
                  .replace("aib_rx_data", "aib_rx_data__cand")
                  + ".ends lane_v\n\n" + cell + "\n")
        body = body[:end] + ".ends lane\n\n" + lane_v + body[end + len(".ends lane\n"):]
        for x in ("Xa  da  douta  rxa  vdd_atx vdd_arx lane\n",
                  "Xb  db  doutb  rxb  vdd_btx vdd_brx lane\n"):
            assert body.count(x) == 1, x
            body = body.replace(x, x.replace(" lane\n", " lane_v\n"))
        return (head + "adoptable split (SELECTED in the data lanes A/B, as-drawn\n"
                "* receiver in the clock lanes C/CB -- the configuration the clk leg's\n"
                "* variant-c numbers force on an adoption).\n"
                + incl + base_inline + link + body)
    return (head + "as-drawn receiver (self-check against the committed ch record).\n"
            ".include ../../spec/channel/channel_rc.cir\n"
            ".include ../../design/aib_tx_data.spice\n"
            ".include ../../design/aib_pad_esd.spice\n"
            + base_inline + link + body)


def _request_t16(netlist) -> dict:
    r = ce.request("ch")
    r["netlist"] = netlist
    r["batch"] = {"capacity_wait_s": 600}
    return r


def cand_cells_inc() -> str:
    return ("* cand_cells.inc -- GENERATED by gen_rx_threshold.py; do not edit.\n"
            "* The study's candidate receiver cells, one subckt each (issue #386). Study\n"
            "* evidence only; the study changed no design/ file. (Since the #398 adoption,\n"
            "* design/aib_rx_data.spice is the SELECTED candidate itself and the committed\n"
            "* inverter lives in design/aib_rx_inv.spice.)\n\n"
            + "\n\n".join(cand_text(c) for c in CANDS) + "\n")


def outputs():
    files = {
        "cand_cells.inc": cand_cells_inc(),
        "prbs7_stim.inc": ce.stim_include(),   # the tb_t16 benches' stimulus: the same
        # bytes gen_channel_eye.py writes, emitted here so a t16 record directory
        # (netlist + stimulus) is self-contained replay evidence
        "tb_screen.cir": tb_screen(),
        "tb_mc.cir": tb_mc(),
        "tb_mc_ctl.cir": tb_mc_ctl(),
        "tb_hyst.cir": tb_hyst(),
        "tb_pin.cir": tb_pin(),
        "tb_clk.cir": tb_clk(),
        "tb_t16_base.cir": _tb_t16("base"),
        "tb_t16_cand.cir": _tb_t16("cand"),
        "tb_t16_mixed.cir": _tb_t16("mixed"),
        "request_screen.json": json.dumps(request_screen(), indent=2) + "\n",
        "request_mc.json": json.dumps(_mc_request("tb_mc.cir", 120, 4410), indent=2) + "\n",
        "request_mc_ctl.json": json.dumps(
            # the control's degraded crossing sits at fr 0.66-0.75 over the grid
            # (measured at tt/1.200V/27C and sf/1.080V/-40C during the study's
            # local probes), outside the committed form's 0.3-0.7 window, so the
            # control bench widens the sweep; the nominal bench keeps the
            # committed window. Everything else is the committed T-10 shape.
            _mc_request("tb_mc_ctl.cir", 20, 4411, sweep="Vfr 0.15 0.95 0.0005"), indent=2) + "\n",
        "request_hyst.json": json.dumps(request_hyst(), indent=2) + "\n",
        "request_pin.json": json.dumps(request_pin(), indent=2) + "\n",
        "request_clk.json": json.dumps(request_clk(), indent=2) + "\n",
        "request_t16_base.json": json.dumps(_request_t16("tb_t16_base.cir"), indent=2) + "\n",
        "request_t16_cand.json": json.dumps(_request_t16("tb_t16_cand.cir"), indent=2) + "\n",
        "request_t16_mixed.json": json.dumps(_request_t16("tb_t16_mixed.cir"), indent=2) + "\n",
    }
    return {k: v for k, v in files.items()}


if __name__ == "__main__":
    raise SystemExit(gen_common.write_or_check(outputs(), base=HERE,
                                               description="Generate the rx-threshold-study benches and requests"))
