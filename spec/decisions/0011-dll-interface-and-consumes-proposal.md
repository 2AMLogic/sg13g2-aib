# DR-0011: DLL interface and the consumes proposal

**Status**: accepted. **Rows**: T-17, T-20, T-21.

## Context

CLAUDE.md: no DLL or duty-cycle corrector is designed here; specify what alignment
needs and compare it with the SG13G2 DLL canary by name and commit. AIB 1.2 treats
both blocks as optional (§2.1.6.6, §2.1.6.7) and runs calibration as if present
(§3.2.3).

## Decision

The requirement is the table in `dll-interface.md`, compared against
`2AMLogic/sg13g2-dll` at `da166a6`. The comparison is draft-versus-draft: the canary
holds a README table only. The findings are gaps G1-G5; they are filed as
`2AMLogic/sg13g2-dll#10`. The `consumes` edge is proposed, not made, and is conditional
on G1 and G2 closing in the sibling's ratified spec. Editing the manifest is an operator
decision outside this issue.

Derived values with no AIB 1.2 source (step ≤ 1/8 UI, placement error ≤ 0.0625 UI, lock
time ≤ 10 µs, jitter ≤ 0.03 UI peak-to-peak) come from the timing budget (DR-0006) and
from lock time not being on the data path; they are this repo's, not AIB's.

## Alternatives rejected

- **Designing a small DLL in this repo.** Scope discipline; the sibling is the candidate.
- **Proposing the edge now.** The target rows do not fit (G1, G2); recording a
  dependency the budget cannot close on would hide the gap.
- **Specifying only what the sibling already offers.** That would make the spec
  fit the block instead of the channel.
