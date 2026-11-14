#!/usr/bin/env python3
"""Check that simulation records are append-only against a base commit.

Stdlib only. Usage: python3 -I scripts/ci/check_sim_append_only.py --base SHA
A record path is any file under one of RECORD_ROOTS with a 'records' or
'corners' path component between the root and the file name. Added (A) entries
pass; modified, deleted, renamed or copied (M/D/R/C/T) entries fail.

READMEs are split, not blanket-exempt. A README *above* a record directory
(`sim/README.md`, `sim/<family>/README.md`) is harness prose and may change. A
README *inside* a record directory (`sim/<family>/records/<stamp>/README.md`) is
a record file and is frozen like the data beside it: it carries that record's
own narrative, so it is evidence, and nothing else would notice its removal --
`check_evidence_format.py` requires a README.md only in the seven top-level
evidence directories, never per record. Harness scripts under the roots are not
records and may change.

The base. A record is immutable once it is on the **default branch**, not from
its first push -- `spec/decisions/0020-dll-recomparison-t21.md`: "An unmerged
result is a claim, not evidence, and this repo's recorded results are
append-only on `main`." So every event must ask the one question "does this
branch rewrite a record that is already on the default branch?":

  * pull_request: --base is the PR base SHA, which asks exactly that.
  * push to a non-default branch: --base is the *previously pushed head*, which
    would instead freeze a record from its own first push, so the merge-base of
    --fallback-ref and the head is used.
  * push to the default branch: that merge-base degenerates to the head and the
    diff would go empty, so --base (the pre-push SHA) is kept -- a direct push
    that rewrites landed evidence must still fail.

The event facts come from --event-name / --push-ref / --default-branch, which
`.github/workflows/ci.yml` supplies; with none of them (a local run) --base is
used as given. An empty or all-zero base (a new branch) is skipped. A base that
is not in the clone (a push after a force-push) falls back to the merge-base of
--fallback-ref and the head.

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


def merge_base(ref: str, head: str):
    """(merge-base of ref and head, git's complaint) -- the first is None if there is none."""
    mb = subprocess.run(["git", "merge-base", ref, head], capture_output=True, text=True)
    if mb.returncode != 0:
        return None, mb.stderr.strip()
    return mb.stdout.strip(), ""


def pushed_to_default(push_ref: str, default_branch: str) -> bool:
    """Does this push event's ref name the default branch?

    An unknown ref or default-branch name answers True, because the pre-push SHA
    is the stricter of the two bases: a fact the workflow failed to supply must
    not loosen the check.
    """
    if not push_ref or not default_branch:
        return True
    return push_ref in (default_branch, f"refs/heads/{default_branch}")


def resolve_base(a) -> str:
    """The commit to diff against, given --base and the event facts.

    Narrates its choice on stdout so the CI log of either event shows which base
    the check actually ran against.
    """
    if a.event_name != "push" or pushed_to_default(a.push_ref, a.default_branch):
        return a.base
    mb, why = merge_base(a.fallback_ref, a.head)
    if mb is None:
        # No default-branch ref in this clone (shallow checkout, a fork). Keep
        # the pre-push SHA: it is the stricter base, so this degrades to the old
        # behaviour rather than to a vacuous check.
        print(f"append-only: no merge-base with {a.fallback_ref} ({why}); keeping "
              f"the pre-push base {a.base}", file=sys.stderr)
        return a.base
    print(f"append-only: push to {a.push_ref} is not the default branch "
          f"{a.default_branch!r}; using merge-base {mb} with {a.fallback_ref} "
          f"rather than the pre-push head {a.base}")
    return mb


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--fallback-ref", default="origin/main")
    ap.add_argument("--event-name", default="", help="forge event: push, pull_request or empty")
    ap.add_argument("--push-ref", default="", help="the ref a push event pushed (github.ref)")
    ap.add_argument("--default-branch", default="main", help="the repository's default branch")
    a = ap.parse_args(argv)
    if not a.base.strip("0"):
        # A branch's very first push reports an all-zero before-SHA. The
        # pull_request event's run covers that tree against the PR base.
        print("append-only: no base commit (new branch); nothing to compare")
        return 0
    base = resolve_base(a)
    have = subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True)
    if have.returncode != 0:
        mb, why = merge_base(a.fallback_ref, a.head)
        if mb is None:
            print(f"FAIL: base {base} is not in the clone and no merge-base with "
                  f"{a.fallback_ref}: {why}", file=sys.stderr)
            return 2
        print(f"append-only: base {base} unreachable; using merge-base {mb} with {a.fallback_ref}")
        base = mb
    print(f"append-only: comparing {base}...{a.head}")
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
