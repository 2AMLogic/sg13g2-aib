# redundancy-mux PVT-FULL record 20261113T174852Z (T-05 `SIM` leg, sized remap stages)

**Simulated.** 45 corners (5 MOS × VDDIO 1.08/1.20/1.32 V × −40/27/125 °C), one `klt sim`
request on the Spot batch fleet, split into 15 jobs of 3 corners; every job id is in
`record.json` → `batch_job_ids`, runner klt 0.9.0, PDK v0.3.0. `klt sim` exited 0: 45/45
corners carry a status, 0 failed, 0 errored, 3870 measurements, every one **reported**, and
**no corner carries a solver diagnostic**. No local grid was run.

**What this record adds to `20261113T160050Z`.** The same bench, the same stimulus and the
same placement, with two more lanes: the **sized** remap stages that the first record said
were unmeasured. The question it answers is how much of the first record's 0.184 UI of
common added delay is the stand-in cell's drive strength rather than the placement — which
is the evidence `spec/decisions/0024-t05-remap-placement.md` rejects a sized in-lane stage
on. The first record is not modified and nothing here supersedes it.

| lane | remap stage |
|---|---|
| `b` | none — baseline, serializer mux → `aib_tx_data` `DIN` (what `design/` has today) |
| `c` | none — control, lane `b` built a second time (the bench's own noise floor) |
| `m0` / `m1` | `sg13g2_mux2_1`, drive 1, selected to `A0` / to `A1` — the DR-0023 stand-in |
| `m2` | `sg13g2_mux2_2`, drive 2, selected to `A0` |
| `m3` | `sg13g2_mux2_1` → `sg13g2_buf_4`, selected to `A0` |

Why `sg13g2_buf_4` of `sg13g2_buf_1..16`: its output devices are about four times the
`mux2_1` output inverter's while its own input load stays light for the drive-1 mux ahead of
it; the header of `sg13g2_buf_4.inc` states the choice and that it is not a claim of
optimality. Only `A0` is measured on the two sized lanes — the select-dependent term is a
property of the select stack, whose devices `sg13g2_mux2_2` does not change, and the first
record measured it at 0.289 ps worst case.

**Nothing here is graded.** `spec/target-spec.md` T-05 states no bound for its `SIM` leg and
DR-0023 invents none, so no measurement in this request carries `limits`. T-05 stays a
**declared gap** in `signoff/block-manifest.json`. The numbers below are *reported*, and
DR-0024 reads them to choose a placement; they are not a pass or a fail of any row.

**Claim scope: CH** for the lane loading — each pad drives `aib_pad_esd` into the declared
channel CH-3MM-RC (`spec/channel/channel_rc.cir`, nominal `kr = kc = 1`), so the TX output
sees its declared load. Every number below is a **lane-internal difference** measured inside
one simulation, not a channel claim: the channel is identical in all six lanes. There is no
die-to-die assembly to measure; this is a modeled-channel result, not silicon.

Reproduce with `sim/redundancy-mux/run_redundancy_mux.sh`; check the bench on one corner
first with `klt sim request_tt.json --backend local` (about 25 s, no fleet).

## The six-lane deck reproduces the four-lane one

The drive-1 lanes are re-measured here, in the same deck as the sized ones, so the sizing
comparison is a difference inside one simulation rather than between two records. That only
holds if adding lanes changes nothing, and it does not:

| | this record | `20261113T160050Z` |
|---|---|---|
| `t05_add_r_s` | 53.786 .. 128.150 ps | 53.786 .. 128.150 ps |
| `t05_add_f_s` | 71.134 .. 183.889 ps | 71.134 .. 183.889 ps |
| `t05_add_r_s` at `mos_tt` 1.20 V 27 °C | 79.4933 ps | 79.4931 ps |
| `t05_stage_r_s` | 94.497 .. 214.143 ps | 94.497 .. 214.143 ps |

Agreement to six significant figures, and 0.2 fs at the nominal corner. ngspice chooses its
timestep over the whole circuit, so a deck with more lanes need not land on the same
timepoints; at this tolerance it does.

## Negative control

Lane `c` is lane `b` built a second time — the remap stage shorted out — and must reproduce
it. Over 45 corners, worst over the grid:

| | worst |
|---|---|
| `t05_ctl_r_s` (c − b, pad rise) | 2.1 × 10⁻¹⁰ ps |
| `t05_ctl_f_s` (c − b, pad fall) | 9.3 × 10⁻¹¹ ps |
| `t05_ctl_cl_f` (c − b, load on the serializer) | 1.2 × 10⁻¹¹ fF |

About twelve orders of magnitude below the terms read against it. A non-zero
baseline-to-with-remap delta is the remap and nothing else.

## 1. Common added delay — no in-lane stage fits, sized or not

With-remap minus baseline at the TX pad. The budget line this reports into has **7.5 ps**
spare (`spec/target-spec.md`, "Timing budget"), and T-20's whole target is 0.10 UI = 100 ps
at 1 Gb/s:

| remap stage | rise | fall | per-corner worst | over 100 ps | over 7.5 ps |
|---|---|---|---|---|---|
| `sg13g2_mux2_1`, drive 1 | 53.8 .. 128.2 ps | 71.1 .. 183.9 ps | 71.2 .. 184.2 ps | 30 / 45 | **45 / 45** |
| `sg13g2_mux2_2`, drive 2 | 21.9 .. 56.0 ps | 52.9 .. 153.9 ps | 52.9 .. 153.9 ps | 14 / 45 | **45 / 45** |
| `sg13g2_mux2_1` + `buf_4` | 46.1 .. 113.9 ps | 63.0 .. 181.2 ps | 63.0 .. 181.2 ps | 25 / 45 | **45 / 45** |

The drive-1 per-corner worst includes its `A1` lane (`t05_add1_*`), hence 184.2 ps against a
fall range ending at 183.9. Fall is the slower edge at **45 of 45** corners for all three
stages. The best corner of the *better* sized option is **52.9 ps — 7.1 times** the 7.5 ps
the budget has spare, and the worst is 153.9 ps.

Where each binds and relaxes:

| corner | drive 1 (r / f) | drive 2 (r / f) | drive 1 + `buf_4` (r / f) |
|---|---|---|---|
| `mos_ff` 1.32 V −40 °C (grid best) | 53.8 / 71.1 ps | 23.3 / 55.3 ps | 46.1 / 65.3 ps |
| `mos_tt` 1.20 V 27 °C (nominal) | 79.5 / 111.7 ps | 31.6 / 90.7 ps | 66.3 / 106.4 ps |
| `mos_ss` 1.08 V 125 °C | 126.6 / 176.2 ps | 56.0 / 140.1 ps | 113.9 / 166.0 ps |
| `mos_ss` 1.08 V −40 °C (grid worst) | 128.2 / 183.9 ps | 54.8 / 153.9 ps | 112.4 / 181.2 ps |
| `mos_sf` (9 corners) | 63.2 .. 132.1 ps | 29.1 .. 96.7 ps | 59.4 .. 116.0 ps |
| `mos_fs` (9 corners) | 64.2 .. 152.4 ps | 21.9 .. 134.8 ps | 47.9 .. 156.8 ps |

The mixed-N/P corners the spec row calls out for skew-class rows are not where any of the
three binds; the slow pair is. `mos_fs` is the second-worst group for all three, and it is
the one corner group where the buffered stage is **worse** than the unbuffered drive-1 cell
on the falling edge (156.8 ps against 152.4 ps).

## 2. Sizing makes the pulse-width distortion worse

`t05_pwd*_s` is the fall-minus-rise of each stage's own added delay: distortion the data lane
gains and the forwarded clock does not.

| remap stage | added pulse-width distortion |
|---|---|
| drive 1 | 15.2 .. 56.8 ps |
| drive 2 | 24.8 .. **101.7 ps** |
| drive 1 + `buf_4` | 0.5 .. 78.8 ps |

Doubling the output drive helps the rising edge about three times as much as the falling one
(the rise range falls from 53.8–128.2 to 21.9–56.0 ps, the fall only from 71.1–183.9 to
52.9–153.9 ps), so the asymmetry nearly doubles. A sized in-lane stage trades a sixth of the
T-20 term for twice the duty-cycle term a capture aperture would pay for.

## 3. The cost is the stage, not the load — and sizing only touches the stage

| remap stage | load term at the serializer output | stage term | net at the pad, worst |
|---|---|---|---|
| drive 1 | −87.6 .. −40.7 ps | +94.5 .. +259.9 ps | 184.2 ps |
| drive 2 | −87.5 .. −38.4 ps | +64.0 .. +228.1 ps | 153.9 ps |
| drive 1 + `buf_4` | −87.6 .. −39.1 ps | +86.8 .. +256.7 ps | 181.2 ps |

(`t05_load*_*` and `t05_stage*_*`, rise and fall pooled.) The load on the serializer output
is the same in all three — it drives two mux *inputs* either way, and `sg13g2_mux2_2`'s
`A0`/`A1` devices are the same size as `sg13g2_mux2_1`'s:

| | range over 45 corners |
|---|---|
| `t05_b_cl_f` — baseline load (one `DIN`) | 29.60 .. 33.60 fF |
| `t05_m0_cl_f` / `t05_m2_cl_f` / `t05_m3_cl_f` | 4.50 .. 5.32 / 4.54 .. 5.36 / 4.50 .. 5.28 fF |
| `t05_dcl_f` / `t05_dcl2_f` / `t05_dcl3_f` — **added** load | −28.72 .. −24.90 / −28.65 .. −24.87 / −28.75 .. −24.95 fF |

So the whole added delay is the remap stage **inheriting** the ~30 fF `DIN` load the
serializer used to drive. Sizing acts on that one term, and buys 26 % of it at the best
corner and 16 % at the worst; the buffered stage buys 11 % and 1.6 %, because
`sg13g2_buf_4` spends most of what its drive saves on its own stage delay and on the input
the mux must now charge.

## What this record does not settle

- **It measures the arrangement DR-0024 rejects.** Both records measure the remap *on the
  serialized wire* (DR-0023's declared placement). DR-0024 reads them as the evidence that
  no in-lane stage fits and puts the remap ahead of the TX input register instead, where the
  in-lane term is zero by construction. Nothing here measures that placement — there is
  nothing in it to measure in this leg, which is the point.
- **The moved cost is not measured either.** Ahead of the input register the remap delay
  becomes setup time on the `tx_d0`/`tx_d1` path at 500 MHz, which synthesis and P&R grade
  (item 7 / digital). DR-0024's follow-ups own that, and this record makes no claim that it
  closes.
- **`buf_4` is one choice of buffer**, stated in the include's header. `buf_8` / `buf_16`
  are not measured; the trade the `buf_4` lane shows (own stage delay against drive) is the
  reason a larger one was not expected to change the verdict, which is an argument, not a
  measurement.
- **No RX-side remap** (`rx_remap`) and no replica stage in the forwarded-clock lane are
  measured. DR-0024 disposes of the replica on argument and says so.
- **Skew across the column** is #136's Monte Carlo campaign; one lane is simulated here,
  with no mismatch.
- **Post-layout**: these are schematic-level numbers; item 7's extracted leg is blocked on
  `2AMLogic/klayout-tools#5491` (`layout/pex/README.md`).

## Provenance

Submitted at 17:35 UTC; the fleet launched 14 of 15 shards inside the
`--wait-for-capacity 600` window and left one job submitted but never launched, so the
harness refused to write a record from a partial grid (`sim/harness/batch_record.sh` exit 6,
no record) and printed its `REDUNDANCY_MUX_WORK=… REDUNDANCY_MUX_RESUME=1` retry line. The
record here is that resume, which launched the remaining job and collected all 15 —
`klt.stderr` ends with the per-shard `had been submitted but never launched; launched it`
recovery notice, which is **not** klt's unlaunched-jobs summary sentence, the distinction
`sim/harness/batch_record.sh` matches on. The first record of this family hit the same
fleet behaviour and was recovered the same way.

Only `report.json.gz` is committed, with no decompressed copy beside it: the pinned grader
(0.9.0) cannot read a `.json.gz` citation (`2AMLogic/klayout-tools#5452`), but this envelope
is **not cited** — T-05 is a declared gap — so there is nothing to make readable.
