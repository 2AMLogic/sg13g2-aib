#!/usr/bin/env python3
"""Generate / check the T1 item 6 / digital `not_applicable` documents.

Stdlib only; PDK-free. Usage:
  python3 -I scripts/ci/gen_item6_digital.py [--root DIR]               # check
  python3 -I scripts/ci/gen_item6_digital.py [--root DIR] --regenerate  # rewrite

`klt signoff` item 6 `not_applicable` wants a ratified JSON spec (rows keyed by
id) and a statement with one {id, class, reason} per row. spec/target-spec.md is
Markdown, so signoff/item6/digital-spec.json is derived from its table: the
digital row ids below, with the parameter name copied from the table. The check
fails when a listed row is missing from the spec, is renamed, carries **STAT**
or `SIM-MC`, or when the derived spec records a stale hash of target-spec.md.
Regenerate, then re-cite both file hashes in signoff/block-manifest.json
(`"6.digital"`) and regrade (signoff/README.md).
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SPEC = "spec/target-spec.md"
OUT_SPEC = "signoff/item6/digital-spec.json"
OUT_STATEMENT = "signoff/item6/digital-statement.json"

# Digital partition rows (synthesized data path, rtl/aib_datapath.v) and why
# each is deterministic. T-04 (clk/clkb crossing at the RX over PVT-FULL) and
# T-28 (weak pull resistance, tristate leakage) are analog-cell rows and are
# deliberately not listed; no STAT row is listed.
DIGITAL = {
    "T-02": ("rtl-format",
             "Exchange format is a property of the RTL: data launched and captured on both "
             "clock edges, with an SDR test mode. Checked by RTL simulation of "
             "rtl/aib_datapath.v; the same inputs give the same outputs, no device variation "
             "enters."),
    "T-03": ("structural-count",
             "Wire count N per direction is a structural parameter of the RTL (N = 20, "
             "fallback N = 8, instantiated lane by lane) and of the layout column; it is a "
             "count, not a measured quantity."),
    "T-05": ("enumerated-fault-function",
             "Shift redundancy is a mux function. The check enumerates every single-fault "
             "position (20 per direction, 40 total, DR-0016) in RTL simulation and formal "
             "equivalence; the outcome is exact for each case, not a distribution."),
    "T-27": ("cycle-accounting",
             "Sequential latency is counted in clock cycles on the RTL (TX input register to "
             "RX output register, 1.5 cycles each way); analog delays are excluded by the "
             "row itself."),
    "T-29": ("mode-function",
             "The digital half of the row is the datapath's loopback select: the one control "
             "input `l1` of rtl/aib_datapath.v, enumerated in both states and simulated per "
             "state. It is a fixed routing of enumerated signals, with no variation "
             "dependence. The RTL has no L2 control input, and `l1` is the digital select "
             "only, not the L1 electrical path: which loopback a wire group offers is set by "
             "its on-die route and its bonding, not by an RTL state, and the analog half of "
             "each loopback is separate SIM evidence outside this partition (DR-0019)."),
}


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def table_rows(root: Path) -> dict:
    rows = {}
    for line in (root / SPEC).read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and re.fullmatch(r"T-\d+", cells[0]):
            rows[cells[0]] = (cells[1], line)
    return rows


def build(root: Path) -> tuple:
    rows = table_rows(root)
    problems = []
    for rid in DIGITAL:
        if rid not in rows:
            problems.append(f"{rid} not in {SPEC}")
        elif "STAT" in rows[rid][1] or "SIM-MC" in rows[rid][1]:
            problems.append(f"{rid} is statistical in {SPEC}; it cannot be not_applicable")
    if problems:
        raise SystemExit("gen_item6_digital: " + "; ".join(problems))
    spec = {
        "status": "ratified",
        "derived_from": SPEC,
        "derived_from_sha256": sha(root / SPEC),
        "partition": "digital",
        "rows": [{"id": rid, "parameter": rows[rid][0].replace("*", "")} for rid in DIGITAL],
    }
    statement = {
        "partition": "digital",
        "rows": [{"id": rid, "class": cls, "reason": why} for rid, (cls, why) in DIGITAL.items()],
    }
    return spec, statement


def dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--regenerate", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    spec, statement = build(root)
    want = {OUT_SPEC: dump(spec), OUT_STATEMENT: dump(statement)}
    bad = 0
    for rel, text in want.items():
        p = root / rel
        if args.regenerate:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            print(f"wrote {rel} {sha(p)}")
        elif not p.exists() or p.read_text(encoding="utf-8") != text:
            print(f"STALE: {rel} (run with --regenerate)", file=sys.stderr)
            bad = 1
    return bad


if __name__ == "__main__":
    sys.exit(main())
