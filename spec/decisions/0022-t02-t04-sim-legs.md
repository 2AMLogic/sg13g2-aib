# DR-0022: the T-02 and T-04 `SIM` legs — a pointer and a report-only leg

**Status**: accepted. **Rows**: T-02, T-04. **Amended by**: this record's own
Amendment, 2026-11-13 (where a wrongly cited T-02 lands; the Decision is unchanged).

## Context

Both rows named a `SIM` verification leg that no number could grade. T-02 read
"`RTL` for the format, `SIM` for the timing" and T-04 read "`RTL`, `SIM` (clk/clkb
crossing at RX over PVT-FULL)", and neither row's Target, Fallback or Stretch cell
states a value either leg could be measured against. The measurements exist: the
45-corner PVT-FULL record `sim/clock-path/records/20261113T095936Z/` carries T-02 with
180 measurements and T-04 with 225, both `verdict: reported`, `binding: null`, because
the record had no bound to grade them with.

An ungradable verification leg is a spec defect, not a simulation gap. This record
decides what each leg is. It introduces no new number, and no row's Target, Fallback or
Stretch value changes. Filed as #191, a declared gap under #42 (T1 item 5 / analog).

## What AIB 1.2 requires of the clk/clkb crossing

Read directly from the specification (`AIB_Specification 1_2.pdf`, CHIPS Alliance
`chipsalliance/AIB-specification`) on 2026-11-13. Cited by section only; no text or
figure is reproduced here.

- **§2.1.6.3 states no numeric requirement of any kind.** Its requirements are
  structural: a channel forwards its transmit clock to the far side, that clock is
  quasi-differential while it crosses between chiplets, and the receiving side makes it
  available to the MAC after conversion back to single-ended. Figures 20 and 21 are
  block diagrams of the transmit and receive arrangement; they carry no levels. In
  particular the section says nothing about the voltage at which clk and clkb cross.
- **The specification defines "quasi-differential" as a pair of digital signals** of
  opposing polarity (§Terminology), and distinguishes it from an analog differential
  signal. A crossing-point requirement is an analog-differential notion; it does not
  apply to a signal the specification defines this way. This is *why* no number is
  stated, not merely that none is.
- **§4.1 Table 17 grades each wire individually**, not the pair: its parameters are the
  eye height VEH, the HI and LO output levels VHI / VLO, the output swing VOSmin /
  VOSmax, and the eye width tEW — which has its own Forwarded Clock entry. No parameter
  in it refers to a crossing point. §4.2 Table 18 adds overshoot and undershoot, also
  per wire.
- A whole-document search for "cross" returns four occurrences, none of which concerns a
  crossing level.

**Conclusion: AIB 1.2 states no clk/clkb crossing requirement, numeric or otherwise.**
T-04's `SIM` leg therefore had nothing to be graded against, and never did.

## Decision

- **T-02's `SIM` leg is a pointer, not a bound of its own.** The DDR exchange *format*
  is verified by `RTL`, as it already is for T1 item 6 (`signoff/item6/digital-spec.json`
  classes T-02 `rtl-format`). The DDR *timing* is graded where the numbers already live:
  T-16 (data-to-clock skew at the RX input), T-19 (receiver capture aperture) and T-20
  (the sampling-margin budget those feed). The clock-path `t02_*` edge-separation
  measurements are reported inputs to those rows, never a grade of T-02.
- **T-04's `SIM` leg is report-only by design.** The row's requirement is the
  arrangement — one forwarded clock per direction, quasi-differential, both wires driven
  and received, converted to single-ended at the receiver — and that is verified by
  `RTL`. The crossing-level measurements stay in the record as reported evidence of the
  clock path's health, and are not a graded claim. Nothing goes unverified by this: every
  consequence a displaced crossing has on the channel is already a graded row —
  duty-cycle distortion at the TX output by T-17, half-period off-centring at the RX
  input by T-16, the per-wire levels by T-06, overshoot by T-09, and the far-end eye by
  T-18.
- **Neither row is a covered row, and neither is silently dropped.** Both are declared
  gaps for as long as their `SIM` leg carries no bound, recorded in
  `signoff/block-manifest.json` under `spec_rows."5.analog"` with a gap string naming
  this record. That list is landed by #42 (PR #199), which already declares both rows as
  gaps tracked to #191; this record does not edit the manifest, because
  `spec_rows."5.analog"` does not exist on `main` at the time of writing.

## How the grader accounts for these rows

Verified 2026-11-13 against the pinned grader (`signoff/KLT_VERSION` = 0.9.0, run via
`uvx --from "klayout-tools==0.9.0" klt signoff --manifest …`) on throwaway copies of
`signoff/block-manifest.json` at `d88b89b`. The committed
`signoff/block-manifest.signoff.json` reproduces byte-identically at that version
(exit 3).

**`klt signoff` never reads `spec/target-spec.md`.** Row accounting is driven entirely by
the manifest's `spec_rows` and the envelopes its `evidence` cites, so rewording a
Verification cell changes no grader output. The one automated consumer of that column is
`scripts/ci/gen_item6_digital.py`, which reads a listed digital row's line only to reject
the tokens `STAT` and `SIM-MC`; it has no notion of an ungraded `SIM` leg. There is no
"ungraded `SIM` row" count anywhere in the toolchain to remove a row from.

What the grader does with a declared row, measured by the probes above:

| how the row is declared in `spec_rows` | where it lands |
|---|---|
| declared, no citation, no `gap` key | `uncovered_rows` |
| declared, cited to the report-only clock-path record | `failed_citations` + `failed_rows` — **superseded, see the Amendment, 2026-11-13**: this holds for a citation to a *non-envelope* file in that record directory, not to its `klt sim` envelope `report.json`, which gives `uncovered_rows` |
| declared with a `gap` string | `declared_gaps`; out of both lists above |

> **Withdrawn — see the Amendment, 2026-11-13.** The paragraph below is kept as
> filed, and its bucket is wrong: cited to the record's `klt sim` envelope
> `report.json`, T-02 lands in `uncovered_rows`, so #191's and PR #199's wording is
> correct. The conclusion it draws is unaffected.

**Correction to #191 as filed.** The issue reports that citing T-02 under the clock-path
envelope "returns `uncovered_rows: ["T-02"]`". It does not: the citation is accepted into
the grading set and then fails, so the row lands in `failed_rows` with the record in
`failed_citations`, while `uncovered_rows` stays empty. The same is true of every file in
that record directory (`record.json`, `rows.json`, `report.json.gz`, `request.json`).
`uncovered_rows: ["T-02"]` is what a row declared with no citation at all returns. The
conclusion the issue draws from it is unaffected and confirmed: a report-only row cannot
be cited into coverage, so a declared gap is its only honest disposition until it has a
bound. Only the bucket it fails into was misnamed. The same wording appears in PR #199's
`signoff/README.md`; correcting it belongs to that PR, not this one.

## Evidence

- `sim/clock-path/records/20261113T095936Z/` — the 45-corner PVT-FULL record, unchanged
  by this decision (records are append-only). T-02: 180 measurements. T-04: 225
  measurements, crossing offset −19.2 mV .. +9.1 mV at the RX **pins** and
  −646.1 mV .. −2.3 mV at the RX **outputs**.
- AIB 1.2 §2.1.6.3 and Figures 20–21; §Terminology; §4.1 Table 17; §4.2 Table 18.

## Alternatives rejected

- **A numeric T-04 bound drawn around the measured ±20 mV at the pins.** A number chosen
  because the data that exists passes it, with no requirement behind it. CLAUDE.md: agents
  do not invent bounds, and the specification states none to adopt.
- **A bound on the RX-*output* crossing.** The −646 mV figure is `aib_rx_data` rise/fall
  asymmetry, not a channel effect; #177 and #190 own it. Bounding it here would duplicate
  them and would attach a receiver-sizing defect to a row about the forwarded-clock
  arrangement.
- **Citing T-02 or T-04 under the passing T-17 clock-path envelope to make them read
  covered.** The grader rejects it (above), and it would be laundering a report-only
  measurement into a claim.
- **Deleting the `SIM` token from both rows and saying nothing more.** The measurements
  are real and worth keeping; the rows would then look verified by `RTL` alone and the
  reader would lose the pointer to where the timing is actually graded.
- **Leaving the rows as they were.** Two permanently ungradable verification legs, which
  is the defect #191 reports.

## Consequences

- No new simulation, and no record under `sim/` is edited.
- `spec/test-configuration.md` is unchanged. Its T-04 row (`CH yes`, `L1 yes`,
  `L2 report`) is not contradicted: the row's requirement is the arrangement, which both
  the channel-model setup and the on-die loopback do verify. The crossing level was never
  a requirement, so no claim in that table rests on an ungraded leg.
- If a future revision of the specification, or a consumer of this block, states a
  crossing requirement, T-04 gets a bound by a new decision record naming it (DR-0001),
  and the 225 measurements already recorded can be graded against it without re-running
  the grid.

## Amendment, 2026-11-13: where a wrongly cited T-02 lands, per citation shape

Appended after #212 reported that the middle row of the "where it lands" table above,
and the "Correction to #191 as filed" paragraph that rests on it, do not reproduce on
the pinned grader. The Decision, Evidence, Alternatives rejected and Consequences
sections are unchanged and no decision is revisited here; what changes is one stated
grader fact.

**What the row above got wrong.** The probes behind it cited `record.json`, `rows.json`,
`report.json.gz` and `request.json` — none of which is a `klt sim` envelope. At
`d88b89b`, the commit this record names, the decompressed envelope
`sim/clock-path/records/20261113T095936Z/report.json` was not in the tree at all; it
arrives with #42 (PR #199). So the row states what the grader does with a citation to a
**non-envelope file** as though it were what the grader does with a citation to the
**record**. Its mechanism is wrong with it: the citation is not "accepted into the
grading set and then fails" — the file is rejected as evidence, before any row is
graded, and the row's report-only status plays no part in that rejection.

**Re-measured 2026-11-13** against the pinned grader (`signoff/KLT_VERSION` = 0.9.0, run
as `uvx --from "klayout-tools==0.9.0" klt signoff --manifest <scratch> --format json`
from the repo root) on throwaway copies of `signoff/block-manifest.json` kept outside the
tree. Every scratch manifest declares `spec_rows."5.analog"` containing `{"id": "T-02"}`
with no `gap` key, and — except for the last row below — cites the file under test in
`evidence."5.analog"` as `{"file": <f>, "rows": ["T-02"]}`. All runs exit 3 and grade
item 5 / analog `unmet`.

| citation shape | commit probed | item `reason` | where T-02 lands |
|---|---|---|---|
| cited to the `klt sim` envelope `report.json` | `0f3bf92` (PR #199 head) | `partial_coverage` | `uncovered_rows: ["T-02"]`, `failed_rows: []`, **no `failed_citations` key**; that citation itself grades `met`; T-02 absent from `row_sources` |
| cited to `record.json`, `rows.json` or `request.json` | `615c357` (`main`) | `unrecognized_envelope` | `failed_rows: ["T-02"]`, `failed_citations: [<the cited file>]`, `uncovered_rows: []` |
| cited to `report.json.gz` | `615c357` (`main`) | `unreadable_evidence` | `failed_rows: ["T-02"]`, `failed_citations: [".../report.json.gz"]`, `uncovered_rows: []` |
| declared, no citation | `615c357` and `0f3bf92` | `partial_coverage` | `uncovered_rows: ["T-02"]`, `failed_rows: []`, no `failed_citations` key |
| declared with a `gap` string | — | — | `declared_gaps`; out of both lists (unchanged from the table above) |

The envelope row can only be probed where `report.json` exists, which today is PR #199's
head; the non-envelope rows ran on `main` at `615c357`, whose record directory holds the
same file set as `d88b89b` (no `report.json`). One trap worth recording: citing the path
`.../report.json` on `main`, where that file does not exist, also returns
`unreadable_evidence` — the same `reason` as a cited `.gz`, so the `reason` string alone
does not tell a missing file from an unreadable one.

**Why `uncovered_rows` is the bucket, and why that agrees with the Decision above.** The
clock-path envelope does tag four measurements — `t02_cf_dr`, `t02_cr_df`, `t02_df_cf`,
`t02_dr_cr` — with `spec_row: "T-02"`, and every one carries `limits: null`. With no
limit there is no verdict to derive, so the grader writes no `row_sources` entry for
T-02 and leaves the row uncovered. T-17's `t17_dcd_c` / `t17_dcd_cb` in the same envelope
do carry limits, and give `row_sources."T-17": "derived"`. A report-only row cited under
its own envelope therefore reads exactly as a row with no citation at all, which is this
record's point: the measurements are present, and they are not a grade.

**"Correction to #191 as filed": withdrawn.** #191's `uncovered_rows: ["T-02"]` is
correct for the citation shape that matters — the record's `klt sim` envelope — and PR
#199's `signoff/README.md` wording is correct for the same reason and needs no change on
this record's account. Nothing in either conclusion moves: a report-only row still cannot
be cited into coverage, and a declared gap is still its only honest disposition until the
row has a bound.

**One caution the original table did not state.** "Citing T-02 or T-04 under the passing
T-17 clock-path envelope to make them read covered — the grader rejects it" (Alternatives
rejected) holds for *that* envelope, as re-measured above. It does not generalise: T-02
appended to the dc-static citation's `rows` at `0f3bf92` returns `uncovered_rows: []` and
`row_sources."T-02": "asserted"`, because that envelope carries no `spec_row` tag the
grader could check the claim against. Citing a row under an envelope that does not
measure it is laundering the tool does not catch. The Alternatives bullet's objection
stands on its own terms — it is honesty, not an enforcement the grader supplies.
