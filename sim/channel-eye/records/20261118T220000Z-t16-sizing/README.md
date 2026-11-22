# T-16 pad-loading sizing study (issue #251, operator ruling `design`, 2026-11-18)

Kind: **simulated**, CH-3MM-RC (a *declared* channel model), PDK v0.3.0, klt 0.9.0 batch fleet.
Append-only study summary; it holds no new measurement of its own, only the table below built from
the five graded records it names. Nothing in `spec/` moved: the 470-530 ps window, the declared
+20 % C corner (DR-0005) and the T-08 / T-24 limits are untouched.

## Runs (all `klt sim --backend batch --wait-for-capacity 600`, via `sim/channel-eye/run_t16sizing.sh`)

| record | what |
|---|---|
| `sim/channel-eye/records/20261118T212228Z-t16sz-screen-dpa` | 12 dpantenna candidates, kr = kc = 1.2, mos_ss + mos_fs, 1.08 V, -40/125 C (48 units) |
| `sim/channel-eye/records/20261118T212634Z-t16sz-screen-2kv` | 4 diodevdd_2kv candidates, same corners (16 units) |
| `sim/dc-static/records/20261118T212900Z-t16sz-dc-dpa` | T-06/07/08/11/24/28 for the 12 dpantenna candidates, PVT-FULL (540 units) |
| `sim/dc-static/records/20261118T213814Z-t16sz-dc-2kv` | same for the 4 diodevdd_2kv candidates (180 units) |
| `sim/channel-eye/records/20261118T215132Z-t16sz-fin-S07` | finalist S07, PVT-FULL x the four (kr, kc) pairs (180 units) |

Levers (`esd_sz_dpa.inc`, `esd_sz_2kv.inc`; defaults are the committed cell): `XDp1` side, `XMn1` finger
count (w = 2 um x ng), `XResd` length (w = 2 um). Both diode variants were studied because #196
is still open. **Bench check:** S00 (the committed cell) reproduces the recorded
`t16_dr_cf_long` of 471.331 ps at kr = kc = 1.2 to the digit, so the parametric cell is the committed cell.

## Candidates (screen: T-16 worst margin over the screen corners; T-08 / T-24 over PVT-FULL)

| id | diode | XDp1 side (um) | XMn1 ng (w=2u*ng) | XResd l (um) | T-16 worst margin (ps) | binding | value (ps) | T-18 eye (mV) | T-08 min (ohm) | T-24 worst (fF) | T-08 / T-24 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S04 | dpantenna | 2.5 | 10 | 2 | 3.32 | `t16_dr_cf_long` | 473.32 | 350 | 42.86 | 87.69 | pass / pass |
| S02 | dpantenna | 3.5 | 10 | 2 | 2.46 | `t16_dr_cf_long` | 472.46 | 348 | 42.86 | 91.45 | pass / pass |
| S11 | dpantenna | 3.5 | 5 | 1 | 22.33 | `t16_dr_cr_long` | 492.33 | 456 | 42.86 | 86.29 | pass / pass |
| S09 | dpantenna | 3.5 | 5 | 2 | 3.60 | `t16_dr_cf_long` | 473.60 | 349 | 42.86 | 86.29 | pass / pass |
| S03 | dpantenna | 3 | 10 | 2 | 2.92 | `t16_dr_cf_long` | 472.92 | 349 | 42.86 | 89.42 | pass / pass |
| S10 | dpantenna | 3 | 5 | 1 | 22.47 | `t16_dr_cf_long` | 492.47 | 458 | 42.86 | 84.26 | pass / pass |
| S07 | dpantenna | 4.5 | 10 | 1 | 21.70 | `t16_dr_cf_long` | 491.70 | 450 | 42.86 | 96.42 | pass / pass |
| S00 | dpantenna | 4.5 | 10 | 2 | 1.33 | `t16_dr_cf_long` | 471.33 | 346 | 42.86 | 96.42 | pass / pass |
| S08 | dpantenna | 4.5 | 10 | 0.5 | 26.68 | `t16_dr_cr_long` | 496.68 | 501 | 42.86 | 96.42 | pass / pass |
| S06 | dpantenna | 4.5 | 2 | 2 | 3.26 | `t16_dr_cf_long` | 473.26 | 347 | 42.86 | 87.70 | pass / pass |
| S05 | dpantenna | 4.5 | 5 | 2 | 2.46 | `t16_dr_cf_long` | 472.46 | 347 | 42.86 | 91.26 | pass / pass |
| S01 | dpantenna | 4 | 10 | 2 | 1.94 | `t16_dr_cf_long` | 471.94 | 347 | 42.86 | 93.78 | pass / pass |
| K02 | diodevdd_2kv | 4.5 (n/a) | 10 | 1 | 22.07 | `t16_dr_cr_long` | 492.07 | 446 | 42.86 | 108.92 | pass / fail |
| K00 | diodevdd_2kv | 4.5 (n/a) | 10 | 2 | 0.40 | `t16_dr_cf_long` | 470.40 | 349 | 42.86 | 108.92 | pass / fail |
| K03 | diodevdd_2kv | 4.5 (n/a) | 5 | 1 | 22.38 | `t16_dr_cr_long` | 492.38 | 448 | 42.86 | 103.77 | pass / fail |
| K01 | diodevdd_2kv | 4.5 (n/a) | 5 | 2 | 1.59 | `t16_dr_cf_long` | 471.59 | 350 | 42.86 | 103.92 | pass / fail |

"T-16 worst margin" is the smaller of (value - 470 ps) and (530 ps - value) over the eight T-16 edges
at the screen corners only, so it is a ranking, not the graded margin. T-08 min is the smallest margin
bound, `t08_rout_up_ohm` at ff/-40 C (bounds 40-80 ohm); it does not vary across candidates.

## What the study shows

1. **The lever is `XResd`, not the shunt C.** Shrinking `XDp1` (4.5 -> 2.5 um) or `XMn1` (ng 10 -> 2)
   buys 0.6-2 ps. Halving `XResd` (2 -> 1 um) buys about 20 ps, 0.5 um about 25 ps. In the channel bench
   `XResd` is the series resistor between the TX cell (and its secondary diode / `XMn2`) and the
   channel-side pad diode `XDp1` / `XMn1`; that RC is term C of record `20261111T231422Z-t16attr`.
2. **T-08 is unaffected by every candidate and T-24 does not get worse.** In the dc-static assembly the driver
   sits on `PAD` ahead of `XResd`, so T-08 cannot see it; T-24 is identical for S00/S07/S08 (96.42 fF).
   Caveat: that independence is a property of the dc-static pin assembly, which differs from the channel
   bench's (the I/O-cell assembly is a separate issue).
3. **2kv diode (DR-0018) is worse for this row and does not fit T-24 at any candidate** (103.8-108.9 fF
   against 100): at the committed `XResd` its T-16 margin is 0.40 ps. `XResd` = 1 um recovers 22.07 ps there too,
   so the T-16 conclusion holds whichever diode #196 selects; T-24 is #196's problem, not this one's.
4. **T-25 is not evaluated, and `XResd` is the T-25-relevant element.** It is the series isolation between the
   pad and the receiver gate / secondary protection (`XDp2`, `XMn2`). Halving it halves that resistance.
   No ESD-transient simulation exists in this repo (DR-0017, `design/README.md`), so this study cannot say
   whether 1 um is acceptable for T-25; it is a cost of the change and is stated, not measured.

## Finalist S07 (`XResd` l = 1 um, all else committed), PVT-FULL x four spread pairs

180/180 units graded, **every row pass in all four groups, fail = 0, error = 0** (`klt` exit 0).

| (kr, kc) | T-16 binding measurement | value (ps) | margin to its edge (ps) | binding corner |
|---|---|---|---|---|
| 0.8 / 0.8 | `t16_df_cr_short` | 510.081 | 19.92 (upper) | mos_sf/-40C |
| 0.8 / 1.2 | `t16_df_cr_short` | 510.020 | 19.98 (upper) | mos_sf/-40C |
| 1.2 / 0.8 | `t16_dr_cr_long` | 490.219 | 20.22 (lower) | mos_sf/-40C |
| 1.2 / 1.2 | `t16_dr_cr_long` | 490.051 | 20.05 (lower) | mos_sf/-40C |

Worst-case T-16 margin at the declared spread: **19.92 ps** (was **1.331 ps**, binding `mos_ss/mixed/-40C`,
kr = kc = 1.2, `t16_dr_cf_long`). The binding corner moved from `mos_ss` to `mos_sf`, and the spread now moves
T-16 by under 1 ps, so the +20 % C corner no longer consumes the margin. Collateral rows at the finalist:
T-18 eye height >= 450 mV (was 346 mV), T-26 simulated energy <= 0.696 pJ (limit 1 pJ), T-15, T-09, T-01 pass.

## Not claimed

- The T-16 **STAT** leg (Monte Carlo, fails its 7-sigma gate at the nominal channel, `sim/mc/README.md`)
  was **not re-run** and is not claimed improved.
- **T-20:** T-16's 0.030 UI allocation and the 7.5 ps closure of the budget table are unchanged. The skew
  from 500 ps at the worst spread corner is now 10.1 ps (was 28.7 ps) against that 30 ps allocation; no T-20 run was made.
- **T-25** (above) and the layout: `layout/` predates DR-0017 and is stale against the netlists (#140); this
  change does not regenerate it, DRC / LVS were not re-run, and the layout still carries the old `XResd` length.
- `design/aib_pad_esd_2kv.spice` (the DR-0018 variant, not committed) still has `l=2u`; it waits on #196.
