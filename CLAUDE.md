# sg13g2-aib — agent instructions

Open-source canary block: an AIB Gen1-class die-to-die parallel I/O channel
on IHP SG13G2, a 130 nm SiGe BiCMOS open PDK, designed and verified by AI
agents. **Mixed-signal** — custom I/O cells plus a synthesized data path —
so both flows apply.

- **PDK**: IHP SG13G2 (open PDK, IHP-GmbH/IHP-Open-PDK), CMOS devices only.
  Analog: xschem + ngspice. Digital: cocotb + Icarus, Yosys, OpenROAD.
  Layout, DRC, and LVS through klayout-tools (`klt`) in both cases. The
  sibling SG13G2 canaries have brought up the device models and the starter
  DRC/LVS deck; start from their setup.
- **There is no die-to-die assembly to test on, and that is the risk.** A
  shuttle die is normally packaged by wire bond, not on an interposer, so the channel
  this block is designed for does not exist in any test this repo can run.
  Every channel claim therefore rests on a declared channel model, and the
  testable silicon is a loopback (on-die, or through bond pads that load the
  I/O far more than the real channel would). Keep the two apart: the spec
  says which results hold for the modeled die-to-die channel and which for
  the test configuration. The second risk is the array — skew across a
  column of I/O cells, and a dense custom I/O cell with reduced ESD. Expect
  the tools to be weakest at the I/O column and file accordingly.
- **Scope discipline.** This repo has no `consumes:` edge. Do not design a
  DLL or duty-cycle corrector here; specify what forwarded-clock alignment
  needs (delay range, resolution, lock time, jitter) and compare it against
  the SG13G2 DLL canary opened alongside this repo, by name and commit. A gap
  goes into the spec and is filed on the sibling (see `2am/REUSE.md`).
- **The specification is a reference, not a claim.** Design against the
  public AIB specification and cite its sections; copy no text or figures
  from it. Do not claim conformance; "AIB Gen1-class" names the
  architecture.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. PVT corners
  on every recorded analog result; recorded results are append-only evidence.
  Energy per bit is simulated and labelled so.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.
- **1 Gb/s per wire is the target.** 500 Mb/s is the fallback and 2 Gb/s a
  stretch. Do not let 2 Gb/s requirements drive architecture before 1 Gb/s
  closes.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.

Work is coordinated through `loom:` labels on issues and pull requests, and the same roles run either under `loom-daemon` or by hand in an attended session — daemon mode is optional. Create the labels once with `.loom/scripts/sync-labels.sh` (an install ships `.github/labels.yml` but does not create the labels on the forge). A pull request ready for review carries `loom:review-requested`; Judge reviews it and applies `loom:pr` (approved) or `loom:changes-requested`; Doctor fixes a `loom:changes-requested` pull request and returns it to `loom:review-requested`. Only a `loom:pr` pull request gets merged, and always via this repo's merge script (`.loom/scripts/merge-pr.sh`) — never a raw forge merge command such as `gh pr merge`. Full state machine: `.loom/docs/label-state-machine.md`.
<!-- END LOOM ORCHESTRATION -->
