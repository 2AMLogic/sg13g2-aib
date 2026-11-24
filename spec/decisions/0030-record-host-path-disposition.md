# DR-0030: committed records carry no host home-directory path; the 81 that do are left as they are

**Status**: **proposed**. Not ratified; ratification follows
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge.
**Rows**: none. **Changes no value**: no Target, Fallback or Stretch cell and no recorded
result moves.

## Context

`klt sim` and `klt pex` write the client's ngspice binary into the report's `environment`
(`client_ngspice_binary`, `ngspice_binary`), as an absolute path into the home directory of
whoever ran it. This repository is public, so those records publish the machine and user name
that produced them, and ratification review has stopped on it more than once. The one scrub
that existed was a per-runner `sed` for the single field name `ngspice_binary` in one bench;
it missed `client_ngspice_binary`, which is the field in every `sim/` record.

Survey, by value over every string in every committed `.json` and `.json.gz` under
`sim/*/records` and `layout/*/records`, at this PR's base: **81 files** carry a string that
starts `/home/<user>/`, in the families channel-eye, channel-model, clock-path, dc-static,
io-cell-study, mc, redundancy-mux, rx-threshold-study (all `client_ngspice_binary` or
`ngspice_binary`) and `layout/pex` (4 reports, `ngspice_binary`, two lines each). The issue's
count of 16 covered only the files that are plain-text `report.json` (a decompressed copy
beside a `.gz` is a separate file, and most records carry only the `.gz`).
No hostname, S3 key or other username was found in those JSON documents; `s3://` is already
scrubbed to `<bucket>` in the stderr copy. **The survey is bounded to JSON documents.** Free-text
files are out of scope and are not scrubbed or checked: two committed records,
`sim/channel-model/records/20261120T220946Z/klt.stderr` and `.../20261120T230233Z/klt.stderr`,
carry `/home/ubuntu/GitHub/sg13g2-aib/.loom/worktrees/issue-384/sim/build/pdk` and
`/home/ubuntu/share/pdk`, a user name and a Loom worktree path. They are a known exception to
this record's title, left as they are under clause 3; `.cir` files were not surveyed. `sim/mc/records/*/samples.json` holds `/tmp/loom-398/...` scratch paths:
no user name, not a home directory.

## Decision

1. **One shared scrub.** `sim/harness/write_record.py` rewrites, in the record directory it is
   handed and before it reads anything, every string value of `report.json.gz` and
   `rows.json` that matches `^/(home|Users|root)/[^/]+/`, by value over the whole JSON tree.
   An `ngspice` binary becomes `/usr/local/bin/ngspice` (the convention the ESD transient
   scrub used); any other path becomes `<home>/<rest>`. Every family that records through
   `batch_record.sh` inherits it. Three record writers do not go through it and call the same
   module's `--scrub-only` entry point, which scrubs every `.json` and `.json.gz` in the record
   directory and writes nothing else: the `mc` leg of `sim/rx-threshold-study/run_rx_threshold.sh`
   and `layout/pex/run_pex.sh` call it before the record is complete, and the documented
   `sim/mc` campaign flow (`sim/mc/README.md`) lists it as its last step, which is a documented
   step and not enforced by a script. No runner carries its own scrub.
2. **A checker that keeps it so.** `scripts/ci/check_no_host_paths.py`, in the CI `evidence`
   job through `check_local.sh`, fails on any such string in a committed record, naming the
   file and JSON path.
3. **Disposition of the existing records: left byte-identical.** Records are append-only
   evidence (`scripts/ci/check_sim_append_only.py`); rewriting 81 committed files, many of
   them cited by hash from signoff attestations, is a larger step than a path leak that the
   operator can weigh separately. The 81 files are listed in
   `scripts/ci/host_path_baseline.json` and pass the checker. The list may only shrink: a
   baseline entry that is missing or no longer carries a host path fails the check. Anything
   not in it fails.
4. **`/tmp/` scratch paths are accepted** (the 8 `samples.json` entries) and are not matched.
5. **Not decided here**: whether to rewrite the 81 files and re-attest. That is a separate,
   human-ratified step; if taken, it supersedes clause 3 and empties the baseline.
6. **Not a tool fix**: `klt` could emit portable paths itself; that is a generic friction
   issue for `2AMLogic/klayout-tools`, not a design change here.

## Consequences

New records from `batch_record.sh`, the rx-threshold `mc` leg and `layout/pex` are clean by
construction; a hand-assembled `sim/mc` record is clean only if its operator runs the
documented `--scrub-only` step, and the CI checker fails the record if they do not. `klt.stderr`
and other free-text files are not covered (Context). The history keeps its leaks until the operator decides
otherwise. The ESD transient runner's `sed` (PR #374, not on `main` at this PR's base) becomes
redundant and should be dropped at that PR's rebase; its two new records need one
`write_record.py REC --scrub-only` pass before they are committed, since they are new files and
the checker would fail them.
