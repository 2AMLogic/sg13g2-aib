# DR-0016: T-05 shift-redundancy layout (two-signal shift, both spares at one end)

**Status**: proposed; ratified by the merge of the pull request that carries it,
after the two key reviews and the operator's approval (DR-0001, issue #29).
**Rows**: T-05. **Amends**: DR-0003 (Redundancy bullet, case count).

## Context

AIB 1.2 §3.3.1 and Figures 43-44 (pin `096a970`) reroute a faulty signal two
signals away, with two spares per channel. `rtl/shift_redundancy.v` shifts one
wire, with a spare at each end of a 22-wire 20 + 2 direction and a selectable
`dir`. T-05 and DR-0003 say "two positions" but also "20 × 2 cases per
direction", which only the one-wire, two-sided layout can produce. A two-wire
shift cannot be built in that layout (wire k + 2 runs past wire 21 for the
spare-B side). The spec therefore contradicted itself, and the RTL validates a
one-wire shift, not the AIB pattern (`rtl/README.md`, "Checked against AIB 1.2
section 3.3.1"). Checked against `origin/main` @ `37d0ff4`, 2026-10-24.

## Decision

Option (a): **keep 20 + 2 wires per direction, put both spares at one end, and
shift by two toward them.**

- Wires 0..19 carry data bits 0..19 with no fault; wires 20 and 21 are the two
  spares.
- A fault on the wire that carries data bit `pos` is repaired by moving bits
  `pos..19` up by two wires. The faulty wire and the wire after it are left
  undriven by the TX side and ignored by the RX side. There is no direction
  input: the shift always runs toward the spares.
- Case count: 20 fault positions × 1 direction = **20 per channel direction,
  40 total** for TX->RX and RX->TX, plus the no-fault case. T-05 and DR-0003 are
  edited to say so.
- **Spare count is two per direction, four per channel.** A channel is 20 TX +
  20 RX (T-03, DR-0003), so this layout carries 2 TX spares and 2 RX spares.
  AIB 1.2 §3.3.1 provides two spares per channel, shared by both directions
  (§6.3.1.1 Tables 23-24, spares configurable as input or output, §3.3.1.1).
  This is a **declared deviation** from §3.3.1 (see T-05); it adds 2 bumps per
  channel (44 instead of 42 per 40 signals) and makes repair per direction.
- Repair limit is per direction: one fault in the TX wires and one in the RX
  wires of a channel are both repairable; a second fault in the same direction
  cannot be repaired. Faults on a spare wire and double faults stay outside the
  cases (DR-0003 is amended to say per direction).
- The 20 wires per direction and the I/O column pitch (DR-0007) are unchanged;
  DR-0007 sizes the 20-wire column without the two spare cells, so the column
  gains two cells per direction (+10 %, 2 x 55 um) that DR-0007 does not budget.
  LAYOUT checks that against the area bound and files any overrun as a spec
  change; it is not absorbed silently here.
- A vacated wire is not left floating at the receiver: the follow-up RTL and cell
  work disables the RX input on a vacated wire or holds it at a defined level,
  and puts the TX output in standby (§3.3.1.1), so no CMOS input sits at mid-rail.

Follow-ups, after this record is ratified and not in this pull request:
rewrite `rtl/shift_redundancy.v` and `verification/test_shift_redundancy.py` to
this layout (the negative control must still exit exactly 1), and update
`rtl/README.md` and `verification/README.md`. Until then the T-05 `RTL` evidence
validates a one-wire shift and must not be cited as validating this record.

## Alternatives rejected

- **(b) Model the shared channel: 40 data wires, two shared spares in the
  middle, shift in each half toward them.** Closest to Figures 43-44 and to
  AIB's two spares per channel, with fewer spare cells (2 instead of 4). It is
  not rejected on pitch or area: DR-0007 and DR-0010 do not settle that either
  way. It is rejected because the two spares are shared by TX and RX and are
  configurable as input or output (§3.3.1.1), so they need bidirectional cells
  that sit between the TX and RX groups. That couples the TX and RX columns that
  DR-0007 and DR-0010 lay out as separate 20-wire columns, and it needs a
  direction-aware shift in each half, which is the control (`dir`) this record
  removes. Option (a) keeps each direction's column self-contained. Revisit (b)
  if LAYOUT shows the four-spare column does not fit the DR-0007 area bound.
- **(c) Keep the one-wire shift as a declared deviation in T-05.** Zero RTL
  work, but it fails the AIB 1.2 repair scheme the spec cites and weakens the
  T-05 repair claim. It also relaxes the ratified spec to keep the current
  design, which agents do not do (CLAUDE.md). Option (a) is also a deviation
  (spare count), but one that strengthens the repair claim (per-direction
  repair) rather than weakening it.

## Consequences

- The clock tree of DR-0010 is symmetric about the centre of the 20 data cells;
  the two spare cells sit past that end and are outside the matched span. The
  spare cells carry no clock load of their own in normal operation, and their
  mux select is static. LAYOUT confirms this when the column is drawn.
- Spares sit at one end of the I/O column, not at both ends. The layout must
  keep the two spare cells and their neighbor-cell capability (§3.3.1.1) at that
  end; this is a LAYOUT concern for the column, not decided here.
- The repair claim stays CH and the mux function stays TC (DR-0003); this
  record changes the layout under test, not what can be shown.
