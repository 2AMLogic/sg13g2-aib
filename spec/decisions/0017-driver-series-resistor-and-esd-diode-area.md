# DR-0017: driver series resistor and primary ESD diode area (T-08, T-24, T-25)

**Status**: proposed; ratified by the merge of the pull request that carries it
(DR-0001, issue #130).
**Rows**: T-06, T-08, T-24, T-25. **Amends**: nothing. No spec row changes; this records
a design trade that DR-0008 §2 left open ("T-24 and T-25 trade against each other").

## Context

The first dc-static PVT-FULL run (`sim/dc-static/records/20261108T002904Z/`) failed T-06
(loaded), T-08 and T-24 (issue #130). Measured, 45 corners:

- MOS-only output resistance spreads 46.6-110.8 ohm (pull-up, 2.38x) and 40.3-86.1 ohm
  (pull-down, 2.14x). T-08 allows 40-80 ohm, a 2.0x window. No output-device width closes a
  spread wider than the window: scaling to put the maximum under 80 ohm puts the minimum under
  40 ohm (28u/14u -> 56u/28u gave 52.1/23.0 ohm at ss/1.08 V/125 C and ff/1.32 V/-40 C).
- Pin capacitance was 102.2-126.2 fF. The primary diode `XDp1` (10u x 10u) was 75 of the
  126 fF at pad = VDDIO (breakdown: `sim/dc-static/README.md`).

## Decision

1. Put a series poly resistor (`rppd`, `w=10u l=0.5u`, about 18 ohm, nearly flat across
   `res_wcs`/`res_bcs`) between each output device and PAD, and size the devices at
   `XMp` 54u and `XMn` 22u. The poly leg compresses the Ron spread into the T-08 window.
2. Shrink the primary diode `XDp1` from 10u x 10u to 4.5u x 4.5u. The wider driver adds
   about 20 fF, so T-24 closes only if the diode gives it back. 5u x 5u passed 45/45 with
   0.64 fF of margin and was not kept.
3. Result (`sim/dc-static/records/20261108T004350Z/`, 45/45 corners): T-06 droop <= 0.075 V,
   T-08 pull-up 42.9-75.1 ohm and pull-down 44.4-72.7 ohm, T-24 worst 96.4 fF. T-07, T-11
   and T-28 unchanged. The spec rows and their limits are unchanged.

## What is not shown

**T-25 is neither met nor failed by this record.** The primary diode is now 20 um^2, one
fifth of the first-cut area. It is a different device from the one DR-0008 sized: DR-0008's
35 um^2 per diode is the `diodevdd_2kv`/`diodevss_2kv` pad-diode model in `sg13g2_esd.lib`,
while `XDp1` is the `dpantenna` model (`diodes.lib`), an antenna diode whose own header says it
is designed for the reverse direction. Its area series resistance is rs = 1.728e5 per unit
area, about 8.5 kohm at 20 um^2 (about 1.7 kohm even at the first-cut 100 um^2). So a T-25
transient on this device type would not be credible, and the T-25 path likely needs the
ESD-library diodes, which bears directly on the DR-0008 §2 fallback invoked below. No
clamp-transient `SIM` at the 0.5 A pulse exists in this repo yet, so the claim "the ESD stage
is adequate" is not made and the first-cut area was itself unverified. The series resistor `Resd` and `XMn1`, `XMclamp`
are unchanged.

If the T-25 transient `SIM` or the `LAYOUT` area check shows the reduced diode cannot carry
the pulse, the pair T-24 / T-25 cannot close in this cell at this driver, and DR-0008 §2
applies: the PDK's own I/O cells at 80 um pitch (T-22 fallback), by a new decision record,
not a relaxation of T-24 or T-25.

## Alternatives rejected

- **Widening the MOS only.** Cannot close T-08 (spread exceeds the window), measured above.
- **Relaxing T-08 or T-24, or moving the 1 mA load.** The spec is not relaxed to make
  results pass.
- **Dropping the primary diode.** Rejected in DR-0008 (an unprotected pin).
- **An impedance-calibration loop.** Would close the spread without poly but is a new
  block (control, replica, update logic) outside this issue.

## Effects on other rows (not re-run here)

The series resistor and wider devices change the driver's output edge and the pin load seen
by the dynamic rows. T-09 (overshoot/undershoot, #53) and the clock path (#54) must be run
on these netlists; their earlier results, if any, do not carry over.

**Layout, LVS and signoff evidence are stale (tracked in #140).** This record changes the
analog netlists but not the committed layout. At this head `layout/gen_io_column.py` fails its
own `check_against_netlists()` (Mp 28 fingers with D=PAD, Mn 14 fingers, Dp1 10.0 um, no
`Rsp`/`Rsn`), the `layout/lvs/*.ref.spice` fail `gen_reference.py --check`, and the analog DRC
and LVS records cited under signoff items `3.analog` / `4.analog` describe the old circuit.
Those two citations are removed from `signoff/block-manifest.json` so the items grade unmet
for this design, and the record is regenerated (`t1_met_count` 18 to 16). T-22 (pitch, a
`LAYOUT` row) and the `LAYOUT` half of T-25 are not evaluated for the wider driver: 54 + 22
fingers come to about 43 um of the ~54 um routable width before the two 10 um `rppd` legs are
placed, which is not verified. Regeneration is issue #140.
