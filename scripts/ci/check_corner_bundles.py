#!/usr/bin/env python3
"""Check every committed `klt sim` request under sim/ against the PVT-FULL table.

Stdlib only, no PDK. Usage: python3 -I scripts/ci/check_corner_bundles.py [--root DIR]

`sim/pvt_full.py` is the one definition of the PVT-FULL corner bundle
(spec/target-spec.md). This checker reads every committed JSON under sim/ that
has a `corners` object and requires each process entry to bundle the MOS,
poly-resistor and diode sections that table pairs, and the supply and
temperature values to come from the PVT-FULL lists. A reduced grid (a
single-corner probe, a bench control) passes; a wrong pairing does not. That is
the invariant three hand-kept copies had already broken (#184).

Records under `sim/*/records/` are skipped: they are append-only evidence and
keep the request they were run with, whatever the table says today. A file that
is not readable as JSON is reported, not skipped -- a malformed request must not
pass unexamined.

Exit 0 if every request conforms, 1 otherwise (each problem on its own line).
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "sim"))
import pvt_full  # noqa: E402  (the one PVT-FULL definition)


def requests(sim_root: Path):
    """Committed JSON under sim/ (records aside), as (path, obj, problem) triples.

    A file that cannot be read or parsed is reported rather than skipped: a
    malformed request would otherwise pass this check unexamined, which is the
    one way a wrong corner bundle could still reach a run.
    """
    for path in sorted(sim_root.rglob("*.json")):
        if "records" in path.relative_to(sim_root).parts[:-1]:
            continue
        try:
            obj = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            yield path, None, f"{path}: not readable as JSON ({e})"
            continue
        if isinstance(obj, dict) and isinstance(obj.get("corners"), dict):
            yield path, obj, None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO), help="repository root (default: this clone)")
    args = ap.parse_args(argv)
    sim_root = Path(args.root) / "sim"
    if not sim_root.is_dir():
        print(f"no sim/ directory under {args.root}", file=sys.stderr)
        return 1
    bad, n = [], 0
    for path, obj, problem in requests(sim_root):
        if problem is not None:
            bad.append(problem)
            continue
        n += 1
        bad += pvt_full.check_corners(obj["corners"], where=str(path.relative_to(args.root)))
    for line in bad:
        print(f"::error::{line}" if os.environ.get("GITHUB_ACTIONS") else line, file=sys.stderr)
    if bad:
        print(f"{len(bad)} corner-bundle problem(s) in {n} request(s); "
              f"the table is sim/pvt_full.py", file=sys.stderr)
        return 1
    print(f"{n} request(s) under sim/ agree with the PVT-FULL table in sim/pvt_full.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
