#!/usr/bin/env python3
"""Produce the item 5 / digital evidence envelopes with the pinned klt.

Run from the repo root with plain python3 (needs uv, iverilog, openroad, and
PDK_ROOT pointing at an ihp-sg13g2 install for the STA half):

    python3 verification/klt/run_evidence.py

Writes signoff/attest/item5-digital/{fv_*.json,sta_*.json}. Every envelope is the
verbatim `klt ... --format json` stdout, except that the three scratch paths in a
functional-verification `environment` block (results_xml, test_log, build_log) are
reduced to their file names: klt emits them absolute, and an absolute host path does
not belong in committed evidence. `klt signoff` reads none of them.

Exit codes of the klt runs are checked against what each request is for: the
positive runs and STA must exit 0; the negative controls must exit exactly 3
(the suite ran and a test failed), never 1 (did not run).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = (ROOT / "signoff" / "KLT_VERSION").read_text().strip()
OUT = ROOT / "signoff" / "attest" / "item5-digital"
FV = [  # (request stem, expected klt exit code)
    ("shift_redundancy", 0), ("datapath_n20", 0), ("datapath_n8", 0),
    ("neg_shift_edge", 3), ("neg_extra_stage", 3),
]
STA = ["clk", "rx_clk"]


def klt(spec: str, *args: str) -> subprocess.CompletedProcess:
    cmd = ["uvx", "--from", f"klayout-tools{spec}=={PIN}", "klt", *args, "--format", "json"]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    bad = 0
    for stem, want in FV:
        with tempfile.TemporaryDirectory() as scratch:
            p = klt("[functional-verification]", "functional-verification",
                    f"verification/klt/{stem}.json", "-o", scratch)
            doc = json.loads(p.stdout)
        for k in ("results_xml", "test_log", "build_log"):
            doc["environment"][k] = Path(doc["environment"][k]).name
        (OUT / f"fv_{stem}.json").write_text(json.dumps(doc, indent=2) + "\n")
        ok = p.returncode == want
        bad += not ok
        print(f"fv  {stem}: klt exit {p.returncode} (want {want}) status={doc['status']} "
              f"{doc['passed_count']}/{doc['test_count']} {'ok' if ok else 'UNEXPECTED'}")
    if not os.environ.get("PDK_ROOT"):
        print("PDK_ROOT is not set; STA skipped", file=sys.stderr)
        return 2
    for clk in STA:
        p = klt("", "sta", f"design/synth/aib_datapath.sta_{clk}.json", "--pdk", "ihp-sg13g2")
        (OUT / f"sta_{clk}.json").write_text(p.stdout if p.stdout.endswith("\n") else p.stdout + "\n")
        doc = json.loads(p.stdout)
        ok = p.returncode == 0
        bad += not ok
        for c in doc["corners"]:
            print(f"sta {clk} {c['corner']}: {c['timing_status']} setup {c['worst_slack_ns']} "
                  f"hold {c['worst_hold_slack_ns']} {'ok' if ok else 'UNEXPECTED'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
