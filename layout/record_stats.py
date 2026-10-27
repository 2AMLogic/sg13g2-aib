#!/usr/bin/env python3
"""Write layout/stats/*.json: `klt stats` of the unit cells and the abutted pair, and the
T-22 / T-23 summary derived from them (layout-measured, pre-extraction).

From the repo root, with the pinned klt (signoff/KLT_VERSION):
    python3 -I layout/record_stats.py
"""
import json
import os
import subprocess
import sys

GDS = "layout/aib_io_column.gds"
CELLS = ["aib_io_tx", "aib_io_rx", "aib_io_tx_clk", "aib_io_column_tx"]
T22_TARGET_UM, T23_LIMIT_UM2 = 55.0, 5500.0


def klt_stats(cell, version):
    out = subprocess.run(
        ["uvx", "--from", f"klayout-tools=={version}", "klt", "stats", GDS, "--top", cell,
         "--per-layer", "--format", "json"], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def main():
    version = open("signoff/KLT_VERSION").read().strip()
    os.makedirs("layout/stats", exist_ok=True)
    stats = {}
    for cell in CELLS:
        stats[cell] = klt_stats(cell, version)
        # The stream path is the only host-dependent field; keep the repo-relative one.
        stats[cell]["file"] = GDS
        with open(f"layout/stats/{cell}.stats.json", "w") as f:
            json.dump(stats[cell], f, indent=2, sort_keys=True)
            f.write("\n")
    def bbox(cell):
        b = stats[cell]["bbox_um"]
        return b["width"] if isinstance(b, dict) else None
    summary = {"record": "t22-t23-layout-measured", "klt_version": version, "stream": GDS,
               "basis": "layout-measured: klt stats bounding box of the drawn cell; pre-extraction; "
                        "DRC and LVS not run on this stream (issues #39, #40)", "cells": {}}
    for cell in CELLS:
        b = stats[cell]["bbox_um"]
        w, h = (b["width"], b["height"]) if isinstance(b, dict) else (b[2] - b[0], b[3] - b[1])
        summary["cells"][cell] = {"bbox_width_um": w, "bbox_height_um": h, "bbox_area_um2": round(w * h, 3)}
    unit = summary["cells"]["aib_io_tx"]
    pair = summary["cells"]["aib_io_tx_clk"]
    summary["T-22"] = {"target_um": T22_TARGET_UM, "unit_cell_pitch_um": unit["bbox_width_um"],
                       "abutted_pair_width_um": pair["bbox_width_um"],
                       "pair_pitch_um": pair["bbox_width_um"] / 2,
                       "met": unit["bbox_width_um"] <= T22_TARGET_UM and pair["bbox_width_um"] / 2 <= T22_TARGET_UM}
    summary["T-23"] = {"limit_um2": T23_LIMIT_UM2, "area_per_wire_um2": unit["bbox_area_um2"],
                       "scope": "I/O cell only: pad, ESD, driver or receiver; bounding box of the unit cell",
                       "met": unit["bbox_area_um2"] <= T23_LIMIT_UM2}
    col = summary["cells"]["aib_io_column_tx"]
    summary["column"] = {"length_um": col["bbox_width_um"], "slots": 24,
                         "data_wires_length_um": 20 * unit["bbox_width_um"],
                         "dr_0007_20_wire_length_um": 1100.0}
    with open("layout/stats/t22-t23.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps({k: summary[k] for k in ("T-22", "T-23", "column")}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
