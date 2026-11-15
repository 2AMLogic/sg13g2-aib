#!/usr/bin/env python3
"""Check that no tracked evidence file is silently gitignored.

Stdlib only, no PDK. Usage: python3 -I scripts/ci/check_record_not_ignored.py

A tracked file under a `records/` or `corners/` directory that an ignore rule
still matches is evidence a plain `git add` would silently drop (#260): git
skips ignored paths without warning, and a sibling force-added once masks the
broken rule from then on -- in the index, `git status` shows nothing. The
`*.log` negations that re-include each evidence family are hand-written, so a
renamed record directory or a new family re-opens the hole silently. This check
fails on any tracked record-path file that is still ignored, naming the path
and the matching `.gitignore` line so the fix is obvious from the CI log alone.

The verdict is the NON-verbose form, batched over --stdin: `git check-ignore
-v` reports negation matches as matches too, so its exit status would fail a
clean tree (11 negation lines on main when this landed). -v runs only on the
paths the verdict already flagged, to recover `source:linenum:pattern` for the
message. --no-index is load-bearing in both: without it check-ignore reports
nothing for a tracked file, which is precisely the force-add masking above.

Membership is the RECORD_PARTS constant from check_sim_append_only.py, tested
as a path component up to the file name -- NOT is_record(): that function's
RECORD_ROOTS gate encodes an append-only scoping decision (the layout/records
DRC trail is deliberately outside it) that must not shrink ignore coverage.
check_local.sh runs every checker as `python3 -I`, which keeps this script's
own directory off sys.path, hence the insert below (the check_corner_bundles.py
idiom).

Exit 0 if no tracked record-path file is ignored, 1 if any is, 2 if git itself
failed: check-ignore reports "none matched" as 1, which is an answer, and
anything else must not be readable as a pass.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_sim_append_only import RECORD_PARTS  # noqa: E402


def under_record_path(path: str) -> bool:
    """A records/corners component between the root and the file name."""
    return any(p in RECORD_PARTS for p in path.split("/")[:-1])


def git(args, stdin=b""):
    """git stdout. check-ignore answers "none matched" with 1, which is an
    answer; any other status is a real failure and exits 2, not 1 -- a broken
    git must not be able to pose as a failed check."""
    r = subprocess.run(["git", *args], input=stdin, capture_output=True)
    if r.returncode not in (0, 1):
        print(f"FAIL: git {' '.join(args)} exited {r.returncode}: "
              f"{r.stderr.decode(errors='replace').strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.decode()


def ignored(paths, verbose=False):
    """The given paths git says ARE ignored, NUL-quoted both ways so no file
    name can forge a line break. Verbose adds (path, source:line:pattern)."""
    out = git(["check-ignore", "-z", "--no-index",
               *(["-v"] if verbose else []), "--stdin"],
              "".join(p + "\0" for p in paths).encode())
    fields = out.split("\0")
    if verbose:
        return [(fields[i + 3], f"{fields[i]}:{fields[i + 1]}:{fields[i + 2]}")
                for i in range(0, len(fields) - 1, 4)]
    return [f for f in fields if f]


def main():
    tracked = [p for p in git(["ls-files", "-z"]).split("\0")
               if p and under_record_path(p)]
    if not tracked:
        print("record-not-ignored: no tracked record-path files; ok")
        return 0
    bad = ignored(tracked)
    if not bad:
        print(f"record-not-ignored: ok ({len(tracked)} tracked record-path "
              f"file(s) checked)")
        return 0
    rules = dict(ignored(bad, verbose=True))
    for p in bad:
        print(f"FAIL: tracked record file is ignored: {p}", file=sys.stderr)
        print(f"  matched by {rules.get(p, '<no -v line recovered>')}",
              file=sys.stderr)
    print("record-not-ignored: FAIL -- add or re-point a negation so each "
          "path above is re-included", file=sys.stderr)
    print(f"record-not-ignored: FAIL ({len(bad)} of {len(tracked)} tracked "
          f"record-path files ignored)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
