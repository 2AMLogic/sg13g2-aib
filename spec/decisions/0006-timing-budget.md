# DR-0006: timing budget and capture

**Status**: accepted. **Rows**: T-13 to T-21.

## Context

The issue asks for a clock-to-data skew budget across the channel, setup/hold at the
receiver and the DDR capture window. AIB 1.2 gives skew (§2.1.3.3 Table 7: data-to-data
0.04 UI near-side output and 0.06 UI far-side input; data-to-clock 0.02 UI and
0.03 UI), duty-cycle distortion (§2.1.6.5 Table 8) and an eye mask (§4.1 Table 17:
0.56 UI near end, 0.1 UI for the trace, 0.4 UI far end, ±90 mV). It does not
define a receiver capture aperture.

## Decision

Adopt the AIB 1.2 skew, duty-cycle and eye numbers as the target, in UI, and add
the rows AIB 1.2 does not give: a receiver capture aperture (T-19, 0.15 UI) and a
sampling-margin row (T-20, ≥ 0.10 UI) closed by the allocation in
`target-spec.md` ("Timing budget"):
0.40 − 0.15 − 0.03 − 0.0625 − 0.05 = 0.1075 UI, which is 7.5 ps over the target
margin at 1 Gb/s. The allocation is a proposal whose lines are each a verified row;
it is the thing T-20's analysis re-derives from results, not an independent claim.

Skew values are measured at the near-side output and far-side input as AIB 1.2
specifies, from the centre of the eye (§4.1, bullet list). They are statistical
(`SIM-MC`) because mismatch across a 20-wire column sets them.

## Alternatives rejected

- **Relaxing skew to what is easy to close.** The values are AIB 1.2's; the
  fallback column relaxes them explicitly and labels the row as not AIB-class.
  Relaxing after ratification is barred (CLAUDE.md).
- **No capture-aperture row.** The eye at the pin is not enough: a receiver that
  needs 0.3 UI of window would pass the eye mask and fail capture. The aperture row
  makes that visible.
- **A larger margin target (0.15 UI).** It does not close with the AIB 1.2 far-end
  eye (0.40 UI) and the allocations above; it would force a different aperture.

## Consequences

The budget leaves 7.5 ps of slack at 1 Gb/s. The sibling DLL's draft
spacing error alone consumes about 40 ps of it (dll-interface.md, D-5): the budget
does not close with the sibling's current draft, and the finding is filed there.
