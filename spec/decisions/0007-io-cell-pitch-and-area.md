# DR-0007: I/O cell pitch, area and pad capacitance

**Status**: accepted. **Rows**: T-22, T-23, T-24.

## Context

AIB 1.2 sizes its Gen1 timing against a 55 µm microbump pitch (§4.1 note; Table 4
for channel sizing at ≤ 55 µm). The shuttle part is wire-bonded, not bumped. The
PDK's own I/O cells are 80 µm wide by 180 µm deep (PDK-io LEF) and carry the
protection for a 3.3 V I/O domain. PDK layout rules give a recommended minimum pad
width of 30 µm and space of 8.4 µm (Pad.aR, Pad.bR), a recommendation of no devices
under a pad (Pad.jR), and 25 µm to the seal ring for wedge bonding (Pad.dR note 1)
(PDK-lay §6.9).

## Decision

Pitch 55 µm (target), 80 µm (fallback, the PDK cell width), 40 µm (stretch; the
physical floor is 38.4 µm = Pad.aR + Pad.bR). Area per wire ≤ 55 µm × 100 µm
(5500 µm²); the depth is chosen so a 20-wire column is 1.1 mm long. Because
Pad.jR recommends no devices under the pad, the I/O cell sits beside its pad, so
the 100 µm depth must hold the driver, receiver, ESD and the redundancy mux
*alongside* a pad that is at least 30 µm wide. Pad plus ESD plus receiver input
capacitance at the pin ≤ 100 fF (T-24), which is also the far-end load in the
channel model.

The area row is labeled **simulated / pre-layout estimate**: area is a layout
quantity and nothing is drawn yet; it is replaced by `klt stats` of the extracted
cell when the layout exists.

## Alternatives rejected

- **Reusing the PDK I/O cells.** They are 80 µm wide (fails the 55 µm target), carry
  3.3 V-domain protection and pad capacitance in the pF range for a 1.2 V
  signalling that does not need it. Kept as the fallback pitch only.
- **Stacking the cell under a bond pad.** Pad.jR recommends against it (mechanical
  stress) and the PDK states a damage risk.
- **A tighter stretch pitch below 38.4 µm.** Below the recommended pad geometry.

## Open

A 55 µm pitch is a *bump* pitch in AIB 1.2. A wire-bond pad row does not need
it; it is kept because the I/O cell is the thing under test (the cell must fit the
pitch the class it names uses). The shuttle's pad pitch is a test-configuration
matter (DR-0009), not this row.
