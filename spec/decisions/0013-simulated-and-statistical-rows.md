# DR-0013: rows labeled simulated, and rows that are statistical

**Status**: accepted. **Rows**: T-10, T-13 to T-16, T-19, T-23, T-26.

## Decision

- **Energy per bit (T-26)** is labeled *simulated* wherever it is quoted. It is the
  integrated supply energy of TX, the channel model and RX over a PRBS-7 stream
  divided by bits delivered, at the headline corner (tt, 1.2 V, 27 °C) and the worst-case
  supply corner. No silicon measurement of it is planned (test-configuration.md).
- **Area per wire (T-23)** is labeled *simulated / pre-layout estimate* until a layout
  exists, then replaced by the extracted figure (`klt stats`); area is a layout
  quantity, and the label states that the number precedes it.
- **Statistical rows** (receiver threshold T-10, TX skew T-13/T-14, RX skew T-15/T-16,
  capture aperture T-19) are marked and need `SIM-MC`: #3 item 6 depends on whether the
  tail meets the row, so the outcome is a mean, sigma and the tail used (14 σ for the
  peak-to-peak budget lines), not a single corner value.

## Alternatives rejected

- **Quoting energy without a label** or from the arithmetic in DR-0004: that is a
  pre-simulation estimate, not a result.
- **Treating skew as a corner result.** The array's skew is a mismatch effect across
  20 cells; a corner sweep sees only the systematic part.
