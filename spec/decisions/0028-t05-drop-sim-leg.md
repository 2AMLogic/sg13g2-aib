# DR-0028: T-05 carries no `SIM` leg and leaves the analog row set

**Status**: **proposed**. Not ratified; ratification follows
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge.
**Rows**: T-05 (and, as consumers of the reported numbers, T-13 and T-20).
**Supersedes**: only the standing-gap disposition at the end of
[DR-0023](0023-redundancy-mux-sim-placement.md) §5 ("T-05 stays a declared gap
in the manifest … is #216's question, not this record's"). DR-0023's declared
placement (§1–§4) and its T-20/T-13 attribution stand. **Changes no value**: no
Target, Fallback or Stretch cell of any row moves, and no bound of T-13 or T-20
moves.

## Context

DR-0023 declared where the shift-redundancy remap sits and what stands in for
it, and the PVT-FULL record it enabled
(`sim/redundancy-mux/records/20261113T160050Z/`, 45 corners) measured the
remap's added load and delay. No measurement in that record carries a limit,
because T-05 states no bound for its `SIM` leg and DR-0023 invented none — the
terms are reported into the rows that do carry numbers. T-05 therefore sat in
the declared analog row set as a standing gap for a reason no verification work
can clear: the leg is ungradable because **no bound exists**, not because a
testbench or tool is missing (#216's question for T-02 and T-04, repeated for
T-05).

The operator ruled on 2026-11-18 (`/fleet:decide` round 20261118-r16, option a)
that T-05's standalone `SIM` leg is removed through a decision record, on the
same reasoning the operator applied to T-02 and T-04 in
[DR-0026](0026-t02-t04-drop-sim-leg.md): it follows the precedent and removes a
gap that no measurement can close, while preserving the measurements and naming
the rows that consume them. This record writes that ruling down; the ruling
itself is not ratified until this record is.

## Decision

1. **T-05 carries no `SIM` leg.** Its verification cell in
   `spec/target-spec.md` names `RTL` — the mux function, all single-fault
   positions, 20 cases per direction, 40 total (DR-0016) — and drops the
   standalone `SIM` token. The numeric requirements (Target, Fallback, Stretch)
   and the CH/TC scope are unchanged, and the cell keeps pointing readers at
   the reported evidence and its consumers (below).
2. **Where the measured load and delay are reported.** Under DR-0023's
   placement, the **common added delay** (data relative to the forwarded clock,
   since every data lane gains the remap stage and the forwarded-clock lane
   does not) is a reported input to **T-20**, and the **select-dependent delay**
   between the mux's two inputs (lane-to-lane skew in a repaired direction) is
   a reported input to **T-13**. The 20261113T160050Z record is not deleted,
   not re-graded and not cited as an envelope for T-05: it stays reported
   evidence, and the existing bounds of T-13 and T-20 are unchanged on its
   account. If [PR #249](https://github.com/2AMLogic/sg13g2-aib/pull/249)
   (remap ahead of the TX input register) lands first, the attribution is
   reconciled with the then-ratified placement by a superseding record.
3. **The analog row set drops T-05.** The derivation rule in `sim/README.md`
   ("every row with a plain `SIM` leg") now yields 18 rows rather than 19
   mechanically, and `signoff/block-manifest.json` removes T-05 from
   `spec_rows."5.analog"` and from `spec_rows."7.analog"`, which carries it
   forward. Item 5 / analog then declares 18 rows, 13 covered and five gaps —
   T-12 (standing, no tracker open), T-20, T-21, T-25 and T-29 (pending) — and
   reads `unmet` / `partial_coverage` as before; T-12 is the remaining standing
   gap. Item 7 / analog then declares 18 gaps.
4. **No number is invented.** If a future revision of the specification, or a
   consumer of this block, states a bound for the remap's added load or delay,
   T-05 regains a `SIM` leg by a new decision record naming it (DR-0001), and
   the recorded 20261113T160050Z measurements can be graded against that bound
   without re-running the grid.

## What this is not

- It is **not** a relaxation made to pass: no Target, Fallback or Stretch value
  changes, the only edit to a ratified cell is the verification token, and no
  bound of T-13 or T-20 moves. The measurements are not deleted; the record and
  the bench that produced it (whose measurements carry `spec_row: "T-05"` tags)
  are append-only history, and the `t05_*` measurement names stay.
- It does **not** make item 5 / analog reachable as `met`: T-12 and the four
  pending gaps keep the item `unmet`. This removes one standing gap and no
  other.
- It does **not** re-open the common-term finding: the record shows the
  measured common delay exceeds T-20's whole 0.10 UI target at 30 of 45
  corners, filed as #232 with no bound moved. That is unresolved work on T-20's
  budget, not on T-05's leg.
- It does **not** edit DR-0023 or the record it enabled. DR-0023 §5's last two
  sentences are superseded here and remain there as provenance.

## Alternatives rejected

- **Keep T-05 a permanent standing gap** (DR-0023's disposition). Rejected by
  the operator on the same ground as T-02/T-04: `unmet` would read as
  outstanding work when none exists.
- **Give T-05 a bound of its own so the row could be cited as covered.**
  DR-0023 rejected it: a new ratified number carved out of the T-13 and T-20
  allocations, which #136 and #177 have not closed.
- **Delete the row from the manifest only.** Rejected (as in DR-0026): the
  derivation rule would stop being mechanical. Removing the `SIM` token from
  the spec cell makes the removal follow from the rule.
- **Wait for PR #249 before writing this record.** The ruling covers the
  DR-0023 placement the grid was measured under; #249 is a separate spec change
  whose record, if it lands, supersedes this one's attribution with its own.

## Consequences

- `signoff/block-manifest.signoff.json` is regenerated by the pinned grader
  (`signoff/KLT_VERSION`); `declared_gaps` shortens by T-05 in both items;
  `uncovered_rows` and `failed_rows` stay `[]`; item 5 / analog stays `unmet`
  while the remaining gaps stand.
- `measurements/row-evidence.json`'s T-05 note stops saying the analog leg "is
  not measured" — false since 20261113T160050Z — and names the reported
  evidence and its consumers; `measurements/characterization-report.md` and
  `signoff/attest/item8.json` are regenerated by their generator and the
  printed item 8 hash is re-cited in the manifest.
- The gap prose in `sim/README.md`, `signoff/README.md`,
  `layout/pex/README.md` and `ROADMAP.md` reflects the 18-row / five-gap
  counts and retires the open-tracker wording for T-05; the historical
  mentions (DR-0023/0025/0026 prose, WORK_LOG, the record's own README) stand
  as provenance.
- No record under `sim/` is edited and no simulation is re-run.
