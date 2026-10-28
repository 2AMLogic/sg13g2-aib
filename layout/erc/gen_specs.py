"""Write the two `klt erc` supply specs in this directory from the committed streams.

`klt erc` ties can narrow a tap only by intersecting marker layers, and SG13G2
draws the n-well tap as Activ inside NWell and outside pSD, which no marker
layer expresses. So the n-well taps are asserted as `tap_boxes` derived here
from each stream's own geometry (the p-substrate taps use `tap_requires`
instead). Run from the repo root with the pinned klt interpreter:

    uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/erc/gen_specs.py
"""

import json
import sys

import klayout.db as db

IO_GDS = "layout/aib_io_column.gds"
IO_TOP = "aib_io_column"
DP_GDS = "layout/pnr/.klt/place-and-route/aib_datapath.gds"
DP_TOP = "aib_datapath"


def stackup(labels):
    """Gate plus Metal1..TopMetal2; `labels` maps stackup name -> label layer."""
    metals = [("metal1", "8/0"), ("metal2", "10/0"), ("metal3", "30/0"),
              ("metal4", "50/0"), ("metal5", "67/0"), ("topmetal1", "126/0"),
              ("topmetal2", "134/0")]
    out = [{"name": "gate", "layer": "5/0", "active_layer": "1/0", "role": "gate"}]
    for name, layer in metals:
        entry = {"name": name, "layer": layer}
        if name in labels:
            entry["label_layer"] = labels[name]
        out.append(entry)
    return out


VIAS = [
    {"name": "cont", "layer": "6/0", "between": ["gate", "metal1"]},
    {"name": "via1", "layer": "19/0", "between": ["metal1", "metal2"]},
    {"name": "via2", "layer": "29/0", "between": ["metal2", "metal3"]},
    {"name": "via3", "layer": "49/0", "between": ["metal3", "metal4"]},
    {"name": "via4", "layer": "66/0", "between": ["metal4", "metal5"]},
    {"name": "topvia1", "layer": "125/0", "between": ["metal5", "topmetal1"]},
    {"name": "topvia2", "layer": "133/0", "between": ["topmetal1", "topmetal2"]},
]


def ntap_boxes(gds, top_name, whole_polygons):
    """Boxes over Activ inside NWell and outside pSD (the n-well taps)."""
    ly = db.Layout()
    ly.read(gds)
    top = ly.cell(top_name)

    def region(layer, datatype):
        return db.Region(top.begin_shapes_rec(ly.layer(layer, datatype)))

    drawn = region(1, 0) & region(31, 0)
    ntap = (drawn - region(14, 0)).merged()
    um = ly.dbu
    boxes = []
    for poly in ntap.each():
        # A holed polygon (guard ring) is split into rectangles so that no box
        # asserts tap area over the ring's interior; a long row strip with
        # notches is boxed whole.
        pieces = [poly] if whole_polygons else poly.decompose_trapezoids(db.Polygon.TD_simple)
        for piece in pieces:
            b = piece.bbox()
            if not whole_polygons and piece.area() != b.area():
                sys.exit("n-well tap piece is not rectangular; boxes would over-assert")
            boxes.append([round(b.left * um, 3), round(b.bottom * um, 3),
                          round(b.right * um, 3), round(b.top * um, 3)])
    boxes.sort()
    asserted = db.Region()
    for l, b, r, t in boxes:
        asserted.insert(db.Box(round(l / um), round(b / um), round(r / um), round(t / um)))
    extra = ((drawn & asserted.merged()) - ntap).area() * um * um
    return boxes, extra


def spec(supply, ground, labels, boxes):
    return {
        "stackup": stackup(labels),
        "vias": VIAS,
        "nets": [{"name": supply, "kind": "supply"}, {"name": ground, "kind": "supply"}],
        "ties": [
            {"name": "psub_" + ground.lower(), "well_layer": None,
             "well_complement_of": "31/0", "tap_layer": "1/0", "tap_requires": ["14/0"],
             "connect_to": "metal1", "net": ground},
            {"name": "nwell_" + supply.lower(), "well_layer": "31/0", "tap_layer": "1/0",
             "tap_boxes": boxes, "connect_to": "metal1", "net": supply},
        ],
    }


def write(path, doc, extra):
    if extra:
        sys.exit(f"{path}: tap boxes cover {extra} um2 of non-tap Activ in NWell")
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")


boxes, extra = ntap_boxes(IO_GDS, IO_TOP, whole_polygons=False)
write("layout/erc/io_cells.erc-spec.json",
      spec("VDDIO", "VSS", {"metal2": "10/1", "metal3": "30/1", "topmetal1": "126/1"}, boxes),
      extra)
boxes, extra = ntap_boxes(DP_GDS, DP_TOP, whole_polygons=True)
write("layout/erc/aib_datapath.erc-spec.json",
      spec("VDD", "VSS", {"metal1": "8/25", "metal3": "30/25", "topmetal2": "134/25"}, boxes),
      extra)
