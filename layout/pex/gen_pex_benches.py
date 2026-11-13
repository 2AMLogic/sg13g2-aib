#!/usr/bin/env python3
"""Write (or --check) the `klt pex` benches, DUTs and requests for T1 item 7 (analog).

`klt pex` re-runs a `klt sim` testbench against the netlist extracted from the
layout and reports a per-corner, per-spec-row schematic-vs-extracted delta. It
takes the testbench in a shape the item 5 benches are not in, for two reasons
measured in layout/pex/README.md:

  1. every testbench body must carry **exactly one** `.include`, naming the
     schematic DUT -- `sim/dc-static/tb_dc_static.cir` carries six;
  2. one `--top` is extracted per run, and the drawn cells merge the pad/ESD
     structure into the driver (`aib_io_tx`) or the receiver (`aib_io_rx`),
     which the item 5 benches instantiate as separate subcircuits.

So this script writes, per extracted top:

  benches/<top>.dut.spice            the simulatable assembly of that drawn cell:
                                     a `.subckt` with the same pin list and order
                                     as layout/lvs/<top>.ref.spice, calling the
                                     item 1 cells, followed by those cells' own
                                     text inlined verbatim from design/. One
                                     self-contained file, so the bench that
                                     includes it has exactly one `.include`.
  benches/tb_dc_static_<top>.cir     the bench body: that single `.include`, the
                                     supply, and the stimulus of the item 5
                                     sub-benches this leg can carry.
  benches/request_dc_static_<top>.json  the `klt sim` request, with the corner
                                     grid, step set, measurement names and limits
                                     imported from sim/dc-static/gen_dc_static.py
                                     rather than restated -- so a change to the
                                     item 5 set shows up here as a --check failure
                                     instead of silently diverging.

Nothing in design/ or sim/ is read for anything but its text, and nothing is
hand-copied: --check rebuilds every file and fails on any difference.

**These benches have never produced an extracted-side measurement.** `klt pex`
cannot simulate an sg13g2 extraction today (two tool defects, both recorded with
their reproductions in layout/pex/README.md and filed upstream). The schematic
leg runs; the extracted leg dies at netlist load. The files are written anyway
because they are the reproduction for those defects, and because the campaign is
one `layout/pex/run_pex.sh` away once the tool is fixed.

From the repo root:
    python3 -I layout/pex/gen_pex_benches.py [--check]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DESIGN = ROOT / "design"
BENCHES = HERE / "benches"

sys.path.insert(0, str(ROOT / "sim" / "dc-static"))
import gen_dc_static as dc  # noqa: E402  (path set above; stdlib-only module)

# --- the drawn cells, as layout/README.md "Assembly choice" assembles them ----
# The pin list and order are NOT restated here: they are read from
# layout/lvs/<top>.ref.spice by `ref_pins`, which is what
# `klt extract --pins --rename-declared-pins` reproduces on the extracted side.
# A pin-order difference is what `klt pex` reports as pin_order_mismatch.
# parts: (instance, item 1 subckt, {subckt pin: net}). PADI is internal to both
# drawn cells: the TX leaves it on the secondary diodes, the RX takes its input
# there, behind the ESD series resistor.
TOPS = {
    "aib_io_tx": {
        "sources": ["aib_pad_esd", "aib_tx_data"],
        "parts": [
            ("Xesd", "aib_pad_esd", {"PAD": "PAD", "PADI": "PADI",
                                     "VDDIO": "VDDIO", "VSS": "VSS"}),
            ("Xtx", "aib_tx_data", {"DIN": "DIN", "OE": "OE", "PUN": "PUN", "PD": "PD",
                                    "PAD": "PAD", "VDDIO": "VDDIO", "VSS": "VSS"}),
        ],
    },
    "aib_io_rx": {
        "sources": ["aib_pad_esd", "aib_rx_data"],
        "parts": [
            ("Xesd", "aib_pad_esd", {"PAD": "PAD", "PADI": "PADI",
                                     "VDDIO": "VDDIO", "VSS": "VSS"}),
            ("Xrx", "aib_rx_data", {"PAD": "PADI", "DOUT": "DOUT",
                                    "VDDIO": "VDDIO", "VSS": "VSS"}),
        ],
    },
}

# `klt extract --label-layer`, read from layout/lvs/<top>.request.json so the
# pex extraction reads net names off the same layers the LVS-`match` run did.
LABEL_LAYERS_FROM = "aib_io_tx.request.json"

# Every drawn cell the extraction leg covers. The two clk tops carry no bench:
# the benches that exercise them are link benches (sim/clock-path), which hold
# both ends of a link and so cannot be put behind one extracted `--top` -- see
# layout/pex/README.md, "One extracted top per run". They are extracted anyway
# (`klt pex --extract-only`), which is evidence about the drawn cells even
# without a measurement leg.
EXTRACT_TOPS = ["aib_io_tx", "aib_io_rx", "aib_io_tx_clk", "aib_io_rx_clk"]


def subckt_pins(path: Path, name: str) -> list:
    """The declared pin list of `.subckt name` in an xschem-style netlist."""
    for line in path.read_text().splitlines():
        t = line.split()
        if len(t) > 1 and t[0].lower() == ".subckt" and t[1] == name:
            return t[2:]
    raise SystemExit(f"{path}: no .subckt {name}")


def ref_pins(top: str) -> list:
    """The pin list `klt extract --pins` must declare for `top`.

    Read from layout/lvs/<top>.ref.spice -- the reference netlist that compares
    `match` against this cell -- so the pins a pex run declares are the pins LVS
    already agreed on, and a regenerated layout cannot leave them behind.
    """
    path = ROOT / "layout" / "lvs" / f"{top}.ref.spice"
    for line in path.read_text().splitlines():
        t = line.split()
        if len(t) > 1 and t[0].upper() == ".SUBCKT" and t[1] == top:
            return t[2:]
    raise SystemExit(f"{path}: no .SUBCKT {top}")


def dut_text(top: str) -> str:
    """The simulatable assembly of one drawn cell: wrapper + its item 1 cells."""
    spec = TOPS[top]
    pins = ref_pins(top)
    srcs = [(n, DESIGN / f"{n}.spice") for n in spec["sources"]]
    lines = [
        "* Generated by layout/pex/gen_pex_benches.py -- DO NOT EDIT BY HAND.",
        f"* Simulatable assembly of the drawn cell {top}, for the schematic leg of",
        "* `klt pex` (T1 item 7, analog). Pin list and order are those of",
        f"* layout/lvs/{top}.ref.spice, the LVS-`match` reference for this cell.",
        "* Built from the item 1 netlists, whose text is inlined verbatim below:",
    ]
    lines += [f"*   design/{n}.spice sha256:"
              f"{hashlib.sha256(p.read_bytes()).hexdigest()}" for n, p in srcs]
    lines.append(f".subckt {top} " + " ".join(pins))
    bound = set()
    for inst, sub, bind in spec["parts"]:
        sub_pins = subckt_pins(DESIGN / f"{sub}.spice", sub)
        missing = [p for p in sub_pins if p not in bind]
        if missing:
            raise SystemExit(f"{top}: {sub} pin(s) {missing} unbound -- design/ moved")
        bound.update(bind[p] for p in sub_pins)
        lines.append(f"{inst} " + " ".join(bind[p] for p in sub_pins) + f" {sub}")
    # Every declared pin must actually reach a device, or the extracted side and
    # this one are not the same circuit however well the pin lists line up.
    floating = [p for p in pins if p not in bound]
    if floating:
        raise SystemExit(f"{top}: declared pin(s) {floating} bound to nothing")
    lines.append(".ends")
    body = "\n".join(lines) + "\n"
    return body + "".join(p.read_text() for _, p in srcs)


# --- the bench bodies ---------------------------------------------------------
# Each is the stimulus of the item 5 sub-benches this leg can carry, rewired onto
# one instance of the drawn cell. `sources` is the set of sources the request may
# `alter`; a step naming anything outside it is dropped from that leg (see
# `leg_steps`), which is how the row split below is enforced rather than asserted.
#
# Row split, and why it is not the item 5 pin:
#   sim/dc-static/tb_pin.cir models one bidirectional pin -- pad/ESD, driver and
#   receiver on the same node. No drawn cell is that: the column draws 24 TX pads
#   (`aib_io_tx`: pad/ESD + driver) and 24 RX pads (`aib_io_rx`: pad/ESD +
#   receiver), each unidirectional. Post-layout, the pin rows are therefore
#   measured on the two pins that exist, not on the combined one that does not:
#     TX pad (aib_io_tx): T-06, T-08 (drive), T-07 (leakage), T-28 (weak pulls),
#                         T-24 (pad capacitance at the TX pin)
#     RX pad (aib_io_rx): T-07 (leakage), T-11 (hysteresis),
#                         T-24 (pad capacitance at the RX pin -- spec/target-spec.md
#                         binds T-24 "at the receiver pin", so this is its leg)
# This is a change of measurement point against item 5, not of limit: every limit
# is the spec bound, imported unchanged from gen_dc_static.py.
LEGS = {
    "aib_io_tx": {
        "sources": {"Ih", "Il", "Voef", "Vdinf", "Vpunf", "Vpdf", "Vpf", "Vacp.ac"},
        "rows": ["T-06", "T-07", "T-08", "T-24", "T-28"],
        "body": """\
* T-06 / T-08: driver DC levels and output resistance at both rails, and
* T-07 / T-24 / T-28 on the tristated TX pad. One `aib_io_tx` instance per
* sub-bench: the drawn cell already contains the pad/ESD structure, so no
* separate aib_pad_esd is instantiated (that is the merge this leg exists for).
* Stimulus is sim/dc-static/tb_drive.cir and tb_pin.cir, rewired onto that cell;
* the receiver tb_pin.cir hangs on the same node is not on a drawn TX pad and is
* measured on the RX leg instead (layout/pex/README.md, "Row split").
Vddio vddio 0 dc 1.2

* -- drive: Ih sinks from the high-driving pad, Il sources into the low one --
Xtx_h vddio vddio pad_h 0 vddio vddio 0 aib_io_tx
Ih pad_h 0 dc 0
Xtx_l 0 vddio pad_l 0 vddio vddio 0 aib_io_tx
Il vddio pad_l dc 0

* -- tristated pin: controls as fractions of VDDIO, so one request tracks every
* supply corner. Default state: output disabled, DIN low, PUN high, PD low.
Voef oef 0 dc 0
Vdinf dinf 0 dc 0
Vpunf punf 0 dc 1
Vpdf pdf 0 dc 0
Boe oe_p 0 V=v(oef)*v(vddio)
Bdin din_p 0 V=v(dinf)*v(vddio)
Bpun pun_p 0 V=v(punf)*v(vddio)
Bpd pd_p 0 V=v(pdf)*v(vddio)
Vpf pf 0 dc 0
Bpin pb 0 V=v(pf)*v(vddio)
Vacp pad_p pb dc 0 ac 0
Xtx_p din_p oe_p pad_p pd_p pun_p vddio 0 aib_io_tx
""",
    },
    "aib_io_rx": {
        "sources": {"Vpf", "Vacp.ac", "Vfr"},
        "rows": ["T-07", "T-11", "T-24"],
        "body": """\
* T-07 / T-24 on the tristated RX pad and T-11 receiver hysteresis, on one
* `aib_io_rx` instance per sub-bench. The drawn RX cell contains the pad/ESD
* structure and takes its input on PADI, behind the ESD series resistor, so the
* pad node here is the bond pad -- sim/dc-static/tb_rx_hyst.cir drove the
* receiver input directly, with no ESD in front of it.
Vddio vddio 0 dc 1.2

* -- tristated pin: the pad is forced through the zero-volt series source Vacp,
* whose current is the pin current and which carries the AC stimulus.
Vpf pf 0 dc 0
Bpin pb 0 V=v(pf)*v(vddio)
Vacp pad_p pb dc 0 ac 0
Xrx_p dout_p pad_p vddio 0 aib_io_rx

* -- hysteresis: the pad is swept as a fraction of VDDIO, up and then down;
* dnorm is the receiver output normalised to VDDIO so the 50 % crossing is a
* literal level in every supply corner.
Vfr fr 0 dc 0
Bpin_r pad_r 0 V=v(fr)*v(vddio)
Xrx_r dout_r pad_r vddio 0 aib_io_rx
Bdn dnorm 0 V=v(dout_r)/v(vddio)
""",
    },
}


# What each item 5 dc-static measurement needs the bench to provide, so a leg
# that cannot provide it drops the measurement instead of reporting a number
# taken on a circuit that does not implement the row. The TX cell has the
# driver and the weak pulls; the RX cell has neither, and only it has a
# receiver to sweep. Every name here is a key of dc.DC_STEPS / dc.DC_TOP: a
# measurement that is renamed or added upstream and not listed is an error, not
# a silent drop (see `_requires`).
MEASUREMENT_NEEDS = {
    "t06_voh_droop_v": {"Ih"},        # the high-driving pad
    "t06_vol_v": {"Il"},              # the low-driving pad
    "t08_rout_up_ohm": {"Ih"},
    "t08_rout_dn_ohm": {"Il"},
    "t07_t28_ipin_a": {"Vpf"},        # pin current through Vacp at a forced pad
    "t24_cpin_ff": {"Vacp.ac"},
    "t28_rpu_ohm": {"Vpunf"},         # needs a weak pull-up to switch on
    "t28_rpd_ohm": {"Vpdf"},
    "vth_up": {"Vfr"},                # the receiver input sweep
    "vth_dn": {"Vfr"},
    "vddio_v": set(),
    "t11_hyst_mv": {"Vfr"},
}


def _requires(name: str) -> set:
    try:
        return MEASUREMENT_NEEDS[name]
    except KeyError:
        raise SystemExit(
            f"measurement {name!r} is in the item 5 dc-static set but not in "
            "MEASUREMENT_NEEDS: say which bench sources it needs before it can "
            "be split across the TX and RX legs") from None


def leg_steps(top: str) -> tuple:
    """(steps, top-level measurements) of the item 5 dc-static set this leg carries.

    A measurement survives when this bench provides every source it needs
    (MEASUREMENT_NEEDS); a step survives when at least one of its measurements
    does, with its `alter` narrowed to the sources that exist here. So the RX leg
    keeps T-07 and T-24 at the three pad biases -- whose alter entries only
    restated a "pulls off" default the RX cell has no pulls to need -- and drops
    the two weak-pull steps outright rather than reporting the default state
    under a T-28 name. Importing the steps from gen_dc_static.py instead of
    restating them is what makes a change to the item 5 set a --check failure
    here.
    """
    have = LEGS[top]["sources"]
    steps = []
    for s in dc.DC_STEPS:
        # A `dc` step sweeps a named source; without it the step cannot run at
        # all, however measurable its measurements look on their own (the TX leg
        # has no Vfr, so `rx_up` goes even though `vddio_v` needs nothing).
        if s["analysis"]["kind"] == "dc":
            sweep = s["analysis"].get("args", "").split()
            if not sweep or sweep[0] not in have:
                continue
        kept = [m for m in s["measurements"] if _requires(m["name"]) <= have]
        if not kept:
            continue
        steps.append({**s,
                      "alter": {k: v for k, v in s["alter"].items() if k in have},
                      "measurements": kept})
    names = {(s["name"], m["name"]) for s in steps for m in s["measurements"]}
    tops = [m for m in dc.DC_TOP
            if _requires(m["name"]) <= have
            and all(tuple(ref.split(".", 1)) in names for ref in _step_refs(m["expr"]))]
    return steps, tops


def _step_refs(expr: str) -> list:
    """`step.measurement` references in a top-level measurement expression."""
    out, tok = [], ""
    for ch in expr + " ":
        if ch.isalnum() or ch in "_.":
            tok += ch
        else:
            if "." in tok and not tok[0].isdigit():
                out.append(tok)
            tok = ""
    return out


def bench_text(top: str) -> str:
    """One bench body: the single DUT `.include`, then this leg's stimulus.

    The `.include` is emitted here, never written into LEGS[...]["body"], so
    there is exactly one of them in every generated bench by construction --
    the rule `klt pex` hard-errors on (two or more, and it cannot tell which is
    the DUT) and the whole reason the item 5 benches cannot be handed to it.
    It is the line `klt pex` re-points at the extracted netlist.
    """
    body = LEGS[top]["body"]
    head, _, rest = body.partition("\n\n")
    if ".include" in body or ".inc " in body:
        raise SystemExit(f"{top}: the bench body must not carry its own .include")
    return f'{head}\n.include "{top}.dut.spice"\n\n{rest}'


def request(top: str) -> dict:
    """The `klt sim` request `klt pex` re-runs against both netlists.

    `osdi_preload` keeps the portable `$PDK_ROOT/...` spelling every committed
    request under sim/ uses. `klt pex` 0.9.0 drops entries in that form from the
    decks it drives (layout/pex/README.md, defect 1); layout/pex/run_pex.sh
    materialises an absolute-path copy at run time and records it, rather than
    committing a host path here.
    """
    steps, tops = leg_steps(top)
    r = {"engine": "ngspice",
         "netlist": f"tb_dc_static_{top}.cir",
         "models": {"pdk": "ihp-sg13g2", "lib": dc.LIBM},
         "corners": dc.corners(),
         "analysis_steps": steps}
    if tops:
        r["measurements"] = tops
    r["options"] = {"stage_model_inputs": True,
                    "fail_on_diagnostic": ["nonconvergence"],
                    "timeout_s": 60,
                    "keep_artifacts": False,
                    "osdi_preload": dc.OSDI}
    r["backend"] = "batch"
    r["batch"] = {"runner_version_check": "warn", "capacity_wait_s": dc.CAPACITY_WAIT_S}
    return r


def label_layers() -> dict:
    """`--label-layer` roles, from the LVS request that matched these cells."""
    req = json.loads((ROOT / "layout" / "lvs" / LABEL_LAYERS_FROM).read_text())
    return req["layout"]["label_layers"]


def files() -> dict:
    """-> {path relative to layout/pex/: text}."""
    out = {}
    for top in TOPS:
        out[f"benches/{top}.dut.spice"] = dut_text(top)
        out[f"benches/tb_dc_static_{top}.cir"] = bench_text(top)
        out[f"benches/request_dc_static_{top}.json"] = (
            json.dumps(request(top), indent=2) + "\n")
    # The extraction arguments, in one machine-readable place: run_pex.sh reads
    # them so the committed record and the script cannot disagree about which
    # pins, label layers or tops a run used.
    out["benches/extraction.json"] = json.dumps(
        {"layout": "../aib_io_column.gds",
         "deck": "sg13g2",
         "pdk": "ihp-sg13g2",
         "label_layers": label_layers(),
         "tops": {t: {"pins": ref_pins(t),
                      "rows": LEGS[t]["rows"] if t in LEGS else []}
                  for t in EXTRACT_TOPS}},
        indent=2) + "\n"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if a committed file is stale, writing nothing")
    args = ap.parse_args()
    bad = 0
    for rel, text in files().items():
        p = HERE / rel
        if args.check:
            if not p.exists() or p.read_text() != text:
                print(f"STALE: layout/pex/{rel} "
                      f"(run python3 -I layout/pex/{Path(__file__).name})", file=sys.stderr)
                bad = 1
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    if args.check and not bad:
        print("ok: committed pex benches, DUTs and requests match a fresh build")
    return bad


if __name__ == "__main__":
    sys.exit(main())
