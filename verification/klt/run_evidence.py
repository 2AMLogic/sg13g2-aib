#!/usr/bin/env python3
"""Produce the item 5 and item 7 / digital evidence envelopes with the pinned klt.

Run from the repo root with plain python3 (needs uv, iverilog, openroad, and
PDK_ROOT pointing at an ihp-sg13g2 install for the STA half):

    python3 verification/klt/run_evidence.py

Writes signoff/attest/item5-digital/{fv_*.json,sta_*.json} and, with PDK_ROOT set,
signoff/attest/item7-digital/ (the post-route runs, see item7() below). Every envelope is the
verbatim `klt ... --format json` stdout, except that the three scratch paths in a
functional-verification `environment` block (results_xml, test_log, build_log) are
reduced to their file names: klt emits them absolute, and an absolute host path does
not belong in committed evidence. `klt signoff` reads none of them.

Exit codes of the klt runs are checked against what each request is for: the
positive runs and STA must exit 0; the negative controls must exit exactly 3
(the suite ran and a test failed), never 1 (did not run).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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

# Item 7 / digital: the post-route functional run. The routed netlist and SDF are
# pinned by hash; a P&R re-run that changes either must be re-cited deliberately.
PNR = ROOT / "layout" / "pnr" / ".klt" / "place-and-route"
OUT7 = ROOT / "signoff" / "attest" / "item7-digital"
PNR_SHA256 = {
    "aib_datapath.v": "a27bec23489faae8489e3b52ee3d478fb885e54bfafa88a50230786fbca2854b",
    "aib_datapath_route.sdf": "3e8edd07efd747d5e6bb6db8b7fb38d13b7dba2607e25617d084ae6b02e24545",
}
FV7 = [("post_route", 0), ("neg_post_route_timing", 3)]  # (request stem, expected exit)
NEG_INSTANCE = r"g_wire\[0\]\.u_tx\/_3_"  # the mux driving tx_wire[0]
NEG_DELAY_NS = "12.000"  # longer than the 10 ns test period


def klt(spec: str, *args: str) -> subprocess.CompletedProcess:
    cmd = ["uvx", "--from", f"klayout-tools{spec}=={PIN}", "klt", *args, "--format", "json"]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def scope_sdf(text: str, mutate: bool) -> str:
    """Re-scope the routed SDF from the netlist top to its instance `dut` in the bench.

    The SDF is written against `aib_datapath` as the root; the bench instantiates it
    as `tb_datapath_postroute.dut`, which is where klt's $sdf_annotate scope points.
    The only edit is prefixing every (INSTANCE ...) with `dut`. With `mutate`, one
    arc is also inflated (the negative control): every delay of NEG_INSTANCE's cell
    becomes NEG_DELAY_NS.
    """
    text = re.sub(r"\(INSTANCE\s*\)", "(INSTANCE dut)", text)
    text = re.sub(r"\(INSTANCE (?!dut\))(\S+)\)", lambda m: f"(INSTANCE dut.{m.group(1)})", text)
    if mutate:
        cell = re.compile(r"\(INSTANCE dut\." + re.escape(NEG_INSTANCE) + r"\)\n  \(DELAY.*?\n  \)\n", re.S)
        m = cell.search(text)
        assert m, "negative-control cell not found in the SDF"
        flat = re.sub(r"\(\d+\.\d+:\d+\.\d+:\d+\.\d+\)",
                      f"({NEG_DELAY_NS}:{NEG_DELAY_NS}:{NEG_DELAY_NS})", m.group(0))
        text = text[:m.start()] + flat + text[m.end():]
    return text


def item7() -> int:
    """Run the suite on the routed netlist with the routed SDF annotated (positive + control)."""
    for name, want in PNR_SHA256.items():
        got = hashlib.sha256((PNR / name).read_bytes()).hexdigest()
        if got != want:
            print(f"item7: {name} sha256 {got} != pinned {want}; re-cite deliberately", file=sys.stderr)
            return 1
    OUT7.mkdir(parents=True, exist_ok=True)
    raw = (PNR / "aib_datapath_route.sdf").read_text()
    sdf = {"@SDF@": OUT7 / "aib_datapath_route.tb.sdf",
           "@SDF_NEG@": OUT7 / "aib_datapath_route.tb.neg_timing.sdf"}
    sdf["@SDF@"].write_text(scope_sdf(raw, False))
    sdf["@SDF_NEG@"].write_text(scope_sdf(raw, True))
    pdk = os.environ["PDK_ROOT"]
    bad = 0
    for stem, want in FV7:
        req = json.loads((ROOT / "verification" / "klt" / f"{stem}.json").read_text()
                         .replace("@PDK_ROOT@", pdk)
                         .replace("@SDF@", str(sdf["@SDF@"])).replace("@SDF_NEG@", str(sdf["@SDF_NEG@"])))
        kdir = ROOT / "verification" / "klt"
        req["sources"] = [s if os.path.isabs(s) else str((kdir / s).resolve()) for s in req["sources"]]
        req["testbench"]["search_path"] = str((kdir / req["testbench"]["search_path"]).resolve())
        with tempfile.TemporaryDirectory() as scratch:
            rp = Path(scratch) / f"{stem}.json"
            rp.write_text(json.dumps(req))
            p = klt("[functional-verification]", "functional-verification", str(rp), "-o", scratch)
            doc = json.loads(p.stdout)
        for k in ("results_xml", "test_log", "build_log"):
            doc["environment"][k] = Path(doc["environment"][k]).name
        doc["environment"]["sdf"]["file"] = Path(doc["environment"]["sdf"]["file"]).name
        text = json.dumps(doc, indent=2) + "\n"
        assert str(ROOT) not in text and pdk not in text, "absolute host path left in envelope"
        (OUT7 / f"fv_{stem}.json").write_text(text)
        ok = p.returncode == want
        bad += not ok
        print(f"fv7 {stem}: klt exit {p.returncode} (want {want}) status={doc['status']} "
              f"{doc['passed_count']}/{doc['test_count']} {'ok' if ok else 'UNEXPECTED'}")
    return 1 if bad else 0


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
    return 1 if (bad or item7()) else 0


if __name__ == "__main__":
    sys.exit(main())
