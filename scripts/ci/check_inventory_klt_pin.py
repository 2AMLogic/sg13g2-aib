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

The same inventory's `pins.tools.ngspice` is compared against the
`tools.ngspice` of the *newest* `sim/pdk-smoke/records/*/record.json`
(stamp order). This closes the drift class issue #368 filed: the smoke
record 20261119T000247Z ran ngspice-47 while the item 9 analog inventory
pinned ngspice-46, and nothing compared the two. Only the newest record
is compared: committed records are append-only evidence and an older
record produced under a different simulator is legitimate history. Zero
records -- including a renamed records path -- is a failure, not a
vacuous pass, by the same rule as the inventory population above.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the one manifest pin definition, #283)

ATTEST_DIR = Path("signoff/attest")
INVENTORY_SUFFIX = ".inventory.json"
RECORDS_DIR = Path("sim/pdk-smoke/records")


def reattest_command(inv_rel, env_rel, item):
    """The pinned-grader re-attest that refreshes pin and provenance together."""
    return (f'uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff'
            f" --attest {item} --inventory {inv_rel} -o {env_rel}")


def newest_smoke_record(root: Path):
    """The newest pdk-smoke record: `((rel, tools.ngspice), [errors])`.

    Stamp directories sort lexicographically and their stamps are UTC, so
    the lexicographic maximum is the newest. Only the newest is returned:
    committed records are append-only evidence and an older record produced
    under a different simulator is legitimate history (#368).
    """
    records = sorted((root / RECORDS_DIR).glob("*/record.json"))
    if not records:
        return None, [f"{RECORDS_DIR}: no pdk-smoke record found"
                      f" ({RECORDS_DIR}/*/record.json) -- a renamed records"
                      " path or stamp layout makes the ngspice pin guard"
                      " vacuous; the analog smoke evidence tree must keep"
                      " landing record.json files"]
    rec = records[-1]
    rec_rel = rec.relative_to(root).as_posix()
    try:
        data = json.loads(rec.read_text())
    except (OSError, ValueError) as exc:
        return None, [f"{rec_rel}: unreadable or invalid JSON ({exc})"]
    return (rec_rel, (data.get("tools") or {}).get("ngspice")), []


def check_inventory(root: Path, inv_path: Path, newest):
    """One inventory's errors; `(klt pin carried, ngspice pin carried, errors)`.

    `newest` is the resolved newest pdk-smoke record, `(rel, tools.ngspice)`,
    or None when the records tree is empty or its newest file is unreadable
    -- those resolution errors are reported once by check().
    """
    inv_rel = inv_path.relative_to(root).as_posix()
    try:
        inv = json.loads(inv_path.read_text())
    except (OSError, ValueError) as exc:
        return False, False, [f"{inv_rel}: unreadable or invalid JSON ({exc})"]
    tools = (inv.get("pins") or {}).get("tools") or {}

    ngspice_pin = tools.get("ngspice")
    errs = []
    ngspice_carried = ngspice_pin is not None
    if ngspice_carried and newest is not None:
        rec_rel, recorded = newest
        if not isinstance(ngspice_pin, str):
            errs.append(f"{inv_rel}: pins.tools.ngspice is {ngspice_pin!r},"
                        " not a tool version string")
        elif not isinstance(recorded, str):
            errs.append(f"{rec_rel}: records no tools.ngspice ({recorded!r})"
                        " -- a smoke record that drops the field is a"
                        " bench/checker gap, not tree drift: extend this"
                        " checker's resolution instead of editing the record")
        elif recorded != ngspice_pin:
            item = inv.get("t1_item", "?")
            env_rel = inv_rel[: -len(INVENTORY_SUFFIX)] + ".json"
            repair = reattest_command(inv_rel, env_rel, item)
            errs.append(
                f"{inv_rel}: pins.tools.ngspice {ngspice_pin} but the newest"
                f" pdk-smoke record {rec_rel} ran {recorded} (tools.ngspice)"
                " -- the attested pin and the simulator that produced the"
                " landed smoke evidence disagree. Committed records are"
                " append-only: do not edit or delete them. Either re-run the"
                f" pdk smoke under {ngspice_pin} and land the new record, or"
                f" bump the pin to {recorded} and re-attest: {repair}")

    pin = tools.get("klt")
    carried = pin is not None
    if pin is None:
        return carried, ngspice_carried, errs
    if not isinstance(pin, str):
        errs.append(f"{inv_rel}: pins.tools.klt is {pin!r}, not a tool version string")
        return carried, ngspice_carried, errs
    env_rel = inv_rel[: -len(INVENTORY_SUFFIX)] + ".json"
    env_path = root / env_rel
    if not env_path.is_file():
        errs.append(f"{inv_rel}: pins.tools.klt {pin} but the paired envelope "
                    f"{env_rel} is missing -- nothing attests this inventory")
        return carried, ngspice_carried, errs
    try:
        env = json.loads(env_path.read_text())
    except (OSError, ValueError) as exc:
        errs.append(f"{env_rel}: unreadable or invalid JSON ({exc})")
        return carried, ngspice_carried, errs
    recorded = (env.get("provenance") or {}).get("klt_version")
    if not isinstance(recorded, str):
        errs.append(f"{env_rel}: records no provenance.klt_version "
                    f"({recorded!r}) -- a grader that drops the field is a"
                    " toolchain/checker gap, not tree drift: extend this"
                    " checker's resolution instead of editing the envelope")
        return carried, ngspice_carried, errs
    if recorded != pin:
        item = inv.get("t1_item", "?")
        repair = reattest_command(inv_rel, env_rel, item)
        errs.append(f"{inv_rel}: pins.tools.klt {pin} but {env_rel} was produced"
                    f" by klt {recorded} (provenance.klt_version) -- the attested"
                    f" pin and the producing grader disagree; re-attest with: {repair}"
                    "; then commit both files (see signoff/README.md)")
    return carried, ngspice_carried, errs


def check(root: Path) -> list:
    attest = root / ATTEST_DIR
    if not attest.is_dir():
        return [f"{ATTEST_DIR}: directory is missing"]
    newest, newest_errs = newest_smoke_record(root)
    errs = []
    carried = ngspice_carried = inventories = 0
    for inv_path in sorted(attest.rglob(f"*{INVENTORY_SUFFIX}")):
        inventories += 1
        klt_did, ngspice_did, inv_errs = check_inventory(root, inv_path, newest)
        carried += klt_did
        ngspice_carried += ngspice_did
        errs += inv_errs
    if carried == 0:
        errs.append(
            f"{root}: checked 0 inventory klt pin(s) across {inventories} "
            "inventory(ies) -- none carries pins.tools.klt. A renamed"
            " inventory field, attest directory or inventory filename suffix"
            " makes this guard vacuous; the attest inventories that pin tools"
            " must keep declaring it"
        )
    if ngspice_carried == 0:
        errs.append(
            f"{root}: checked 0 inventory ngspice pin(s) across {inventories} "
            "inventory(ies) -- none carries pins.tools.ngspice. A renamed"
            " inventory field, attest directory or inventory filename suffix"
            " makes this guard vacuous; the attest inventories that pin tools"
            " must keep declaring it"
        )
    if ngspice_carried and newest is None:
        errs += newest_errs
    return errs


if __name__ == "__main__":
    sys.exit(manifest_pins.cli("inventory klt pins", check))
