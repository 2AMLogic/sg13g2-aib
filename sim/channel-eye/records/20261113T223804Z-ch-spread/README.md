# channel-eye `ch-spread` — CH-3MM-RC at the declared ±20 % channel R/C spread

**Scope: CH (the modeled die-to-die channel CH-3MM-RC), not the test configuration.** This
is the parameter-sensitivity run that T-12's grid column in `spec/target-spec.md`
("PVT-FULL, plus channel R/C ±20 % (DR-0005)") asks for, and that no record carried before
(#193). It is **simulated** evidence against a **declared** channel model
(`spec/channel/channel_rc.cir`, `spec/channel-model.md`) — there is no die-to-die assembly
to measure, so the ±20 % corners bound the sensitivity to a declared input, they do not
measure a channel.

- Request `request.json` (= `sim/channel-eye/request_ch_spread_1g.json`), bench
  `tb_ch_spread.cir`, stimulus `prbs7_stim.inc`, body `tb_body.inc`.
- **180 units, 180/180 with a status, all `pass`**: PVT-FULL (45 corners) at each of the
  four (kr, kc) pairs in {0.8, 1.2}. `klt` exit code 0 (every limit met). 23 batch jobs,
  fleet runner klt 0.9.0, PDK v0.3.0.
- Same measurements, limits, stimulus and analysis as the nominal CH request — they come
  from the same generator builder, so they cannot drift. Only the netlist (`kr`/`kc` lifted
  to top-level `.param` so `corners.params` can target them) and the per-unit `timeout_s`
  differ; see `sim/README.md`, channel-eye section.
- **Nothing here is a bound change, a model change or a spec change**, and the nominal
  record `20261111T235838Z-ch` is untouched (records are append-only).

## Result per row, per spread corner

Every row passes at every one of the four spread corners. The figure quoted is the row's
**binding** (smallest-margin) measurement, the same one the nominal record binds on, so the
columns are directly comparable. "nominal" is record `20261111T235838Z-ch` (`kr = kc = 1`).

| row | binding measurement | limit | nominal | kr .8 / kc .8 | kr .8 / kc 1.2 | kr 1.2 / kc .8 | kr 1.2 / kc 1.2 | verdict |
|---|---|---|---|---|---|---|---|---|
| T-01 | `t01_dout_edges_a` | 63.5–64.5 counts | 64.0 | 64.0 | 64.0 | 64.0 | 64.0 | pass ×4 |
| T-09 | `t09_dwell_over_a` | ≤ 0.4 ns | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | pass ×4 |
| T-15 | `t15_ar_bf_short` | ±60 ps | −19.52 ps | −18.65 ps | **−20.28 ps** | −18.97 ps | −19.87 ps | pass ×4 |
| T-16 | `t16_dr_cf_long` | 470–530 ps | 480.9 ps | 487.0 ps | 472.0 ps | 486.7 ps | **471.3 ps** | pass ×4 |
| T-18 | `t18_eye_height_ok_v` | ≥ 90 mV | 378.7 mV | 426.8 mV | **343.2 mV** | 424.9 mV | 346.0 mV | pass ×4 |
| T-26 | `t26_energy_per_bit_simulated_j` | ≤ 1 pJ | 0.637 pJ | 0.578 pJ | **0.692 pJ** | 0.578 pJ | 0.692 pJ | pass ×4 |

Bold marks each row's worst spread corner. Per-row pass/fail/error counts and the binding
corner (process / supply / temperature, with the spread corner appended) are in
`record.json` → `param_groups` and `rows.json`, one group per spread corner; the pooled
`rows` block grades all 180 corners together. T-26 is **simulated** energy per bit; no
measurement exists (`record.json` says so in `energy_label`).

Per-row measurement counts in each 45-corner group: T-01 90, T-09 720, T-15 180, T-16 360,
T-18 1845, T-26 180 — all `pass`, zero `fail`, zero `error`.

## What the sensitivity says

1. **The spread is a capacitance effect, not a resistance one.** Across every row, moving
   `kc` 0.8 → 1.2 moves the result; moving `kr` 0.8 → 1.2 barely does (T-18: 83.6 mV for
   `kc`, at most 2.8 mV for `kr`). Ten 0.3 mm RLC π-sections of 1.65 Ω each are a small series term
   next to the shunt C at a 1 ns UI.
2. **Three rows bind at an _off-diagonal_ corner** — T-15, T-18 and T-26 are all worst at
   `kr 0.8 / kc 1.2`, not at `kr 1.2 / kc 1.2`. The two diagonal corners alone would have
   mis-stated their worst case, which is why all four were run (#193 sizing call).
3. **T-16 is the one row whose margin becomes small.** `t16_dr_cf_long` is 471.3 ps against
   the 470 ps lower edge: a **1.3 ps** margin, where the nominal channel leaves 10.9 ps. The
   +20 % C corner therefore consumes 9.5 ps of T-16's margin. It still passes and **no bound
   was relaxed**; whether a 1.3 ps worst-case margin is acceptable is a `spec/` question and
   is tracked in **#251**, not settled here.
4. T-18 (343 mV against a 90 mV floor), T-26 (0.692 pJ against a 1 pJ ceiling), T-15, T-09
   and T-01 all keep wide margins at the spread corners.

## Why T-12 is still a declared gap

T-12 is **not** cited as a covered row, and this record does not change that. Two separate
reasons, both checked:

- The channel model is an **input definition**, not a block measurable — citing it as
  evidence of itself would be circular (`spec/channel/channel_rc.cir`: "A declared model,
  not a measured one").
- Mechanically, the pinned grader cannot accept it either. Probed with klt 0.9.0 against a
  scratch copy of the manifest (nothing committed): adding
  `{"file": ".../report.json", "rows": ["T-12"]}` to `evidence."5.analog"` while T-12 is a
  declared gap makes item 5 `unmet` / `invalid_evidence` ("a member names a row that is
  undeclared or a declared gap"); undeclaring the gap as well makes that one citation grade
  `met` but leaves item 5 `unmet` / `partial_coverage` with `uncovered_rows: ["T-12"]`,
  because coverage is derived from the `spec_row` tags the report carries and no measurement
  carries T-12.

So this record is referenced from T-12's gap text in `signoff/block-manifest.json` rather
than cited as an envelope, and the six dependent rows keep their nominal citation
(`20261111T235838Z-ch`) unchanged.

## No decompressed `report.json` copy

The other channel-eye records carry a plain `report.json` beside the `.gz` because the
pinned grader (0.9.0) grades a `.json.gz` **citation** as `unreadable_evidence`
(`2AMLogic/klayout-tools#5452`). This record is not cited as evidence — it is referenced
from a gap text — so nothing reads it through the grader and the copy would be dead weight.
Verify the committed report with:

```bash
gzip -dc sim/channel-eye/records/20261113T223804Z-ch-spread/report.json.gz | python3 -c 'import json,sys; r=json.load(sys.stdin); print(len(r["corners"]), r["status"])'
# 180 pass
```

## Reproduce

```bash
sim/channel-eye/run_channel_eye.sh ch-spread    # writes a NEW records/<UTC>-ch-spread/
```

Needs `PDK_ROOT` and `uvx`; goes to the batch fleet (no local loop, no fallback). This
record's own run is append-only evidence and is never overwritten.
