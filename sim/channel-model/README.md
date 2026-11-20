# Channel-model conformance family (T-12)

`spec/channel/channel_rc.cir` (`chan_rlc`, ten RLC pi-sections) is hand-written, and
T-01, T-09, T-15, T-16, T-18 and T-26 all take it as input. This family checks the one
thing about it that is not circular: **that the committed netlist implements the
declared table in [`spec/channel-model.md`](../../spec/channel-model.md)**. It is T-12's
`SIM` leg ("PVT-FULL, plus channel R/C ±20 %", DR-0005). The disposition is in
[DR-0029](../../spec/decisions/0029-t12-conformance-leg.md) (proposed, awaiting
DR-0001 ratification).

## What it shows, and what it does not

- Shows: at CH-3MM-RC, CH-1MM and CH-5MM, at nominal and at each of the four
  (kr, kc) pairs in {0.8, 1.2}, over the 45-corner PVT-FULL grid (675 units), the
  netlist's end-to-end series R, total shunt C (far-end load included) and total series L
  agree with the declared table to within the tolerance below.
- Does **not** show: that the table matches any interposer or silicon (T-12 is CH only),
  that crosstalk is modeled (it is not, DR-0005), or that the section count is right
  (see "Boundary").

## Files

| file | role |
|---|---|
| `gen_channel_model.py` | generator (stdlib); parses the declared table, writes the bench and request; `--check` for staleness |
| `tb_channel_model.cir`, `request_channel_model.json` | generated; do not edit |
| `run_channel_model.sh` | submits the request to the batch fleet (`--wait-for-capacity 600`) via `sim/harness/batch_record.sh` |
| `test_channel_model.py` | offline self-test: exact ideal-ladder solver, seeded defects, post-processor wiring |
| `records/<UTC>/` | append-only run records |

## Method

Expected values are parsed from `spec/channel-model.md` by the generator, never restated.
The bench instantiates `chan_rlc` twice (far end shorted, far end open) next to two
reference ladders built from the parsed table, and grades DUT/reference **ratios**:

- `t12_r_ratio`: DC operating point, far end shorted, 1 A drive; the reference's R arms sum
  to `kr · r_mm · len_mm`.
- `t12_c_ratio`: open-end impedance at 1 MHz; the reference's shunt C sums to
  `kc · c_mm · len_mm + cfar`.
- `t12_l_ratio`: the ω² coefficient of `W = −ω·Im Z_open` between 1 MHz and 10 MHz.

Why differential: the probe-frequency observables of the declared ladder differ from the
lumped constants (R-coupled terms, about 3 % of L at 3 mm on the shorted read and 62 % on the
open two-frequency read). Those corrections are properties of the declared ladder and appear
identically on both sides, so they cancel in the ratio. The generator docstring has the
derivation.

## Tolerance

**±1 %** on each ratio. This is a numerical-agreement tolerance, a property of the check and
**not a spec bound**; no Target, Fallback or Stretch value changes. It is wide enough to
absorb probe-frequency residue (the offline solver bounds it below 2e-3) and narrow enough that
any of the seeded defects below leaves the band by 10 % or more.

## Negative control

`test_channel_model.py` runs the same extraction on an exact ideal-ladder solver and seeds four
defect classes into the DUT only: a wrong `r_mm` default, a dropped `kr` scaling, a dropped
far-end load, a wrong `l_mm`. Each must leave the ±1 % band.

## Boundary

A section-count change that keeps the totals identical moves the probe-frequency reads by
about 1e-5 relative and is **not detectable** by this bench; the signature of the section count
only appears near the ~1.7 GHz section resonance. The bench checks the declared values, their
kr/kc scaling and the far-end load.

## Reproduce

```bash
python3 -I sim/channel-model/gen_channel_model.py --check
python3 -I sim/channel-model/test_channel_model.py
source sim/harness/env.sh && sim/channel-model/run_channel_model.sh   # needs PDK_ROOT, uvx
```

The record lists both `report.json.gz` and a decompressed `report.json` (`gzip -dc`), because
the pinned grader (klt 0.9.0) refuses a `.json.gz` citation (`signoff/README.md`, "The
decompressed `report.json` copies").
