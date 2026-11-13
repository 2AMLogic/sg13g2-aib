#!/usr/bin/env python3
"""Check the committed routed SPEF and DEF against their manifest pins.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_pnr_pins.py [--root DIR]

`layout/pnr/.klt/place-and-route/aib_datapath_route.spef` and `aib_datapath.def` are kept as
recorded P&R evidence. No tool here regenerates them cheaply, so the manifest's
`derived_inputs."pnr.digital"` block pins each by sha256 (outside `evidence`: the grader reads
every `evidence` entry as an envelope). This fails if the block is missing, if either file is
not pinned, or if either file's bytes differ from its pin.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST = "signoff/block-manifest.json"
KEY = "pnr.digital"
PNR_DIR = "layout/pnr/.klt/place-and-route/"
REQUIRED = (PNR_DIR + "aib_datapath_route.spef", PNR_DIR + "aib_datapath.def")


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def check(root: Path) -> list:
    block = json.loads((root / MANIFEST).read_text()).get("derived_inputs", {}).get(KEY)
    if not block:
        return [f"{MANIFEST}: derived_inputs.{KEY} is missing"]
    pins = {f["file"]: f.get("content_hash") for f in block.get("files", [])}
    errs = [f"{MANIFEST}: derived_inputs.{KEY} has no pin for {r}" for r in REQUIRED if r not in pins]
    for name in REQUIRED:
        if name not in pins:
            continue
        path = root / name
        if not path.is_file():
            errs.append(f"{name}: file is missing")
        elif sha(path.read_bytes()) != pins[name]:
            errs.append(f"{name}: sha256 differs from the manifest pin {pins[name]}; "
                        "re-cite deliberately after a P&R re-run")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    errs = check(ap.parse_args().root)
    for e in errs:
        print(e, file=sys.stderr)
    print(f"routed SPEF/DEF pins: {'FAIL' if errs else 'ok'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
