# rtl

## shift_redundancy.v: T-05 shift-redundancy remap (one 20 + 2 channel direction)

`tx_remap` / `rx_remap` implement the mux **function** only (test configuration;
repair on a real channel is CH and is not shown here, DR-0003). Wires 0..21:
wire 0 = spare A, wires 1..20 = data bits 0..19 with no fault, wire 21 = spare B.
Inputs `en` (0 = no fault), `dir` (0 = shift toward spare A, 1 = toward spare B),
`pos` (0..19, the data position whose wire is faulty).

### Case-count definition (T-05 "20 x 2 cases per direction")

Read as 20 fault positions x 2 shift directions = 40 per channel direction,
80 for the two channel directions (TX->RX and RX->TX), plus the no-fault case.
Faults on a spare wire and double faults are outside the 80 (DR-0003).

### Unverified against AIB 1.2 section 3.3.1

The public AIB specification could not be read when this was written (the forge
reader was unavailable), so the "x 2" reading and the exact shift pattern
(one-wire shift per side here, versus the "two positions" wording of T-05) are
**not checked against section 3.3.1 / Figures 43-44**. If the specification
differs, the module and this section change; the 80 does not change without a
decision record. Tracked in the PR for #23.

`INJECT_BUG_SHIFT_EDGE` (negative control): TX skips the spare-B shift at
position 19.
