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
