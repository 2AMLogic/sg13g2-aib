# DR-0019: per-draw skew definition for the "14 sigma peak-to-peak" rows

**Status**: proposed; ratified by the merge of the pull request that carries it
(DR-0001, issue #136).
**Rows**: T-13, T-14, T-15, T-16 (and T-19 when it lands, #138). **Amends**: nothing. No spec
row or limit changes.

## Context

The skew rows of `spec/target-spec.md` are **STAT** (DR-0013) and their bound is read at
"14 sigma peak-to-peak". The spec does not say how one Monte Carlo draw yields a skew number or
how a peak-to-peak line maps to a `target_sigma` in `klt yield`. `sim/mc/README.md` has carried
a reading ("Assumptions for ratification") since the T-15/T-16 records (`415a6f2`); this record
ratifies it, so T-13/T-14 and T-15/T-16 use one definition.

## Decision

- **Per draw**, the skew is the **signed** difference of the mid-rail (50 %) crossing times of two
  edges in one transient: lane B minus lane A for the data-to-data rows (A rises, the complement
  lane B falls, launched together); for the data-to-clock rows, the data-to-clock delay minus
  the nominal centre alignment (0.5 UI).
- **Limits** are +-bound (T-13 +-0.04 UI, T-14 +-0.02 UI; T-15/T-16 as recorded), applied to the
  signed value.
- **Tail**: `target_sigma` 7 on each side, so the two-sided span is 14 sigma peak-to-peak. A row
  passes the gate when the `klt yield` lower confidence bound on sigma-to-spec is at least 7.
- **Population**: the 45-corner PVT-FULL grid is pooled, as for T-10 (`klt yield` reports a
  worst-case envelope, not a distribution anyone sampled). Per-corner readings are not part of
  the verdict.

## Rejected

- **Absolute value per draw**: hides the sign (a systematic offset and a symmetric spread look
  alike) and halves the tail the row names.
- **A single 14 sigma one-sided line**: it would ask 14 sigma of one side for a quantity whose
  limit is two-sided; 7 + 7 keeps each limit at the sigma `target_sigma` carries.

## Consequences

- T-13 and T-14 are measured with this definition (`sim/mc/records/*-t13`, `*-t14`).
- T-15 and T-16 were recorded under the same definition and need no re-run.
- If the PO reads the line differently, the DR changes first, then the requests, and the
  affected rows re-run in a separate issue; no recorded result is edited.
