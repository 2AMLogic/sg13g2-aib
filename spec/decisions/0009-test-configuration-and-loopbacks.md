# DR-0009: test configuration and the two loopbacks (open question 2)

**Status**: accepted. **Rows**: T-29 and the scope tag of every row.

## The question

How far does a wire-bond loopback distort results relative to the modeled channel, and
is an on-die loopback a better test of the I/O cell?

## Evidence

- The shuttle die is normally wire-bonded (CLAUDE.md). The PDK has no bond-pad model
  (`sg13g2_bondpad` is an empty placeholder, PDK `v0.3.0`) and the repo has no package
  data, so any wire-bond figure is a declared assumption.
- First-order estimate with the declared inputs in `test-configuration.md` (4 nH loop,
  0.5 pF per pin): resonance near 5 GHz and Q of about 2 against a 40-80 Ω driver, which
  is a second-order overshoot of tens of percent, against a 0.25 × VOS limit (T-09). The
  per-pin load is five times the T-24 target. Both are `ANALYSIS`, labeled
  assumption-driven, and replaced by `SIM` once a package assumption exists.
- The modeled channel (`CH-3MM-RC`) is a 50 Ω-class RC line with 30 ps flight time.

## Answer

A wire-bond loopback is a *different, much worse* channel: higher capacitance at both
pins, a series inductance that rings, and bond-pad ESD that is not the die-to-die
cell's. Its results are labeled TC (L2), are not quoted as channel results, and T-09
is expected to fail there. An on-die loopback with a route emulating the channel's R
and C and the real cells at both ends is the better test of the I/O cell, and is the
configuration the spec relies on for TC claims about the cell (T-13, T-14, T-19,
T-20). It cannot show an analog eye (no pin to probe), so its observable is an error
count against sampling phase, supply and temperature.

## Decision

Define L1 (on-die) and L2 (wire-bond) as in `test-configuration.md`, with the
coverage matrix there. L1 is the primary silicon test; L2 exists to get the loopback
off the die for bring-up and is reported separately.

## Alternatives rejected

- **Wire-bond loopback as the only test.** It would test the package, not the cell, and
  would force T-09 to be relaxed to pass; barred.
- **An on-die loopback with no emulation of the channel** (a zero-length strap). It
  hides the line's R and C from the driver and receiver.
- **Probing the on-die eye.** No on-die probe cell is in scope; the shmoo gives T-20.

## Limits

L1's route reproduces the model's R and C by extraction check; its inductance is not
reproduced. The L2 numbers are assumptions until package data exists.
