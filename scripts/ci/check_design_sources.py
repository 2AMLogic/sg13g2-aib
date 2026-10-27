#!/usr/bin/env python3
"""Freshness check (and regenerator) for T1 item 1 / digital: the committed
gate-level netlist and the inventory the attestation envelope pins.

Stdlib only; PDK-free. Usage:
  python3 -I scripts/ci/check_design_sources.py [--root DIR]
  python3 -I scripts/ci/check_design_sources.py [--root DIR] --regenerate

The chain checked, each link by content hash:
  RTL sources -> synthesis report (provenance.input.content_hash, the klt
  multi-source digest) -> netlist (report netlist_sha256) -> inventory ->
  attestation envelope (provenance.input.content_hash) -> manifest pin.

Not covered here: the standard-cell liberty hash in the report
(provenance.deck.content_hash) needs the PDK, which no workflow installs.
Run `klt synthesize --check ... [--rerun]` locally for that (signoff/README.md).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

DIR = "design/synth"
REQUEST = f"{DIR}/aib_datapath.synth.json"
REPORT = f"{DIR}/aib_datapath.report.json"
INVENTORY = "signoff/attest/item1-digital.inventory.json"
ENVELOPE = "signoff/attest/item1-digital.attest.json"
MANIFEST = "signoff/block-manifest.json"
MANIFEST_KEY = "1.digital"
RTL = ("rtl/aib_tx_slice.v", "rtl/aib_rx_slice.v", "rtl/aib_datapath.v", "rtl/shift_redundancy.v")
# The request lists the sources klt synthesizes; shift_redundancy.v is in the
# inventory (design source) but is not instantiated by aib_datapath.
SYNTH_RTL = RTL[:3]


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def klt_combined(paths) -> str:
    """klt's multi-source input digest: sha256 over the per-file hex digests,
    files sorted by path (klayout_tools._provenance._combined_content_hash)."""
    digests = [sha(p)[len("sha256:"):] for p in sorted(paths)]
    return "sha256:" + hashlib.sha256("".join(digests).encode()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def netlist_rel(report: dict) -> str:
    return report["netlist_path"]["path"]


def build_inventory(root: Path, t05_commit: str) -> dict:
    report = load(root / REPORT)
    nl = netlist_rel(report)
    files = list(RTL) + [REQUEST, REPORT, nl, report["script_path"]["path"]]
    return {
        "schema_version": 1,
        "t1_item": 1,
        "partition": "digital",
        "block": "sg13g2-aib",
        "top": "aib_datapath",
        "synthesis": {
            "tool": "klt synthesize",
            "request": REQUEST,
            "report": REPORT,
            "netlist": nl,
            "cell_library": "sg13g2_stdcell",
            "corner": "slow_1p08V_125C",
        },
        "rtl_revision": {
            "shift_redundancy_v_last_commit": t05_commit,
            "note": "rtl/shift_redundancy.v is not instantiated by aib_datapath; the netlist does not depend on it. Re-synthesize after the T-05 decision (#29, PR #32).",
        },
        "files": [{"path": p, "sha256": sha(root / p)} for p in files],
    }


def regenerate(root: Path, t05_commit: str) -> None:
    inv = build_inventory(root, t05_commit)
    (root / INVENTORY).parent.mkdir(parents=True, exist_ok=True)
    (root / INVENTORY).write_text(json.dumps(inv, indent=2) + "\n")
    h = sha(root / INVENTORY)
    env = {
        "schema_version": 1,
        "kind": "generic",
        "status": "pass",
        "t1_item": 1,
        "source": "scripts/ci/check_design_sources.py --regenerate",
        "summary": "Design-source inventory for the digital partition: RTL sources, klt synthesize request/report, and the gate-level netlist derived from them, each pinned by sha256.",
        "provenance": {"input": {"path": {"path": INVENTORY, "scope": "repo"}, "content_hash": h}},
    }
    (root / ENVELOPE).write_text(json.dumps(env, indent=2) + "\n")
    man = load(root / MANIFEST)
    man.setdefault("evidence", {})[MANIFEST_KEY] = {
        "file": "attest/item1-digital.attest.json",
        "content_hash": h,
    }
    (root / MANIFEST).write_text(json.dumps(man, indent=2) + "\n")


def check(root: Path):
    errs = []
    try:
        inv = load(root / INVENTORY)
        report = load(root / REPORT)
        env = load(root / ENVELOPE)
        man = load(root / MANIFEST)
    except (OSError, ValueError) as e:
        return [f"unreadable input: {e}"]
    for ent in inv.get("files", []):
        p = root / ent["path"]
        if not p.is_file():
            errs.append(f"{ent['path']}: listed in the inventory but missing")
        elif sha(p) != ent["sha256"]:
            errs.append(f"{ent['path']}: content differs from the inventory (stale; regenerate)")
    listed = {e["path"] for e in inv.get("files", [])}
    for must in list(RTL) + [REQUEST, REPORT]:
        if must not in listed:
            errs.append(f"{must}: not listed in the inventory")
    try:
        got = klt_combined([root / p for p in SYNTH_RTL])
        want = report["provenance"]["input"]["content_hash"]
        if got != want:
            errs.append(f"RTL sources differ from the synthesis report provenance ({got} != {want}); re-synthesize")
        nl = root / netlist_rel(report)
        if not nl.is_file() or sha(nl)[len("sha256:"):] != report["netlist_sha256"]:
            errs.append("netlist does not match the report netlist_sha256")
        if inv["synthesis"]["netlist"] != netlist_rel(report):
            errs.append("inventory names a different netlist than the report")
        h = sha(root / INVENTORY)
        if env["provenance"]["input"]["content_hash"] != h:
            errs.append("attestation envelope does not pin the current inventory hash")
        pin = man["evidence"][MANIFEST_KEY]["content_hash"]
        if pin != h:
            errs.append("manifest pin for item 1 / digital does not match the inventory hash")
    except (KeyError, TypeError) as e:
        errs.append(f"malformed input: missing {e}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--regenerate", action="store_true")
    ap.add_argument("--t05-commit", help="last commit touching rtl/shift_redundancy.v (default: from git)")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.regenerate:
        commit = a.t05_commit
        if not commit:
            import subprocess
            commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", "rtl/shift_redundancy.v"],
                                    cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        regenerate(root, commit)
        print("regenerated", INVENTORY, ENVELOPE, MANIFEST)
        return 0
    errs = check(root)
    for e in errs:
        print(f"check_design_sources: {e}", file=sys.stderr)
    if not errs:
        print("check_design_sources: ok")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
