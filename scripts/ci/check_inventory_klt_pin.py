#!/usr/bin/env python3
"""Check every inventory klt pin names the grader that produced its envelope.

Stdlib only; PDK-free. Usage: python3 -I scripts/ci/check_inventory_klt_pin.py [--root DIR]

The invariant: for every `signoff/attest/*.inventory.json` that declares
`pins.tools.klt`, that pin must equal the `provenance.klt_version` of the
paired envelope (the same path with ".inventory" removed) -- the attested
tool pin and the version of the grader that actually produced the evidence
must be the same statement.

This closes the drift class issue #324 filed: `klt signoff --attest` records
an inventory's pins verbatim (the envelope's `pin`/`role: tools` check value
is a copy) and records its own version separately as provenance, and `--check`
never compares the two (signoff/README.md, "What CI checks"). An inventory
re-attested by a bumped grader without the pin bump -- or the reverse --
attests a tool version the evidence was not produced with, and nothing
notices. It happened twice in one week: PR #325 fixed item 9 digital's stale
`0.8.0` pin sitting next to a `0.9.0` provenance, and commit fa07030 left
item 9 analog the same way.

Deliberately not compared: `signoff/KLT_VERSION`. The repo-wide pin is the
grader for the *next* attestation; an envelope produced by an earlier pin is
legitimate landed evidence, and comparing across that line would force
regenerating sound envelopes. The pairing is the boundary: each inventory is
compared only against the envelope built from it. (Comparing klt's own
version to the pin at attest time belongs in klt itself; that gap is tracked
on the tool, not patched here.)

Inventories without `pins.tools.klt` (item 1, item 10) are skipped: they
declare no klt pin to compare. A schema change that leaves no inventory
carrying the pin -- including one that leaves no `*.inventory.json` file
at all, as a renamed filename suffix does -- must not turn this guard off
silently, so -- as in check_attested_paths.py -- a run whose population
is empty fails and names the likely cause.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the one manifest pin definition, #283)

ATTEST_DIR = Path("signoff/attest")
INVENTORY_SUFFIX = ".inventory.json"


def reattest_command(inv_rel, env_rel, item):
    """The pinned-grader re-attest that refreshes pin and provenance together."""
    return (f'uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff'
            f" --attest {item} --inventory {inv_rel} -o {env_rel}")


def check_inventory(root: Path, inv_path: Path):
    """One inventory's errors; `(pin carried, errors)`."""
    inv_rel = inv_path.relative_to(root).as_posix()
    try:
        inv = json.loads(inv_path.read_text())
    except (OSError, ValueError) as exc:
        return False, [f"{inv_rel}: unreadable or invalid JSON ({exc})"]
    tools = (inv.get("pins") or {}).get("tools") or {}
    pin = tools.get("klt")
    if pin is None:
        return False, []
    if not isinstance(pin, str):
        return True, [f"{inv_rel}: pins.tools.klt is {pin!r}, not a tool version string"]
    env_rel = inv_rel[: -len(INVENTORY_SUFFIX)] + ".json"
    env_path = root / env_rel
    if not env_path.is_file():
        return True, [f"{inv_rel}: pins.tools.klt {pin} but the paired envelope "
                      f"{env_rel} is missing -- nothing attests this inventory"]
    try:
        env = json.loads(env_path.read_text())
    except (OSError, ValueError) as exc:
        return True, [f"{env_rel}: unreadable or invalid JSON ({exc})"]
    recorded = (env.get("provenance") or {}).get("klt_version")
    if not isinstance(recorded, str):
        return True, [f"{env_rel}: records no provenance.klt_version "
                      f"({recorded!r}) -- a grader that drops the field is a"
                      " toolchain/checker gap, not tree drift: extend this"
                      " checker's resolution instead of editing the envelope"]
    if recorded != pin:
        item = inv.get("t1_item", "?")
        repair = reattest_command(inv_rel, env_rel, item)
        return True, [f"{inv_rel}: pins.tools.klt {pin} but {env_rel} was produced"
                      f" by klt {recorded} (provenance.klt_version) -- the attested"
                      f" pin and the producing grader disagree; re-attest with: {repair}"
                      "; then commit both files (see signoff/README.md)"]
    return True, []


def check(root: Path) -> list:
    attest = root / ATTEST_DIR
    if not attest.is_dir():
        return [f"{ATTEST_DIR}: directory is missing"]
    errs = []
    carried = inventories = 0
    for inv_path in sorted(attest.rglob(f"*{INVENTORY_SUFFIX}")):
        inventories += 1
        did, inv_errs = check_inventory(root, inv_path)
        carried += did
        errs += inv_errs
    if carried == 0:
        errs.append(
            f"{root}: checked 0 inventory klt pin(s) across {inventories} "
            "inventory(ies) -- none carries pins.tools.klt. A renamed"
            " inventory field, attest directory or inventory filename suffix"
            " makes this guard vacuous; the attest inventories that pin tools"
            " must keep declaring it"
        )
    return errs


if __name__ == "__main__":
    sys.exit(manifest_pins.cli("inventory klt pins", check))
