# DR-0018: dedicated ESD pad diode against T-24 pin capacitance

**Status**: proposed; ratified by the merge of the pull request that carries it
(DR-0001, issue #147).
**Rows**: T-06, T-08, T-24, T-25. **Amends**: nothing. No spec row or limit changes. This
closes the T-24 / T-25 question DR-0017 left open ("the T-25 path likely needs the ESD-library
diodes").

## Context

DR-0017 closed T-24 by shrinking the primary diode `XDp1` to a 4.5u x 4.5u `dpantenna`
(worst pin capacitance 96.4 fF against 100 fF, a 3.6 fF margin). That device is an antenna
diode modelled for the reverse direction; a 0.5 A T-25 discharge through it is not credible.
The PDK's pad diodes are `diodevdd_2kv` / `diodevss_2kv` (and `_4kv`) in `sg13g2_esd.lib`. This
record measures their capacitance and series resistance from the PDK models and re-runs T-24,
T-06 and T-08 with `diodevdd_2kv` in place of `XDp1`.

## Method

- **Units** (`sim/build/pdk/ihp-sg13g2/libs.tech/ngspice/models/sg13g2_esd.lib`, v0.3.0): the
  model cards are L22-L23 and the instances L29-L33 / L47-L50 (2kv, `DEV_A=35`) and L38-L43 /
  L55-L58 (4kv, `DEV_A=70`). Here `area` is the ngspice level-1 multiplier, not um^2 against a
  per-um^2 model: `cj0`, `is` scale with it and `rs` divides by it. So `diodevdd_2kv` is
  cj0 = 8.716e-16 x 35 = 30.5 fF, rs = 289.6 / 35 = 8.3 ohm. `diodes.lib` L80-L87 `dpantenna`
  is the opposite: `DEV_A` is in um^2 against per-um^2 models (`dparea` cj = 8.252e-16 F/um^2,
  rs = 1.728e5 per unit area).
  The `dsub_*` diode inside each subcircuit is VDD to VSS, not on the pad, and does not load it.
- **Extraction** (`sim/dc-static/tb_esd_diode.cir`, `request_esd_diode.json`, 45 corners on
  the fleet): pad small-signal C at 500 MHz, same method as `tb_pin.cir`, at pad = 0, VDDIO/2,
  VDDIO; forward dynamic resistance from the ac admittance at 2 V and 3 V forced past the
  forward rail. `dpantenna` 4.5u x 4.5u is the baseline.
- **Variant** (`design/aib_pad_esd_2kv.spice`): `XDp1` becomes `diodevdd_2kv`, nothing else
  changes. `tb_dc_static_2kv.cir` + `request_2kv.json` re-run the full dc-static set at 45
  corners. The committed `design/aib_pad_esd.*` is not changed.
- **Record**: `sim/dc-static/records/20261110T084631Z/`.

## Results (45 corners, worst case over corners)

Pad capacitance of the diode alone (fF, `esd-diode-report.json`):

| Device | pad = 0 | pad = VDDIO/2 | pad = VDDIO |
|---|---|---|---|
| `dpantenna` 4.5u x 4.5u (DR-0017 `XDp1`) | 11.9 | 13.2 | 15.6 |
| `diodevdd_2kv` (anode PAD, cathode VDDIO) | 22.8 | 26.3 | 34.0 |
| `diodevss_2kv` (anode VSS, cathode PAD) | 36.4 | 28.8 | 25.3 |
| `diodevdd_4kv` | 45.6 | 52.6 | 68.1 |
| `diodevss_4kv` | 72.8 | 57.7 | 50.7 |

Hand check: `diodevdd_2kv` at pad = 0 has 1.2 V reverse bias, so
C = 30.5 fF / (1 + 1.2/0.6621)^0.3294 = 21.7 fF (extraction 20.4-22.8 fF); at pad = VDDIO the
bias is zero and the diode sits at its 30.5 fF cj0, plus the temperature spread and the
forward-bias edge at 125 C (28.2-34.0 fF). It agrees with the model's bias law.

Forward dynamic resistance (ohm, 45 corners, at the forward current shown):

| Device | at 2 V overdrive | at 3 V overdrive |
|---|---|---|
| `diodevdd_2kv` | 8.5-8.6 (0.12-0.13 A) | 8.4-8.5 (0.23-0.25 A) |
| `diodevss_2kv` | 6.0-6.1 (0.16-0.18 A) | 5.8-5.9 (0.33-0.34 A) |
| `diodevdd_4kv` | 4.3 (0.23-0.26 A) | 4.2 (0.47-0.49 A) |
| `diodevss_4kv` | 3.0-3.1 (0.32-0.35 A) | 2.9-3.0 (0.66-0.69 A) |
| `dpantenna` 4.5u x 4.5u | 7573-7706 (0.14-0.16 mA) | 7441-7526 (0.27-0.29 mA) |

The `dpantenna` carries about 0.3 mA where `diodevdd_2kv` carries 0.25 A at the same
overdrive, and its series resistance is about 900 times larger.

T-24 with `diodevdd_2kv` as `XDp1` (`report.json`, 45 corners):

| Pad bias | DR-0017 netlist (`20261108T004350Z`) | `diodevdd_2kv` variant | Limit |
|---|---|---|---|
| 0 | 84.17 fF | 95.10 fF (ss/1.08 V/125 C) | 100 fF |
| VDDIO/2 | 96.42 fF | **108.9 fF** (fs/1.32 V/125 C) | 100 fF |
| VDDIO | 90.26 fF | **108.7 fF** (ss/1.08 V/125 C) | 100 fF |

**T-24 fails by 8.9 fF** (fails in 29 of 45 corners at VDDIO/2 and 44 of 45 at VDDIO; only
pad = 0 passes everywhere). T-06 (droop <= 0.0751 V), T-08 (pull-up 42.9-75.1 ohm, pull-down
44.4-72.8 ohm), T-07 (<= 0.84 uA), T-11 and T-28 are unchanged from DR-0017 because the swap
does not touch the driver. Every 45-corner failure is T-24.

## Options

(a) *The dedicated diode fits T-24.* **Not supported**: 8.9 fF over.

(b) *It fits with a named compensation.* The only named lever is a narrower driver, and T-08
cannot pay for it. First-order estimate from the DR-0017 probe table (28u/14u and 56u/28u,
no series resistor), not simulated here: the driver costs about 0.8-0.9 fF per um of PMOS
width at the 2:1 N/P ratio, so giving back 8.9 fF needs about 10.5 um off the 54u PMOS.
Let a = 28u/W, so the pull-up device resistance is 110.8a ohm at ss/1.08 V/125 C and
46.6a ohm at ff/1.32 V/-40 C, and let a flat series resistance R sit on top. T-08 needs
110.8a + R <= 80 and (110.8a + R) <= 2 (46.6a + R), i.e. R >= 17.6a. Both hold only for
a <= 0.623, W >= 45u. That recovers at most 9u x 0.85 = 7.7 fF, with zero T-08 margin at both
ends, which is 1.2 fF short of the 8.9 fF needed. The pull-down side is less binding.
So no driver width reaches both T-08 and T-24, and the narrowest one that does is not a
margin. Shrinking `DEV_A` below 35 would shrink the capacitance (about 0.75 fF per unit at
VDDIO/2, so `DEV_A` near 23) but is no longer the PDK cell DR-0008 sized and carries about two
thirds of the current. It is not simulated here and is a different decision, not a
compensation. The 4kv diodes are worse (52.6 fF at VDDIO/2 against 26.3 fF). Adding
`diodevss_2kv` as the second half of the pair would add 25-36 fF more on its own, so a full
2kv pair is further out of reach than the single diode tested.

(c) *The pair cannot close.* **Supported.**

## Decision

1. **Recommended outcome: (c).** With the dedicated ESD diode in place, T-24 does not close at
   the T-08-compliant driver, and no driver sizing in this cell closes both. With the
   `dpantenna`, T-24 closes but the diode cannot carry the T-25 pulse (series resistance
   about 7.5 kohm). The two rows cannot both be met in this cell at 55 um pitch with the
   ESD path DR-0008 sized. No row limit is relaxed.
2. The committed `design/aib_pad_esd.sch` / `.spice` are **not changed**. `aib_pad_esd_2kv.spice`
   is evidence only.
3. DR-0017 stands for what it recorded (T-24 closed at 96.4 fF on the antenna diode). Its
   claim cannot be taken as "the ESD stage is adequate": this record shows that closing T-24
   that way left the ESD path unable to carry T-25.
4. **Proposed separate decision (not made here, each needs its own key review per DR-0008
   §2):** either the PDK's own I/O cells at 80 um pitch (the T-22 fallback), or a lower
   T-25 target. Neither is chosen or relaxed in this record.

## What is not shown

- **The 0.5 A clamp transient** (the `SIM` half of T-25) is not run: the forward resistance
  above is a small-signal extraction at 0.12-0.7 A forced DC, not a discharge pulse, and says
  nothing about clamp triggering, voltage overshoot at the pad or peak temperature.
- **The `LAYOUT` area and current-path check** (the `klt` half of T-25) is not run.
- T-24 is an extracted-capacitance estimate (model small-signal admittance), without
  bond-pad or post-layout parasitics.
- The driver-width bound in option (b) is first-order arithmetic on DR-0017 probe data (flat
  series R, 1/W scaling), not a 45-corner run.

## Effects on other work

If a later decision adopts the dedicated diode, the netlist changes `XDp1` and the layout
targets of #140 change with it (`layout/gen_io_column.py` `check_against_netlists()`, the
`layout/lvs/*.ref.spice` references, the analog DRC/LVS records), and the T-09 re-run (#146)
must use that netlist. Until then neither moves. This record edits no layout file.

## Tool friction

Filed on the tool tracker, generically: `2AMLogic/klayout-tools#5221` (`klt sim` reports no
per-measurement min/max over corners for limit-less extraction measurements; the ranges above
were computed from `corners[].measurements[]`). The deck question for ESD diodes
(`2AMLogic/klayout-tools#3854`) is a layout/DRC matter and not exercised here.
