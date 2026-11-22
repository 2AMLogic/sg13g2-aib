# DR-0020: T-21 re-comparison against the DLL canary at `381d989`, and the gaps it leaves

**Status**: **proposed**. Not ratified; ratification follows
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge.
**Rows**: T-20, T-21, D-1…D-12 are *named*; **none is changed**. **Amends**:
nothing. This record is documentation only: it pins a comparison and names what
is unresolved. It does not relax a requirement, select a topology, or close T-21.

## Context

T-21 carries two halves of evidence: a `SIM` of the interface contract in
[`dll-interface.md`](../dll-interface.md), and "compared against the sibling".
Issue #54 covered T-17, T-04 and T-02 on the clock path and **declared the T-21
`SIM` half a gap** rather than inventing a DLL model for it — this repo has no
`consumes:` edge and does not design a DLL or a duty-cycle corrector (CLAUDE.md,
[DR-0011](0011-dll-interface-and-consumes-proposal.md)).

This record delivers the **second half only**. The sibling's draft table has moved
out of its README into its own `spec/target-spec.md`, so `dll-interface.md`'s own
re-comparison trigger fired. The refreshed comparison is in that file, under
"Re-comparison 2026-11-13: `381d989`"; this record states what it found that
needs a decision, and what remains open.

**After this record, T-21's `SIM` half is still a declared gap.** Nothing in this
repo is edited to show T-21 as covered or passing.

## Pinned sources

| Source | Pin | State at the pin |
|---|---|---|
| This repo, `main` | `70b7d23` | T-20, T-21 ratified; DR-0014 *proposed*; **`sim/clock-path/` not in the tree** (#54 open, PR #178 open) |
| `2AMLogic/sg13g2-dll`, `main` | `381d989` (2026-11-13T09:39:25Z) | `spec/target-spec.md` status **"proposed — ratification candidate"**; ratification issue `sg13g2-dll#41` **open**; `sim/corners.json` status `proposed-pending-human-merge`; `sim/bench-rows.json` `"dut": "standin"` |
| Prior pin | `da166a6` (2026-10-17) | README draft table; the comparison [DR-0014](0014-finer-forwarded-clock-alignment-proposal.md) and `dll-interface.md` were built on |

**Every sibling number in this record is a *proposed* number**, and every one is
**specified only** — at `381d989` no spec row of the sibling has a recorded,
graded simulation result. Re-read both pins before relying on any figure here;
these go stale the same way DR-0014's did.

## What the re-comparison found

### 1. The previous comparison used the wrong column

The two repos key their columns to their own `f0`. The sibling's are 1 GHz target
/ 500 MHz fallback / 2 GHz stretch. This repo's target is 1 Gb/s DDR on a
**500 MHz** forwarded clock (T-01), which lands on the sibling's **fallback**
column — not its target column, which the `da166a6` table quoted. This repo's
fallback (250 MHz) has **no sibling column at all**, and its stretch (1 GHz) is
the sibling's target.

Two verdicts in the `da166a6` table therefore change, both in the unsafe
direction:

| Row | `da166a6` verdict | Corrected at `381d989` |
|---|---|---|
| D-4, phase resolution | "Gap G2": 8 phases against the 16 needed — 2× | **4** phases at 500 MHz (fallback column), step 0.50 UI — **4×** |
| D-7, added jitter | "**Fits at the target, barely**" (≤ 2 ps rms inside 2.1 ps rms) | **Does not fit**: ≤ 5 ps rms at 500 MHz = 0.07 UI p-p at 14 σ against 0.03 UI — **2.3× over** |

The 2 ps rms that fitted, and the 8 phases, are the sibling's **1 GHz** numbers.
1 GHz is this repo's *stretch* clock.

### 2. Two of the five T-21 numbers fit; two are gaps; one is not derivable

Full table, with columns and definitions, in
[`dll-interface.md`](../dll-interface.md) § "The five T-21 numbers". Summary:

| T-21 number | Verdict at `381d989` |
|---|---|
| Range ≥ one clock period | **Fits** (tap N pinned at 1 × T, lock range ±20 % around 500 MHz), within the fallback column's ±5 % T lock tolerance |
| Lock ≤ 10 µs | **Fits** with 2× margin (≤ 5 µs) |
| Step ≤ 1/8 UI | **Gap**, 4× (0.50 UI) |
| DLL-added jitter ≤ 0.03 UI p-p | **Gap**, 2.3× (0.07 UI p-p at 14 σ), and no number exists yet — the sibling's jitter bench is blocked on its noise-method record |
| Worst-case placement error ≤ 0.0625 UI | **Not derivable.** The sibling's row 4 bounds *systematic* spacing only and states its Monte Carlo result carries **no limit**, so no worst-case total exists. The derivable part alone (0.25 UI quantization + 0.10 UI systematic) is ≥ 0.35 UI |

"Not derivable" is the finding that matters most. A consumer cannot close a
worst-case placement row against an unbounded random term however good the
silicon is: the row is *unanswerable* at this pin, not merely failing.

### 3. G1–G5: two closed, one declined, one declined-out-of-scope, one half-open

State and citations are in `dll-interface.md` § "Gaps filed on the sibling, and
their state". In brief, at `381d989`: **G4** (1.2 V thin-oxide ±10 %) and **G5**
(lock-status output) are **accepted and closed** — D-10 and D-11 fit, and the
sibling's 45-corner set is the same grid as this repo's PVT-FULL. **G1** is
**partly accepted**: 500 MHz ±20 % closes D-1 / D-2 at this repo's target, while
the 250 MHz half was never addressed. **G2** is **declined at target**. **G3** is
**declined as out of scope** by the sibling (a corrector is a separate block).

### 4. D-9 / G3 is pending #54, not "not triggered"

D-9 is conditional: a duty-cycle corrector is needed only if this repo's own TX
clock path cannot hold T-17 in simulation. #54 reports T-17 passing at 45/45
corners with 1.964 % of margin, which would leave D-9 **not triggered** — but
that record (`sim/clock-path/records/20261113T095936Z/`) is **not on `main` at
`70b7d23`**; PR #178 is open. Until it merges, the row says **pending #54**.
An unmerged result is a claim, not evidence, and this repo's recorded results are
append-only on `main`.

## Decision

1. **Record the comparison, change no value.** The refreshed, pinned comparison
   lands in `dll-interface.md`. T-20, T-21 and D-1…D-12 keep their values. In
   particular D-4, D-5 and D-7 are **not** relaxed to match the sibling's
   fallback column; a shortfall is recorded as a shortfall.
2. **T-21 stays an open row.** Its `SIM` half is a declared gap; its comparison
   half is now current. T-21 is not marked covered or passing anywhere.
3. **File the remainder on the sibling, not here.** Filed as
   **`2AMLogic/sg13g2-dll#72`**: the 250 MHz half of G1, the column-corrected G2,
   the unbounded Monte Carlo spacing term, and the fallback-column jitter limit.
   `sg13g2-dll#10` is closed and `0002`/`0007` settled what it could; #72 carries
   what the spec's arrival changed.
4. **Hold the `consumes:` edge.** [DR-0011](0011-dll-interface-and-consumes-proposal.md)
   conditions the edge on G1 and G2 closing in the sibling's *ratified* spec.
   Neither has: G2 is declined at target, G1 is half-open, and the sibling's spec
   is not ratified. The edge stays a proposal. No `repos.yml` or
   `reuse.lock.json` change.
5. **Leave the finer-alignment question where it is.** The sibling's `0007`
   decision 4 observes that this repo's DR-0014 shows 16 steps does not close its
   own budget either, "so the next move is theirs". That move belongs to **#9**
   and DR-0014 — the 16-vs-32-step and spacing-error allocation question — and is
   deliberately **not** made here.

## What this costs the budget (arithmetic, not a change)

Substituting the sibling's fallback-column numbers into the T-20 allocation
(`target-spec.md` § Timing budget): the 0.0625 UI placement line becomes ≥ 0.35 UI,
costing ≥ 0.2875 UI; and the DLL's share of the 0.050 UI clock-path jitter line
goes from 0.03 UI to 0.07 UI, costing a further 0.04 UI. The DLL holds 0.03 of
that 0.050 line (`target-spec.md` § Timing budget), so the forwarded clock's own
0.02 UI share is left in place rather than absorbed. About **0.33 UI comes out of
a 0.1075 UI margin**, leaving roughly **−0.22 UI** (linear sum).

So: **the sibling's fallback column, as specified at `381d989`, does not close
T-20 at this repo's target.** This is hand arithmetic from two tables, in the same
spirit as DR-0014 — not a simulation, not a feasibility claim, and not a reason to
change a row. It is the size of the gap #72 asks about.

## Alternatives considered

- **A standalone comparison file.** Rejected: it splits the contract from its
  comparison, and the re-comparison trigger lives in `dll-interface.md`.
- **A behavioural DLL model in `sim/` to produce the `SIM` half.** Rejected:
  CLAUDE.md scope discipline, and DR-0014 already records that such a model needs
  its own authorization. Declaring the gap is the correct outcome.
- **Relaxing D-4, D-5 or D-7 to the sibling's fallback column.** Rejected: agents
  do not relax the ratified spec to make results pass (CLAUDE.md). The spec says
  what this repo needs; the sibling's answer is recorded next to it.
- **Rewriting the `da166a6` table in place.** Rejected: recorded comparisons are
  append-only evidence. The old table is marked history and kept unedited, with
  its two superseded verdicts named.

## Consequences

- `dll-interface.md` now carries two dated comparisons; the `381d989` one is
  current.
- The next trigger is the sibling ratifying its spec (`sg13g2-dll#41`) or a
  disposition on `sg13g2-dll#72`. Either re-fires the comparison.
- If #54's PR #178 merges, the D-9 / G3 row moves from *pending* to whatever
  T-17's recorded result supports. That is a one-line edit against a merged
  record, not a new comparison.

## Addendum 2026-11-13, read at `main` `8107ae0`: D-9 / G3 moves off *pending #54*

§ 4 above and the § Consequences bullet below it stay as written. This addendum
is the step that bullet authorised — "If #54's PR #178 merges, the D-9 / G3 row
moves from *pending* to whatever T-17's recorded result supports. That is a
one-line edit against a merged record, not a new comparison." That is this
record's own authority for the move; no new decision is taken here and this
record's **proposed** status is unchanged.

PR #178 merged at `952f026`, putting
[`sim/clock-path/records/20261113T095936Z/`](../../sim/clock-path/records/20261113T095936Z/)
on `main`; it is read here at **`8107ae0`**. T-17 passes there — 90/90 graded
`t17_dcd_c` / `t17_dcd_cb` measurements inside ±3 % over 45 corners, worst |DCD|
**−1.036 %** (margin 1.964 %) at `mos_sf` / 1.08 V / −40 °C; `rows.json` carries
`verdict: pass`, binding `mos_sf/mixed/-40C`, `t17_dcd_c` = −0.0103576 — so
**D-9 / G3 is not triggered** by that record.

The scope travels with the verdict, and it is narrower than D-9. The record is
**simulated**, **CH**-scoped (CH-3MM-RC at nominal `kr = kc = 1`, not the test
configuration), and covers the **target rate point only**: an ideal complementary
50 % 500 MHz forwarded clock (1 Gb/s DDR), with no 250 MHz or 1 GHz run. It
therefore does not reach the **2 Gb/s stretch** point, the **test configuration**
(T-17's scope column in `target-spec.md` is BOTH, and this record is CH), or a
**non-ideal upstream duty cycle** — D-9 is written as correcting ±10 % input DCD
to ±3 %, and this stimulus is ideal. Whether the netlist under test is pre- or
post-layout is not stated in the record and is not established here.

**G3 is not closed.** D-9 stays conditional and "to be decided before layout" on
the terms above; § 4's text and this record's five decisions are unchanged; no
T-row or D-row value moves; T-21's `SIM` half remains a declared gap. The
matching note is in [`dll-interface.md`](../dll-interface.md) § "Gaps filed on
the sibling, and their state".
