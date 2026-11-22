#!/usr/bin/env python3
"""Check the README's status statement against the committed signoff record.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_readme_status.py [--root DIR]

README.md states the T1 met count in exactly one anchored sentence —
"16 of 22 T1 signoff rows read `met`" — and this checks that sentence against
`t1_met_count` / `t1_item_count` in `signoff/block-manifest.signoff.json`.
It fails when the sentence is absent, when the two integers differ from the
record (either one), or when more than one sentence matches — the last so the
count cannot be stated twice and drift apart. The regex anchors on the
"T1 signoff rows" wording, so the item-8 aggregate's "16 pass ... of 30 spec
rows" and the characterization report's "16 of 30 rows" cannot satisfy or
collide with it.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the shared checker main(), #283)

RECORD = "signoff/block-manifest.signoff.json"
MET_RE = re.compile(r"(\d+) of (\d+) T1 signoff rows read `met`")


def check(root: Path) -> list:
    rec_path = root / RECORD
    readme_path = root / "README.md"
    if not rec_path.is_file():
        return [f"{RECORD}: missing"]
    if not readme_path.is_file():
        return ["README.md: missing"]
    record = json.loads(rec_path.read_text())
    met = record.get("t1_met_count")
    total = record.get("t1_item_count")
    if not isinstance(met, int) or not isinstance(total, int):
        return [f"{RECORD}: t1_met_count/t1_item_count missing or not integers"]
    matches = MET_RE.findall(readme_path.read_text())
    if not matches:
        return [f"README.md: no met-count sentence — expected one line matching "
                f"`{{n}} of {{m}} T1 signoff rows read `met``; the record reads "
                f"t1_met_count={met} of t1_item_count={total}"]
    if len(matches) > 1:
        return [f"README.md: {len(matches)} met-count sentences — state the count once"]
    got_met, got_total = (int(g) for g in matches[0])
    if (got_met, got_total) != (met, total):
        return [f"README.md: states {got_met} of {got_total} T1 signoff rows read `met`; "
                f"the record reads t1_met_count={met} of t1_item_count={total}"]
    return []


if __name__ == "__main__":
    sys.exit(manifest_pins.cli("README status vs signoff record", check))
