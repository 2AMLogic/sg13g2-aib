#!/usr/bin/env python3
"""Check every hash-bound attested path still matches its recorded content_hash.

Stdlib only; PDK-free; needs no klt. Usage:
  python3 -I scripts/ci/check_attested_paths.py [--root DIR]

Walks signoff/attest/**/*.json and, for every attestation.checks[] entry with
check == "present", re-hashes the file at the entry's path (sha256 over the
raw bytes, the algorithm the envelopes record as "sha256-raw-bytes") and
compares it to the recorded content_hash. A mismatch or a missing file means
an envelope no longer describes the tree -- typically a hash-bound path
(README.md, LICENSE, .github/workflows/ci.yml, ...) was edited without the
re-attest its envelope requires. This is the same drift the pinned grader's
re-grade catches at the end of the evidence job, named there as "the record
does not reproduce"; here it fails in seconds and names the path, the envelope
and the repair.

Report, never regenerate: the failure carries the copy-pasteable re-attest
command (pinned via signoff/KLT_VERSION, never a bare host klt); the checker
never runs klt and never writes an envelope. *.inventory.json files and JSON
files with no attestation.checks[] list are not envelopes and are skipped.

Two of the guard's own assumptions are loud, not silent: a run that checks
zero attested paths fails (naming the resolved root and the likely causes --
a renamed or missing signoff/attest/, or a renamed "present" discriminator),
and every envelope that hashes a path must declare attestation.hash_algorithm
equal to SUPPORTED_HASH_ALGORITHM. A declared-algorithm mismatch is a
toolchain/checker gap, not drift, so its message carries no re-attest advice.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ATTEST_DIR = Path("signoff/attest")
SUPPORTED_HASH_ALGORITHM = "sha256-raw-bytes"


def reattest_command(env_rel, env):
    """The pinned-grader re-attest for `env`, derived from the envelope itself."""
    item = env.get("t1_item", "?")
    source = env.get("source", "<envelope.source>")
    return (f'uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff'
            f" --attest {item} --inventory {source} -o {env_rel}")


def entry_errors(entry, root, env_rel, env, cmd):
    path = entry.get("path")
    recorded = entry.get("content_hash")
    where = f"T1 item {env.get('t1_item', '?')}, role {entry.get('role', 'unknown')}"
    repair = f"re-attest with: {cmd}; then commit {env_rel} (see signoff/README.md)"
    if not isinstance(path, str) or not path:
        return [f"{env_rel}: 'present' check with no path ({where}); {repair}"]
    if not isinstance(recorded, str):
        return [f"{env_rel}: {path} records no content_hash ({where}); {repair}"]
    alg, _, digest = recorded.partition(":")
    if alg != "sha256" or not digest:
        return [f"{env_rel}: {path} records unsupported hash {recorded!r} ({where}); {repair}"]
    target = root / path
    if not target.is_file():
        return [f"{env_rel}: {path} is attested but missing from the tree ({where}); {repair}"]
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        return [f"{env_rel}: {path} drifted from its attested content_hash ({where}); {repair}"]
    return []


def check_envelopes(root: Path):
    errs = []
    checked = envelopes = 0
    attest = root / ATTEST_DIR
    if attest.is_dir():
        for env_path in sorted(attest.rglob("*.json")):
            env_rel = env_path.relative_to(root).as_posix()
            if env_rel.endswith(".inventory.json"):
                continue
            try:
                env = json.loads(env_path.read_text())
            except (OSError, ValueError) as e:
                errs.append(f"{env_rel}: unreadable or invalid JSON ({e})")
                continue
            att = env.get("attestation") if isinstance(env, dict) else None
            checks = att.get("checks") if isinstance(att, dict) else None
            if not isinstance(checks, list):
                continue
            envelopes += 1
            if any(isinstance(e, dict) and e.get("check") == "present" for e in checks):
                # The declared algorithm is load-bearing only where an entry is
                # hashed: an envelope with no "present" entry never reads it.
                declared = att.get("hash_algorithm")
                if declared is None:
                    errs.append(
                        f"{env_rel}: attestation declares no hash_algorithm; this"
                        f" checker requires {SUPPORTED_HASH_ALGORITHM!r} for every"
                        " envelope that hashes a path. The tree is fine and no"
                        " envelope edit fixes it -- the checker is behind the"
                        " toolchain: extend this checker's supported algorithm set"
                    )
                elif declared != SUPPORTED_HASH_ALGORITHM:
                    errs.append(
                        f"{env_rel}: attestation declares hash_algorithm"
                        f" {declared!r}; this checker supports only"
                        f" {SUPPORTED_HASH_ALGORITHM!r}. This is a"
                        " toolchain/checker gap, not tree drift, and no envelope"
                        " edit fixes it -- extend this checker's supported"
                        " algorithm set"
                    )
            cmd = reattest_command(env_rel, env)
            for entry in checks:
                if isinstance(entry, dict) and entry.get("check") == "present":
                    checked += 1
                    errs += entry_errors(entry, root, env_rel, env, cmd)
    return errs, checked, envelopes


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    root = Path(ap.parse_args(argv).root).resolve()
    errs, checked, envelopes = check_envelopes(root)
    if checked == 0:
        # Keyed on checked, not envelopes: a schema rename of the
        # check == "present" discriminator leaves the envelopes parsing
        # (envelopes counts up) while nothing at all is verified.
        errs.append(
            f"{root}: checked 0 attested path(s) across {envelopes} envelope(s)"
            " -- signoff/attest/ may be renamed or missing under this root, or"
            ' the envelopes no longer declare any check == "present" entry'
            " (a renamed schema discriminator makes this guard vacuous)"
        )
    for e in errs:
        print(f"FAIL: {e}", file=sys.stderr)
    print(f"attested paths: {'FAIL' if errs else 'ok'} "
          f"({checked} attested path(s) across {envelopes} envelope(s) checked)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
