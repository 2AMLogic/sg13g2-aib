# DR-0004: signalling, driver, receiver

**Status**: accepted. **Rows**: T-06, T-07, T-08, T-09, T-10, T-11, T-26.

## Context

AIB 1.2 specifies a 0.7-0.9 V output swing with a minimum high of 0.7 V
(§4.1 Table 17). Its appendix (§7.1.2) says that for one named
interposer implementation the I/O-buffer supply (VCCIO) varies between 0.75 V and
0.97 V, so the swing is that of a sub-1 V I/O supply. SG13G2's thin-oxide devices are
a 1.2 V technology (PDK-proc §1: thin oxide for the 1.2 V logic, thick oxide for
a 3.3 V supply). The issue asks: core-supply CMOS, or reduced swing?

## Decision

Full-rail CMOS at VDDIO (1.2 V nominal, thin-oxide devices only), unterminated,
point-to-point, with a driver output impedance of 40-80 Ω chosen to source-match
the 50 Ω channel (channel-model.md) within ±40 %. The receiver is an
inverter-class stage with its threshold within ±60 mV of VDDIO/2 (inside the ±90 mV
eye-height mask with margin) at every corner including 3σ mismatch (T-10, statistical), and no deliberate hysteresis
(≤ 60 mV if added, below the ±90 mV eye-height mask). Overshoot is limited by
applying AIB 1.2 §4.2 Table 18 with this repo's own VOS (0.25 × VOS, ≤ 0.4 ns).

This is a **deliberate deviation from AIB 1.2's swing** (T-06). It is recorded
here and is the reason the spec is "Gen1-class" and not a conformance claim.

## Alternatives rejected

- **Reduced swing (0.7-0.9 V) as the baseline.** It needs a second, lower, regulated
  rail and a level-restoring receiver; the repo specifies no such rail, and
  CLAUDE.md keeps reduced swing in the stretch column and forbids letting the
  stretch drive architecture before 1 Gb/s closes.
- **Terminated (parallel or series-parallel) signalling.** AIB 1.2 is unterminated
  (Table 17 has no termination parameter), and termination current costs energy per
  bit on every wire; the channel is a few millimetres.
- **A driver with no impedance requirement** (minimum-size inverter). On an
  unterminated 50 Ω line it would be far from matched and the overshoot row (T-09)
  would decide the sizing late; stating the range now lets the testbench check it.

## Energy cost of this choice (arithmetic, not a result)

A full-swing wire load of 0.70 pF (channel 0.60 pF plus far-end 0.10 pF) at
1.2 V draws C·V² = 1.0 pJ per rising edge; random data toggles on half the bits,
so the channel load alone is about 0.50 pJ/bit at nominal and about 0.61 pJ/bit
at 1.32 V, before driver internals, receiver and the clock share (about
0.05 pJ/bit for a clk/clkb pair over 40 data bits). The 1 pJ/bit target (T-26) is
therefore plausible but not slack, and the 0.5 pJ/bit stretch is out of reach at
full swing on this model: it needs reduced swing or a shorter channel. That is one
more reason the stretch is not allowed to shape the architecture. These are
pre-simulation figures and set no recorded result.
