# rtl

## shift_redundancy.v: T-05 shift-redundancy remap (one 20 + 2 channel direction)

`tx_remap` / `rx_remap` implement the mux **function** only (test configuration;
repair on a real channel is CH and is not shown here, DR-0003). They follow DR-0016
(two-signal shift, both spares at one end). Wires 0..21: wires 0..19 = data bits 0..19
with no fault, wires 20 and 21 = the two spares. Inputs `en` (0 = no fault) and `pos`
(0..19, the wire that is faulty). A fault at `pos` moves bits `pos..19` up two wires
(bit k to wire k + 2); bits below `pos` stay put; the faulty wire `pos` and wire
`pos + 1` are undriven (TX) / ignored (RX). There is no direction input.

### Case-count definition (T-05 "20 x 2 cases per direction")

Read as 20 fault positions x 2 channel directions (TX->RX and RX->TX) = 40, plus the
no-fault case = 41 tests. Faults on a spare wire and double faults are outside the 40
(DR-0003, DR-0016). The bench also checks, per position, from the TX wires, that the
bit-to-wire map is injective, stays inside wires 0..21 and avoids wires `pos` and
`pos + 1`.

### Relation to AIB 1.2 section 3.3.1

Read against AIB 1.2 at pin `096a970` (`spec/README.md`): section 3.3.1 reroutes a
faulty signal two signals away toward the spares, and DR-0016 adopts that two-signal
shift with both spares at one end of the channel. This module implements DR-0016. No
conformance is claimed. Section 3.3.1.1 (neighbour cells can take a rerouted signal;
spares configurable as input or output) is cell-level behaviour and is not exercised
by this mux; neither is RX input-disable or TX standby on the vacated wires.

**Scope of the evidence.** This is the `RTL` leg of T-05 only, in the test
configuration: it shows the mux function, not repair on a real channel, and not the
added load and delay of the mux (no SIM leg). The synthesized netlist under
`design/` predates the mux and does not contain it.

`INJECT_BUG_SHIFT_EDGE` (negative control): TX skips the shift at
position 19 (bit 19 stays on the faulty wire).

## aib_datapath.v: T-02 DDR/SDR serializer, deserializer, T-29 loopback select, T-27 latency

`aib_datapath #(N)` instantiates N `aib_tx_slice` + `aib_rx_slice` pairs, one per
wire (N = 20 default, 8 fallback, T-03). The design follows AIB 1.2 sections
2.1.3.1-2.1.3.2 (DDR data exchange) and 2.1.7 Table 9 (latency); no text is copied
and no conformance is claimed. The spare wires of T-05 are `shift_redundancy.v`'s
and are not in this module.

| Port | Meaning |
|---|---|
| `clk` | TX forwarded clock; every TX register is on its edges |
| `rx_clk` | RX forwarded clock, already centred in the data eye (the DLL's job; the bench uses `clk` delayed a quarter cycle) |
| `rst_n` | asynchronous active-low reset of every register |
| `sdr` | 0 = DDR, 1 = SDR test mode (TX side): `tx_d0` is held for the whole cycle and `tx_d1` is ignored |
| `l1` | 1 = **digital** loopback: each RX slice samples its own `tx_wire` instead of `rx_wire`. The select function only — this path contains no I/O cell, pad or route, so it is **not** the L1 electrical path of `spec/test-configuration.md` (DR-0019); the port name predates that record |
| `tx_d0`, `tx_d1` | the two bits per wire per cycle; `d0` goes out first |
| `tx_wire`, `rx_wire` | the N wires out and in |
| `rx_q0`, `rx_q1` | the received word, `q0` the first bit; in SDR `q1` repeats `q0` and carries no data |

**Scope of the T-29 evidence (DR-0019).** This module carries the **`RTL` leg** of T-29
and nothing more: `l1` is the digital select, enumerated in both states by
`verification/test_datapath.py` (`l1_round_trip_ddr`, `l1_round_trip_sdr`,
`l1_ignores_rx_wire`). Three things follow, and the first two are easy to get wrong:

- **`l1 = 1` is not the spec's L1.** The spec's L1 is a TopMetal2 route between two real
  I/O cells (`spec/test-configuration.md`, DR-0009); exercising it needs `l1 = 0`, so that
  the RX slices sample `rx_wire`, the real RX cell's output. The `SIM` leg of L1 is
  `sim/channel-eye/tb_l1.cir`, and of L2 the existing `tb_tc.cir` record.
- **There is no L2 control input, and none is owed.** Which loopback a wire group offers
  is set by its on-die route and its bonding, not by an RTL state (DR-0019).
- **Selection granularity is the wire group.** `sdr` and `l1` are one per
  `aib_datapath` instance, and one instance is one direction's N wires sharing a
  forwarded clock (T-03) — which is the granularity T-29's "per wire group" asks for.

### Cycle accounting (T-27)

1 UI = one clock edge = half a forwarded-clock cycle; the budget of 1.5 cycles each
way is 3 UI. Counted on clock edges, E0 being the first edge:

- **TX**, from the posedge that loads the TX input register (E0) to the UI where the
  bit starts on the wire: `d0` starts at E2 (2 UI), `d1` at E3 (**3 UI**, equal to the
  budget). Registers: input (posedge), `o_n` (negedge, E1), `o_p` (posedge, E2), then
  a clock-selected mux. SDR starts at 2 UI.
- **RX**, from the `rx_clk` edge that samples the first bit (E0, posedge) to the edge
  that loads the RX output register (E2, posedge): **2 UI**. The second bit is
  sampled on the negedge E1.

The bench (`verification/test_datapath.py`) measures both and prints
`LATENCY mode=... tx_ui=... rx_ui=... budget_ui=3`. Defining `INJECT_EXTRA_STAGE`
adds one posedge stage to the TX input path and one to the RX output (TX 5 UI, RX 4 UI)
and the latency tests fail; the PRBS round trips still pass, so only the cycle
accounting catches it. These results hold for the test configuration (zero-delay
wire, ideal eye-centred `rx_clk`); they are not channel results.

Synthesis smoke: `sim/rtl-synth/` (Yosys against `sg13g2_stdcell`; mapping only, no
timing). The mux on the TX wire is selected by the clock, a structure the P&R flow
will need to treat deliberately; that is not judged here.
