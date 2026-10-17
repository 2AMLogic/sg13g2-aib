#!/usr/bin/env python3
"""Check the repo evidence structure and the format of sim/ records.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_evidence_format.py [--root DIR]

Checks:
  * each evidence directory has a README.md;
  * each sim/**/records/<stamp>/record.json parses, carries the required
    fields (record, utc_stamp, pdk.release_tag) and holds no absolute path.
With zero records the record check passes vacuously.
"""
import argparse
import json
import re
import sys
from pathlib import Path

EVIDENCE_DIRS = ("spec", "design", "rtl", "verification", "sim", "layout", "measurements")
REQUIRED_TOP = ("record", "utc_stamp")
REQUIRED_PDK = ("release_tag",)
ABS_PATH = re.compile(r"(^|[\s\"'=:(])(/(?:home|tmp|Users|var|opt|usr|mnt|root|etc)/|[A-Za-z]:\\)")


def _strings(node, where=""):
    if isinstance(node, str):
        yield where, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, f"{where}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, f"{where}[{i}]")


def check_structure(root: Path):
    return [f"missing {d}/README.md" for d in EVIDENCE_DIRS if not (root / d / "README.md").is_file()]


def check_record(path: Path, root: Path):
    rel = path.relative_to(root)
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return [f"{rel}: unreadable or invalid JSON ({e})"]
    if not isinstance(data, dict):
        return [f"{rel}: top level is not an object"]
    errs = [f"{rel}: missing required field '{k}'" for k in REQUIRED_TOP if k not in data]
    pdk = data.get("pdk")
    if not isinstance(pdk, dict):
        errs.append(f"{rel}: missing 'pdk' object (PDK revision)")
    else:
        errs += [f"{rel}: missing required field 'pdk.{k}'" for k in REQUIRED_PDK if not pdk.get(k)]
    for where, s in _strings(data):
        if ABS_PATH.search(s):
            errs.append(f"{rel}: absolute path in {where.lstrip('.')}: {s!r}")
    return errs


def check_records(root: Path):
    errs = []
    for p in sorted((root / "sim").glob("**/records/*/record.json")):
        errs += check_record(p, root)
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    root = Path(ap.parse_args(argv).root).resolve()
    errs = check_structure(root) + check_records(root)
    for e in errs:
        print(f"FAIL: {e}", file=sys.stderr)
    n = len(list((root / "sim").glob("**/records/*/record.json")))
    print(f"evidence format: {'FAIL' if errs else 'ok'} ({n} sim record(s) checked)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
