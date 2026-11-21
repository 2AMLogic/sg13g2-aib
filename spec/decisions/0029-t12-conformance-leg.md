# DR-0029: T-12 is covered by a channel-model conformance record and leaves the item 5 gap set

**Status**: **proposed**. Not ratified; ratification follows
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge.
**Rows**: T-12 (and, as consumers of the netlist, T-01, T-09, T-15, T-16, T-18, T-26).
**Supersedes**: only the standing-gap disposition of T-12 recorded in the manifest's
T-12 `gap` string, `sim/README.md` ("T-12 is an input definition") and DR-0028 §3
("T-12 (standing, no tracker open)"). **Changes no value**: no Target, Fallback or Stretch
cell and no verification cell in `spec/target-spec.md` moves, and the channel values of
[`channel-model.md`](../channel-model.md) are unchanged.

## Context

T-12 names `SIM` over PVT-FULL plus channel R/C ±20 % (DR-0005). The repo's position was
that citing the channel model as evidence of itself is circular, so T-12 stayed a declared
gap with no tracker, which by the grader's rule keeps item 5 / analog `unmet` whatever else
closes (DR-0028 says so in terms). The spread campaign (closed #193) cannot be cited for T-12:
coverage is derived from `spec_row` tags and none of its measurements carries T-12.

One thing about the model is measurable and was not checked: that the committed netlist the
six dependent rows include implements the declared table. A wrong default, a broken `kr`/`kc`
scaling or a dropped far-end load would move all six rows with no check noticing.

## Decision

1. **T-12's `SIM` leg is the conformance check** in `sim/channel-model/` (#384): the netlist
   against the table, at the three declared lengths and five (kr, kc) points, over PVT-FULL.
   Record: `sim/channel-model/records/20261121T000100Z/` (675 units, 4050 graded
   measurements, all pass, `klt` exit 0): the R, C and L ratios on the swept instances and
   again on instances that use the subcircuit's own defaults. It supersedes two records, both
   kept as provenance: `records/20261120T220946Z/` (2025 graded measurements; review found the L
   read blind to a single-section error, the C ratio inverted, and the defaults masked by the
   sweep) and `records/20261120T230233Z/` (4050; review found its L ratio still carried the
   ladder's R-C bias, so an L error was amplified at 5 mm and R/C edits moved the L verdict).
   The L ratio now adds that bias back, so the grid was re-run.
2. **Tolerance.** ±1 % on each DUT/reference ratio. It is a numerical-agreement tolerance
   and a property of the check, not a spec bound.
3. **Manifest.** `signoff/block-manifest.json` cites the record under `evidence."5.analog"` with
   rows `[T-12]` and drops T-12's `gap` from `spec_rows."5.analog"` (the row stays declared,
   now covered). Item 5 / analog then declares 18 rows, 14 covered and four gaps (T-20, T-21,
   T-25, T-29) and still reads `unmet` / `partial_coverage`.
4. **Item 7 / analog is unchanged in effect.** `spec_rows."7.analog"` keeps T-12 as a gap
   because no extracted T-12 measurement exists; its text is updated to say so and no longer
   calls it a standing gap with no tracker.
5. **The spread record stays supporting evidence** for the six dependent rows and is not
   cited for T-12.

## What this is not

- **Not a relaxation.** No value or verification cell changes; no result is made to pass by
  moving a bound.
- **Not validation of the table.** The record verifies the netlist against the declared
  table. It says nothing about silicon or an interposer (the row's own "CH only" note).
- **Not a section-count check.** A same-total change of the section count is below the
  tolerance (`sim/channel-model/README.md`, "Boundary").
- **Not self-ratifying.** This record is proposed; the manifest change stands or falls with
  its ratification.
- It does **not** make item 5 / analog `met`: T-20, T-21, T-25 and T-29 remain.

## Alternatives rejected

- **Cite the spread record for T-12.** Rejected: no measurement in it carries a T-12 tag, and
  the pinned grader (0.9.0) grades that citation `invalid_evidence` / `partial_coverage`.
- **Keep T-12 a permanent standing gap.** Rejected: item 5 / analog could then never read
  `met`, for no work that remains to be done.
- **Drop the `SIM` token from T-12's cell**, as DR-0026/DR-0028 did. Rejected: unlike those
  rows a measurable exists, so the leg is gradable rather than boundless.

## Consequences

- `signoff/block-manifest.signoff.json` is re-rendered with the pinned grader
  (`signoff/KLT_VERSION`, 0.9.0).
- `measurements/row-evidence.json` gains a T-12 entry for the cited record.
- The T-12 paragraphs of `README.md`, `ROADMAP.md`, `signoff/README.md`, `sim/README.md`
  and `layout/pex/README.md` are updated; historical mentions stand as provenance.
- No existing record is edited and no other simulation is re-run.
