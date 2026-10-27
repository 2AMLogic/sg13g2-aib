#!/usr/bin/env python3
"""Write (or --check) signoff/attest/item2-digital.json, the T1 item 2 (Layout) digital envelope.

klt 0.8.0 has no `klt signoff --attest 2`, and item 2 accepts only a `generic` envelope (a
`place-and-route` response is item 11 evidence). This writes the artifact-anchored envelope for
the routed GDS in layout/pnr/, but only after the report it rests on is consistent:
status ok, stage_reached route, power.pdn true, and the committed GDS is the report's own
output (the report's gds_path file name). `regenerated_hash` is the geometry digest of the
committed stream, which the full `klt place-and-route --check ... --rerun` reproduced
byte-identically (recorded in layout/README.md). The cheap `--check` (input and deck hashes)
is run by the operator, not here: it needs the PDK.

From the repo root, in the pinned klt environment:
    uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/attest_item2_digital.py [--check]
"""
import hashlib
import json
import os
import sys

from klayout_tools.signoff import layout_geometry_digest

REPORT = "layout/pnr/request.report.json"
GDS = "layout/pnr/.klt/place-and-route/aib_datapath.gds"
OUT = "signoff/attest/item2-digital.json"
GENERATOR = ("PDK_ROOT=<pdk root> uvx --from klayout-tools==$(cat signoff/KLT_VERSION) klt "
             "place-and-route layout/pnr/request.json --pdk ihp-sg13g2 --format json "
             "> layout/pnr/request.report.json")


def sha256_file(path):
    return "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()


def build():
    rep = json.load(open(REPORT))
    if (rep.get("status"), rep.get("stage_reached")) != ("ok", "route") or not rep["power"]["pdn"]:
        sys.exit("FAIL: report is not an ok, routed, PDN-built run")
    if os.path.basename(rep["gds_path"]) != os.path.basename(GDS):
        sys.exit("FAIL: report gds_path is not the committed stream")
    digest = layout_geometry_digest(GDS)
    if digest is None:
        sys.exit("FAIL: no geometry digest for " + GDS)
    return {
        "schema_version": 1,
        "kind": "generic",
        "status": "pass",
        "t1_item": 2,
        "summary": "T1 item 2 (Layout, digital): routed GDS from klt place-and-route of the item 1 "
                   "netlist, regenerated to identical geometry by the full --rerun check; report "
                   "route_drc_violation_count=%s antenna_violation_count=%s; not DRC or LVS evidence"
                   % (rep["route_drc_violation_count"], rep["antenna_violation_count"]),
        "source": REPORT,
        "provenance": {
            "klt_version": open("signoff/KLT_VERSION").read().strip(),
            "klayout_version": None,
            "pdk": None,
            "deck": None,
            "input": {"path": {"path": GDS, "scope": "repo"}, "content_hash": sha256_file(GDS)},
            "regeneration": {"generator": GENERATOR, "regenerated_hash": digest, "hash_kind": "geometry"},
        },
    }


def main():
    text = json.dumps(build(), indent=2) + "\n"
    if "--check" in sys.argv:
        if not os.path.exists(OUT) or open(OUT).read() != text:
            print("DRIFT: " + OUT + " does not reproduce")
            return 3
        print("match")
        return 0
    open(OUT, "w").write(text)
    print("wrote " + OUT + " content_hash=" + sha256_file(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
