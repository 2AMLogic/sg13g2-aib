# DR-0019: what "selectable per wire group" means for T-29, and no loopback mux in the I/O cell

**Status**: proposed; ratified by the merge of the pull request that carries it
(DR-0001, issue #2).
**Rows**: T-29. **Amends**: nothing. **No spec row, target, fallback or scope changes.**
Issue #176. Builds on [DR-0009](0009-test-configuration-and-loopbacks.md), which defines
L1 and L2 and is not changed here.

## The question

T-29 asks for "on-die loopback L1 and wire-bond loopback L2 as defined in
`test-configuration.md`; both selectable per wire group", verified `RTL` and `SIM`, scope
TC. Issue #176 observed that none of the five cells in `design/` has a mode input and
concluded that the `SIM` half of T-29 is unverifiable: "there is nothing to select".

Two things therefore need deciding:

1. Does the analog I/O cell gain a loopback mux?
2. What does "selectable per wire group" resolve to electrically, for each loopback, and
   which RTL control state corresponds to each?

## Evidence

All checked on `main` @ `70b7d23`, 2026-11-13.

- **The cell port lists in #176 are correct.** `git grep -n "^.subckt" -- design/*.spice`:
  `aib_tx_data DIN OE PUN PD PAD VDDIO VSS`, `aib_rx_data PAD DOUT VDDIO VSS`,
  `aib_tx_clk CLK_D CLKB_D OE PUN PD CLK_PAD CLKB_PAD VDDIO VSS`,
  `aib_rx_clk CLK_PAD CLKB_PAD CLK_O CLKB_O VDDIO VSS`,
  `aib_pad_esd PAD PADI VDDIO VSS`. No cell has a mode input, and no cell carries a path
  from a TX input to an RX output other than through the pad.
- **The ratified spec does not ask for one.** `test-configuration.md` "L1: on-die
  loopback" defines L1 as a TX pin driving an RX pin *of the same die* through a
  TopMetal2 route sized to emulate `CH-3MM-RC`, with "the real I/O cells at both ends,
  with their real pad (if any) and ESD structures, so the capacitance at the pin is the
  one T-24 specifies". DR-0009 says the same and adds, under "Limits", that the route
  reproduces the model's R and C by extraction check and *not* its inductance.
  `test-configuration.md` further states that L2 "exists to get the loopback off the die"
  and that a property of a configuration "is not ... a reason to relax T-09 **or to
  change the cell** to pass L2". So the loopbacks are defined as *configurations of the
  existing cells*, not as a cell mode.
- **An L2 `SIM` already exists and was not cited.** `sim/channel-eye/tb_tc.cir` is the
  declared L2 loop (2 nH per bond wire, two wires, 0.5 pF per pin) between the existing
  `aib_tx_data` / `aib_pad_esd` / `aib_rx_data` cells, with 45-corner records
  `sim/channel-eye/records/20261108T221445Z-tc/` and `20261110T083756Z-tc/`. Neither was
  referenced by T-29.
- **The RTL input named `l1` is not the spec's L1 electrical path.** `rtl/aib_datapath.v`
  line 29: `.wire_i(l1 ? tx_wire[i] : rx_wire[i])`. That path is inside the datapath and
  contains neither I/O cell, no pad and no route. `verification/test_datapath.py`
  exercises it (`l1_round_trip_ddr`, `l1_round_trip_sdr`, and `l1_ignores_rx_wire`, which
  confirms the select is real by showing a decoy `rx_wire` corrupts the round trip at
  `l1 = 0` and not at `l1 = 1`). The module's only control inputs are `sdr` and `l1`;
  **there is no L2 control input.**
- **The controls are per-instance.** `aib_datapath #(N)` takes one `sdr` and one `l1` for
  all N slices (`rtl/aib_datapath.v` lines 14-15, the `generate` loop lines 23-31). One
  instance is one direction's wire set: N = 20 data wires per forwarded clock (T-03,
  and `N_WIRES = 20` in `sim/channel-eye/gen_channel_eye.py`), N = 8 the fallback.
- **The L1 route does not exist in layout.**
  `grep -n -i "topmetal2\|TM2\|loopback" layout/gen_io_column.py` returns nothing.
- **The pin-capacitance margin a mux would spend is 3.6 fF.** DR-0017 closed T-24 at
  96.42 fF worst case against the 100 fF limit (pad bias VDDIO/2, 45 corners, record
  `sim/dc-static/records/20261108T004350Z/`). DR-0018 then measured that swapping `XDp1`
  for the PDK's `diodevdd_2kv` adds 12.5 fF at that bias and **fails T-24 by 8.9 fF**,
  and that no driver width in this cell closes both T-08 and T-24 once it does. So the
  headroom at the pin is 3.6 fF, and it is already the subject of an open T-24/T-25
  conflict.

## What "wire group" is, and what "selectable" resolves to

**A wire group is one direction's wire set sharing one forwarded clock**: 20 data wires
(T-03 target; 8 in the fallback) plus that direction's 2 spares (T-05), driven by one
`aib_datapath` instance. The repo already uses that granularity everywhere — the
forwarded clock per direction (T-04), the energy share over `N_WIRES = 20` (T-26), the
per-direction spares (DR-0016).

**Selection is at the wire group, and it is a configuration choice, not a cell mode.**
For a group:

| | L1 (on-die) | L2 (wire bond) |
|---|---|---|
| Physical path | TopMetal2 route from the group's TX pins to its RX pins, sized to `CH-3MM-RC` R and C within ±20 % | the group's TX bond pads out through bond wire, package trace and a second bond wire to its RX bond pads |
| How a group is put in it | the route is built for that group in layout; the group's TX is enabled (`OE` = 1) and its RX pins are read | the group's pads are bonded in a loop; the group's TX is enabled and its RX pins are read |
| How a group is taken out of it | the group's TX is tristated (`OE` = 0, T-28), so nothing on the group is driven from this die | as L1 |
| RTL control state | `l1 = 0` — the RX slices must sample `rx_wire`, i.e. the **real RX cell output**, for the analog path to be in the measurement | `l1 = 0`, for the same reason |
| `sdr` | either; `sdr = 1` is the slower test mode of T-02, independent of the loopback | either |

Two consequences, stated plainly because they are easy to get wrong:

1. **`l1 = 1` is not L1.** It is a *digital-only* loopback of the datapath: each RX slice
   samples its own `tx_wire` inside the module, so no I/O cell, pad, ESD structure or
   route is in the path. It is legitimate evidence — of the select function and of the
   serializer/deserializer round trip — and it is what the `RTL` half of T-29 covers. It
   is **not** evidence of the L1 electrical path and is never cited as such. The port
   name is misleading; renaming it is RTL work outside this record (see "Effects on other
   work").
2. **L1 and L2 are not two runtime states of one group.** Which loopback a group offers
   is fixed when the die is routed and the part is bonded. Per group, "selectable" is:
   whether that group is in loopback at all (its `OE`, and which group you drive and
   read), at the granularity of one `aib_datapath` instance. This is the reading
   `test-configuration.md` already takes: its T-03 row gives L1 "the subset the seat
   holds" and L2 "the pads the package allows" — the ratified definitions already put
   the two loopbacks on *different* wire subsets, so "both selectable per wire group"
   cannot mean "every group can be switched between them at run time". The target text
   is read together with the document it cites, and is not changed.

## Decision

1. **No loopback mux is added to any cell in `design/`, and no cell revision is made.**
   The analog loopbacks are configurations of the existing cells, exactly as DR-0009 and
   `test-configuration.md` define them.
2. **"Selectable per wire group" resolves as tabulated above**: a per-group enable and
   observation at the granularity of one `aib_datapath` instance (one forwarded clock's
   worth of wires), with the loopback a group offers fixed by its route and bond.
3. **The two halves of T-29 are cited separately and never substituted for each other.**
   - `RTL` leg: the digital select function, `verification/test_datapath.py`
     (`l1_round_trip_ddr`, `l1_round_trip_sdr`, `l1_ignores_rx_wire`), recorded in
     `signoff/attest/item5-digital/fv_datapath_n20.json`. This is the `l1 = 1` digital
     path; it contains no I/O cell.
   - `SIM` leg, L1: `sim/channel-eye/tb_l1.cir` and its 135-corner record — PVT-FULL ×
     the route's −20 %, nominal and +20 % R/C points, through the real
     `aib_tx_data` / `aib_pad_esd` / `aib_rx_data` cells.
   - `SIM` leg, L2: the existing `sim/channel-eye/records/20261110T083756Z-tc/`.
   All three are scope **TC**. None of them is ever quoted as a CH result.
4. **T-29's target, fallback, verification, PVT and scope cells in `target-spec.md` are
   unchanged**, and no limit is relaxed anywhere by this record.

## Alternatives rejected

- **A loopback mux inside the I/O cell** (a mode input on `aib_tx_data` / `aib_rx_data`,
  or a new cell revision). Rejected on measured evidence, not on general density
  grounds: the pass transistors and their routing sit on the pin node, and T-24 has
  3.6 fF of margin there (DR-0017, 96.42 fF of 100 fF), with DR-0018 already showing that
  12.5 fF more at that node fails T-24 by 8.9 fF and that no driver width in this cell
  recovers it without failing T-08. A mux also adds area in the 55 µm-pitch cell CLAUDE.md
  names as this block's second risk, and `test-configuration.md` bars changing the cell to
  suit a loopback. It would additionally need its own PVT-FULL rows and a new LVS/DRC
  lineage for no row the spec asks for.
- **Declaring the `SIM` half of T-29 a permanent gap.** Rejected: that would read as a
  relaxation of a ratified row when both loopbacks are simulable as configurations of the
  committed cells — L2 already was, and L1 is by this record's testbench.
- **A per-group runtime switch between L1 and L2** (both paths present on one pin, with
  an analog select choosing between them). Rejected: the two paths would otherwise sit in
  parallel on the same pin, so the select has to be analog and lands on the pin node,
  which is the mux above. It is also not what the ratified definitions ask for (previous
  section). If a future operator decision does insist on the strict reading, the row's
  own **fallback is already "L1 only"** — so even then no target text needs changing.
- **Leaving it to #54.** #54 is the clock-path family; it recorded that the mux is absent
  and that T-29 was not claimable from that family, and decided nothing.

## What is not shown

- **The L1 route is not in layout.** `layout/gen_io_column.py` has no TopMetal2 loopback
  route, so the ±20 % R and C band the testbench sweeps is a *declared* emulation
  tolerance, not an extracted one. `test-configuration.md` requires the band to be
  confirmed by `klt extract` / `klt pex` on the real route, with an added explicit
  capacitor if the route alone is short of the model's C. That check is owed and is filed as **#182**,
  not done here.
- **The route's inductance is not reproduced** (DR-0009 "Limits"): `tb_l1.cir` sets
  `l_mm = 0`. A real TopMetal2 line has inductance; this bench does not model it.
- **The far-end term is the model's.** `tb_l1.cir` keeps the channel model's default
  `cfar = 0.1 pF`, as `tb_ch.cir` does, on top of the real cells' own pin capacitance.
  Both benches therefore load the receiver side the same way, and both over-count the pin
  load by that term.
- **Selectability itself is not measured.** The per-group enable and observation above is
  a structural property of the RTL and of the route and bond plan; no testbench in this
  repo switches a group between L1 and L2, because no part exists to switch.
- **No silicon.** T-29 is TC-scoped: it is what a part *could* show. Every number cited
  for it today is simulated or an RTL functional result.
- **The clock lane's loopback** is not covered: `tb_l1.cir` carries the clk/clkb pair as
  two `aib_tx_data` / `aib_rx_data` instances (as `tb_body.inc` does for every bench
  here), not `aib_tx_clk` / `aib_rx_clk`.

## Effects on other work

- `rtl/aib_datapath.v`'s port named `l1` denotes the digital select, not the spec's L1,
  and the module has no L2 control. Renaming the port and documenting the absence of an
  L2 control is RTL work and is **filed as #181, not done here** (this record does not change
  `rtl/`). `scripts/ci/gen_item6_digital.py`'s T-29 reason text, which claimed both modes
  are selected by RTL control inputs, is corrected by the pull request carrying this
  record because it is a generated signoff input, not design.
- The TopMetal2 L1 route in `layout/` and its `klt extract` / `klt pex` R/C check are
  owed by this record and filed as **#182**.
- If a later decision adopts an in-cell mux after all, T-24 (DR-0017, DR-0018), T-22/T-23
  and the LVS references move with it, and the L1 record here would be superseded rather
  than amended.

## Tool friction

None new. The `corners.params` axis of `klt sim` carried the route's ±20 % R/C band
directly (`alterparam` + `reset`), and `klt sim` rejects a `corners.params` name that no
top-level `.param` declares, so a silently-ignored sweep is not a risk here.
