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
