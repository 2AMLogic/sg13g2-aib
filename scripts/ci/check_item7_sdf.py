#!/usr/bin/env python3
"""Check the derived item-7 SDFs against their manifest pins and against regeneration.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_item7_sdf.py [--root DIR]

The two committed SDFs under signoff/attest/item7-digital/ are inputs to the item 7
envelopes. They are derived from the pinned routed SDF by run_evidence.py's scope_sdf().
The manifest's `derived_inputs."7.digital"` block pins the source and both outputs by
sha256 (kept outside `evidence`: the grader reads every `evidence` entry as an envelope).
This fails if the source is not the pinned one, if regenerating from it does not reproduce
the committed bytes, or if the committed bytes are not the pinned ones.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

MANIFEST = "signoff/block-manifest.json"
KEY = "7.digital"
GENERATOR = "verification/klt/run_evidence.py"


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_generator(root: Path):
    spec = importlib.util.spec_from_file_location("run_evidence", root / GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(root: Path) -> list:
    errs = []
    block = json.loads((root / MANIFEST).read_text()).get("derived_inputs", {}).get(KEY)
    if not block:
        return [f"{MANIFEST}: derived_inputs.{KEY} is missing"]
    src = root / block["source"]["file"]
    if sha(src.read_bytes()) != block["source"]["content_hash"]:
        return [f"{block['source']['file']}: sha256 differs from the manifest pin; re-cite deliberately"]
    gen = load_generator(root)
    raw = src.read_text()
    want = {"aib_datapath_route.tb.sdf": gen.scope_sdf(raw, False),
            "aib_datapath_route.tb.neg_timing.sdf": gen.scope_sdf(raw, True)}
    pins = {Path(f["file"]).name: f for f in block["files"]}
    if set(pins) != set(want):
        return [f"{MANIFEST}: derived_inputs.{KEY} pins {sorted(pins)}, run_evidence.py writes {sorted(want)}"]
    for name, text in want.items():
        f = pins[name]
        committed = (root / f["file"]).read_bytes()
        if committed != text.encode():
            errs.append(f"{f['file']}: not reproduced by run_evidence.py regeneration from the pinned source")
        if sha(committed) != f["content_hash"]:
            errs.append(f"{f['file']}: sha256 {sha(committed)} != manifest pin {f['content_hash']}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    errs = check(ap.parse_args().root)
    for e in errs:
        print(e, file=sys.stderr)
    print(f"item7 derived SDFs: {'FAIL' if errs else 'ok'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
