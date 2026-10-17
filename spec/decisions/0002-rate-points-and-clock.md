# DR-0002: rate points and the forwarded clock

**Status**: accepted. **Rows**: T-01, T-02, T-04, T-18.

## Context

CLAUDE.md fixes 1 Gb/s per wire as the target, 500 Mb/s as the fallback and
2 Gb/s as a stretch, and says the 2 Gb/s requirements must not drive architecture
before 1 Gb/s closes. The issue asks to confirm the Gen1 rate envelope from the
specification, not from the README.

## What AIB 1.2 says

- It sets *minimum operating* rates and no maximum: an implementation supports a
  minimum clock rate no greater than 1 GHz, and for the double-data-rate
  configuration a minimum data rate no greater than 2 Gb/s (§1.3.1.2, Table 2).
  The base SDR configuration is a minimum of 1 Gb/s at 1 GHz (§1.3.1.1).
- DDR exchange sends data on both clock edges (§2.1.3.2), so the forwarded clock
  runs at half the data rate. 1 Gb/s per wire is a 500 MHz clock, 500 Mb/s is
  250 MHz, 2 Gb/s is 1 GHz.
- 1 UI is the minimum interval between data changes (§4.1, bullet list under
  Table 17); timing rows are in UI.

So the specification does not define 1 Gb/s, 500 Mb/s or 2 Gb/s as rates. They are
this repo's operating points, which sit inside the range the specification leaves
open, and the target is chosen by CLAUDE.md, not derived.

## Decision

DDR at 1 Gb/s per wire (500 MHz clock, UI 1000 ps) as the target; 500 Mb/s
(250 MHz, UI 2000 ps) as the fallback; 2 Gb/s (1 GHz, UI 500 ps) as a stretch that
does not drive architecture. An SDR path exists as a test mode (T-02). The clock
is forwarded quasi-differentially (clk and clkb), as AIB 1.2 §2.1.6.3 describes,
because the differential crossing gives the receiver a threshold-independent
sampling edge.

## Alternatives rejected

- **SDR as the baseline.** AIB 1.2 §2.1.3.1 SDR sends on one clock edge, so a
  500 MHz clock would carry only 500 Mb/s. Reaching 1 Gb/s per wire in SDR needs a
  1 GHz clock on the channel; DDR halves the clock activity and the DLL's
  frequency (dll-interface.md).
- **A single-ended forwarded clock.** Saves one pad per direction but makes the
  capture instant depend on the receiver threshold; it is kept only as the
  fallback arrangement for T-04.
- **2 Gb/s as the target.** The timing budget does not close with margin on these
  allocations (target-spec.md, Timing budget), and CLAUDE.md rules it out.

## Consequences

The DLL canary's 1 GHz target corresponds to this repo's stretch, not target
(dll-interface.md, gap G1).
