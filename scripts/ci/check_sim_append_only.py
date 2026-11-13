#!/usr/bin/env python3
"""Check that simulation records are append-only against a base commit.

Stdlib only. Usage: python3 -I scripts/ci/check_sim_append_only.py --base SHA
A record path is any file under one of RECORD_ROOTS with a 'records' or
'corners' path component. Added (A) entries pass; modified, deleted, renamed or
copied (M/D/R/C/T) entries fail. Harness scripts and READMEs under those roots
are not records and may change. An empty or all-zero base (new branch) is
skipped. A base that is not in the clone (a push event after a force-push)
falls back to the merge-base of --fallback-ref and the head.

RECORD_ROOTS is `sim` plus `layout/pex` (T1 item 7, analog), whose `klt pex`
reports are recorded evidence under the same append-only rule. `layout/records`
(the DRC trail) is deliberately NOT here: nothing has enforced it so far, and
bringing it under the rule is a separate change from adding item 7's.
"""
import argparse
import subprocess
import sys

RECORD_PARTS = ("records", "corners")
RECORD_ROOTS = ("sim", "layout/pex")


def is_record(path: str) -> bool:
    if not any(path.startswith(root + "/") for root in RECORD_ROOTS):
        return False
    parts = path.split("/")
    return any(p in RECORD_PARTS for p in parts[1:-1])


def violations(name_status: str):
    bad = []
    for line in name_status.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        status, paths = fields[0], fields[1:]
        if status[0] == "A":
            continue
        if any(is_record(p) for p in paths):
            bad.append(f"{status}\t{' -> '.join(paths)}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--fallback-ref", default="origin/main")
    a = ap.parse_args(argv)
    if not a.base.strip("0"):
        print("append-only: no base commit (new branch); nothing to compare")
        return 0
    base = a.base
    have = subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True)
    if have.returncode != 0:
        mb = subprocess.run(["git", "merge-base", a.fallback_ref, a.head], capture_output=True, text=True)
        if mb.returncode != 0:
            print(f"FAIL: base {base} is not in the clone and no merge-base with "
                  f"{a.fallback_ref}: {mb.stderr.strip()}", file=sys.stderr)
            return 2
        base = mb.stdout.strip()
        print(f"append-only: base {a.base} unreachable; using merge-base {base} with {a.fallback_ref}")
    # --no-renames: a rename must surface as D + A, never hide an edit.
    out = subprocess.run(
        ["git", "diff", "--name-status", "--no-renames", f"{base}...{a.head}",
         "--", *(f"{root}/" for root in RECORD_ROOTS)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        print(f"FAIL: git diff failed: {out.stderr.strip()}", file=sys.stderr)
        return 2
    bad = violations(out.stdout)
    for b in bad:
        print(f"FAIL: record not append-only: {b}", file=sys.stderr)
    print(f"append-only: {'FAIL' if bad else 'ok'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
