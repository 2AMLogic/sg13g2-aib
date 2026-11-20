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
| `test_channel_model.py` | offline self-test: nodal solver of the netlist text, seeded netlist edits, post-processor wiring |
| `records/<UTC>/` | append-only run records |

## Method

Expected values are parsed from `spec/channel-model.md` by the generator, never restated.
The bench instantiates `chan_rlc` four times: a far-end-shorted and a far-end-open copy
with `len_mm`, `kr` and `kc` passed from the sweep, and the same pair with **no** parameters
(the subcircuit's own defaults, what consumers such as `sim/channel-eye` instantiate). Next
to them sit reference ladders built from the parsed table (swept, and fixed at the declared
3 mm nominal for the default pair). It grades DUT/reference **ratios**, each twice (`_default`
suffix for the default pair):

- `t12_r_ratio`: DC operating point, far end shorted, 1 A drive; the reference's R arms sum
  to `kr · r_mm · len_mm`.
- `t12_c_ratio`: open-end impedance at 1 MHz. The reactance is `−1/(ωC)`, so the ratio of DUT
  capacitance to the declared value is the **reference** reactance over the DUT's. The
  reference's shunt C sums to `kc · c_mm · len_mm + cfar`.
- `t12_l_ratio`: `Im Z` of the far-end-shorted network at 10 MHz. All ten series inductors
  carry the same loop current, so each weighs equally and a defect in any single section moves
  the total (an open-end read weights each inductor by the current behind it and cannot see an
  error near the receiver).

Why differential: the shorted read carries an inductance bias from the ladder's own R-C
structure (about 3 % of L at 3 mm, 12 % at 5 mm with kr 1.2). It is a property of the declared
ladder and appears identically on both sides, so it cancels in the ratio. The generator
docstring has the derivation. The generator reads the target, fallback and stretch columns of
the table and refuses a table where they differ, since the bench supports one value per
quantity.

## Tolerance

**±1 %** on each ratio. This is a numerical-agreement tolerance, a property of the check and
**not a spec bound**; no Target, Fallback or Stretch value changes. It is wide enough to
absorb solver noise (the offline solve of the committed netlist stays within 1e-5) and narrow enough that
any of the seeded defects below leaves the band by 10 % or more.

## Negative control

`test_channel_model.py` solves **the netlist text** (`channel_rc.cir` parsed: defaults,
`.param`s, every R/L/C, zero-volt sources) with a nodal solver, runs the same extraction as
the request, and seeds defects by editing that text: wrong `r_mm`/`c_mm`/`l_mm`/`cfar`
defaults, `kr` or `kc` dropped from a section expression, the `Cfar` device removed, one
series inductor +20 % (at either end of the ladder), and a changed DUT default of `kr` or
`len_mm` (only the default-instance pair sees those). Each must leave the ±1 % band; the C
tolerance edges are exercised in both directions at ±1 %.

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
