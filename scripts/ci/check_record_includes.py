#!/usr/bin/env python3
"""Check that every archived record deck's .include lines still resolve.

Stdlib only, PDK-free. Usage: python3 -I scripts/ci/check_record_includes.py

The invariant (#414): the record harness copies the bench deck into the record
verbatim (sim/harness/batch_record.sh), so a deck's .include strings stay
relative to the bench staging directory (`sim/<family>/`, the directory the
harness cd'd into before the run), not to the record directory the deck is
archived in. Nothing checked that every include a record names is either
record-local or still resolvable from the staging directory, so a cleanup that
deletes a staging-dir sibling (#412 removed `sim/channel-eye/esd_sz_*.inc`)
silently turned two re-runnable records into ones needing a hand-repointed
include -- with every check green.

For every `.cir` deck tracked at HEAD under a `records/` or `corners/`
component of `sim/` (RECORD_PARTS from check_sim_append_only.py), each
`.include` argument is resolved against (a) the record directory the deck
lives in, then (b) the bench staging directory (the directory holding that
`records/` component); it passes if either names a file tracked at HEAD.
An argument carrying a `$variable` (`$PDK_ROOT/...`, the io-cell-study deck)
cannot be resolved statically and is skipped, counted in the summary. Any
include resolving to neither fails, naming the deck and the include string,
unless the (deck, include) pair is on the in-file ALLOWLIST below -- the four
pairs already dangling when this guard landed (#412's two dc-static decks,
whose record-local `esd_sz_*.inc` copies are the re-run path, and the two
mc T-19 decks, authored three levels deeper than the family dir the record
was staged under).

The list is shrink-only, the netlist_closure_allowlist.json discipline: an
entry whose deck exists at HEAD while the pair no longer dangles (the staging
sibling came back, or the include string changed) fails too, so an allowlisted
case can only be fixed, never forgotten. An entry whose deck is absent from
the tree entirely is inert rather than stale, so the checker stays applicable
to fixture trees that seed only one case.

Membership and bytes both come from HEAD (`git ls-tree`, `git show`), so an
unstaged working tree cannot change the verdict, and nothing under `records/`
is ever written (append-only, sim/README.md). Quoted include arguments and
trailing `;` comments are handled: the layout/pex decks already spell their
record-local includes as `.include "aib_io_tx.dut.spice"`. `.lib`/`.inc`
directives appear in no record deck today and are out of scope.
"""
import posixpath
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_sim_append_only import RECORD_PARTS  # noqa: E402

DIRECTIVE = re.compile(r"^\s*\.include\s+(.+?)\s*$", re.IGNORECASE)

# (deck path at HEAD, include string verbatim) -> why it may dangle.
# Every entry's deck exists on main; the checker fails if one stops dangling.
ALLOWLIST = {
    ("sim/dc-static/records/20261118T212900Z-t16sz-dc-dpa/tb_dc_static_sz_dpa.cir",
     "../channel-eye/esd_sz_dpa.inc"):
        "#412 removed the staging-dir sibling sim/channel-eye/esd_sz_dpa.inc; the "
        "record-local copy esd_sz_dpa.inc beside this deck is the re-run path",
    ("sim/dc-static/records/20261118T213814Z-t16sz-dc-2kv/tb_dc_static_sz_2kv.cir",
     "../channel-eye/esd_sz_2kv.inc"):
        "#412 removed the staging-dir sibling sim/channel-eye/esd_sz_2kv.inc; the "
        "record-local copy esd_sz_2kv.inc beside this deck is the re-run path",
    ("sim/mc/records/20261112T082047Z-t19/tb_t19.cir",
     "../../../design/aib_rx_data.spice"):
        "authored in sim/mc/capture_window/, three levels deeper than the sim/mc "
        "staging dir this record was written under; design/aib_rx_data.spice is "
        "tracked at the repo root",
    ("sim/mc/records/20261112T082047Z-t19/tb_t19_ctl.cir",
     "../../../design/aib_rx_data.spice"):
        "authored in sim/mc/capture_window/, three levels deeper than the sim/mc "
        "staging dir this record was written under; design/aib_rx_data.spice is "
        "tracked at the repo root",
    ("sim/mc/records/20261123T094302Z-t19/tb_t19.cir",
     "../../../design/aib_rx_data.spice"):
        "authored in sim/mc/capture_window/, three levels deeper than the sim/mc "
        "staging dir this record was written under; design/aib_rx_data.spice is "
        "tracked at the repo root",
    ("sim/mc/records/20261123T094302Z-t19/tb_t19_ctl.cir",
     "../../../design/aib_rx_data.spice"):
        "authored in sim/mc/capture_window/, three levels deeper than the sim/mc "
        "staging dir this record was written under; design/aib_rx_data.spice is "
        "tracked at the repo root",
}


def git(args):
    """git stdout. Any non-zero status is a real failure and exits 2, not 1 --
    a broken git must not be able to pose as a failed check."""
    r = subprocess.run(["git", *args], capture_output=True)
    if r.returncode != 0:
        print(f"FAIL: git {' '.join(args)} exited {r.returncode}: "
              f"{r.stderr.decode(errors='replace').strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.decode(errors="replace")


def decks(tracked):
    """Sorted (deck path, bench staging dir) for every tracked sim/ record deck.

    The staging dir is the directory holding the `records/` component -- what
    batch_record.sh cd'd into (`REC="${DIR}/records/..."`), so includes written
    relative to it are the ones that ran.
    """
    found = []
    for path in sorted(tracked):
        parts = path.split("/")
        if parts[0] != "sim" or not path.endswith(".cir"):
            continue
        for i, part in enumerate(parts[1:-1], start=1):
            if part in RECORD_PARTS:
                found.append((path, "/".join(parts[:i])))
                break
    return found


def include_strings(deck_text):
    """The .include arguments of a deck: quote-stripped, `;` comment cut."""
    for line in deck_text.splitlines():
        m = DIRECTIVE.match(line)
        if not m:
            continue
        arg = m.group(1).split(";", 1)[0].strip()
        if len(arg) >= 2 and arg[0] == arg[-1] == '"':
            arg = arg[1:-1]
        if arg:
            yield arg


def resolves(deck_dir, staging, include, tracked):
    """Does the include name a tracked file from the record dir or the staging dir?"""
    return any(posixpath.normpath(posixpath.join(base, include)) in tracked
               for base in (deck_dir, staging))


def main():
    tracked = {p for p in git(["ls-tree", "-r", "-z", "--name-only", "HEAD"]).split("\0") if p}
    if not tracked:
        print("FAIL: HEAD tracks no files; not a usable tree", file=sys.stderr)
        return 2
    found = decks(tracked)
    bad = []
    stale = []
    used = set()
    lines = skipped = 0
    for deck, staging in found:
        for include in include_strings(git(["show", f"HEAD:{deck}"])):
            lines += 1
            if "$" in include:
                skipped += 1
                continue
            if resolves(posixpath.dirname(deck), staging, include, tracked):
                continue
            if (deck, include) in ALLOWLIST:
                used.add((deck, include))
                continue
            bad.append(f"FAIL: record include resolves from neither the record "
                       f"directory nor the bench staging directory: {deck} -> {include}")
    for key in sorted(set(ALLOWLIST) - used):
        if key[0] in tracked:
            stale.append(f"FAIL: allowlist entry no longer dangles; drop it: {key[0]} "
                         f"-> {key[1]} ({ALLOWLIST[key]})")
    for msg in bad + stale:
        print(msg, file=sys.stderr)
    if bad:
        print("record-includes: FAIL -- repoint the deck at its record-local copy, "
              "restore the staging-dir file, or (if owned) allowlist the pair",
              file=sys.stderr)
    verdict = "FAIL" if (bad or stale) else "ok"
    print(f"record-includes: {verdict} ({len(found)} record deck(s), "
          f"{lines} include line(s), {skipped} $variable path(s) skipped, "
          f"{len(used)} allowlisted)")
    return 1 if (bad or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
