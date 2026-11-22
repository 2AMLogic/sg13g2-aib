# DR-0023: where the redundancy mux sits for the T-05 `SIM` leg, and what stands in for it

**Status**: accepted. **Rows**: T-05 (and, as consumers of the numbers, T-13 and T-20).
**Supersedes**: nothing. **Related**: DR-0003 (spares per direction), DR-0016 (the
two-wire shift), DR-0022 (a `SIM` leg with no bound).

## Context

`spec/target-spec.md` T-05 carries two evidence legs: `RTL` for the mux function (covered
by `verification/`, 40 single-fault cases) and **`SIM` for the mux added load and delay**,
"inside T-12/T-13", with the grid column "PVT-FULL for the delay; n/a for the function".
The `SIM` leg had no testbench and no record, and was a declared gap under
`signoff/block-manifest.json` `spec_rows."5.analog"` (#42, #192).

The obstacle is that **there is no transistor-level mux in this repo to measure**.
`tx_remap` / `rx_remap` exist only in `rtl/shift_redundancy.v`; `rtl/aib_datapath.v`
instantiates `aib_tx_slice` / `aib_rx_slice` and nothing else, and the committed
synthesized netlist predates the remap and does not contain it (`rtl/README.md`). A
testbench for this leg therefore has to **declare** where the mux sits and what stands in
for it, before it can measure anything. That declaration is what this record makes, so the
numbers in `sim/redundancy-mux/records/` are read against a stated arrangement rather than
an implied one.

## Decision

**1. The remap sits on the serialized wire, between the serializer mux and the TX cell's
`DIN`.** That is the placement the ratified row already presumes when it says the added
load and delay land "inside T-12/T-13": T-13 is data-to-data skew *at the TX output*, so
the row's term is in the lane between the datapath and the pad. Each physical wire `j`
then takes a 2:1 choice between bit `j` and bit `j - 2` (`rtl/shift_redundancy.v`), and
each serializer output fans out to two remap inputs — its own wire's `A0` and wire
`j + 2`'s `A1` — instead of one `DIN`.

**2. `sg13g2_mux2_1` stands in for both the serializer mux and the remap stage.** Synthesis
already maps the serializer's clock-selected mux (`wire_o = clk ? o_n : o_p`,
`rtl/aib_tx_slice.v`) to that cell: the committed netlist holds 22 instances of it. Using
the same cell for the remap makes the two stages directly comparable and introduces no
cell this design does not already use. The subcircuit is vendored unmodified into
`sim/redundancy-mux/sg13g2_mux2_1.inc` from the PDK pinned in `sim/pdk.json`, the way
`sim/mc/capture_window/` vendors its flop, so the batch fleet needs no standard-cell path.

**3. The standard cells run from the same supply as the TX cell, swept by
`corners.supply_v`.** The bench has one supply source, `vdd_tx`, taking each PVT-FULL
VDDIO value (1.08 / 1.20 / 1.32 V); the vendored mux's `VDD` is that node and its `VSS` is
ground. This repo declares no separate core supply anywhere in `spec/` or `design/`, the
whole data path is thin-oxide 1.2 V, and `sim/mc/capture_window/tb_t19.cir` supplies its
vendored flop the same way. If a later revision splits VDDIO from a core supply, this leg
is re-run with the split and this record is superseded.

**4. The leg is measured as a difference inside one simulation, not between two runs.**
`sim/redundancy-mux/tb_redundancy_mux.cir` carries four lanes on one stimulus and one
corner: a baseline lane (serializer → `DIN`), a **control** lane that is the baseline built
a second time, and two with-mux lanes selected to `A0` and to `A1`. Every reported number
is a difference between two lanes of the same deck, so the corner, the supply, the
stimulus and the solver step are identical by construction and cannot contribute to it.

**5. No measurement in this leg carries a limit.** T-05 states no bound for the `SIM` leg,
and this record invents none — the three terms are reported, and are consumed by the rows
that do carry numbers: the **common added delay** by T-20 (every data lane gains a remap
stage and the forwarded-clock lane does not, so it is a data-to-clock offset) and the
**select-dependent delay** by T-13 (in a repaired direction, wires below `pos` take `A0`
and wires at or above it take `A1`). T-05 stays a declared gap in the manifest, in the form
DR-0022 established for T-02 and T-04: a row whose `SIM` leg has no gradable bound is
declared, never cited into coverage. Whether item 5 / analog can read `met` with such a row
is #216's question, not this record's.

## Alternatives rejected

- **Moving the remap ahead of the TX input register** (22 slices, a mux on each slice's
  `d0`/`d1`). It would make the in-lane delta zero by construction, which is exactly why it
  cannot be assumed here: it changes T-05's evidence leg, the RTL and the netlist, and it
  is a spec change that needs this measurement as its evidence. The record this decision
  enables is the input to that argument, not a pre-judgement of it.
- **Instantiating `tx_remap` in `aib_datapath` and re-synthesizing first.** The
  measurement does not need it, and it would pull place-and-route and item 7 evidence into
  a question about one lane.
- **Giving T-05 a bound of its own so the row could be cited as covered.** That is a new
  ratified number carved out of the T-13 and T-20 allocations, which #136 and #177 have not
  closed. Decide it with the measurement in hand, as its own spec change.
- **A bench self-check limit on the negative control**, so `klt sim` would grade it. It
  would make the only limits in the envelope belong to the bench rather than the spec, and
  anyone who later cited this envelope for T-05 would get a *pass* out of a self-check.
  The control is reported like everything else and read in the record's `README.md`.
- **Two separate runs, a baseline deck and a with-mux deck.** A difference between two runs
  carries both runs' solver noise. Four lanes in one deck is the same comparison with that
  term removed, and the control lane measures what is left of it.
- **An ideal voltage source on the remap's unselected input.** The unselected input of
  `sg13g2_mux2_1` couples into the internal select stack, so its slew matters. Each with-mux
  lane drives that input from its own neighbour serializer carrying the complementary
  pattern: a realistic standard-cell edge, toggling every UI, which is the worst case.

## Consequences

- `sim/redundancy-mux/` is a new family of the T1 item 5 (analog) campaign, with the shared
  record harness (`sim/harness/batch_record.sh`) and no second submit path.
- `design/` and `rtl/` are unchanged. Nothing is instantiated, nothing is re-synthesized,
  and no existing record is touched.
- The measured numbers are a property of **one minimum-strength `sg13g2_mux2_1`** in the
  declared position. A sized remap stage (`sg13g2_mux2_2` exists in the same library) or a
  buffered one would give different numbers; this record fixes the stand-in so that a later
  comparison has a baseline, and does not claim the stand-in is the eventual
  implementation.
- If a measured term does not fit the T-13 or T-20 allocation, the record says so and a
  follow-up is filed. No bound is relaxed on this record's account. **This happened**: the
  first record under this decision (`sim/redundancy-mux/records/20261113T160050Z/`) measures
  a common added delay of up to 0.184 UI, which exceeds T-20's whole 0.10 UI target on its
  own at 30 of the 45 corners; at the other 15 (the 1.32 V corners of `mos_ff`, `mos_sf`,
  `mos_tt` and `mos_fs`, plus `mos_ff` at 1.20 V) it reads 0.071 .. 0.099 UI. At **every**
  corner it is far larger than the ~0.0045 UI left of #177's 0.1075 UI static-off-centring
  allocation after the clock path's 0.103 UI (#54), so it does not fit anywhere on the grid.
  That is filed as #232 — which also owns the two ways out this record
  rejected assuming, a sized remap stage and the alternative placement — and no bound moved.
