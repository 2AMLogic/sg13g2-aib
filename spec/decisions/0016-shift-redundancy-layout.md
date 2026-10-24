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
- Faults on a spare wire and double faults stay outside the cases (DR-0003: a
  second fault in a channel cannot be repaired).
- The 20 + 2 count per direction, the I/O column pitch (DR-0007) and the column
  area and skew matching (DR-0010) are unchanged.

Follow-ups, after this record is ratified and not in this pull request:
rewrite `rtl/shift_redundancy.v` and `verification/test_shift_redundancy.py` to
this layout (the negative control must still exit exactly 1), and update
`rtl/README.md` and `verification/README.md`. Until then the T-05 `RTL` evidence
validates a one-wire shift and must not be cited as validating this record.

## Alternatives rejected

- **(b) Model the shared channel: 40 data wires, two shared spares in the
  middle, shift in each half toward them.** Closest to Figures 43-44, but it
  breaks DR-0003's per-direction 20 + 2 count and the pitch and area of
  DR-0007 and DR-0010, so it ripples furthest; worse than (a) for a canary.
- **(c) Keep the one-wire shift as a declared deviation in T-05.** Zero RTL
  work, but it fails the AIB 1.2 repair scheme the spec cites and weakens the
  T-05 repair claim. It also relaxes the ratified spec to keep the current
  design, which agents do not do (CLAUDE.md).

## Consequences

- Spares sit at one end of the I/O column, not at both ends. The layout must
  keep the two spare cells and their neighbor-cell capability (§3.3.1.1) at that
  end; this is a LAYOUT concern for the column, not decided here.
- The repair claim stays CH and the mux function stays TC (DR-0003); this
  record changes the layout under test, not what can be shown.
