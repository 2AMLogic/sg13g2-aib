#!/usr/bin/env python3
"""Check every cited sim record binds the netlists it was computed with.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_netlist_closure.py [--root DIR]

The invariant: a `klt sim` report records, under `environment.netlist_closure`,
the sha256 of every netlist in its include closure. For every sim record cited
under `evidence` in signoff/block-manifest.json, each closure member with
`scope: repo` must hash, in the working tree, to the sha256 the record wrote.

This closes the gap #405 filed: #332 (`e47bb80`) shortened `XResd` in
design/aib_pad_esd.spice, and cited analog records went on describing the
pre-edit cell with every check green. The manifest's `content_hash` pins a
record's *declared* hash, and check_evidence_pins.py binds a record to the one
stream its `provenance.input` names, so neither can see a netlist in the
record's include closure move underneath it; this check compares each recorded
closure hash against the committed bytes.

The population is citation-driven, through check_evidence_pins.citations: a
glob over `sim/` would flag superseded and probe records that are history by
design, since committed records are append-only. A cited path under `sim/` is a
sim record; every other citation (the `signoff/attest/` envelopes, the item 6
documents, the `layout/` records) is out of population and is never an error
here. A record is read through the cited file when that carries the closure,
otherwise through the `report*.json[.gz]` files beside it: item 6 cites
`yield.json`, a summary with no `environment` block, and its closure lives in
the sibling `report.json.gz` and `report_ctl.json.gz`. A sim record that
reaches no closure at all is an error naming it, not a silent skip -- the rule
check_evidence_pins.py holds -- and so is an examined report that declares none.

The verdict is a hard fail, with a dated, shrink-only allowlist for mismatches
already known and owned (scripts/ci/netlist_closure_allowlist.json). An entry
is keyed on (record, member, recorded sha256) and names the re-run that retires
it. A mismatch not on the list fails. An entry whose mismatch is gone fails:
the netlist was restored, or the record was re-run and re-cited, so the entry
is dropped, never edited to cover a new mismatch. A mismatch at another
recorded hash is another key, so a report re-made in place cannot hide behind
an old entry. The list can therefore only shrink.

Not bound here: uncited records; members that are not `scope: repo` (a PDK
model behind $PDK_ROOT is recorded unhashed, with a reason); klt's aggregate
hashes, which check_design_sources.py measured as not reproducible from the
paths alone; and whether a re-run would change any row's verdict. A stale
record says what it simulated, not what the current cells would measure.
"""
import gzip
import json
import re
import sys
import zlib
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the one manifest pin definition, #283)
from check_evidence_pins import citations  # noqa: E402  (the one evidence citation walk)

SIM_ROOT = "sim/"
ALLOWLIST = "scripts/ci/netlist_closure_allowlist.json"
REPORT_SUFFIXES = (".json", ".json.gz")
KEY = ("record", "member", "sha256")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
UNREADABLE = (OSError, ValueError, EOFError, zlib.error)


def read_json(path: Path):
    """The parsed JSON of a `.json` or `.json.gz` file."""
    data = path.read_bytes()
    if path.name.endswith(".gz"):
        data = gzip.decompress(data)
    return json.loads(data.decode())


def closure_of(report):
    """The report's `environment.netlist_closure` when it is a non-empty list, else None."""
    environment = report.get("environment") if isinstance(report, dict) else None
    closure = environment.get("netlist_closure") if isinstance(environment, dict) else None
    return closure if isinstance(closure, list) and closure else None


def sibling_reports(path: Path) -> list:
    """The `report*.json[.gz]` files beside `path`, `path` itself excluded, in name order."""
    return sorted(q for q in path.parent.iterdir()
                  if q != path and q.is_file()
                  and q.name.startswith("report") and q.name.endswith(REPORT_SUFFIXES))


def tree_hash(path: Path) -> str:
    """The file's sha256 as bare hex, the form a closure records it in."""
    return manifest_pins.sha(path.read_bytes()).partition(":")[2]


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def is_day(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def check_closure(root: Path, name: str, carrier: Path, closure: list, mismatches: dict) -> list:
    """Record every stale `scope: repo` member of one report's closure; return the other errors.

    `mismatches` maps (record, member, recorded sha256) to the report that
    declared it and the member's hash in the tree, None when the file is gone.
    """
    errs = []
    for member in closure:
        if not isinstance(member, dict):
            errs.append(f"{name}: a closure member in {relative(root, carrier)} is not an object")
            continue
        if member.get("scope") != "repo":
            continue
        target, recorded = member.get("path"), member.get("sha256")
        if not isinstance(target, str) or not target:
            errs.append(f"{name}: a scope: repo closure member in "
                        f"{relative(root, carrier)} names no path")
            continue
        if not isinstance(recorded, str) or not recorded:
            errs.append(f"{name}: closure member {target} is scope: repo with no sha256")
            continue
        tree = root / target
        actual = tree_hash(tree) if tree.is_file() else None
        if actual != recorded:
            mismatches.setdefault((name, target, recorded), (relative(root, carrier), actual))
    return errs


def check_record(root: Path, name: str, mismatches: dict) -> list:
    """Examine one cited sim record; record its mismatches and return its other errors."""
    path = root / name
    if not path.is_file():
        return [f"{name}: cited record file is missing"]
    try:
        closure = closure_of(read_json(path))
    except UNREADABLE as exc:
        return [f"{name}: not a readable JSON report ({exc})"]
    carriers = [(path, closure)] if closure is not None else []
    errs = []
    if not carriers:
        for sibling in sibling_reports(path):
            where = f"{name}: sibling report {relative(root, sibling)}"
            try:
                closure = closure_of(read_json(sibling))
            except UNREADABLE as exc:
                errs.append(f"{where} is not a readable JSON report ({exc})")
                continue
            if closure is None:
                errs.append(f"{where} declares no environment.netlist_closure")
            else:
                carriers.append((sibling, closure))
        if not carriers and not errs:
            errs.append(f"{name}: cited sim record yields no environment.netlist_closure -- "
                        "no report*.json[.gz] beside it declares one")
    for carrier, closure in carriers:
        errs += check_closure(root, name, carrier, closure, mismatches)
    return errs


def load_allowlist(root: Path) -> tuple:
    """(keys, errors): the allowlist's (record, member, sha256) keys and its format errors."""
    path = root / ALLOWLIST
    if not path.is_file():
        return set(), [f"{ALLOWLIST}: file is missing"]
    try:
        entries = json.loads(path.read_text())["entries"]
    except (ValueError, KeyError, TypeError) as exc:
        return set(), [f"{ALLOWLIST}: is not a JSON object with an entries list ({exc})"]
    if not isinstance(entries, list):
        return set(), [f"{ALLOWLIST}: entries is not a list"]
    keys, errs = set(), []
    for i, entry in enumerate(entries):
        where = f"{ALLOWLIST}: entries[{i}]"
        if not isinstance(entry, dict):
            errs.append(f"{where}: is not an object")
            continue
        problems = [f"{where}: {field} is missing" for field in KEY + ("reason",)
                    if not isinstance(entry.get(field), str) or not entry[field].strip()]
        added = entry.get("added")
        if not isinstance(added, str) or not DAY.fullmatch(added) or not is_day(added):
            problems.append(f"{where}: added must be a YYYY-MM-DD date")
        if problems:
            errs += problems
            continue
        key = tuple(entry[field] for field in KEY)
        if key in keys:
            errs.append(f"{where}: duplicates the entry for {' / '.join(key)}")
        keys.add(key)
    return keys, errs


def check(root: Path) -> list:
    manifest = root / manifest_pins.MANIFEST
    if not manifest.is_file():
        return [f"{manifest_pins.MANIFEST}: file is missing"]
    allow, errs = load_allowlist(root)
    mismatches = {}
    seen = set()
    evidence = json.loads(manifest.read_text()).get("evidence") or {}
    for cited in evidence.values():
        for entry in citations(cited):
            name = entry.get("file")
            if not name or name in seen or not name.startswith(SIM_ROOT):
                continue
            seen.add(name)
            errs += check_record(root, name, mismatches)
    for key in sorted(mismatches):
        if key in allow:
            continue
        record, member, recorded = key
        carrier, actual = mismatches[key]
        state = f"hashes to {actual}" if actual else "has no such file"
        errs.append(f"{record}: {carrier} records {member} at sha256 {recorded} "
                    f"but the tree {state}; re-run from the current netlists and re-cite, "
                    f"or add a dated entry to {ALLOWLIST} naming the re-run")
    for record, member, recorded in sorted(allow - set(mismatches)):
        errs.append(f"{ALLOWLIST}: the entry for {record} / {member} / {recorded} "
                    "no longer mismatches (the netlist was restored, or the record was re-run "
                    "and re-cited); drop it, the list only shrinks")
    return errs


if __name__ == "__main__":
    sys.exit(manifest_pins.cli("cited netlist closures", check))
