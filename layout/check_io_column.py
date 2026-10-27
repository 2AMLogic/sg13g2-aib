#!/usr/bin/env python3
"""Geometry self-checks on layout/aib_io_column.gds (the T-22/DR-0007/DR-0010 structure).

Run with the pinned klt environment from the repo root:
    uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/check_io_column.py layout/aib_io_column.gds
Exit 0 only if every check passes. These are structural checks, not DRC.
"""
import sys

import klayout.db as db

PITCH, DEPTH, SLOTS = 55.0, 100.0, 24
DEVICE_LAYERS = [(1, 0), (5, 0), (6, 0), (8, 0), (31, 0), (14, 0)]
PAD_OPEN = (7.5, 56.0, 47.5, 96.0)
RAIL_LABELS = ("VSS", "VDDIO")


def metal_clusters(ly, cell):
    """Metal1..Metal3 conductivity (Via1/Via2 joined) of one cell, flattened, as a
    LayoutToNetlist plus its layers. Devices are not recognised: this is wire connectivity."""
    names = {"M1": (8, 0), "V1": (19, 0), "M2": (10, 0), "V2": (29, 0), "M3": (30, 0)}
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, cell, []))
    r = {k: l2n.make_layer(ly.layer(*v), k) for k, v in names.items()}
    for a, b in (("M1", "M1"), ("M1", "V1"), ("V1", "M2"), ("M2", "M2"), ("M2", "V2"), ("V2", "M3"), ("M3", "M3")):
        l2n.connect(r[a], r[b])
    l2n.extract_netlist()
    return l2n, r


def cluster_at(l2n, r, x, y):
    """Cluster id of the metal at (x, y) um, probed on Metal1 (the terminal layer); None if no metal."""
    n = l2n.probe_net(r["M1"], db.DPoint(x, y))
    return None if n is None else n.cluster_id


def label_clusters(ly, cell, l2n, r):
    """{cluster id: set of label strings} for the Metal2/Metal3 label purposes, whatever net they name."""
    out = {}
    for layer, key in (((10, 1), "M2"), ((30, 1), "M3")):
        idx = ly.find_layer(*layer)
        if idx is None:
            continue
        it = cell.begin_shapes_rec(idx)
        while not it.at_end():
            sh = it.shape()
            if sh.is_text():
                t = sh.text.transformed(it.trans())
                n = l2n.probe_net(r[key], db.DPoint(t.x * ly.dbu, t.y * ly.dbu))
                if n is not None:
                    out.setdefault(n.cluster_id, set()).add(t.string)
            it.next()
    return out


def main(path):
    ly = db.Layout()
    ly.read(path)
    k = 1000
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + (" " + detail if detail else ""))
        ok = ok and cond

    for cn in ("aib_io_tx", "aib_io_rx"):
        bb = ly.cell(cn).dbbox()
        check(f"{cn} bbox is {PITCH} x {DEPTH} um", (bb.width(), bb.height()) == (PITCH, DEPTH), str(bb))
        check(f"{cn} area per wire <= 5500 um2", bb.width() * bb.height() <= 5500.0)
        # No device layer shape under the pad opening (DR-0007, Pad.jR).
        for li in DEVICE_LAYERS:
            idx = ly.find_layer(*li)
            if idx is None:
                continue
            reg = db.Region(ly.cell(cn).begin_shapes_rec(idx))
            under = reg & db.Region(db.Box(*[int(v * k) for v in PAD_OPEN]))
            check(f"{cn}: nothing on layer {li[0]}/{li[1]} under the pad opening", under.is_empty())
    # Wire connectivity of the unit cells, including the shapes no label names (a short between
    # an unlabelled terminal and a rail is invisible to a check that walks labelled nets only).
    for cn in ("aib_io_tx", "aib_io_rx"):
        cell = ly.cell(cn)
        l2n, r = metal_clusters(ly, cell)
        labels = label_clusters(ly, cell, l2n, r)
        multi = sorted("/".join(sorted(v)) for v in labels.values() if len(v) > 1)
        check(f"{cn}: no two differently labelled nets share a metal cluster", not multi, ",".join(multi))
        rail_clusters = {c for c, v in labels.items() if v & set(RAIL_LABELS)}
        bad = []
        res = db.Region(cell.begin_shapes_rec(ly.find_layer(128, 0)))
        for poly in res.each():
            bx = poly.bbox()
            yc = bx.center().y * ly.dbu
            ends = [cluster_at(l2n, r, bx.left * ly.dbu - 0.28, yc), cluster_at(l2n, r, bx.right * ly.dbu + 0.28, yc)]
            if None in ends or ends[0] == ends[1] or rail_clusters & set(ends):
                bad.append(f"({bx.left * ly.dbu:.2f},{yc:.2f})")
        check(f"{cn}: each resistor's two ends are on separate metal clusters, neither on a rail", not bad, " ".join(bad))
        bad = []
        recog = db.Region(cell.begin_shapes_rec(ly.find_layer(99, 31)))
        for poly in recog.each():
            bx = poly.bbox()
            cx, cy, h = bx.center().x * ly.dbu, bx.center().y * ly.dbu, bx.width() * ly.dbu / 2
            plate, ring = cluster_at(l2n, r, cx, cy), cluster_at(l2n, r, cx, cy + h + 0.65)
            if plate is None or ring is None or plate == ring:
                bad.append(f"({cx:.2f},{cy:.2f})")
        check(f"{cn}: each diode's plate and tie ring are on separate metal clusters", not bad, " ".join(bad))
    for col in ("aib_io_column_tx", "aib_io_column_rx"):
        c = ly.cell(col)
        bb = c.dbbox()
        check(f"{col} length is {SLOTS} x {PITCH} um", abs(bb.width() - SLOTS * PITCH) < 1e-6, f"{bb.width()} um")
        # Mirror symmetry about the column centre, layer by layer (flattened).
        cx = int(SLOTS * PITCH / 2 * k)
        bad = []
        for li in ly.layer_indexes():
            info = ly.get_info(li)
            if info.layer == 63 or info.datatype == 1:   # text / label purposes name positions
                continue
            reg = db.Region(c.begin_shapes_rec(li))
            # mirror about the vertical centre line: x -> 2*cx - x
            mir = reg.transformed(db.Trans(db.Trans.M90, 2 * cx, 0))
            if not (reg ^ mir).is_empty():
                bad.append(f"{info.layer}/{info.datatype}")
        check(f"{col} is mirror-symmetric about its centre", not bad, ",".join(bad))
        # Abutment: the unioned prBoundary is one gap-free rectangle of the expected size.
        idx = ly.find_layer(189, 0)
        bnd = db.Region(c.begin_shapes_rec(idx)).merged()
        check(f"{col} cell boundaries abut without gap or overlap",
              bnd.count() == 1 and bnd.bbox().width() == int(SLOTS * PITCH * k),
              f"{bnd.count()} polygon(s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "layout/aib_io_column.gds"))
