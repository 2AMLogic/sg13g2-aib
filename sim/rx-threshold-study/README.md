# sim/rx-threshold-study

Sizing study of the `aib_rx_data` input stage for T-10 (issue #386). T-10 fails on the
committed cell as a **systematic corner shift, not mismatch**: 8 of 45 PVT-FULL corner
means sit outside the ±60 mV limit (every `sf` corner except `sf/1.080V/-40C`, up to
79.0 mV at `sf/1.320V/125C`), per-corner σ is only 4.9–6.8 mV, and the corner-mean span
is 84.9 mV against a 120 mV window — a 121.5 mV ±3σ envelope (`sim/mc/per_corner.md`,
record `sim/mc/records/20261108T035315Z-t10/`), so no re-centring of the present cell
closes the row. This study screens first-stage candidates on the T-10 bench form,
confirms the selected one by Monte Carlo, and measures its side effects. **It changes no
`design/`, `layout/`, spec or manifest file**: candidates are study cells in
`cand_cells.inc`, inlined into the benches; the T-10 row and item 6 stay honestly
`unmet` until an adoption lands a passing record on a committed cell.

**Simulated, pre-layout**, on the batch fleet through `run_rx_threshold.sh` (one leg per
record; `--wait-for-capacity 600`, append-only `records/<UTC>-<leg>/`). Design revision
simulated: `design/aib_rx_data.spice` as of `df5bcfa` (`XMi1p` w=2.5u, `XMi1n` w=1u,
both l=0.13u ng=2 — `w` is total width, the PDK device splits it into `ng` fingers;
restore stage `XMi2p`/`XMi2n` 4u/2u l=0.13u ng=2).

## Outcome (one of the two the issue allows)

**(a) holds: a candidate is named, confirmed by Monte Carlo, side effects measured,
adoption issue filed.** The candidate is **`vref`**, a supply-referenced input stage:
an NMOS pair (input vs a matched `rppd` VDDIO/2 divider) with a PMOS mirror load and a
~100 µA tail, restore inverter at half the committed width (`cand_cells.inc`, study
cell `rx__vref`). Comparing the pad against a divider that tracks the same supply turns
the PVT N/P strength skew — the mechanism that moves an inverter trip point — into a
near common-mode current change. Its T-10 Monte Carlo record reads `klt yield`
**status `pass`** at ±60 mV / 3σ pooled over the 45 corners, **0 of 5400 draws and 0 of
45 corners outside the limits**, negative control detected (record
`records/20261121T091822Z-mc/`, per-corner table in its `per_corner.md`).
Adoption follow-up: #398 (netlist change, layout regeneration, re-attestation,
new T-10 record; coordinated with #190 so the cell is resized once).
**But see "Clock path" below: the candidate is for the data lanes only — the clock
legs must keep the committed inverter, and the adoption issue says so.**

## The DC screen (record `records/20261121T084734Z-screen/`)

All candidates on one pad ramp per corner, ordinary process sections, 45 corners;
`t10_<id>_mv` is the single DC crossing minus VDDIO/2 per corner (a **nominal offset**).
The as-drawn cell (`base`) is the screen's baseline: its nominal offsets match the
committed record's per-corner MC means within 1.1 mV at every corner (mean |Δ| 0.42 mV;
the committed means are 120-draw averages that include mismatch, this is the nominal),
so the screen bench and the committed T-10 bench read the same quantity.

Estimated ±3σ endpoints per candidate: per-corner recorded σ (4.9–6.8 mV, from
`sim/mc/per_corner.md`) **scaled by 1/√(gate area)** — input-stage P+N area for the
inverters (`w·l`, `ng`-independent; base 0.455 µm²), the NMOS pair's combined area
(1.0 µm²) for `vref` — applied to the candidate's own per-corner nominal offsets. The
`vref` estimate is provisional (a diff pair + mirror is not an inverter; the mirror's
mismatch is not in the area rule) and the MC leg replaces it with measured σ.

| Candidate (stage 1) | area µm² | mean of means | min mean | max mean | span | est. lo 3σ | est. hi 3σ | headroom to ±60 mV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base` (as drawn, 2.5:1) | 0.46 | +34.7 | −5.8 | +79.0 | 84.9 | −22.7 | +98.7 | −38.7 |
| `r20` (2.0:1) | 0.39 | +22.3 | −13.4 | +60.9 | 74.2 | −31.5 | +82.1 | −22.1 |
| `r225` (2.25:1) | 0.42 | +28.9 | −9.3 | +70.5 | 79.8 | −26.8 | +90.9 | −30.9 |
| `r30` (3.0:1) | 0.52 | +44.7 | +0.1 | +93.8 | 93.6 | −15.6 | +112.1 | −52.1 |
| `r35` (3.5:1) | 0.58 | +53.1 | +5.0 | +106.1 | 101.1 | −9.8 | +123.4 | −63.4 |
| `l25` (2.0:1, l=0.25u) | 0.75 | −44.0 | −83.0 | −4.4 | 78.6 | −96.1 | +8.9 | −36.1 |
| `l50` (2.0:1, l=0.5u) | 1.50 | −74.3 | −114.4 | −32.9 | 81.5 | −124.1 | −23.5 | −64.1 |
| `a2` (2.0:1, ng=4) | 0.39 | +15.7 | −22.2 | +57.3 | 79.5 | −41.2 | +77.1 | −17.1 |
| `vref` (supply-referenced) | 1.00 | +2.7 | −2.0 | +10.7 | **12.7** | −13.3 | +24.6 | **+35.4** |

All values mV; binding corners `fs/1.080V/−40C` (low) and `sf/1.320V/125C` (high) for
the ratio sweep, `ff/1.320V/125C` (high) for `vref`. `a2` is a finger-width probe, not
an area doubling: `w` is total width, so ng=4 at the same w halves the finger width and
shifts Vt (mean +15.7 vs `r20`'s +22.3) without touching mismatch area.

**No inverter sizing closes the row.** The narrowest envelope among the tested
inverters is `r20`'s 113.6 mV (−31.5..+82.1); the best-centred is `r20`/`a2` (mean
+22.3/+15.7). Even a hypothetical perfectly centred `r20` (shift −22.3 mV) lands at
−53.8..+59.8 mV — **under 1 mV of margin on the high side**, with a σ estimate whose
uncertainty (the 1/√area rule) is of that order, before any of the secondary effects.
Length (`l25`, `l50`) shifts the mean far faster than it narrows σ; more ratio (`r30`,
`r35`) widens the span monotonically. The span is set by the N/P strength skew's
sensitivity, which a ratio/length/area knob of the same inverter topology cannot
reduce — exactly what the supply-referenced stage removes: its mean span is 12.7 mV.

## The Monte Carlo confirmation (record `records/20261121T091822Z-mc/`)

Committed T-10 request shape (`sim/mc/README.md`): 45-corner PVT-FULL mismatch grid,
120 draws/corner seed 4410, limits ±60 mV `target_sigma` 3, negative control
(input-side NMOS 4× narrower) 20 draws/corner seed 4411 — **detected** (0/900 in
limit). One stated deviation: the control's DC sweep widens to 0.15–0.95, because the
degraded candidate crosses at fr 0.66–0.75 over the grid, outside the committed 0.3–0.7
window; the nominal bench keeps the committed window.

- `klt yield`: **pass**, sigma-to-spec 6.25 (target 3), sample-size verdict
  `sufficient` (required 183, observed CI half-width 3.4e-4).
- Pooled: mean +2.74 mV, σ (n−1) 9.60 mV, worst draw +42.3 mV; **0 of 5400 draws
  outside the limits; 0 of 45 corners hold any out-of-limit draw** (the committed
  cell: 13 of 45, 16.1 % of draws).
- Per-corner means −2.4..+10.8 mV; per-corner σ 7.5–10.8 mV — **about twice the
  screen's 1/√area estimate** (the mirror's mismatch adds); the MC leg's measured
  values replace the estimate. Highest corner mean+3σ: +39.2 mV (`ff/1.320V/125C`),
  20.8 mV of headroom.
- Static supply current at the crossing point: ~57 µA per receiver at tt/1.2 V
  (`ivdd_a` in the record) — the divider + tail. This is the architecture's standing
  cost, ~0.7 mW per data lane at 1.2 V, and is in the adoption issue.

## Side effects (each from its own run)

| Row | Record | Committed cell | Candidate | Verdict |
|---|---|---|---|---|
| T-11 hysteresis | `records/20261121T090435Z-hyst/` | ≤ 1.7 µV | ≤ 1.7 µV | unchanged; both pass (limit 60 mV) |
| T-24 pin capacitance | `records/20261121T095530Z-pin/` | 79.7–96.4 fF | 76.3–92.4 fF | slightly lower at every bias; both pass (target 100 fF) |
| Clock-path t02 | `records/20261121T104210Z-clk/` | see below | see below | candidate **out of the clock legs**; split configuration measured |
| T-16 at nominal channel | `records/20261121T104646Z-t16-base/`, `…T100828Z-t16-cand/`, `…T103057Z-t16-mixed/` | all rows pass | all rows pass | T-16 unchanged (+9.8 → +9.5 ps binding) |

**Clock path (T-02's opposite-edge separations, relative to 500 ps; this bench's
variant b is the in-bench committed-cell reference).** With the candidate in
**both clock legs and the data lane** (variant c), the binding corner
`mos_ss/1.080V/−40C` reads `t02_cr_df` **+624 ps** and `t02_cf_dr`
**−124 ps** — the opposite-edge ordering inverts; the committed cell's worst on the
same bench is −76/+76 ps. The candidate's asymmetric output slew (d1 charges through
the mirror but discharges through the input pair) multiplies the clock-path duty
distortion by ~8× at the binding corner. **The candidate cannot be the clock
receiver.** The adoptable configuration is the split — candidate in the data lane,
committed inverter in both clock legs (variant d), measured on the same bench:
`t02_cr_df__d` +87..+590 ps and `t02_cf_dr__d` +15..+156 ps over the grid (worst
`mos_ss/1.080V/−40C` / `mos_sf/1.080V/−40C`), against variant b's −76/+76 ps; the
same-edge pairs move to `t02_dr_cr__d` 380..534 ps and `t02_df_cf__d` −139..392 ps
against b's 500.000±0.005 ps. The data lane's late falling edge is the cost the
adoption issue carries: the forwarded-clock alignment budget (the SG13G2 DLL canary's
delay range, #198's slew sensitivity) must absorb ~±0.5 UI of corner-worst
data-vs-clock distortion, or the candidate's output stage needs a symmetric revision
before adoption. The adoption issue proposes the split and says both.

**T-16 (data-to-clock skew at the nominal channel, ±30 ps limit, with the RX-pin
probes of the committed `request_ch_1g` family).** Three records, all `klt exit 0`,
every row (T-01, T-09, T-15, T-16, T-18, T-26) passing at every corner:
`t16-base` (as-drawn receiver — the bench self-check: its t16 values sit within a
median 2.8 ps / max 13.2 ps of the newest committed channel-eye `ch` record
(`sim/channel-eye/records/20261111T235838Z-ch/`), whose residual is the
`aib_pad_esd` XResd shortening of `e47bb80` (2026-11-18, "T-16 margin 1.3 → 19.9 ps")
landing after that record), `t16-cand` (candidate in all four lanes), and `t16-mixed`
(candidate in the data lanes A/B only — the adoptable split). T-16 binding corner
`mos_sf/mixed/−40C` in all three: **+9.8 ps (base), +9.5 ps (cand), +9.5 ps (mixed)**
— the candidate leaves nominal-channel T-16 effectively unchanged.

**Energy (T-26, from the same three records).** The candidate's standing tail and
divider current raise the RX lane's simulated energy `e_lane_a_rx_j` from
0.85–2.24 pJ to 5.1–18.4 pJ per bit, and the lane total `t26_energy_per_bit_simulated_j`
from 0.354–0.634 pJ to 0.390–0.752 pJ (+10–19 %). Labeled SIMULATED; the adoption
issue carries it as a design cost of the architecture.

## Records

| Record | Leg | What it holds |
|---|---|---|
| `records/20261121T084734Z-screen/` | screen | per-corner nominal offsets of all 9 candidates, 45 corners (the candidate table above) |
| `records/20261121T090435Z-hyst/` | hyst | T-11: as-drawn (b) and candidate (c) hysteresis, 45 corners |
| `records/20261121T091822Z-mc/` | mc | T-10 MC confirmation: nominal + control reports, `samples.json`, `yield.json` (pass), `per_corner.md`, hand-written `record.json` |
| `records/20261121T093011Z-clk/` | clk | first clk record, variants b/c only (two-lane bench); superseded by the three-lane rerun below for the d variant — kept as evidence, its b/c numbers are identical to the rerun's |
| `records/20261121T095530Z-pin/` | pin | T-24: two pins (b as-drawn, c candidate), AC at pad 0 / VDDIO/2 / VDDIO, 45 corners |
| `records/20261121T100828Z-t16-cand/` | t16-cand | channel-eye `ch` family, candidate in all four lanes; every row passes |
| `records/20261121T103057Z-t16-mixed/` | t16-mixed | channel-eye `ch` family, candidate in lanes A/B, committed receiver in C/CB; every row passes |
| `records/20261121T104646Z-t16-base/` | t16-base | channel-eye `ch` family, as-drawn receiver — the bench self-check |
| `records/20261121T104210Z-clk/` | clk | the three-lane clk bench (b committed, c candidate everywhere, d adoptable split) — the numbers quoted above |

Fleet transients during the runs: three legs hit `submitted but never launched` once
each and were retried with the same work dirs (`--resume`), and the t16-mixed leg once
hit a harness bug (`write_record.py` dereferenced a null `fleet` shard entry; fixed
with a self-test, `sim/harness/test_write_record.py::test_a_null_fleet_entry_is_skipped`)
— the sim data was re-fetched, nothing was hand-edited into any record.

## Reproduce

```bash
python3 -I sim/rx-threshold-study/gen_rx_threshold.py --check   # benches/requests fresh
sim/rx-threshold-study/run_rx_threshold.sh screen               # then hyst pin clk
sim/rx-threshold-study/run_rx_threshold.sh t16-base             # t16-cand t16-mixed
sim/rx-threshold-study/run_rx_threshold.sh mc                   # T-10 MC pair + yield
```

Every leg is one `klt sim` request on the batch fleet (`--wait-for-capacity 600`), one
append-only record; there is no local loop and no fallback. The mc leg is the pinned
`sim/mc/README.md` flow (two requests, `klt yield-samples`, `klt yield`); its
`record.json` and `per_corner.md` are written by hand from the yield verdict, as for
the committed mc records. The study adds no post-processing script: the per-corner
table is committed evidence inside the record, computed by the same recipe
`sim/mc/gen_per_corner.py` documents.

## What is not shown

No layout, no PEX, no bond pad; the pin-capacitance numbers are extracted from
small-signal admittance like `sim/dc-static`'s. The divider resistors are corner-section
devices (`cornerRES`), which carry no per-instance mismatch on this grid — the MC
varies MOS mismatch only, same as the committed T-10 record. The candidate's trip point
is process-section-dependent through the divider only weakly (both sides see the same
supply); its temperature coefficient is inside the measured 12.7 mV span. Static supply
current is measured, not a spec row; the adoption issue carries it as a design cost.
T-15 (data-to-data skew) is not re-run here: #385 owns the committed-cell mismatch
records, and an adoption re-runs it on the landed cell.
