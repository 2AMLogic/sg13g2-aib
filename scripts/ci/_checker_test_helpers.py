#!/usr/bin/env python3
"""The fixtures the scripts/ci self-test suites share.

Stdlib only; PDK-free. Imported by the test_*.py suites beside it; never run
directly. The underscore prefix keeps it out of the check list's test_*.py
candidate discovery (scripts/ci/test_ci_guards.py).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DIRS = ("spec", "design", "rtl", "verification", "sim", "layout", "measurements")
GOOD = {"record": "x", "utc_stamp": "20260101T000000Z", "pdk": {"release_tag": "v0.3.0"}, "log": "ngspice.log"}


def run(*cmd, cwd=None):
    return subprocess.run([sys.executable, "-I", *map(str, cmd)], cwd=cwd, capture_output=True, text=True)


def git(cwd, *args):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       cwd=cwd, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def make_tree(root: Path, record=None, record_readme=False):
    """A minimal evidence tree; `record` seeds one sim record under sim/s/records/.

    `record_readme` also writes that record's own README.md -- the narrative file
    the append-only tests need present in the base commit. It is off by default
    because only AppendOnlyTests cares whether it exists.
    """
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        (root / d / "README.md").write_text("# " + d + "\n")
    if record is not None:
        p = root / "sim/s/records/20260101T000000Z"
        p.mkdir(parents=True)
        (p / "record.json").write_text(json.dumps(record))
        if record_readme:
            (p / "README.md").write_text("# landed record\n")
