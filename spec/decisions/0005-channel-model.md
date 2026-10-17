# DR-0005: the channel model

**Status**: accepted. **Rows**: T-12, T-09, T-15, T-16, T-18, T-24, T-26.

## Context

AIB 1.2 has no trace model (its Table 17 "Trace" column is an eye-width budget
only) and the interposer is out of scope here. Every CH claim needs one declared
model that all simulations include. See [`../channel-model.md`](../channel-model.md).

## Decision

A 3 mm distributed RLC line (ten pi-sections), R 5.5 Ω/mm, C 0.20 pF/mm,
L 0.5 nH/mm, far-end load 0.1 pF, with 1 mm and 5 mm variants and ±20 % R and C
spread corners. R is anchored in the PDK (TopMetal2 sheet resistance, a 2 µm
line). C, L and the far-end load are **declared assumptions**, labeled as such.
The model file is committed (`spec/channel/channel_rc.cir`).

## Alternatives rejected

- **A lumped RC (no L).** The 30 ps flight time is small against a 100-300 ps edge
  but the inductance sets overshoot at the unterminated far end (T-09), so L stays.
- **A vendor interposer or silicon-bridge model.** None is available to this repo,
  and adopting one without a source would be an invented citation. A vendor model
  can supersede this one through a new record.
- **A lossless transmission line.** With 16.5 Ω of series resistance at 3 mm and
  a 50 Ω impedance, resistive loss is not negligible; a lossless line would
  flatter the eye.
- **No crosstalk model.** Accepted for this version (the per-mm C is meant to
  include a quiet neighbor); crosstalk and simultaneous-switching noise are a known
  omission and are listed in the channel-model limits, not hidden.

## Consequences

If C, L or the load are wrong, CH rows move. The three lengths and the spread
corners bound the sensitivity; they do not remove the assumption.
