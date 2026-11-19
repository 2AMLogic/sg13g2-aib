# Roadmap

An AIB Gen1-class die-to-die parallel I/O channel on IHP SG13G2, built to a
ratified spec with every claim traced to a recorded result.

Status as of 2026-11-15, `main` @ `432a578`.

The verdict of record is [`signoff/block-manifest.signoff.json`](signoff/block-manifest.signoff.json)
(grader pinned at 0.9.0 in `signoff/KLT_VERSION`); the per-row table is
[`measurements/characterization-report.md`](measurements/characterization-report.md).
[`WORK_PLAN.md`](WORK_PLAN.md) is a generated snapshot of tracker labels; this
file is the reasoned sequence. The checklist in tracking issue #3 predates
the signoff record.

## Where it stands

**T1 signoff record: 16 of 22 rows `met`, 1 `not_applicable`, 5 `unmet`.**

Items 1 to 4 (design sources, layout, DRC, LVS) and 9 to 11 (testbenches,
hygiene, power delivery) read `met` in both partitions, as do `5.digital` and
`7.digital`; `6.digital` is `not_applicable`. The unmet rows are `5.analog`,
`6.analog`, `7.analog`, `8.analog` and `8.digital` (detail in
`signoff/README.md`):

- **Item 5 / analog.** Of 19 declared rows, thirteen are cited and pass over
  PVT-FULL (45 corners): T-01, T-06 to T-09, T-11, T-15 to T-18, T-24, T-26,
  T-28. The six declared gaps keep the item `unmet` / `partial_coverage`:
  T-05 and T-12 by design (DR-0023; how to account for T-05's ungraded SIM
  leg is #333), and T-20, T-21, T-25, T-29 as open work (#194, #195, #196,
  #176). DR-0026 removed T-02 and T-04 from the gap set. Settling #333 alone
  would leave the other five gaps standing.
- **Item 6 / analog.** T-19 passes; T-10, T-15 and T-16 are recorded and fail
  their sigma gates (`sim/mc/README.md`); T-13 and T-14 have no campaign on
  `main` (#136).
- **Item 7 / analog.** The four I/O cells extract cleanly, but nothing is
  graded: `klt pex` cannot yet simulate an sg13g2 extraction
  ([klayout-tools#5491](https://github.com/2AMLogic/klayout-tools/issues/5491)).
  No spec row has been measured post-layout.
- **Item 8, both partitions.** The report follows the records: of 30 rows,
  16 pass, 3 fail (T-10, T-15, T-16) and 11 are `not-yet-measured`.

On the README's maturity ladder: I/O cells simulated across PVT, channel
simulated end to end over CH-3MM-RC (with the ±20 % R/C spread run of #252),
I/O column drawn with DRC and LVS `met`. Post-layout re-verification is the
first rung not reached.

## Now

Can start today; each is one pull request. #270 is in build.

1. **Bring the README status paragraph and ladder position in line with the
   signoff record** (#270). The README still says no PVT or channel
   simulation exists and that I/O-cell LVS mismatches. Done when both
   statements match the committed record.

Recently landed: the per-corner reading of the three failing Monte Carlo
rows (#269, PR #293), the `.gitignore` cleanup (#260, PR #262), the item 7
analog extraction re-bound to the post-#248 reordered stream (#253,
PR #272), the `gen_redundancy_mux.py` strict-flag conversion and the
PWL-helper consolidation it carried (#256, #257; PR #264), the I/O-column
slot order with both spares at one end (#248, PR #254), and the append-only
check's base commit and README treatment (#255, PR #258).

## Next

- **Instantiate the shift-redundancy remap ahead of the TX input register**
  (#246), then **re-synthesize and re-place-and-route and confirm the
  `tx_d0`/`tx_d1` path closes setup at 500 MHz** (#247). Both wait on PR
  #249, which carries the decision record placing the remap (closes #232).
- **Loopback follow-ups**, after #176 (PR #188): rename the `l1` port to
  what it selects (#181), draw and extract the L1 TopMetal2 loopback route
  (#182), fix the binding-corner label in `channel_eye_post` (#185).
- **Receiver timing**, after #177 (PR #201): measure the receiver's slew
  sensitivity for T-19 (#198); size `aib_rx_data` for rise/fall symmetry or
  show T-19 closes without it (#190); then the T-20 end-to-end
  sampling-margin confirmation (#194), which also needs T-21.
- **Grade T-03 (wires per direction) in the item 8 report**, after #248. Done
  when `measurements/row-evidence.json` cites an RTL and a layout record for
  N = 20 and the row no longer reads `not-yet-measured`. No issue yet.
- **Pin the AIB 1.2 §3.3.1 shift pattern against the RTL** (#27), after #29.

## Later

- **Post-layout delta for item 7 / analog** (#226): the 45-corner campaign
  is committed and waits on klayout-tools#5491; the multi-top capability the
  graded run needs is klayout-tools#5494. Question: does the
  extracted netlist hold the pre-layout margins, T-16 and T-19 above all?
- **Post-layout legs of T-13 and T-14, and the T-30 signoff row**, after
  item 7 / analog. Question: what does the pre-layout campaign (#136) show?
- **A `consumes:` edge to the SG13G2 DLL canary.** Question: does the
  sibling meet the T-21 contract in `spec/dll-interface.md`? DR-0020 records
  the gaps as of the last comparison.
- **2 Gb/s stretch**, not before 1 Gb/s closes (`CLAUDE.md`); **shuttle seat
  and measured silicon**, the last two ladder rungs. Question: which loopback
  subset (L1, L2) a seat can hold.

## Blocked and waiting

Waiting on a maintainer decision:

- **Approved pull requests under a hold**: #168 (T-13/T-14 Monte Carlo and
  the skew definition), #188 (T-29 loopback selection), #201 (T-19 aperture
  referred to the RX pin), #249 (remap placement). Most of Next queues here.
- **#107** rewrites the T-05 shift redundancy and conflicts with `main`; a
  triage note on #29 says a later merged change may have superseded it.
- **#251** — T-16 margin at the +20 % channel-C corner (1.3 ps recorded,
  `loom:very-important`): accept and record it, spend design effort to
  recover margin, or narrow what the channel model's ±20 % C column claims.
  The figures are re-verified on `main` and the decision filed 2026-11-14;
  it needs a ruling, not another read.
- **Spec questions**: T-21 placement-error allocation (#9); the T-21 SIM
  half, which this repo cannot close without designing a DLL (#195); the
  T-24/T-25 pad-diode trade that gates the ESD transient (#196); how to
  account for T-05's ungraded SIM leg, a standing gap by DR-0023 (#333);
  T-12, a channel-model definition no measurement can cite as evidence of
  itself (#193).
- **Proposed removals** awaiting a decision: #213, #220, #241, #245, #261,
  #285. New `loom:hermit` proposals land between stamps; the live set is the
  tracker's open `loom:operator` queue, not this list.

Waiting on an upstream tool fix: klayout-tools#5491, for item 7 / analog
(#226).

Item 5 / analog stays `unmet` while its six declared gaps stand; the spec
questions above hold four of them. Items 6 and 8 cannot read `met` while
T-10, T-15 and T-16 fail; the spec is not relaxed for that.

## Not planned

- The AIB adapter layer, any protocol above the wires, the interposer or
  package; a conformance claim against the AIB specification (README, Scope).
- Designing a DLL or duty-cycle corrector here; this repo specifies the
  interface only.
- An ESD measurement: T-25 plans no `MEAS` leg.
