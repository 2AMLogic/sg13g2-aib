# DR-0003: channel width, spares and what the test part can hold

**Status**: accepted. **Rows**: T-03, T-05. **Amended by**: DR-0016 (redundancy layout and case count).

## Context

The README draft says 20 data wires plus a forwarded clock, fallback 8 data,
stretch 40, with a spare wire per channel. AIB 1.2 defines channels in steps of
20 signals per direction (§1.3.4.1 Table 4) and two spares per channel with shift
redundancy (§3.3.1, Figures 43-44, neighbor-cell requirements §3.3.1.1).

## Decision

- **Channel** = 20 TX data + 20 RX data (the balanced minimum at ≤ 55 µm pitch,
  Table 4), a quasi-differential forwarded clock per direction (T-04), and two
  spare wires per direction (four per channel, a declared deviation from AIB's two per channel, DR-0016). N counts wires *per direction*.
- **Fallback** 8 + 8 is below the AIB 1.2 channel minimum and exists only as a
  smaller test-vehicle size. It is labeled as such and is not "AIB Gen1-class".
- **Stretch** 40 + 40 (Table 4 allows 20-80 per direction in steps of 20).
- **Redundancy** is the AIB shift scheme: a fault reroutes two positions toward
  the spares in both chiplets (spares at one end of each direction's wires, DR-0016), and a second fault in the same direction cannot be repaired.
  The README's "spare wire per channel" is replaced by AIB's two.

## What the test part can show

No test here can produce an open or short between two chiplets, so the *repair*
claim is CH (simulation of the mux over the channel model) and the shuttle part
exercises only the mux *function*: every single-fault selection, each verified by
`RTL` and its delay verified by `SIM` (test-configuration.md). The shuttle seat
may hold fewer than 20 + 20 wires; the area and pad count decide, and the subset
is recorded when the layout exists. A subset is a smaller test vehicle, not a
re-ratification of N.

## Alternatives rejected

- **One spare wire** (the README draft). It does not meet the AIB shift scheme,
  whose shift is two positions.
- **No redundancy** as the target. The array is the second risk (CLAUDE.md), and
  redundancy muxing is in the README scope; it stays a fallback only.
- **Counting wires per channel rather than per direction.** AIB 1.2 sizes
  balanced channels per direction; mixing the two would double-count.
