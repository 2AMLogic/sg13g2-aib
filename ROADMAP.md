# Roadmap

An AIB Gen1-class die-to-die parallel I/O channel on IHP SG13G2, built to a
ratified spec with every claim traced to a recorded result.

Status as of 2026-11-13, `main` @ `4603363`.

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

- **Item 5 / analog.** Thirteen rows are cited and pass over PVT-FULL (45
  corners): T-01, T-06 to T-09, T-11, T-15 to T-18, T-24, T-26, T-28. Eight
  rows are declared gaps: T-02, T-04, T-05 and T-12 by design (DR-0022,
  DR-0023; how the manifest should account for them is #216), and T-20,
  T-21, T-25, T-29 as open work (#194, #195, #196, #176).
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

Can start today; each is one pull request. Items 2 and 3 are in review.

1. **Convert `sim/redundancy-mux/gen_redundancy_mux.py` to the shared
   write-or-check helper** (#256, ready). Done when `--check` exits 0 on an
   unchanged tree and a mistyped flag exits 2 without regenerating.
2. **Land the I/O-column slot order with both spares at one end** (#248, PR
   #254 approved). Done when `layout/check_io_column.py` checks the slot order
   against DR-0016 and the committed stream passes it.
3. **Fix the append-only check's base commit and its treatment of a record's
   README** (#255, PR #258 approved). Done when
   `scripts/ci/check_sim_append_only.py` matches its own docstring.
4. **Per-corner reading of the three failing Monte Carlo rows** (no issue
   yet; seed drafted). `klt yield` pools the 45 corners, so the records do
   not say which corners carry the T-10, T-15 and T-16 failures or how much
   is systematic shift against mismatch. Done when a committed, generated
   table gives per-corner mean, sigma and out-of-limit count for each row,
   derived from the existing `sim/mc/records/` reports with no new simulation.
5. **Bring the README status paragraph and ladder position in line with the
   signoff record** (no issue yet; seed drafted). The README still says no
   PVT or channel simulation exists and that I/O-cell LVS mismatches. Done
   when both statements match the committed record.
6. **Remove four stale `.gitignore` rules** (#260, proposal awaiting
   promotion). Done when the rules are gone and the Yosys-log negation points
   at `sim/rtl-synth/records`.

## Next

- **Instantiate the shift-redundancy remap ahead of the TX input register**
  (#246), then **re-synthesize and re-place-and-route and confirm the
  `tx_d0`/`tx_d1` path closes setup at 500 MHz** (#247). Both wait on PR
  #249, which carries the decision record placing the remap (closes #232).
- **Re-run the item 7 analog extraction on the reordered stream** (#253),
  after #248. Done when the `layout/pex/records/` citations bind the new
  stream hash.
- **Loopback follow-ups**, after #176 (PR #188): rename the `l1` port to
  what it selects (#181), draw and extract the L1 TopMetal2 loopback route
  (#182), fix the binding-corner label in `channel_eye_post` (#185).
- **Receiver timing**, after #177 (PR #201): measure the receiver's slew
  sensitivity for T-19 (#198); size `aib_rx_data` for rise/fall symmetry or
  show T-19 closes without it (#190); then the T-20 end-to-end
  sampling-margin confirmation (#194), which also needs T-21.
- **T-16 margin at the +20 % channel C corner** (#251, 1.3 ps recorded). Its
  stated blocker #193 closed with #252, so it needs a fresh read first.
- **Grade T-03 (wires per direction) in the item 8 report**, after #248. Done
  when `measurements/row-evidence.json` cites an RTL and a layout record for
  N = 20 and the row no longer reads `not-yet-measured`. No issue yet.
- **Consolidate the duplicated PWL stimulus helpers** (#257), after #256;
  **pin the AIB 1.2 §3.3.1 shift pattern against the RTL** (#27), after #29.

## Later

- **Post-layout delta for item 7 / analog** (#226): the 45-corner campaign
  is committed and waits on klayout-tools#5491 and #5493. Question: does the
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
- **Spec questions**: T-21 placement-error allocation (#9); the T-21 SIM
  half, which this repo cannot close without designing a DLL (#195); the
  T-24/T-25 pad-diode trade that gates the ESD transient (#196); how item 5
  accounts for rows with no gradable leg (#216).
- **Proposed removals** labelled for a decision: #213, #220, #241, #245.

Waiting on an upstream tool fix: klayout-tools#5491 and #5493, for item 7 /
analog (#226).

Item 5 / analog cannot read `met` until #216 is ruled. Items 6 and 8 cannot
read `met` while T-10, T-15 and T-16 fail; the spec is not relaxed for that.

## Not planned

- The AIB adapter layer, any protocol above the wires, the interposer or
  package; a conformance claim against the AIB specification (README, Scope).
- Designing a DLL or duty-cycle corrector here; this repo specifies the
  interface only.
- An ESD measurement: T-25 plans no `MEAS` leg.
