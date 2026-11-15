#!/usr/bin/env python3
"""Check the derived item-7 SDFs against their manifest pins and against regeneration.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_item7_sdf.py [--root DIR]

The two committed SDFs under signoff/attest/item7-digital/ are inputs to the item 7
envelopes. They are derived from the pinned routed SDF by run_evidence.py's scope_sdf().
The manifest's `derived_inputs."7.digital"` block pins the source and both outputs by
sha256 (kept outside `evidence`: the grader reads every `evidence` entry as an envelope).
This fails if the source is not the pinned one, if regenerating from it does not reproduce
the committed bytes, or if the committed bytes are not the pinned ones.

What is specific here is the source pin and the run_evidence.py regeneration comparison,
which check_pnr_pins.py deliberately does not do; the exists-and-hash contract for the
pinned outputs is manifest_pins.py's (#283).
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the one manifest pin definition, #283)

KEY = "7.digital"
GENERATOR = "verification/klt/run_evidence.py"


def load_generator(root: Path):
    spec = importlib.util.spec_from_file_location("run_evidence", root / GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(root: Path) -> list:
    block, errs = manifest_pins.manifest_block(root, KEY)
    if block is None:
        return errs
    src = root / block["source"]["file"]
    if manifest_pins.sha(src.read_bytes()) != block["source"]["content_hash"]:
        return [f"{block['source']['file']}: sha256 differs from the manifest pin; re-cite deliberately"]
    gen = load_generator(root)
    raw = src.read_text()
    want = {"aib_datapath_route.tb.sdf": gen.scope_sdf(raw, False),
            "aib_datapath_route.tb.neg_timing.sdf": gen.scope_sdf(raw, True)}
    errs += manifest_pins.verify_pins(root, KEY, block)
    pins = {Path(f["file"]).name: f for f in block["files"]}
    if set(pins) != set(want):
        errs.append(f"{manifest_pins.MANIFEST}: derived_inputs.{KEY} pins {sorted(pins)}, "
                    f"run_evidence.py writes {sorted(want)}")
    else:
        for name, text in want.items():
            p = root / pins[name]["file"]
            if p.is_file() and p.read_bytes() != text.encode():
                errs.append(f"{pins[name]['file']}: not reproduced by run_evidence.py "
                            "regeneration from the pinned source")
    return errs


if __name__ == "__main__":
    sys.exit(manifest_pins.cli("item7 derived SDFs", check))
