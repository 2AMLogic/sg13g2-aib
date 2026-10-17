# DR-0008: ESD level for a die-to-die pad (open question 1)

**Status**: accepted as a target with an explicit statement that realizability
at the ratified pitch is **not shown**. **Rows**: T-24, T-25.

## The question

What ESD level is appropriate for pads that only see a die-to-die assembly, and can
the PDK's ESD devices and rules realize it at the ratified pitch?

## Evidence (read, with sources)

- **AIB 1.2 §4.3 Table 19**: at 55 µm pitch, minimum discharge voltage (CDM) 70 V
  and 0.5 A discharge current; 10 µm pitch TBD. No human-body-model level is given.
- **The PDK documents do not state a protection level.** PDK-lay §6.8 says "refer to
  the ESD documents for details about protection level" and only defines recognition
  of the clamp devices `nmoscl_2`, `nmoscl_4` and `scr1` (text labels in `Recog:esd`).
  The PDK `v0.3.0` `libs.doc/doc` holds three PDFs (EM overview, layout rules, process
  spec); no ESD document is among them.
- **`sg13g2_esd.lib`** (PDK `v0.3.0`) gives pad diode models named `diodevdd_2kv`,
  `diodevss_2kv`, `diodevdd_4kv`, `diodevss_4kv`. The names say 2 kV/4 kV; the file does
  not say which test model they mean, and this repo does not equate them with CDM.
  The model parameters: pad-to-VDD diode `cj0 = 8.716e-16`, `area = 35` (2kv), series
  `rs = 289.6`; VSS-to-pad diode `cj0 = 9.42e-16`, `area = 35`, `rs = 200`.
- **`sg13g2_bondpad.lib` is an empty placeholder** (no electrical content), so pad
  capacitance has no PDK model.
- The PDK I/O library's own cells carry a secondary-protection stage and large clamps
  for a 3.3 V domain at 80 µm pitch (PDK-io SPICE: `sg13g2_SecondaryProtection`,
  `sg13g2_Clamp_*`).

## First-order arithmetic (not a simulation result; inputs are the model values above)

If `area` is in µm² as the area/perimeter pair suggests, junction capacitance at zero
bias is `cj0 × area` ≈ 30 fF (VDD diode) + 33 fF (VSS diode) ≈ 64 fF for a 2kv-class
pair, ≈ 127 fF for 4kv-class. The 2kv-class pair alone uses about two thirds of the
T-24 target of 100 fF, and the 4kv-class pair exceeds it. Series resistance scales
as `rs/area` ≈ 8.3 Ω (VDD diode) and 5.7 Ω (VSS diode), so a 0.5 A pulse drops
about 3-4 V across a diode by ohmic loss alone, far above the 1.2 V domain supply:
the ESD path needs more diode area, a series resistor with
a secondary stage, or both, each at the expense of T-24 (capacitance) and T-19/T-20
(bandwidth and margin).

## Decision

1. The target is the AIB 1.2 Table 19 level at 55 µm pitch (CDM 70 V, 0.5 A), because
   the assembly sees only controlled in-package handling and that is the level the
   class names (T-25). No HBM level is claimed.
2. T-24 and T-25 trade against each other and **are not both shown achievable**. They
   are ratified as the target pair; the answer to "can the PDK realize it at this pitch"
   is: *not shown here, and not answerable from the PDK documents; it is answered by
   the clamp-transient `SIM` of T-25 and the `LAYOUT` area check*. If that evidence
   shows the pair cannot close, the fallback applies by a new decision record: the
   PDK's own I/O cells at 80 µm pitch (T-22 fallback), not a quiet relaxation of T-25.
3. The test configuration's bond pads face the package and board and need more than
   the die-to-die level. Whether they use the PDK I/O pad cells (full protection, large
   pad) or this cell is decided with the seal-ring and pad-pitch of the shuttle layout
   (test-configuration.md); this record only states that L1 uses internal pins and
   needs no package-level protection.

## Alternatives rejected

- **Claiming a number from a naming convention** (2 kV, 4 kV): the PDK does not say
  what it measures.
- **Dropping ESD to hit T-24.** An unprotected pin is not a die-to-die I/O cell.
- **Copying the PDK pad protection** into the 55 µm cell: its area is why the PDK cells
  are 80 µm wide.

## Follow-ups

Tool gap filed: `2AMLogic/klayout-tools#3854` (the sg13g2 deck evaluates no pad or ESD
rules and recognizes no ESD diode or clamp). The ESD documents the PDK layout rules cite
are an upstream gap this repo cannot fill.
