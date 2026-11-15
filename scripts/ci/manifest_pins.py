#!/usr/bin/env python3
"""The one definition of the manifest pin contract the signoff checkers share.

Stdlib only; PDK-free. Imported by the scripts/ci checkers; never run directly.

A `derived_inputs` block of signoff/block-manifest.json pins derived artefacts
by sha256. The pins live outside `evidence` because the grader reads every
`evidence` entry as an envelope; a pinned file is valid when it exists and its
bytes hash to its `content_hash`. That contract was hand-kept in two checkers
that no test compared against each other (#283) -- the same shape the corner
table had drifted into before #184 and the generator builders before #256.
This module is the one definition, and `cli()` is the one checker entry point
(`--root`, one error per line on stderr, `<label>: FAIL/ok` on stdout).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST = "signoff/block-manifest.json"


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def manifest_block(root: Path, key: str):
    """The manifest's `derived_inputs.<key>` block, or (None, [one error])."""
    block = json.loads((root / MANIFEST).read_text()).get("derived_inputs", {}).get(key)
    if not block:
        return None, [f"{MANIFEST}: derived_inputs.{key} is missing"]
    return block, []


def verify_pins(root: Path, key: str, block, required=None, advice=None):
    """Each pinned file exists and its bytes hash to its `content_hash`.

    Every name in `required` must have a pin; with `required` unset every pin
    in the block is verified. `advice`, when given, is appended to a
    hash-mismatch error. A pinned-but-missing file is an error, not a crash:
    the caller reads only what this reports present.
    """
    pins = {f["file"]: f.get("content_hash") for f in block.get("files", [])}
    names = list(required) if required is not None else list(pins)
    errs = [f"{MANIFEST}: derived_inputs.{key} has no pin for {r}" for r in names if r not in pins]
    for name in names:
        if name not in pins:
            continue
        path = root / name
        if not path.is_file():
            errs.append(f"{name}: file is missing")
        elif sha(path.read_bytes()) != pins[name]:
            errs.append(f"{name}: sha256 differs from the manifest pin {pins[name]}"
                        + (f"; {advice}" if advice else ""))
    return errs


def cli(label: str, check) -> int:
    """The shared checker `main()`: parse --root, print errors, return the exit code.

    The default root is the repository root; every caller lives one directory
    deep under it, next to this module.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    errs = check(ap.parse_args().root)
    for e in errs:
        print(e, file=sys.stderr)
    print(f"{label}: {'FAIL' if errs else 'ok'}")
    return 1 if errs else 0
