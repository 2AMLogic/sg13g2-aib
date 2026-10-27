#!/usr/bin/env python3
"""Generator for the AIB I/O cell and I/O column stream (layout/aib_io_column.gds).

Direct geometry on IHP SG13G2 base layers through klayout.db; no PDK PCell is
used (the PDK's PCell library cannot be loaded in this environment, see
layout/README.md). Run with the pinned klt environment, from the repo root:

    uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I \
        layout/gen_io_column.py -o layout/aib_io_column.gds

Everything that is drawn derives from the schematics' derived netlists in
design/ (device type, W, L, ng and the net each terminal sits on); the device
table below repeats those numbers and `check_against_netlists()` fails the run
if design/*.spice and this table disagree.

Cells written: aib_io_tx, aib_io_rx (unit cells, 55 x 100 um), aib_io_tx_clk,
aib_io_rx_clk (clk | clkb pairs), aib_io_column_tx, aib_io_column_rx and the
top cell aib_io_column.

Intra-cell routing is done by a small deterministic maze router (Metal2
vertical-preferred, Metal3 horizontal-preferred, 0.8 um grid) so the stream is
reproducible. Nothing here is DRC, LVS or extraction clean by claim: those are
separate checks (see layout/README.md).
"""
import argparse
import heapq
import math
import os
import re
import sys

import klayout.db as db

DBU = 0.001

# GDS layer/datatype, from the PDK's sg13g2.lyp.
LAY = dict(
    Activ=(1, 0), GatPoly=(5, 0), Cont=(6, 0), nSD=(7, 0), M1=(8, 0), Pas=(9, 0),
    M2=(10, 0), pSD=(14, 0), SalBlock=(28, 0), V2=(29, 0), M3=(30, 0), NWell=(31, 0),
    Sub=(40, 0), V3=(49, 0), M4=(50, 0), V4=(66, 0), M5=(67, 0), Text=(63, 0),
    Recog=(99, 31), Ext=(111, 0), TV1=(125, 0), TM1=(126, 0), PolyRes=(128, 0),
    V1=(19, 0), Bnd=(189, 0),
    M1lbl=(8, 1), M2lbl=(10, 1), M3lbl=(30, 1), TM1lbl=(126, 1),
    M2pin=(10, 2), M3pin=(30, 2), TM1pin=(126, 2),
)

# Unit cell: pitch x depth (DR-0007, T-22, T-23).
CELL_W = 55.0
CELL_H = 100.0

# Router grid.
OX, OY, P = 1.2, 1.6, 0.8
NCOL = 67              # columns 0..66 -> x 1.2 .. 54.0
ROW_LO, ROW_HI = 3, 66  # routable rows -> y 4.0 .. 54.4
WIRE = 0.3             # M2/M3 wire width
VIA = 0.19             # Via1/Via2 size

VSS_RAIL_ROW = 1       # rows 0..2
VDD_RAIL_ROW = 64      # rows 63..65
TRACK_ROWS = {"OE": 60, "PUN": 61, "PD": 62}  # TX shared control tracks (M3)

# Pad (DR-0007: pad >= 30 um wide, no devices under it, cell beside the pad).
PAD_OPEN = (7.5, 56.0, 47.5, 96.0)     # passivation opening, 40 x 40 um
PAD_TM1 = (5.5, 54.0, 49.5, 98.0)      # topmost metal, 2 um overlap
PAD_PLATE = (6.0, 54.2, 49.0, 97.4)    # M3/M4/M5 landing under the pad stack

FINGER = 0.57          # gate pitch for l = 0.13: 0.13 + 2 x 0.14 + 0.16


def gx(i):
    return round(OX + P * i, 3)


def gy(j):
    return round(OY + P * j, 3)


def col_of(x):
    return int(round((x - OX) / P))


def row_of(y):
    return int(round((y - OY) / P))


def r3(v):
    return round(v, 3)


# --------------------------------------------------------------------------
# Device table: repeated from design/*.spice, verified against them.
# (name, type, w, l, ng, {pin: net})
# --------------------------------------------------------------------------
TX_DEVICES = [
    ("Mi1p", "pmos", 2.0, 0.13, 1, dict(D="OEB", G="OE", S="VDDIO")),
    ("Mi1n", "nmos", 1.0, 0.13, 1, dict(D="OEB", G="OE", S="VSS")),
    ("Mnd1p", "pmos", 4.0, 0.13, 2, dict(D="GP", G="DIN", S="VDDIO")),
    ("Mnd2p", "pmos", 4.0, 0.13, 2, dict(D="GP", G="OE", S="VDDIO")),
    ("Mnd1n", "nmos", 4.0, 0.13, 2, dict(D="GP", G="DIN", S="NA")),
    ("Mnd2n", "nmos", 4.0, 0.13, 2, dict(D="NA", G="OE", S="VSS")),
    ("Mnr1p", "pmos", 4.0, 0.13, 2, dict(D="NB", G="DIN", S="VDDIO")),
    ("Mnr2p", "pmos", 4.0, 0.13, 2, dict(D="GN", G="OEB", S="NB")),
    ("Mnr1n", "nmos", 2.0, 0.13, 2, dict(D="GN", G="DIN", S="VSS")),
    ("Mnr2n", "nmos", 2.0, 0.13, 2, dict(D="GN", G="OEB", S="VSS")),
    ("Mp", "pmos", 1.0, 0.13, 28, dict(D="PAD", G="GP", S="VDDIO")),
    ("Mn", "nmos", 1.0, 0.13, 14, dict(D="PAD", G="GN", S="VSS")),
    ("Mpu", "pmos", 2.0, 0.13, 1, dict(D="PUX", G="PUN", S="VDDIO")),
    ("Mpd", "nmos", 1.0, 0.13, 1, dict(D="PDX", G="PD", S="VSS")),
]
TX_RES = [
    ("Rpu", 0.5, 24.0, "PUX", "PAD"),
    ("Rpd", 0.5, 24.0, "PAD", "PDX"),
]
RX_DEVICES = [
    ("Mi1p", "pmos", 2.5, 0.13, 2, dict(D="N1", G="PADI", S="VDDIO")),
    ("Mi1n", "nmos", 1.0, 0.13, 2, dict(D="N1", G="PADI", S="VSS")),
    ("Mi2p", "pmos", 4.0, 0.13, 2, dict(D="DOUT", G="N1", S="VDDIO")),
    ("Mi2n", "nmos", 2.0, 0.13, 2, dict(D="DOUT", G="N1", S="VSS")),
]
# aib_pad_esd: diodes (anode, cathode), clamp, series resistor.
ESD_DIODES = [
    ("Dp1", "p", 10.0, "PAD", "VDDIO"),    # p+ in nwell: anode PAD, nwell VDDIO
    ("Dn1", "n", 10.0, "PAD", "VSS"),      # n+ in psub: cathode PAD, substrate VSS
    ("Dp2", "p", 2.0, "PADI", "VDDIO"),
    ("Dn2", "n", 2.0, "PADI", "VSS"),
]
ESD_CLAMP = ("Mclamp", "nmos", 2.0, 0.35, 20, dict(D="VDDIO", G="VSS", S="VSS"))
ESD_RES = ("Resd", 2.0, 2.0, "PAD", "PADI")


def check_against_netlists(design_dir):
    """Fail if the device table above drifts from the derived design/*.spice."""
    def parse(path):
        devs = {}
        for line in open(path):
            m = re.match(r"^X(\w+)\s+(.*)$", line.strip())
            if not m:
                continue
            toks = m.group(2).split()
            kv = {t.split("=")[0]: t.split("=")[1] for t in toks if "=" in t}
            nodes = [t for t in toks if "=" not in t]
            devs[m.group(1)] = (nodes, kv)
        return devs

    def num(s):
        return float(s.rstrip("u")) if s.endswith("u") else float(s)

    def chk_mos(devs, table, fix=None):
        for name, typ, w, l, ng, nets in table:
            nodes, kv = devs["" + name]
            model = nodes[-1]
            assert model.endswith(typ), (name, model)
            n = nodes[:-1]
            got = dict(D=n[0], G=n[1], S=n[2])
            for pin in "DGS":
                exp = nets[pin]
                if fix and exp in fix:
                    exp = fix[exp]
                assert got[pin] == exp, (name, pin, got[pin], exp)
            assert abs(num(kv["w"]) - w) < 1e-9 and abs(num(kv["l"]) - l) < 1e-9, name
            assert int(kv["ng"]) == ng, name

    chk_mos(parse(os.path.join(design_dir, "aib_tx_data.spice")), TX_DEVICES)
    chk_mos(parse(os.path.join(design_dir, "aib_rx_data.spice")), RX_DEVICES,
            fix={"PADI": "PAD", "N1": "M1"})
    esd = parse(os.path.join(design_dir, "aib_pad_esd.spice"))
    nodes, kv = esd["Mclamp"]
    assert nodes[:3] == ["VDDIO", "VSS", "VSS"] and int(kv["ng"]) == ESD_CLAMP[4]
    assert abs(num(kv["w"]) - ESD_CLAMP[2]) < 1e-9 and abs(num(kv["l"]) - ESD_CLAMP[3]) < 1e-9
    for name, kind, size, a, b in ESD_DIODES:
        nodes, kv = esd[name]
        assert abs(num(kv["w"]) - size) < 1e-9 and abs(num(kv["l"]) - size) < 1e-9, name
        if kind == "p":
            assert nodes[:2] == [a, b] and nodes[2] == "dpantenna", name
        else:
            assert nodes[:2] == [b, a] and nodes[2] == "dantenna", name
    nodes, kv = esd["Resd"]
    assert nodes[:2] == ["PAD", "PADI"] and abs(num(kv["w"]) - 2.0) < 1e-9
    tx = parse(os.path.join(design_dir, "aib_tx_data.spice"))
    for name, w, l, a, b in TX_RES:
        nodes, kv = tx[name]
        assert nodes[:2] == [a, b] and abs(num(kv["w"]) - w) < 1e-9 and abs(num(kv["l"]) - l) < 1e-9, name


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
class Draw:
    def __init__(self, layout, cell):
        self.ly = layout
        self.cell = cell
        self._li = {}

    def li(self, name):
        if name not in self._li:
            l, d = LAY[name]
            self._li[name] = self.ly.layer(l, d)
        return self._li[name]

    def rect(self, layer, x0, y0, x1, y1):
        k = 1.0 / DBU
        self.cell.shapes(self.li(layer)).insert(
            db.Box(int(round(x0 * k)), int(round(y0 * k)), int(round(x1 * k)), int(round(y1 * k))))

    def rect_c(self, layer, cx, cy, hw, hh=None):
        hh = hw if hh is None else hh
        self.rect(layer, cx - hw, cy - hh, cx + hw, cy + hh)

    def text(self, layer, x, y, s):
        k = 1.0 / DBU
        self.cell.shapes(self.li(layer)).insert(db.Text(s, int(round(x * k)), int(round(y * k))))


class Term:
    """A device terminal's Metal1 shape, reduced to router access nodes."""

    def __init__(self, net, nodes, tag):
        self.net = net
        self.nodes = nodes     # list of (col,row) grid nodes with M1 under them
        self.tag = tag


class Ctx:
    """Per-unit-cell drawing state: terminals, anchors and the pin list."""

    def __init__(self, d):
        self.d = d
        self.terms = []
        self.anchors = {}      # net -> list of (layer 0/1, col, row)
        self.pins = []         # (layer, net, x, y)

    def add_term(self, t):
        self.terms.append(t)

    def anchor(self, net, layer, col, row):
        self.anchors.setdefault(net, []).append((layer, col, row))


def nodes_in_bar(x0, x1, yc, d=None, need_extend=True):
    """Grid nodes whose via fits inside a horizontal M1 bar [x0,x1] at height yc (on a grid row).

    Returns (nodes, extra_rect). If no column fits, the bar is extended to the nearest column."""
    row = row_of(yc)
    assert abs(gy(row) - yc) < 1e-6, ("bar not on a grid row", yc)
    cols = [c for c in range(NCOL) if gx(c) - 0.15 >= x0 - 1e-9 and gx(c) + 0.15 <= x1 + 1e-9]
    if cols:
        return [(c, row) for c in cols], None
    cm = col_of((x0 + x1) / 2)
    gxc = gx(cm)
    return [(cm, row)], (min(x0, gxc - 0.15), max(x1, gxc + 0.15))


def mos(ctx, kind, w, l, ng, x0, rs, nets, name, gate_row=None):
    """Multi-finger MOS. Fingers run vertically, S/D regions alternate (S first).

    x0: left edge of Activ. rs: grid row of the source bus (Metal1, horizontal).
    Gate lands on a Cont/Metal1 pad on a grid node left of the device; the bulk tap
    (ntap/ptap) sits on a grid node right of it. Returns (right_x, top_row)."""
    d = ctx.d
    pitch = l + 0.44
    ys = gy(rs)
    y0 = r3(ys + 0.4)
    ax1 = r3(x0 + ng * pitch + 0.30)
    d.rect("Activ", x0, y0, ax1, y0 + w)
    top_poly = y0 + w + 0.18 + 0.13
    for j in range(ng):
        g0 = r3(x0 + 0.37 + pitch * j)
        d.rect("GatPoly", g0, y0 - 0.18, g0 + l, top_poly)
    bar_y0, bar_y1 = y0 + w + 0.18, top_poly
    g_first = r3(x0 + 0.37)
    g_last = r3(x0 + 0.37 + pitch * (ng - 1) + l)
    d.rect("GatPoly", g_first, bar_y0, g_last, bar_y1)
    # Contacts and M1 stripes.
    n = int((w - 0.14 + 0.18 + 1e-9) // 0.34)
    span = n * 0.16 + (n - 1) * 0.18
    cy0 = r3(y0 + (w - span) / 2)
    rd = int(math.ceil((bar_y1 + 0.2 + 0.15 - OY) / P - 1e-9))
    yd = gy(rd)
    s_x, d_x = [], []
    for i in range(ng + 1):
        cx = r3(x0 + 0.07 + pitch * i)
        for k in range(n):
            d.rect("Cont", cx, cy0 + 0.34 * k, cx + 0.16, cy0 + 0.34 * k + 0.16)
        if i % 2 == 0:
            d.rect("M1", cx, ys - 0.15, cx + 0.16, cy0 + span)
            s_x.append(cx)
        else:
            d.rect("M1", cx, cy0, cx + 0.16, yd + 0.15)
            d_x.append(cx)
    for bus_y, xs, pin in ((ys, s_x, "S"), (yd, d_x, "D")):
        bx0, bx1 = xs[0], xs[-1] + 0.16
        nodes, ext = nodes_in_bar(bx0, bx1, bus_y)
        if ext:
            bx0, bx1 = ext
        d.rect("M1", bx0, bus_y - 0.15, bx1, bus_y + 0.15)
        ctx.add_term(Term(nets[pin], nodes, f"{name}.{pin}"))
    # Implants and well.
    if kind == "pmos":
        d.rect("pSD", x0 - 0.18, y0 - 0.18, ax1 + 0.18, y0 + w + 0.18)
    # Gate landing on a grid node left of the device.
    gc = int(math.floor((x0 - 0.9 - OX) / P))
    gr = gate_row if gate_row is not None else row_of((bar_y0 + bar_y1) / 2)
    gxx, gyy = gx(gc), gy(gr)
    bc = (bar_y0 + bar_y1) / 2
    d.rect("GatPoly", gxx - 0.065, bar_y0, g_first + 0.001, bar_y1)          # neck along the bar
    d.rect("GatPoly", gxx - 0.17, min(bc, gyy), gxx + 0.17, max(bc, gyy))  # vertical neck, as wide as the landing
    d.rect_c("GatPoly", gxx, gyy, 0.17)
    d.rect_c("Cont", gxx, gyy, 0.08)
    d.rect_c("M1", gxx, gyy, 0.15)
    ctx.add_term(Term(nets["G"], [(gc, gr)], f"{name}.G"))
    # Bulk tap on a grid node right of the device.
    tc = int(math.ceil((ax1 + 0.9 + 0.39 - OX) / P))
    tr = row_of(y0 + w / 2)
    txx, tyy = gx(tc), gy(tr)
    d.rect_c("Activ", txx, tyy, 0.39)
    for dx in (-0.17, 0.17):
        for dy in (-0.17, 0.17):
            d.rect_c("Cont", txx + dx, tyy + dy, 0.08)
    d.rect_c("M1", txx, tyy, 0.25)
    if kind == "pmos":
        wx0, wx1 = x0 - 0.31, txx + 0.39 + 0.31
        wy0 = min(y0 - 0.31, tyy - 0.39 - 0.31)
        wy1 = max(y0 + w + 0.31, tyy + 0.39 + 0.31)
        d.rect("NWell", wx0, wy0, wx1, wy1)
        d.text("Text", txx, tyy, "well")
        ctx.add_term(Term("VDDIO", [(tc, tr)], f"{name}.B"))
    else:
        d.rect_c("pSD", txx, tyy, 0.57)
        d.rect_c("Sub", txx, tyy, 0.39)
        d.text("Text", txx, tyy, "sub!")
        ctx.add_term(Term("VSS", [(tc, tr)], f"{name}.B"))
    return r3(txx + 0.5 + (0.31 if kind == "pmos" else 0)), rd


def rppd(ctx, name, w, l, x0, row, net_a, net_b):
    """Horizontal P+ poly resistor (rppd) body x0..x0+l at grid row `row`; heads at both ends."""
    d = ctx.d
    yc = gy(row)
    hl = 0.43
    d.rect("GatPoly", x0 - hl, yc - w / 2, x0 + l + hl, yc + w / 2)
    d.rect("PolyRes", x0, yc - w / 2, x0 + l, yc + w / 2)
    d.rect("SalBlock", x0, yc - w / 2 - 0.2, x0 + l, yc + w / 2 + 0.2)
    ext = (x0 - hl - 0.18, yc - w / 2 - 0.18, x0 + l + hl + 0.18, yc + w / 2 + 0.18)
    d.rect("pSD", *ext)
    d.rect("Ext", *ext)
    n = int((w - 0.14 + 0.18 + 1e-9) // 0.34)
    span = n * 0.16 + (n - 1) * 0.18
    for side, net in (("L", net_a), ("R", net_b)):
        cx = (x0 - 0.2 - 0.16) if side == "L" else (x0 + l + 0.2)
        for k in range(n):
            cyk = yc - span / 2 + 0.34 * k
            d.rect("Cont", cx, cyk, cx + 0.16, cyk + 0.16)
        mx0, mx1 = cx - 0.15, cx + 0.31
        my = max(span / 2 + 0.07, 0.3)
        d.rect("M1", mx0, yc - my, mx1, yc + my)
        # M1 stub to the nearest grid column on the same row.
        c = col_of(cx + 0.08)
        xs = gx(c)
        d.rect("M1", min(xs - 0.15, mx0), yc - 0.15, max(xs + 0.15, mx1), yc + 0.15)
        ctx.add_term(Term(net, [(c, row)], f"{name}.{side}"))
    return x0 + l + hl + 0.5


def diode(ctx, name, kind, size, cx_col, cy_row, net_a, net_c):
    """dpantenna ('p': p+ in nwell, anode net_a on the plate, nwell tie net_c on the ring) or
    dantenna ('n': n+ plate, cathode net_a; p+ ring tie net_c). Centered on a grid node."""
    d = ctx.d
    cx, cy = gx(cx_col), gy(cy_row)
    h = size / 2
    d.rect_c("Activ", cx, cy, h)
    d.rect_c("Recog", cx, cy, h)
    n = int((size - 0.14 + 0.18 + 1e-9) // 0.34)
    span = n * 0.16 + (n - 1) * 0.18
    for i in range(n):
        for j in range(n):
            d.rect("Cont", cx - span / 2 + 0.34 * i, cy - span / 2 + 0.34 * j,
                   cx - span / 2 + 0.34 * i + 0.16, cy - span / 2 + 0.34 * j + 0.16)
    mh = span / 2 + 0.07
    d.rect_c("M1", cx, cy, mh)
    nodes = [(c, r) for c in range(NCOL) for r in range(ROW_HI + 1)
             if abs(gx(c) - cx) <= mh - 0.15 and abs(gy(r) - cy) <= mh - 0.15]
    ctx.add_term(Term(net_a, nodes, f"{name}.plate"))
    # Tie ring (Activ 0.3 wide, 0.5 clear of the plate).
    r0, r1 = h + 0.5, h + 0.8
    for (a, b, c_, e) in ((cx - r1, cy - r1, cx + r1, cy - r0), (cx - r1, cy + r0, cx + r1, cy + r1),
                          (cx - r1, cy - r0, cx - r0, cy + r0), (cx + r0, cy - r0, cx + r1, cy + r0)):
        d.rect("Activ", a, b, c_, e)
        d.rect("M1", a, b, c_, e)
    # Ring contacts, every 0.5 um along each side (centered, inside the 0.3 wide ring).
    k = int((2 * r1 - 0.3) / 0.5)
    for i in range(k + 1):
        px = cx - r1 + 0.07 + 0.5 * i
        if px + 0.16 > cx + r1 - 0.07:
            break
        d.rect("Cont", px, cy - r1 + 0.07, px + 0.16, cy - r1 + 0.23)
        d.rect("Cont", px, cy + r1 - 0.23, px + 0.16, cy + r1 - 0.07)
    for i in range(int((2 * r0 - 0.3) / 0.5) + 1):
        py = cy - r0 + 0.11 + 0.5 * i
        if py + 0.16 > cy + r0 - 0.11:
            break
        d.rect("Cont", cx - r1 + 0.07, py, cx - r1 + 0.23, py + 0.16)
        d.rect("Cont", cx + r1 - 0.23, py, cx + r1 - 0.07, py + 0.16)
    if kind == "p":
        d.rect_c("pSD", cx, cy, h + 0.18)
        d.rect_c("NWell", cx, cy, r1 + 0.24)
        d.text("Text", cx - r1 + 0.15, cy, "well")
        tie_lbl = None
    else:
        d.rect("pSD", cx - r1 - 0.18, cy - r1 - 0.18, cx + r1 + 0.18, cy - r0 + 0.18)
        d.rect("pSD", cx - r1 - 0.18, cy + r0 - 0.18, cx + r1 + 0.18, cy + r1 + 0.18)
        d.rect("pSD", cx - r1 - 0.18, cy - r0, cx - r0 + 0.18, cy + r0)
        d.rect("pSD", cx + r0 - 0.18, cy - r0, cx + r1 + 0.18, cy + r0)
        for (a, b, c_, e) in ((cx - r1, cy - r1, cx + r1, cy - r0), (cx - r1, cy + r0, cx + r1, cy + r1),
                              (cx - r1, cy - r0, cx - r0, cy + r0), (cx + r0, cy - r0, cx + r1, cy + r0)):
            d.rect("Sub", a, b, c_, e)
        d.text("Text", cx - r1 + 0.15, cy, "sub!")
    # Tie stub: M1 from the top ring strip straight up to a grid row clear of the ring.
    top = cy + r1
    tr = int(math.ceil((top + 0.6 - OY) / P - 1e-9))
    d.rect("M1", cx - 0.15, cy + r0, cx + 0.15, gy(tr) + 0.15)
    ctx.add_term(Term(net_c, [(cx_col, tr)], f"{name}.tie"))
    return cx + r1 + 0.31, tr


# --------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------
class Router:
    def __init__(self, ctx, rows_blocked=()):
        self.ctx = ctx
        self.owner = {}                     # (layer, c, r) -> net
        self.used_via1 = {}                 # (c, r) -> net
        self.paths = []                     # (net, [(layer,c,r),...])
        self.failed = []

    def own(self, net, layer, c, r):
        self.owner[(layer, c, r)] = net

    def free(self, net, layer, c, r):
        if not (0 <= c < NCOL and 0 <= r <= ROW_HI):
            return False
        o = self.owner.get((layer, c, r))
        return o is None or o == net

    def route_net(self, net, terms, anchors):
        tree = set()
        for a in anchors:
            tree.add(a)
            self.own(net, *a)
        pending = list(terms)
        if not tree:
            if len(pending) < 2:
                return
            # Seed the tree with the terminal closest to the others' centroid.
            cs = [n for t in pending for n in t.nodes]
            mc = sum(c for c, _ in cs) / len(cs)
            mr = sum(r for _, r in cs) / len(cs)
            first = pending.pop(0)
            best = min(first.nodes, key=lambda n: abs(n[0] - mc) + abs(n[1] - mr))
            self.seed(net, best, tree)
        # Order remaining terminals nearest-first to the tree.
        while pending:
            pending.sort(key=lambda t: min(abs(n[0] - m[0]) + abs(n[1] - m[1])
                                           for n in t.nodes for m in list(tree)[:400]))
            t = pending.pop(0)
            res = self.dijkstra(net, t, tree)
            if res is None:
                self.failed.append((net, t.tag, [(n, self.owner.get((0,)+n)) for n in t.nodes][:6]))
                continue
            path, src = res
            self.used_via1[(src[1], src[2])] = net
            for node in path:
                self.own(net, *node)
                tree.add(node)

    def seed(self, net, node, tree):
        n = (0, node[0], node[1])
        self.own(net, *n)
        self.used_via1[node] = net
        tree.add(n)

    def dijkstra(self, net, term, tree):
        pq = []
        dist = {}
        prev = {}
        for (c, r) in term.nodes:
            n = (0, c, r)
            if self.free(net, 0, c, r):
                dist[n] = 0.0
                heapq.heappush(pq, (0.0, n))
        while pq:
            dd, n = heapq.heappop(pq)
            if dd > dist.get(n, 1e18):
                continue
            if n in tree:
                path = [n]
                while n in prev:
                    n = prev[n]
                    path.append(n)
                return path, path[-1]
            L, c, r = n
            cand = []
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                horiz = dr == 0
                pref = (L == 1) == horiz         # M3 horizontal, M2 vertical
                cand.append(((L, c + dc, r + dr), 1.0 if pref else 2.5))
            cand.append((((1 - L), c, r), 4.0))
            for m, cost in cand:
                if not self.free(net, *m):
                    continue
                if not (ROW_LO - 3 <= m[2] <= ROW_HI):
                    continue
                nd = dd + cost
                if nd < dist.get(m, 1e18) - 1e-12:
                    dist[m] = nd
                    prev[m] = n
                    heapq.heappush(pq, (nd, m))
        return None

    def emit(self, d):
        """Write wires/vias for every owned node connected by the recorded paths."""
        # Re-derive geometry from node ownership: neighbours of the same net on the same
        # layer are joined; a node owned on both layers gets a Via2.
        keys = set(self.owner)
        for (L, c, r), net in self.owner.items():
            x, y = gx(c), gy(r)
            lay = "M2" if L == 0 else "M3"
            for dc, dr in ((1, 0), (0, 1)):
                m = (L, c + dc, r + dr)
                if self.owner.get(m) == net:
                    d.rect(lay, x - WIRE / 2, y - WIRE / 2, gx(c + dc) + WIRE / 2, gy(r + dr) + WIRE / 2)
            if (1 - L, c, r) in keys and self.owner[(1 - L, c, r)] == net and L == 0:
                d.rect_c("V2", x, y, VIA / 2)
                d.rect_c("M2", x, y, WIRE / 2)
                d.rect_c("M3", x, y, WIRE / 2)
        for (c, r), net in self.used_via1.items():
            x, y = gx(c), gy(r)
            d.rect_c("V1", x, y, VIA / 2)
            d.rect_c("M2", x, y, WIRE / 2)


# --------------------------------------------------------------------------
# Unit cells
# --------------------------------------------------------------------------
def rails_and_pad(ctx, router, tx):
    d = ctx.d
    # Cell boundary.
    d.rect("Bnd", 0, 0, CELL_W, CELL_H)
    # VSS / VDDIO rails (Metal3, 1.6 um, edge to edge so abutted cells share them).
    for net, row in (("VSS", VSS_RAIL_ROW), ("VDDIO", VDD_RAIL_ROW)):
        d.rect("M3", 0, gy(row) - 0.8, CELL_W, gy(row) + 0.8)
        d.text("M3lbl", 1.0, gy(row), net)
        for r in (row - 1, row, row + 1):
            for c in range(NCOL):
                router.own(net, 1, c, r)
                ctx.anchor(net, 1, c, r)
    # Control tracks (TX only): 0.3 wide Metal3 across the cell.
    if tx:
        for net, row in TRACK_ROWS.items():
            d.rect("M3", 0, gy(row) - 0.15, CELL_W, gy(row) + 0.15)
            d.text("M3lbl", 1.0, gy(row), net)
            for c in range(NCOL):
                router.own(net, 1, c, row)
                ctx.anchor(net, 1, c, row)
    # Pad stack: M3/M4/M5 plates, via arrays, TopVia1, TopMetal1, passivation opening.
    px0, py0, px1, py1 = PAD_PLATE
    for lay in ("M3", "M4", "M5"):
        d.rect(lay, px0, py0, px1, py1)
    def varray(layer, size, pitch):
        nx = int((px1 - px0 - 1.2) // pitch) + 1
        ny = int((py1 - py0 - 1.2) // pitch) + 1
        for i in range(nx):
            for j in range(ny):
                x = px0 + 0.6 + pitch * i
                y = py0 + 0.6 + pitch * j
                d.rect(layer, x, y, x + size, y + size)
    varray("V3", 0.19, 1.2)
    varray("V4", 0.19, 1.2)
    varray("TV1", 0.42, 1.2)
    d.rect("TM1", *PAD_TM1)
    d.rect("Pas", *PAD_OPEN)
    d.text("TM1lbl", (PAD_TM1[0] + PAD_TM1[2]) / 2, (PAD_TM1[1] + PAD_TM1[3]) / 2, "PAD")
    for c in range(NCOL):
        if px0 + 0.15 <= gx(c) <= px1 - 0.15:
            for r in range(ROW_HI, ROW_HI + 1):
                if gy(r) >= py0 + 0.15:
                    router.own("PAD", 1, c, r)
                    ctx.anchor("PAD", 1, c, r)


def add_pin(ctx, router, net, col, y_label):
    """Bottom-edge Metal2 pin stub at grid column `col` up to the first routable row."""
    d = ctx.d
    x = gx(col)
    d.rect("M2", x - WIRE / 2, 0, x + WIRE / 2, gy(ROW_LO) + WIRE / 2)
    d.rect("M2pin", x - WIRE / 2, 0, x + WIRE / 2, 1.0)
    d.text("M2lbl", x, 0.5, net)
    for r in range(0, ROW_LO + 1):
        router.own(net, 0, col, r)
    ctx.anchor(net, 0, col, ROW_LO)
    ctx.pins.append((net, x))


def build_unit(layout, name, tx):
    cell = layout.create_cell(name)
    d = Draw(layout, cell)
    ctx = Ctx(d)
    router = Router(ctx)
    rails_and_pad(ctx, router, tx)

    # --- ESD block (aib_pad_esd) --------------------------------------------
    band_row = 5
    # Dn1 / Dp1 / clamp / Resd / small diodes, left to right, one band.
    c_dn1 = col_of(3.2 + 5.8)
    r_dn1 = band_row + 8
    diode(ctx, "Dn1", "n", 10.0, c_dn1, r_dn1, "PAD", "VSS")
    c_dp1 = col_of(gx(c_dn1) + 5.8 + 1.6 + 6.05)
    diode(ctx, "Dp1", "p", 10.0, c_dp1, r_dn1, "PAD", "VDDIO")
    xr = gx(c_dp1) + 6.4
    # Clamp: nmos w=2 l=0.35 ng=20 (D=VDDIO, G=VSS, S=VSS) -- drawn with its own l.
    mos(ctx, "nmos", 2.0, 0.35, 20, r3(xr + 1.4), band_row + 1,
        dict(D="VDDIO", G="VSS", S="VSS"), "Mclamp", gate_row=band_row + 6)
    # Resd (2 um x 2 um) and the secondary diodes.
    rppd(ctx, "Resd", 2.0, 2.0, r3(xr + 1.6), band_row + 15, "PAD", "PADI")
    c_dp2 = col_of(49.5)
    diode(ctx, "Dp2", "p", 2.0, c_dp2, band_row + 3, "PADI", "VDDIO")
    diode(ctx, "Dn2", "n", 2.0, c_dp2, band_row + 9, "PADI", "VSS")
    if tx:
        build_tx(ctx, router)
    else:
        build_rx(ctx, router)
    # Route.
    allt = {}
    for t in ctx.terms:
        allt.setdefault(t.net, []).append(t)
    for t in ctx.terms:
        if len(t.nodes) <= 3:
            for (c, r) in t.nodes:
                router.own(t.net, 0, c, r)
    order = ["VDDIO", "VSS", "PAD"] + sorted(n for n in allt if n not in ("PAD", "VDDIO", "VSS"))
    for net in order:
        if net not in allt:
            continue
        router.route_net(net, allt[net], ctx.anchors.get(net, []))
    router.emit(d)
    for f in router.failed:
        print('UNROUTED', name, f, file=sys.stderr)
    return cell, ctx, router


def build_tx(ctx, router):
    dev = {n: (t, w, l, ng, nets) for n, t, w, l, ng, nets in TX_DEVICES}
    add_pin(ctx, router, "DIN", col_of(4.0), 0)

    def put(nm, x, row, grow=None):
        t, w, l, ng, nets = dev[nm]
        return mos(ctx, t, w, l, ng, r3(x), row, nets, nm, gate_row=grow)[0]

    x = put("Mp", 5.0, 25, 27)
    put("Mn", x + 2.5, 25, 27)
    x = 3.5
    for nm in ("Mnd1p", "Mnd2p", "Mnr1p", "Mnr2p"):
        x = put(nm, x + 2.0, 33)
    x = 3.5
    for nm in ("Mnd1n", "Mnd2n", "Mnr1n", "Mnr2n"):
        x = put(nm, x + 2.0, 44)
    x = 3.0
    for nm in ("Mi1p", "Mi1n", "Mpu", "Mpd"):
        x = put(nm, x + 1.5, 53)
    rppd(ctx, "Rpu", 0.5, 24.0, 28.0, 56, "PUX", "PAD")
    rppd(ctx, "Rpd", 0.5, 24.0, 28.0, 58, "PAD", "PDX")


def build_rx(ctx, router):
    dev = {n: (t, w, l, ng, nets) for n, t, w, l, ng, nets in RX_DEVICES}
    add_pin(ctx, router, "DOUT", col_of(4.0), 0)
    x = 3.5
    for nm in ("Mi1p", "Mi2p"):
        t, w, l, ng, nets = dev[nm]
        x = mos(ctx, t, w, l, ng, r3(x + 2.0), 33, nets, nm)[0]
    x = 3.5
    for nm in ("Mi1n", "Mi2n"):
        t, w, l, ng, nets = dev[nm]
        x = mos(ctx, t, w, l, ng, r3(x + 2.0), 44, nets, nm)[0]


def mirror_x(cell_w, x):
    return cell_w - x


def place(parent, child, slot, mirrored, x_off=0.0):
    """Instance of a 55 um unit/pair `child` at pitch slot `slot` (mirrored about its own
    vertical centre line when `mirrored`)."""
    k = 1.0 / DBU
    x = int(round((x_off + slot * CELL_W) * k))
    if mirrored:
        w = int(round(child_width(child) * k))
        t = db.Trans(db.Trans.M90, x + w, 0)
    else:
        t = db.Trans(db.Trans.R0, x, 0)
    parent.insert(db.CellInstArray(child.cell_index(), t))


_WIDTH = {}


def child_width(cell):
    return _WIDTH[cell.name]


def build_pair(layout, name, unit, labels):
    """clk | clkb pair of two unit cells; slot parity follows the column (left cell mirrored)."""
    cell = layout.create_cell(name)
    _WIDTH[name] = 2 * CELL_W
    _WIDTH[unit.name] = CELL_W
    place(cell, unit, 0, True)
    place(cell, unit, 1, False)
    d = Draw(layout, cell)
    d.rect("Bnd", 0, 0, 2 * CELL_W, CELL_H)
    return cell


def build_column(layout, name, unit, pair, role):
    """24 slots: spare, 10 data, clk/clkb pair, 10 data, spare. Slot k is mirrored when k is odd,
    so the column is mirror-symmetric about its centre (slot k <-> slot 23-k)."""
    cell = layout.create_cell(name)
    n_slots = 2 + 10 + 2 + 10
    d = Draw(layout, cell)
    names = ["SP0"] + [f"D{i}" for i in range(10)] + ["CLK", "CLKB"] + [f"D{i}" for i in range(10, 20)] + ["SP1"]
    k = 0
    while k < n_slots:
        if k == 11:
            place(cell, pair, 11, True)
            k += 2
            continue
        place(cell, unit, k, k % 2 == 1)
        k += 1
    for k, nm in enumerate(names):
        d.text("TM1lbl", k * CELL_W + CELL_W / 2, CELL_H / 2, f"{role}_{nm}")
    _WIDTH[name] = n_slots * CELL_W
    return cell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="layout/aib_io_column.gds")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    check_against_netlists(os.path.join(here, "..", "design"))
    layout = db.Layout()
    layout.dbu = DBU
    tx, _, _ = build_unit(layout, "aib_io_tx", True)
    rx, _, _ = build_unit(layout, "aib_io_rx", False)
    _WIDTH["aib_io_tx"] = _WIDTH["aib_io_rx"] = CELL_W
    txp = build_pair(layout, "aib_io_tx_clk", tx, None)
    rxp = build_pair(layout, "aib_io_rx_clk", rx, None)
    ctx_ = build_column(layout, "aib_io_column_tx", tx, txp, "TX")
    crx = build_column(layout, "aib_io_column_rx", rx, rxp, "RX")
    top = layout.create_cell("aib_io_column")
    top.insert(db.CellInstArray(ctx_.cell_index(), db.Trans(db.Trans.R0, 0, 0)))
    top.insert(db.CellInstArray(crx.cell_index(), db.Trans(db.Trans.R0, int(round(24 * CELL_W / DBU)), 0)))
    opts = db.SaveLayoutOptions()
    opts.format = 'GDS2'
    opts.gds2_write_timestamps = False
    opts.gds2_libname = 'aib_io_column'
    layout.write(args.output, opts)


if __name__ == "__main__":
    main()
