#!/usr/bin/env python3
"""Check every cited evidence record binds the stream the repo ships.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_evidence_pins.py [--root DIR]

The invariant: for every record cited under `evidence` in
signoff/block-manifest.json that declares an input hash
(`provenance.input.content_hash`), that declared hash must equal the sha256
of the repo-scoped stream the record names, computed from the working tree.

This closes the gap #253 named and #273 sized: when #248 (PR #254) regenerated
`layout/aib_io_column.gds`, the four cited `klt pex --extract-only` reports kept
declaring the pre-regeneration hash and `klt signoff --manifest` re-graded
byte-identically. The manifest's evidence `content_hash` pins the record's
*declared* hash, so no manifest pin can see a stream that moved underneath a
record; this check compares the declaration against the shipped bytes.

The population is citation-driven, not a path glob: `layout/pex/records/`
holds superseded and probe directories that still declare the stale hash by
design (one is "history, not evidence" per the README, one is the never-cited
netlist-load probe), so a glob would report failures on a correct tree.

Stream resolution is a fixed key order, not `provenance.input.role`: role is
not reliable (`layout/lvs/digital.report.json` declares `role: "netlist"` but
its hash names the file in its `.layout` field). The first of
`provenance.input.path`, `file`, `layout`, `netlist`, `verilog_path` whose
value is a `{path, scope}` object with `scope == "repo"` and a non-null path
names the stream; the scope/null filter is what makes the order safe (a PEX
report carries both `.layout`, repo-scoped, and `.netlist`, external with a
null path, while the P&R report's top-level `verilog_path` is a bare string a
scratch worktree left behind).

The multi-source attest shape (`provenance.input.paths[]`, item 1 analog) is
verified per path. The envelope's aggregate `provenance.input.content_hash`
is deliberately not recomputed: check_design_sources.py measured that klt's
aggregate recipe is not reproducible from the paths alone, so reimplementing
it here would be a guess.

A record that declares an input hash but matches no resolution key is an
error naming the record and the keys tried, not a silent skip: that is what
surfaces a future klt schema change instead of quietly shrinking the
population. Records with no `provenance.input` hash are skipped outright --
`klt functional-verification` carries none, nor do the item 6 spec/statement
inputs (signoff/README.md).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the one manifest pin definition, #283)

INPUT_KEY = "provenance.input.path"
TOP_KEYS = ("file", "layout", "netlist", "verilog_path")
RESOLUTION_KEYS = (INPUT_KEY,) + TOP_KEYS


def repo_scoped(value):
    """The path a `{path, scope}` object names, when that path is repo-scoped."""
    if isinstance(value, dict) and value.get("scope") == "repo" and value.get("path"):
        return value["path"]
    return None


def citations(node):
    """Every `{file, ...}` citation leaf under one evidence row.

    Rows are lists of envelopes, single envelopes, or `not_applicable` maps
    whose leaves are envelopes; descend until a dict carries `file`.
    """
    if isinstance(node, dict):
        if "file" in node:
            yield node
        else:
            for value in node.values():
                yield from citations(value)
    elif isinstance(node, list):
        for item in node:
            yield from citations(item)


def stream_of(record):
    """(key, path) of the repo-scoped stream the record names; (None, None) if no key matches."""
    spots = [(INPUT_KEY, (record.get("provenance") or {}).get("input") or {}, "path")]
    spots += [(key, record, key) for key in TOP_KEYS]
    for key, obj, field in spots:
        path = repo_scoped(obj.get(field))
        if path is not None:
            return key, path
    return None, None


def check_stream(root: Path, record_name: str, stream: str, declared: str) -> list:
    stream_path = root / stream
    if not stream_path.is_file():
        return [f"{record_name}: names stream {stream}, which is missing"]
    actual = manifest_pins.sha(stream_path.read_bytes())
    if actual != declared:
        return [f"{record_name}: declares input {declared} but {stream} hashes to {actual}; "
                "the record binds a superseded stream -- re-run it from the shipped "
                "stream and re-cite it"]
    return []


def check_paths_entry(root: Path, record_name: str, entry) -> list:
    if not isinstance(entry, dict):
        return [f"{record_name}: a provenance.input.paths entry is not an object"]
    stream = repo_scoped(entry.get("path"))
    declared = entry.get("content_hash")
    if stream is None:
        return [f"{record_name}: a provenance.input.paths entry names no repo-scoped path"]
    if not declared:
        return [f"{record_name}: pins {stream} with no content_hash"]
    return check_stream(root, record_name, stream, declared)


def check_record(root: Path, name: str) -> list:
    path = root / name
    if not path.is_file():
        return [f"{name}: cited record file is missing"]
    try:
        record = json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"{name}: not valid JSON ({exc})"]
    input_block = (record.get("provenance") or {}).get("input") or {}
    declared = input_block.get("content_hash")
    if not declared:
        return []
    paths = input_block.get("paths")
    if isinstance(paths, list):
        if not paths:
            return [f"{name}: declares {declared} but provenance.input.paths is empty"]
        return [err for entry in paths for err in check_paths_entry(root, name, entry)]
    key, stream = stream_of(record)
    if stream is None:
        return [f"{name}: declares {declared} but names no repo-scoped stream "
                f"(tried {', '.join(RESOLUTION_KEYS)}); extend the resolution table"]
    return check_stream(root, name, stream, declared)


def check(root: Path) -> list:
    manifest = root / manifest_pins.MANIFEST
    if not manifest.is_file():
        return [f"{manifest_pins.MANIFEST}: file is missing"]
    evidence = json.loads(manifest.read_text()).get("evidence") or {}
    errs = []
    seen = set()
    for row, cited in evidence.items():
        for entry in citations(cited):
            name = entry.get("file")
            if not name or name in seen:
                continue
            seen.add(name)
            errs += check_record(root, name)
    return errs


if __name__ == "__main__":
    sys.exit(manifest_pins.cli("evidence input pins", check))
