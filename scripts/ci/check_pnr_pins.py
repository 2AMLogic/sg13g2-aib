#!/usr/bin/env python3
"""Check the committed routed SPEF and DEF against their manifest pins.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_pnr_pins.py [--root DIR]

`layout/pnr/.klt/place-and-route/aib_datapath_route.spef` and `aib_datapath.def` are kept as
recorded P&R evidence. No tool here regenerates them cheaply, so the manifest's
`derived_inputs."pnr.digital"` block pins each by sha256 (outside `evidence`: the grader reads
every `evidence` entry as an envelope). This fails if the block is missing, if either file is
not pinned, or if either file's bytes differ from its pin. The pin contract itself is
manifest_pins.py; what is specific here is the required pair and the re-cite advice.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the one manifest pin definition, #283)

KEY = "pnr.digital"
PNR_DIR = "layout/pnr/.klt/place-and-route/"
REQUIRED = (PNR_DIR + "aib_datapath_route.spef", PNR_DIR + "aib_datapath.def")


def check(root: Path) -> list:
    block, errs = manifest_pins.manifest_block(root, KEY)
    if block is None:
        return errs
    return errs + manifest_pins.verify_pins(
        root, KEY, block, required=REQUIRED,
        advice="re-cite deliberately after a P&R re-run")


if __name__ == "__main__":
    sys.exit(manifest_pins.cli("routed SPEF/DEF pins", check))
