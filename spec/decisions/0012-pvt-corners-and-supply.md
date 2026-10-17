# DR-0012: PVT corners and the I/O supply tolerance

**Status**: accepted. **Rows**: all analog rows (PVT-FULL).

## Context

The issue asks for MOS process corners, supply tolerance on the I/O supply
"(confirm from the PDK docs)" and −40 … +125 °C (proposed).

## What the PDK documents say

- The PDK documents read (process spec Rev. 1.2, layout rules Rev. 0.4, the
  `sg13g2_io` README) state *supply voltages* (1.2 V thin oxide, 3.3 V thick oxide;
  PDK-proc §1) but **no supply tolerance in prose**.
- The only machine-readable tolerance is the `sg13g2_io` liberty corner set (PDK-io
  `lib/`): `slow_1p08V_3p0V_125C`, `typ_1p2V_3p3V_25C`, `fast_1p32V_3p6V_m40C` for the
  1.2 V domain (and 1p35/1p5/1p65 for a 1.5 V domain), with core ±10 %, I/O 3.0-3.6 V
  around 3.3 V, and −40 °C, 25 °C and 125 °C.
- MOS corners: `mos_tt`, `mos_ss`, `mos_ff`, `mos_sf`, `mos_fs` in
  `cornerMOSlv.lib` (thin-oxide devices).

## Decision

The I/O supply of this block is VDDIO = the 1.2 V domain (signalling is thin-oxide,
DR-0004; no 3.3 V device is in the data path). Tolerance ±10 % (1.08 / 1.20 / 1.32 V),
taken from the liberty corner set, **stated as inferred from those corners and not
as a documented specification**. Temperature −40, 27, 125 °C. Process: the five MOS
corners. PVT-FULL is their 45-point product; worst-case pairs are `mos_ss`/1.08 V/125 °C
and `mos_ff`/1.32 V/−40 °C, with `mos_sf`/`mos_fs` added for skew-class rows.

## Alternatives rejected

- **±5 % supply.** Tighter than anything the PDK files show; it would flatter timing.
- **Corner-only (no mismatch).** Skew and threshold rows are statistical (T-10, T-13 to
  T-16, T-19); a corner without `SIM-MC` would not see them.
- **Using the 3.3 V domain for signalling.** Larger swing, slower, more energy; the
  thick-oxide devices are for the PDK's pad cells.

## Follow-up

If the IHP documentation states a supply tolerance, a new record replaces the inference
with the citation.
