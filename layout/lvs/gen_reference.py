#!/usr/bin/env python3
"""Write (or --check) the assembled I/O-cell reference netlists for `klt lvs` (T1 item 4, analog).

The item 1 netlists in design/ are per-block subcircuits (aib_pad_esd, aib_tx_data, aib_rx_data,
and the clk/clkb pairs). The layout cells are assembled (pad + ESD + driver or receiver), so no
single item 1 subckt is the LVS reference. This script composes the existing subckts, flattens
them and writes `klt lvs` plain-element SPICE, one file per layout cell. Nothing is edited by
hand and design/*.spice is read only; each output carries the sha256 of every source it was
built from, and --check fails if the committed files differ from a fresh build.

Assembly (mirrors layout/README.md "Assembly choice"): the bond pad is the PAD of aib_pad_esd.
TX: driver output on PAD, PADI left on the secondary diodes and Mn2 only. RX: receiver input
on PADI, behind the series resistor.

Device forms follow what klt's sg13g2 deck extracts: MOS class nfet/pfet, one device per gate
finger (design netlists carry the total w, so a finger is w/ng; klt extract also emits fingers), rppd as the 3-terminal
bulk-bearing X card klt extracts (R value from the SG13G2 symbol; klt lvs does not compare it), dantenna/dpantenna as D with A = w*l, P = 2(w+l).

From the repo root:
    python3 -I layout/lvs/gen_reference.py [--check] [--diagnostic]
"""
import hashlib
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DESIGN = os.path.join(ROOT, "design")
OUT = os.path.join(ROOT, "layout", "lvs")
SOURCES = ["aib_pad_esd", "aib_tx_data", "aib_rx_data", "aib_tx_clk", "aib_rx_clk"]

# --diagnostic: reconcile the reference to the two ways the drawn layout differs from the item 1
# schematic (see layout/lvs/README.md). Diagnostic files only explain a mismatch; they are
# never the reference a result is claimed against.
DIAG = "--diagnostic" in sys.argv
TOTAL_W = {"Mp", "Mn", "Mclamp"}   # drawn at the netlist's total width / ng per finger

SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3}


def val(s):
    m = re.fullmatch(r"([0-9.]+(?:e[-+]?\d+)?)([fpnumk]?)", s.strip().lower())
    return float(m.group(1)) * SUFFIX.get(m.group(2), 1.0)


def um(x):
    return f"{x * 1e6:.6g}U"


def parse(path):
    """-> {subckt: (pins, [(inst, nodes, model, params)])}; the X-lines of an xschem netlist."""
    subs, cur = {}, None
    for line in open(path):
        line = line.strip()
        if line.lower().startswith(".subckt"):
            t = line.split()
            cur = (t[1], t[2:], [])
        elif line.lower().startswith(".ends"):
            subs[cur[0]] = (cur[1], cur[2])
            cur = None
        elif cur and line.startswith("X"):
            t = line.split()
            kv = dict(x.split("=", 1) for x in t[1:] if "=" in x)
            pos = [x for x in t[1:] if "=" not in x]
            cur[2].append((t[0][1:], pos[:-1], pos[-1], kv))
    return subs


def load():
    subs = {}
    for n in SOURCES:
        subs.update(parse(os.path.join(DESIGN, n + ".spice")))
    return subs


def rppd_ohms(w, l):
    # SG13G2 rppd symbol value with b = 0, m = 1: end term + 260 ohm/sq body, width-corrected.
    return 70.0e-6 / w + 260.0 * l / (w + 6.0e-9)


def device(path, model, nodes, p):
    name = path.replace("/", "_")
    if model in ("sg13_lv_nmos", "sg13_lv_pmos"):
        d, g, s, b = nodes
        cls = "nfet" if model.endswith("nmos") else "pfet"
        ng = int(p["ng"])
        wf = val(p["w"]) / ng                       # IHP models: w is the total, w/ng per finger
        if DIAG and path.rsplit("/", 1)[-1] not in TOTAL_W:
            wf *= ng                                # drawn at the netlist w per finger
        return "\n".join(
            f"M{name}_f{i} {d} {g} {s} {b} {cls} L={um(val(p['l']))} W={um(wf)}" for i in range(ng))
    if model == "rppd":
        a, b, sub = nodes
        w, l = val(p["w"]), val(p["l"])
        return f"X{name} {a} {b} {sub} rppd r={rppd_ohms(w, l):.1f} L={um(l)} W={um(w)}"
    if model in ("dantenna", "dpantenna"):
        a, c = nodes[:2]
        w, l = val(p["w"]), val(p["l"])
        return f"D{name} {a} {c} {model} A={w * l * 1e12:.6g}P P={um(2 * (w + l))}"
    raise SystemExit(f"unsupported device model {model!r} at {path}")


def flatten(subs, top, conn, path=""):
    """Instantiate subckt `top` with its pins bound by `conn`; internal nets get a path prefix."""
    pins, insts = subs[top]
    netmap = dict(zip(pins, conn))
    out = []
    for inst, nodes, model, params in insts:
        def net(n):
            return netmap.get(n) or (n if n in ("0",) else (path + n))
        real = [net(n) for n in nodes]
        if model in subs:
            out += flatten(subs, model, real, path + inst + "/")
        else:
            out.append(device(path + inst, model, real, params))
    return out


def src_hashes():
    return [(n, hashlib.sha256(open(os.path.join(DESIGN, n + ".spice"), "rb").read()).hexdigest())
            for n in SOURCES]


def cell(subs, name, pins, parts):
    """parts: [(label, subckt, {pin: net})]; the label keeps instance and internal net names unique."""
    lines = (["* DIAGNOSTIC reference (see layout/lvs/README.md); not a result reference."] if DIAG else []) + ["* Generated by layout/lvs/gen_reference.py -- DO NOT EDIT BY HAND.",
             "* Plain-element form for `klt lvs`; flattened from the item 1 netlists:"]
    lines += [f"*   design/{n}.spice sha256:{h}" for n, h in src_hashes()]
    lines.append(f".SUBCKT {name} " + " ".join(pins))
    for label, sub, bind in parts:
        lines += flatten(subs, sub, [bind[p] for p in subs[sub][0]], label + "/")
    lines.append(".ENDS")
    return "\n".join(lines) + "\n"


def build():
    subs = load()
    esd = lambda k, pad, padi: (k + "esd", "aib_pad_esd", dict(PAD=pad, PADI=padi, VDDIO="VDDIO", VSS="VSS"))
    tx = lambda k, din, pad: (k + "tx", "aib_tx_data", dict(DIN=din, OE="OE", PUN="PUN", PD="PD", PAD=pad,
                                               VDDIO="VDDIO", VSS="VSS"))
    rx = lambda k, pad, dout: (k + "rx", "aib_rx_data", dict(PAD=pad, DOUT=dout, VDDIO="VDDIO", VSS="VSS"))
    files = {}
    if DIAG:   # PADI of every cell is drawn on VSS
        _esd = esd
        esd = lambda k, pad, padi: _esd(k, pad, "VSS")
        _rx = rx
        rx = lambda k, pad, dout: _rx(k, "VSS" if pad.startswith("PADI") else pad, dout)
    txpins = ["DIN", "OE", "PAD", "PD", "PUN", "VDDIO", "VSS"]
    files["aib_io_tx"] = cell(subs, "aib_io_tx", txpins, [esd("", "PAD", "PADI"), tx("", "DIN", "PAD")])
    files["aib_io_rx"] = cell(subs, "aib_io_rx", ["DOUT", "PAD", "VDDIO", "VSS"],
                              [esd("", "PAD", "PADI"), rx("", "PADI", "DOUT")])
    # clk/clkb pair: two units sharing OE/PUN/PD and the rails. klt names the repeated labels
    # DIN, DIN$1 and PAD, PAD$1; DIN pairs with PAD and DIN$1 with PAD$1.
    files["aib_io_tx_clk"] = cell(
        subs, "aib_io_tx_clk", ["DIN", "DIN$1", "OE", "PAD", "PAD$1", "PD", "PUN", "VDDIO", "VSS"],
        [esd("a", "PAD", "PADI_A"), tx("a", "DIN", "PAD"), esd("b", "PAD$1", "PADI_B"),
         tx("b", "DIN$1", "PAD$1")])
    files["aib_io_rx_clk"] = cell(
        subs, "aib_io_rx_clk", ["DOUT", "DOUT$1", "PAD", "PAD$1", "VDDIO", "VSS"],
        [esd("a", "PAD", "PADI_A"), rx("a", "PADI_A", "DOUT"), esd("b", "PAD$1", "PADI_B"),
         rx("b", "PADI_B", "DOUT$1")])
    return files


def main():
    files = build()
    bad = False
    for name, text in files.items():
        path = os.path.join(OUT, name + (".diag.ref.spice" if DIAG else ".ref.spice"))
        if "--check" in sys.argv:
            if not os.path.exists(path) or open(path).read() != text:
                print("DIFFERS", path)
                bad = True
        else:
            open(path, "w").write(text)
    if "--check" in sys.argv:
        print("FAIL" if bad else "ok: committed reference netlists match a fresh build")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
