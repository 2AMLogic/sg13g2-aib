#!/usr/bin/env python3
"""Write (or --check) signoff/attest/item2-analog.json, the T1 item 2 (Layout) envelope.

klt 0.8.0 has no `klt signoff --attest 2` (it accepts 1, 9 and 10), so this script writes the
artifact-anchored generic envelope the grader documents for item 2, but only after doing the
work the envelope claims: it regenerates the stream into a scratch directory with
layout/gen_io_column.py, requires the regenerated geometry digest to equal the committed
stream's, and requires layout/check_io_column.py to pass. A failure writes nothing.

From the repo root, in the pinned klt environment:
    uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" python -I layout/attest_item2.py [--check]
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

from klayout_tools.signoff import layout_geometry_digest

GDS = "layout/aib_io_column.gds"
OUT = "signoff/attest/item2-analog.json"
GENERATOR = ("uvx --from klayout-tools==$(cat signoff/KLT_VERSION) python -I "
             "layout/gen_io_column.py -o layout/aib_io_column.gds")


def sha256_file(path):
    return "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()


def build():
    version = open("signoff/KLT_VERSION").read().strip()
    with tempfile.TemporaryDirectory() as tmp:
        scratch = os.path.join(tmp, "regen.gds")
        subprocess.run([sys.executable, "-I", "layout/gen_io_column.py", "-o", scratch], check=True)
        regen = layout_geometry_digest(scratch)
    committed = layout_geometry_digest(GDS)
    if regen is None or regen != committed:
        sys.exit(f"FAIL: regenerated geometry {regen} != committed {committed}")
    subprocess.run([sys.executable, "-I", "layout/check_io_column.py", GDS], check=True,
                   stdout=subprocess.DEVNULL)
    return {
        "schema_version": 1,
        "kind": "generic",
        "status": "pass",
        "t1_item": 2,
        "summary": "T1 item 2 (Layout): committed stream regenerates to identical geometry from "
                   "layout/gen_io_column.py and passes the structural checks in "
                   "layout/check_io_column.py; not DRC, LVS or extraction evidence",
        "source": GDS,
        "provenance": {
            "klt_version": version,
            "klayout_version": None,
            "pdk": None,
            "deck": None,
            "input": {"path": {"path": GDS, "scope": "repo"}, "content_hash": sha256_file(GDS)},
            "regeneration": {"generator": GENERATOR, "regenerated_hash": regen, "hash_kind": "geometry"},
        },
    }


def main():
    env = build()
    text = json.dumps(env, indent=2) + "\n"
    if "--check" in sys.argv:
        if not os.path.exists(OUT) or open(OUT).read() != text:
            print("DRIFT: " + OUT + " does not reproduce")
            return 3
        print("match")
        return 0
    with open(OUT, "w") as f:
        f.write(text)
    print("wrote " + OUT + " content_hash=" + sha256_file(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
