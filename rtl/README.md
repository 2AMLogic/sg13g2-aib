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

## aib_datapath.v: T-02 DDR/SDR serializer, deserializer, T-29 L1 select, T-27 latency

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
| `l1` | 1 = L1 on-die loopback: each RX slice samples its own `tx_wire` instead of `rx_wire` (`spec/test-configuration.md`, "L1"). The digital select only; the TopMetal2 route is layout work |
| `tx_d0`, `tx_d1` | the two bits per wire per cycle; `d0` goes out first |
| `tx_wire`, `rx_wire` | the N wires out and in |
| `rx_q0`, `rx_q1` | the received word, `q0` the first bit; in SDR `q1` repeats `q0` and carries no data |

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
