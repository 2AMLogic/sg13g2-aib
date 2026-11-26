#!/usr/bin/env python3
"""Check that no committed record carries a host home-directory path.

Stdlib only, no PDK. Usage: python3 -I scripts/ci/check_no_host_paths.py [--root DIR]

Walks every .json and .json.gz under sim/*/records and layout/*/records and fails, naming
the file and the JSON path, on any string value shaped like a path into a user's home
(/home/<u>/, /Users/<u>/, /root/<u>/). The repository is public and these paths leak the
machine that ran the simulation (#437). The shared scrub that keeps new records clean is
sim/harness/write_record.py; the one regex is deliberately re-implemented here, so this
check does not trust the code it polices.

Records are append-only evidence, so the offenders already on main are not rewritten: they
are listed in scripts/ci/host_path_baseline.json (DR-0030). A baselined file passes; a file
not in the baseline fails, as does a baseline entry whose file no longer exists or no longer
offends (the list must only shrink, never go stale). `/tmp/` scratch paths are accepted by
DR-0030 and are not matched.

Exit 0 clean, 1 on a finding.
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

HOST_PATH = re.compile(r"^/(?:home|Users|root)/[^/]+/")
BASELINE = Path(__file__).resolve().parent / "host_path_baseline.json"
GLOBS = ("sim/*/records/**/*.json", "sim/*/records/**/*.json.gz",
         "layout/*/records/**/*.json", "layout/*/records/**/*.json.gz")


def host_paths(obj, where=""):
    """Yield (json path, value) for every host-home path string under obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from host_paths(v, f"{where}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from host_paths(v, f"{where}/{i}")
    elif isinstance(obj, str) and HOST_PATH.match(obj):
        yield where, obj


def load(path: Path):
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def scan(root: Path):
    """{relative path: [(json path, value), ...]} for every offending committed record file."""
    found = {}
    for pattern in GLOBS:
        for p in sorted(root.glob(pattern)):
            try:
                hits = list(host_paths(load(p)))
            except (ValueError, OSError):
                continue  # not a JSON document (e.g. a .json.gz.stderr is excluded by glob anyway)
            if hits:
                found[p.relative_to(root).as_posix()] = hits
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent.parent)
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    args = ap.parse_args(argv)

    baseline = set(json.loads(args.baseline.read_text())["files"]) if args.baseline.is_file() else set()
    found = scan(args.root)
    bad = False
    for path, hits in found.items():
        if path in baseline:
            continue
        bad = True
        for where, value in hits:
            print(f"FAIL: {path}: {where} = {value!r} is a host home-directory path "
                  f"(scrub it; sim/harness/write_record.py does this for new records)",
                  file=sys.stderr)
    for path in sorted(baseline - set(found)):
        bad = True
        print(f"FAIL: {args.baseline.name} lists {path}, which is missing or no longer carries a "
              f"host path: drop the stale entry", file=sys.stderr)
    if not bad:
        print(f"ok: no new host path in committed records ({len(found)} baselined)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
