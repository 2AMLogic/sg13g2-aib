# Work Plan

Backlog snapshot from current GitHub label state, maintained by the Guide role.
Direction lives in the hand-written roadmap: [`ROADMAP.md`](ROADMAP.md).

The body below is a snapshot of GitHub label state as of the last merged docs-maintenance PR — it may lag live labels until the next one merges. The `_Generated:` stamp at the top of the generated region dates the snapshot; `git log -1 -- WORK_PLAN.md` finds the merge that wrote it.

<!-- guide:plan-body:start -->
_Generated: 2026-11-21T08:40:20Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`).

- **#168**: feat(sim): record T-13/T-14 TX skew Monte Carlo and ratify skew definition (DR-0019)
- **#188**: feat(spec,sim): decide T-29 loopback selection and add the L1 on-die SIM record
- **#201**: docs(spec): refer T-19's aperture to the RX pin, add DR-0021
- **#249**: evidence(sim): measure two sized remap stages and place the T-05 remap ahead of the TX input register
- **#390**: fix(layout,ci): draw Resd at the netlist l=1u and check the device table in CI

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#386**: T-10: receiver threshold fails Monte Carlo on systematic corner shift (8 of 45 corner means outside +-60 mV) — sizing study for the aib_rx_data input stage

## Important

`loom:important`; taken before unlabelled work.

- **#9**: spec: T-21 placement-error target leaves zero allocation for phase-spacing error *(held)*
- **#194**: T-20 SIM leg: no end-to-end sampling-margin confirmation exists, and two of its inputs are open *(held)*

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#29**: spec: decide the T-05 shift-redundancy layout (AIB 1.2 shifts two signals, shared spares)
- **#136**: T1 item 6 (Monte Carlo): TX skew campaigns T-13/T-14 (klt yield)
- **#176**: T-29 SIM: no loopback mux exists in design/, so loopback modes L1/L2 are unverifiable
- **#177**: RX receiver buffer adds up to 0.103 UI of DDR half-period off-centring after the pin, where T-16 is graded
- **#232**: T-20: one shift-redundancy remap stage adds up to 0.184 UI of data-to-clock delay, exceeding the whole margin target
- **#385**: T1 item 6 (analog): re-run the T-15 / T-16 Monte Carlo campaigns on the current cells — the cited failing records predate two resizes
- **#386**: T-10: receiver threshold fails Monte Carlo on systematic corner shift (8 of 45 corner means outside +-60 mV) — sizing study for the aib_rx_data input stage
- **#387**: layout: the committed I/O column still draws Resd 2 um x 2 um while design/aib_pad_esd.spice is l=1u — regenerate before the item 7 delta campaign

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#168**: feat(sim): record T-13/T-14 TX skew Monte Carlo and ratify skew definition (DR-0019) — closes #136
- **#188**: feat(spec,sim): decide T-29 loopback selection and add the L1 on-die SIM record — closes #176
- **#201**: docs(spec): refer T-19's aperture to the RX pin, add DR-0021 — closes #177
- **#249**: evidence(sim): measure two sized remap stages and place the T-05 remap ahead of the TX input register — closes #232
- **#390**: fix(layout,ci): draw Resd at the netlist l=1u and check the device table in CI — closes #387
- **#391**: mc: re-run T-15/T-16 Monte Carlo on the current cells; both rows pass the 7-sigma gate — closes #385

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 (klayout-tools design-evidence-tiers.md) *(curated)*
- **#9**: spec: T-21 placement-error target leaves zero allocation for phase-spacing error *(curated)* *(held)*
- **#27**: Pin down AIB 1.2 §3.3.1 shift pattern against rtl/shift_redundancy.v (T-05) *(curated)* *(held)*
- **#29**: spec: decide the T-05 shift-redundancy layout (AIB 1.2 shifts two signals, shared spares) *(curated)*
- **#136**: T1 item 6 (Monte Carlo): TX skew campaigns T-13/T-14 (klt yield) *(curated)*
- **#176**: T-29 SIM: no loopback mux exists in design/, so loopback modes L1/L2 are unverifiable *(curated)*
- **#177**: RX receiver buffer adds up to 0.103 UI of DDR half-period off-centring after the pin, where T-16 is graded *(curated)*
- **#185**: channel_eye_post's binding-corner label always reads `mixed` instead of the supply voltage *(curated)* *(held)*
- **#195**: T-21 SIM half of the forwarded-clock alignment contract is still a gap after #175 *(curated)* *(held)*
- **#196**: T-25 SIM leg: the 0.5 A ESD transient is blocked on the T-24/T-25 device trade (DR-0017, DR-0018) *(curated)* *(held)*
- **#226**: T1 item 7 (analog): submit the committed 45-corner pex delta campaign and record delta[] once klt pex can simulate an sg13g2 extraction *(curated)* *(held)*
- **#232**: T-20: one shift-redundancy remap stage adds up to 0.184 UI of data-to-clock delay, exceeding the whole margin target *(curated)*
- **#285**: Remove sim/channel-eye/scratch94: the #111 keep premise expired when the committed ESD diode was resized *(curated)* *(held)*
- **#385**: T1 item 6 (analog): re-run the T-15 / T-16 Monte Carlo campaigns on the current cells — the cited failing records predate two resizes *(curated)*
- **#386**: T-10: receiver threshold fails Monte Carlo on systematic corner shift (8 of 45 corner means outside +-60 mV) — sizing study for the aib_rx_data input stage *(curated)*
- **#387**: layout: the committed I/O column still draws Resd 2 um x 2 um while design/aib_pad_esd.spice is l=1u — regenerate before the item 7 delta campaign *(curated)*
- **#396**: sim/channel-model README overstates the seeded-defect detection margin (measured: 2 %, not >=10 %) *(curated)*

## Proposed (Architect / Hermit)

- **#280**: Move the shared klt sim row summariser out of sim/channel-eye: four families post-process through another family's directory *(hermit)* *(held)*
- **#285**: Remove sim/channel-eye/scratch94: the #111 keep premise expired when the committed ESD diode was resized *(hermit)* *(held)*
- **#395**: Use the generator freshness run to establish CI coverage and drop five manual entries *(hermit)* *(held)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 5 |
| Very important | 1 |
| Important | 2 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 0 |
| In Progress (`loom:building`) | 8 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 6 |
| Curated | 17 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
