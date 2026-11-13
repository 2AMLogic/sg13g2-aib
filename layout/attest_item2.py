#!/usr/bin/env python3
"""Write (or --check) a T1 item 2 (Layout) envelope with `klt signoff --attest 2`.

klt builds the envelope; this script does the work the envelope claims first and passes klt the
resulting geometry digest. A failed check writes nothing.
  analog : regenerate layout/aib_io_column.gds into scratch with layout/gen_io_column.py, require
           the same geometry digest as the committed stream, and require check_io_column.py to pass.
  digital: require layout/pnr/request.report.json to be ok, stage_reached route, power.pdn true,
           and its gds_path to be the committed routed stream. The digest is the committed stream's,
           which the full `klt place-and-route --check ... --rerun` reproduced (layout/pnr/README.md).

From the repo root, in the pinned klt environment:
    uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/attest_item2.py analog|digital [--check]
"""
import json
import os
import subprocess
import sys
import tempfile

from klayout_tools.signoff import layout_geometry_digest as digest

PNR_GDS = "layout/pnr/.klt/place-and-route/aib_datapath.gds"
REPORT = "layout/pnr/request.report.json"
ITEMS = {
    "analog": ("layout/aib_io_column.gds", "signoff/attest/item2-analog.json",
               "uvx --from klayout-tools==$(cat signoff/KLT_VERSION) python -I "
               "layout/gen_io_column.py -o layout/aib_io_column.gds"),
    "digital": (PNR_GDS, "signoff/attest/item2-digital.json",
                "PDK_ROOT=<pdk root> uvx --from klayout-tools==$(cat signoff/KLT_VERSION) klt "
                "place-and-route layout/pnr/request.json --pdk ihp-sg13g2 --format json "
                "> layout/pnr/request.report.json"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ITEMS:
        sys.exit(__doc__)
    gds, out, generator = ITEMS[sys.argv[1]]
    got = digest(gds)
    if sys.argv[1] == "analog":
        with tempfile.TemporaryDirectory() as tmp:
            scratch = os.path.join(tmp, "regen.gds")
            subprocess.run([sys.executable, "-I", "layout/gen_io_column.py", "-o", scratch], check=True)
            got = digest(scratch)
        if got is None or got != digest(gds):
            sys.exit(f"FAIL: regenerated geometry {got} != committed {digest(gds)}")
        subprocess.run([sys.executable, "-I", "layout/check_io_column.py", gds], check=True,
                       stdout=subprocess.DEVNULL)
    else:
        rep = json.load(open(REPORT))
        if (rep.get("status"), rep.get("stage_reached")) != ("ok", "route") or not rep["power"]["pdn"]:
            sys.exit("FAIL: report is not an ok, routed, PDN-built run")
        if os.path.basename(rep["gds_path"]) != os.path.basename(gds) or got is None:
            sys.exit("FAIL: report gds_path is not the committed stream")
    cmd = ["klt", "signoff", "--attest", "2", "--input", gds, "--generator", generator,
           "--regenerated-hash", got, "--hash-kind", "geometry"]
    cmd += ["--check", out] if "--check" in sys.argv else ["-o", out]
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
