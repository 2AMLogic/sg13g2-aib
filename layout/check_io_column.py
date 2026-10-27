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
