# DR-0027: T-04's arrangement leg is the clock-path netlist, not `RTL`

**Status**: **proposed**. Not ratified; ratification follows
[DR-0001](0001-spec-structure-and-ratification.md) and is a human merge.
**Rows**: T-04. **Amends**: the verification token of T-04 set by
[DR-0026](0026-t02-t04-drop-sim-leg.md), item 2 (the `RTL` token for the arrangement), and the
matching statement in [DR-0022](0022-t02-t04-sim-legs.md). **Changes no value**: no Target,
Fallback or Stretch cell moves, and no bound is added.

## Context

DR-0026 left T-04 naming `RTL` for its arrangement (clk and clkb both driven and received,
converted to single-ended at the RX) and noted that the item 6 digital partition omits T-04 (issue
#327). Measured at `95d2e00`: `rtl/aib_datapath.v` has a single-ended `clk` and `rx_clk`; no RTL
source or RTL test mentions a complement clock. The `RTL` leg for T-04 is therefore not checked
anywhere, and cannot be: the arrangement is not in the synthesized data path. It exists in the
analog clock path (`design/aib_tx_clk.spice`, `design/aib_rx_clk.spice`, wired in
`sim/clock-path/tb_clock_path.cir`).

## Decision

1. **T-04's arrangement leg is named `NETLIST`**: a structural assertion over the clock-path
   netlists, `sim/clock-path/check_clk_pair.py`, run in CI through `scripts/ci/check_local.sh`.
   It asserts that both TX outputs are driven by distinct drivers, each is connected through the
   channel to its own RX input, and the RX emits a single-ended output per input. It fails if clkb
   is unconnected, shorted to clk, or not converted. It measures nothing.
2. **The T-04 verification cell in `spec/target-spec.md` changes only that token.** Everything
   else in the cell, including "no `SIM` leg" and the reported-evidence wording, stands.
3. **The item 6 digital partition is unchanged.** T-04 stays out of
   `scripts/ci/gen_item6_digital.py`'s `DIGITAL` set (a determinism claim about RTL that does not
   contain the arrangement would be false); `signoff/item6/*` is not edited.

## Scope of the claim

The check holds for the modeled-channel testbench arrangement (CH-3MM-RC netlist wiring) only. It
says nothing about a real die-to-die channel, and nothing about the clk/clkb crossing level.

## Alternatives rejected

- **Add T-04 to the item 6 digital partition.** The RTL has no complement clock to be
  deterministic about.
- **Add clk/clkb ports to `aib_datapath.v` so `RTL` has something to check.** That changes the
  synthesized data path for a row that is analog by nature; if the operator prefers it, it is a
  separate PO-level change.
