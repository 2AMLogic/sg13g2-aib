# DR-0015: local cocotb runner instead of the gf180-polysynth one

**Status**: accepted. **Rows**: T-05 (`RTL` verification).

## Context

The reuse rule prefers adopting a sibling runner by pinned reference.
`2AMLogic/gf180-polysynth` @ `010efac225b6173105bfb4a13dcbf1b94121ec6f`,
`tb/run_tb.py` (sha256 `f0ac9323555b56389f9ac3a86eea1551395dc3431ffa73a1981d4c12c2124758`)
was reviewed. It hard-codes `SOURCES`, `TOPLEVEL`, `test_module`, a design
parameter (`--nv`) and a `REFERENCE` path inside `main()`, none of which can be
overridden without editing the file, so it cannot be vendored byte-identical.

## Decision

`verification/run_tb.py` is a short local runner built on the same
`cocotb_tools.runner` calls. It keeps the polysynth exit contract exactly:
0 all passed, 1 the suite ran and a test failed, 2 the suite did not run. The
polysynth file is the origin of that contract and is cited here, not vendored,
so `reuse.lock.json` has no new entry.

## Alternatives rejected

- **Vendor verbatim**: would run the wrong design.
- **Vendor and edit**: breaks the sha256 pin the lock file exists to check.

## Consequence

Negative controls (`--define INJECT_BUG_*`) must require exit 1 exactly.

## Amendment, 2026-11-13: the bench is named by a request file, not by flags

Appended after issue #217; the decision above is unchanged — `verification/run_tb.py`
is still a short local runner on `cocotb_tools.runner`, and a negative control must
still require exit 1 exactly. Only how a run is named changed.

The runner no longer carries its own copy of the bench definitions. It takes one
`klt functional-verification` request path (default
`verification/klt/shift_redundancy.json`, so the item 9 cold start
`python3 verification/run_tb.py` is unchanged) and reads the sources, top, test
module, parameters, defines, timescale and seed from it. The `--bench`, `--param`
and `--define` flags are gone, so the Consequence line above now reads: a negative
control is a request whose `options.defines` carries the `INJECT_BUG_*` /
`INJECT_*` define — `verification/klt/neg_shift_edge.json` and
`verification/klt/neg_extra_stage.json` — and `scripts/ci/check_local.sh` requires
exit 1 exactly from each.

This is what the local runner and the item 5 digital envelopes now share: one
definition per run, the file the evidence cites. A request the runner cannot
honour PDK-free (`options.sdf`, or an unresolved `@PDK_ROOT@`-style placeholder)
is refused with exit 2 — the suite did not run — and stays with
`verification/klt/run_evidence.py`.
