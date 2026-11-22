#!/usr/bin/env python3
"""Structural check of T-04's arrangement (DR-0027): a quasi-differential forwarded clock,
clk and clkb both driven at the TX, both carried through the channel, both received at the RX
and converted to single-ended there.

Reads design/aib_tx_clk.spice, design/aib_rx_clk.spice and sim/clock-path/tb_clock_path.cir and
asserts connectivity only. It measures nothing and states no bound: the crossing level stays
reported evidence (DR-0022, DR-0026). It holds for the modeled-channel testbench arrangement,
not for a real die-to-die channel.

  python3 -I sim/clock-path/check_clk_pair.py [--root DIR]     exit 0 pass, 1 fail
"""
import argparse
import re
import sys
from pathlib import Path

SUPPLY = {"0", "vss", "vdd_tx", "vdd_rx", "vddio", "gnd"}


def logical_lines(text):
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s[0] in "*;":
            continue
        if s[0] == "+" and out:
            out[-1] += " " + s[1:].strip()
        else:
            out.append(s)
    return out


PARAM = re.compile(r"^[^=\s]+=\S*$")


def instance(ln):
    """(instance, nodes, model) of one X line, nets lower-cased. Trailing key=value
    parameters are stripped first, so the model is the last positional token."""
    tok = ln.split()
    while len(tok) > 2 and PARAM.match(tok[-1]):
        tok.pop()
    return (tok[0], [t.lower() for t in tok[1:-1]], tok[-1].lower())


def subckt_body(text, name):
    """Instance lines of one .subckt, as (instance, nodes, model) with lower-cased nets."""
    inside, body = False, []
    for ln in logical_lines(text):
        low = ln.lower()
        if low.startswith(".subckt"):
            inside = low.split()[1] == name.lower()
        elif low.startswith(".ends"):
            inside = False
        elif inside and ln[0] in "xX":
            body.append(instance(ln))
    return body


def top_instances(text):
    """Instances outside every .subckt: a subckt's own formal nets are not testbench nets."""
    depth, body = 0, []
    for ln in logical_lines(text):
        low = ln.lower()
        if low.startswith(".subckt"):
            depth += 1
        elif low.startswith(".ends"):
            depth = max(depth - 1, 0)
        elif depth == 0 and ln[0] in "xX":
            body.append(instance(ln))
    return body


def reach(start, edges):
    seen, todo = {start}, [start]
    while todo:
        n = todo.pop()
        for a, b in edges:
            for x, y in ((a, b), (b, a)):
                if x == n and y not in seen:
                    seen.add(y)
                    todo.append(y)
    return seen


def check(root):
    root = Path(root)
    errs = []
    tx = (root / "design/aib_tx_clk.spice").read_text()
    rx = (root / "design/aib_rx_clk.spice").read_text()
    tb = (root / "sim/clock-path/tb_clock_path.cir").read_text()

    # TX cell: two aib_tx_data drivers, distinct data inputs and distinct pads.
    drv = [i for i in subckt_body(tx, "aib_tx_clk") if i[2] == "aib_tx_data"]
    if len(drv) != 2:
        errs.append("aib_tx_clk: expected 2 aib_tx_data drivers, found %d" % len(drv))
    else:
        for k, label in ((0, "DIN"), (4, "PAD")):
            if len({d[1][k] for d in drv}) != 2:
                errs.append("aib_tx_clk: the two drivers share their %s net" % label)
        if {d[1][4] for d in drv} != {"clk_pad", "clkb_pad"}:
            errs.append("aib_tx_clk: drivers must drive exactly CLK_PAD and CLKB_PAD")
        if {d[1][0] for d in drv} != {"clk_d", "clkb_d"}:
            errs.append("aib_tx_clk: drivers must take exactly CLK_D and CLKB_D")

    # RX cell: two aib_rx_data receivers, CLK_PAD->CLK_O and CLKB_PAD->CLKB_O (single-ended each).
    rcv = [i for i in subckt_body(rx, "aib_rx_clk") if i[2] == "aib_rx_data"]
    if len(rcv) != 2:
        errs.append("aib_rx_clk: expected 2 aib_rx_data receivers, found %d" % len(rcv))
    elif {(r[1][0], r[1][1]) for r in rcv} != {("clk_pad", "clk_o"), ("clkb_pad", "clkb_o")}:
        errs.append("aib_rx_clk: receivers must map CLK_PAD->CLK_O and CLKB_PAD->CLKB_O")

    # Testbench: the pair goes through the channel, net by net.
    inst = top_instances(tb)
    txi = [i for i in inst if i[2] == "aib_tx_clk"]
    rxi = [i for i in inst if i[2] == "aib_rx_clk"]
    if len(txi) != 1 or len(rxi) != 1:
        return errs + ["tb_clock_path.cir: need exactly one aib_tx_clk and one aib_rx_clk"]
    # aib_tx_clk ports: CLK_D CLKB_D OE PUN PD CLK_PAD CLKB_PAD VDDIO VSS
    # aib_rx_clk ports: CLK_PAD CLKB_PAD CLK_O CLKB_O VDDIO VSS
    txc, txcb = txi[0][1][5], txi[0][1][6]
    rxc, rxcb, cko, ckbo = rxi[0][1][0:4]
    if txc == txcb:
        errs.append("tb: TX clk and clkb pads are the same net")
    if rxc == rxcb:
        errs.append("tb: RX clk and clkb pins are the same net")
    if cko == ckbo or {cko, ckbo} & SUPPLY:
        errs.append("tb: RX outputs must be two distinct signal nets")
    # Channel edges: only the pad-ESD and link cells carry a net across; the TX and RX
    # cells are excluded so the two legs cannot short through them.
    edges = [(i[1][0], i[1][1]) for i in inst
             if i[2] not in ("aib_tx_clk", "aib_rx_clk", "aib_tx_data", "aib_rx_data")
             and len(i[1]) >= 2]
    for a, b, other, name in ((txc, rxc, rxcb, "clk"), (txcb, rxcb, rxc, "clkb")):
        r = reach(a, edges)
        if b not in r:
            errs.append("tb: TX %s (%s) is not connected through the channel to RX pin %s" % (name, a, b))
        if other in r:
            errs.append("tb: the %s leg also reaches the other RX pin (%s)" % (name, other))
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    errs = check(ap.parse_args().root)
    for e in errs:
        print("FAIL:", e, file=sys.stderr)
    if not errs:
        print("T-04 arrangement: clk and clkb both driven, carried and received (structure only)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
