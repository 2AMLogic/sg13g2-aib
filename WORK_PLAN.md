# Work Plan

Backlog snapshot from current GitHub label state, maintained by the Guide role.
Direction lives in the hand-written roadmap: [`ROADMAP.md`](ROADMAP.md).

The body below is a snapshot of GitHub label state as of the last merged docs-maintenance PR — it may lag live labels until the next one merges. `git log -1 -- WORK_PLAN.md` finds the merge that wrote it, and dates the snapshot.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#168**: feat(sim): record T-13/T-14 TX skew Monte Carlo and ratify skew definition (DR-0019)
- **#188**: feat(spec,sim): decide T-29 loopback selection and add the L1 on-die SIM record
- **#249**: evidence(sim): measure two sized remap stages and place the T-05 remap ahead of the TX input register
- **#374**: feat(design,sim): adopt diodevdd_2kv as the primary pad diode (DR-0030) and record the failing 0.5 A T-25 transient

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#9**: spec: T-21 placement-error target leaves zero allocation for phase-spacing error
- **#194**: T-20 SIM leg: no end-to-end sampling-margin confirmation exists, and two of its inputs are open
- **#196**: T-25 SIM leg: the 0.5 A ESD transient is blocked on the T-24/T-25 device trade (DR-0017, DR-0018)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#196**: T-25 SIM leg: the 0.5 A ESD transient is blocked on the T-24/T-25 device trade (DR-0017, DR-0018)

## In Progress

Issues currently being built (`loom:building`).

- **#29**: spec: decide the T-05 shift-redundancy layout (AIB 1.2 shifts two signals, shared spares)
- **#136**: T1 item 6 (Monte Carlo): TX skew campaigns T-13/T-14 (klt yield)
- **#176**: T-29 SIM: no loopback mux exists in design/, so loopback modes L1/L2 are unverifiable
- **#177**: RX receiver buffer adds up to 0.103 UI of DDR half-period off-centring after the pin, where T-16 is graded
- **#232**: T-20: one shift-redundancy remap stage adds up to 0.184 UI of data-to-clock delay, exceeding the whole margin target

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#168**: feat(sim): record T-13/T-14 TX skew Monte Carlo and ratify skew definition (DR-0019)
- **#188**: feat(spec,sim): decide T-29 loopback selection and add the L1 on-die SIM record
- **#201**: docs(spec): refer T-19's aperture to the RX pin, add DR-0021
- **#249**: evidence(sim): measure two sized remap stages and place the T-05 remap ahead of the TX input register
- **#374**: feat(design,sim): adopt diodevdd_2kv as the primary pad diode (DR-0030) and record the failing 0.5 A T-25 transient

## Proposed

Issues carrying `loom:curated`.

- **#3**: Track the gap to T1 (klayout-tools design-evidence-tiers.md) *(curated)*
- **#9**: spec: T-21 placement-error target leaves zero allocation for phase-spacing error *(curated)*
- **#27**: Pin down AIB 1.2 §3.3.1 shift pattern against rtl/shift_redundancy.v (T-05) *(curated)*
- **#29**: spec: decide the T-05 shift-redundancy layout (AIB 1.2 shifts two signals, shared spares) *(curated)*
- **#136**: T1 item 6 (Monte Carlo): TX skew campaigns T-13/T-14 (klt yield) *(curated)*
- **#176**: T-29 SIM: no loopback mux exists in design/, so loopback modes L1/L2 are unverifiable *(curated)*
- **#177**: RX receiver buffer adds up to 0.103 UI of DDR half-period off-centring after the pin, where T-16 is graded *(curated)*
- **#185**: channel_eye_post's binding-corner label always reads `mixed` instead of the supply voltage *(curated)*
- **#195**: T-21 SIM half of the forwarded-clock alignment contract is still a gap after #175 *(curated)*
- **#196**: T-25 SIM leg: the 0.5 A ESD transient is blocked on the T-24/T-25 device trade (DR-0017, DR-0018) *(curated)*
- **#226**: T1 item 7 (analog): submit the committed 45-corner pex delta campaign and record delta[] once klt pex can simulate an sg13g2 extraction *(curated)*
- **#232**: T-20: one shift-redundancy remap stage adds up to 0.184 UI of data-to-clock delay, exceeding the whole margin target *(curated)*
- **#285**: Remove sim/channel-eye/scratch94: the #111 keep premise expired when the committed ESD diode was resized *(curated)*

## Proposed (Architect / Hermit)

- **#280**: Move the shared klt sim row summariser out of sim/channel-eye: four families post-process through another family's directory *(hermit)*
- **#285**: Remove sim/channel-eye/scratch94: the #111 keep premise expired when the committed ESD diode was resized *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 4 |
| Very important | 0 |
| Important | 3 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 5 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 5 |
| Curated | 13 |
| Architect / Hermit proposals | 2 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
