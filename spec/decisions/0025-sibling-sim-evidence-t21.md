# DR-0025: Recorded sibling results are the T-21 `SIM` evidence

**Status**: **proposed**. Not ratified; ratification follows
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge.
**Rows**: T-21 is *named*; **it is not changed**. **Amends**: nothing. This record
states what counts as evidence for T-21's `SIM` half. It does not edit the T-21
row, relax any of its five numbers, add a DLL model, or close the gap.

## Context

`spec/target-spec.md` T-21 (forwarded-clock alignment) carries two evidence
halves: a `SIM` of the interface contract in
[`dll-interface.md`](../dll-interface.md), and "compared against the sibling".
[DR-0020](0020-dll-recomparison-t21.md) delivered the second half, and states that
the `SIM` half **remains a declared gap**. It also rejects a behavioural DLL model
in `sim/` as a way to produce it, because this repo does not design a DLL or a
duty-cycle corrector (CLAUDE.md scope discipline;
[DR-0011](0011-dll-interface-and-consumes-proposal.md)).

That left an unanswered question: what may stand as the `SIM` evidence for a row
whose device under test is not in this repo. The operator-level ruling (issue #195,
2026-11-18, option (a)) was to admit the sibling's results. This record writes that
rule down; the ruling itself is not ratified until this record is.

## Decision

1. **Producer.** The `SIM` evidence for T-21 is produced in `2AMLogic/sg13g2-dll`,
   where the DLL is designed. Nothing in this repo simulates a DLL.
2. **Admissible evidence.** A result is admissible only if it is *recorded and
   graded* in the sibling (a committed result with a pass/fail against the sibling's
   own row, not a spec number, a stand-in bench or a plan) and is **cited here by
   repo and commit**. A citation without a commit is not evidence.
3. **Per-number coverage.** The contract has five numbers in
   [`dll-interface.md`](../dll-interface.md): step ≤ 1/8 UI, worst-case placement
   error ≤ 0.0625 UI, range ≥ one forwarded-clock period, lock ≤ 10 µs, and
   DLL-added jitter ≤ 0.03 UI p-p. Each needs its own recorded, graded sibling
   result, at this repo's target and over PVT-FULL, before T-21's `SIM` half counts
   as covered. A sibling result at a different target does not cover a number here
   (DR-0020 finds the sibling missing three of the five at this repo's target).
4. **Gap stays declared.** At `2AMLogic/sg13g2-dll` `381d989` (the pin in DR-0020)
   `sim/bench-rows.json` still says `"dut": "standin"` and no spec row has a
   recorded, graded result. So **no number is covered today and T-21 stays a
   declared gap**. Issue #195 remains open as the gap tracker and the manifest gap
   entry keeps naming it. Nothing here lets T-21 read as met.
5. **Unchanged.** The T-21 row, its verification column and its five numbers are
   not edited. The verification-column rewrite (making the sibling comparison
   satisfy the `SIM` half) was considered and not chosen.

## Costs

- **T-21 stays an open gap** until the sibling records results, on a schedule this
  repo does not control.
- **A cross-repo evidence dependency.** This repo now relies on another repo's
  results for a ratified row while the DR-0011 `consumes` edge is still only
  *proposed*. The dependency sits beside that edge and does not replace it: if the
  edge is made, the evidence rule here is the first thing it must be reconciled
  with; if it is not, T-21 may never reach covered from this repo alone.
- **Staleness.** A cited result describes the sibling at one commit. A later
  sibling change reopens the question, as DR-0014 and DR-0020 found for the
  comparison.

## What this record does not do

- Ratify itself or the 2026-11-18 ruling.
- Design, model or simulate a DLL here, or relax any T-21 number.
- Decide how the sign-off manifest accounts for a row with no gradable leg (#216),
  or land `spec_rows."5.analog"` (#42).
