# redundancy-mux PVT-FULL record 20261113T160050Z (T-05 `SIM` leg)

**Simulated.** 45 corners (5 MOS × VDDIO 1.08/1.20/1.32 V × −40/27/125 °C), one `klt sim`
request on the Spot batch fleet, split into 15 jobs of 3 corners; every job id is in
`record.json` → `batch_job_ids`, runner klt 0.9.0, PDK v0.3.0. `klt sim` exited 0: 45/45
corners carry a status, 0 failed, 0 errored, 2205 measurements, every one **reported**. No
local grid was run.

**Nothing here is graded.** `spec/target-spec.md` T-05 states no bound for its `SIM` leg and
DR-0023 invents none, so no measurement in this request carries `limits`. T-05 stays a
**declared gap** in `signoff/block-manifest.json`, in the form DR-0022 established for T-02
and T-04 — the measurements are real, and they are not a grade. The two delay terms are
*reported into* the rows that carry numbers: the common term into T-20, the select-dependent
term into T-13. Neither bound changes on this record's account.

**Claim scope: CH** for the lane loading — the pad drives `aib_pad_esd` into the declared
channel CH-3MM-RC (`spec/channel/channel_rc.cir`, nominal `kr = kc = 1`, far end loaded by
the model's own `cfar` and nothing else), so the TX output sees its declared load. The
numbers below are **lane-internal differences**, not channel claims: the channel is identical
in all four lanes and is there to load the pad realistically. There is no die-to-die assembly
to measure; this is a modeled-channel result, not silicon.

Reproduce with `sim/redundancy-mux/run_redundancy_mux.sh`; check the bench on one corner
first with `klt sim request_tt.json --backend local` (about 15 s, no fleet).

## What was simulated

**There is no transistor-level redundancy mux in this repo.** `tx_remap` / `rx_remap` live
only in `rtl/shift_redundancy.v`, `rtl/aib_datapath.v` does not instantiate them, and the
committed synthesized netlist predates them. DR-0023 therefore *declares* the arrangement
this record measures, and these numbers hold for that arrangement only:

- the remap sits **on the serialized wire**, between the serializer mux and the TX cell's
  `DIN` — the placement the ratified row presumes when it puts the term "inside T-12/T-13";
- **`sg13g2_mux2_1`** stands in for both the serializer mux and the remap stage (synthesis
  already maps the serializer's clock-selected mux to that cell: 22 instances in the
  committed netlist), vendored unmodified as `sg13g2_mux2_1.inc`;
- the standard cells run from **the same swept VDDIO** as the TX cell (one supply, `vdd_tx`).

Four lanes share one stimulus and one corner in `tb_redundancy_mux.cir`, so every number
below is a difference measured *inside one simulation*: **b** baseline (serializer → `DIN`),
**c** control (lane b built a second time), **m0** and **m1** with the remap in the path,
selected to `A0` and to `A1`. Each with-mux lane carries the real fan-out — its serializer
drives two remap inputs, its own wire's `A0` and wire `j + 2`'s `A1`
(`rtl/shift_redundancy.v`) — and the remap's unselected input is driven by a neighbour
serializer carrying the complementary pattern, so it toggles every UI with a standard-cell
edge. Stimulus: the serializer's two inputs held at static complementary levels, so each
lane's serialized output is `~clk`, a 1010 pattern at 1 Gb/s (UI 1000 ps).

## Negative control: the bench has no lane-to-lane offset

Lane **c** is lane **b** built a second time — the remap stage shorted out — and it must
reproduce the baseline. Over 45 corners:

| | worst over the grid |
|---|---|
| `t05_ctl_r_s` (c − b, pad rise) | **2.4 × 10⁻¹⁰ ps** |
| `t05_ctl_f_s` (c − b, pad fall) | **5.5 × 10⁻¹¹ ps** |
| `t05_ctl_cl_f` (c − b, load on the serializer) | **2.1 × 10⁻¹¹ fF** |

That is the solver's own arithmetic noise, about **twelve orders of magnitude** below the
added delay reported next. Two nominally identical lanes of this deck measure the same number
at every corner, so a non-zero delta between lane b and lane m0/m1 is the remap and nothing
else.

## The three terms

Per-corner values are in `report.json.gz`; the min and max over the grid, with the corner at
each end, are in `record.json` → `report_only_ranges`.

### 1. Common added delay — reports into T-20. **It does not fit.**

Every data lane gains one remap stage and the forwarded-clock lane does not, so this is a
data-to-clock offset.

| measurement | fastest corner | slowest corner |
|---|---|---|
| `t05_add_r_s` (pad rise, m0 − b) | 53.79 ps — `mos_ff` 1.32 V −40 °C | **128.15 ps** — `mos_ss` 1.08 V −40 °C |
| `t05_add_f_s` (pad fall, m0 − b) | 71.13 ps — `mos_ff` 1.32 V −40 °C | **183.89 ps** — `mos_ss` 1.08 V −40 °C |

At 1 Gb/s that worst case is **0.184 UI**. `spec/target-spec.md` T-20 asks for ≥ 0.10 UI of
sampling margin *remaining* at every PVT-FULL corner, and #177 allocates 0.1075 UI to static
off-centring, of which the clock-path record (#54) already measures 0.103 UI consumed at the
capture node. **One remap stage as measured here exceeds the entire T-20 target on its own,
at every corner of the grid** (the best corner, 53.8 ps, is still 0.054 UI). This record
relaxes nothing: it reports the number, and the consequence is filed as **#232** rather
than absorbed.

Because the rise and fall terms differ, the remap also adds **pulse-width distortion** to the
data lane: `t05_add_f_s − t05_add_r_s` runs 15.2 ps (`mos_ff` 1.32 V 125 °C) to **56.8 ps**
(`mos_ss` 1.08 V 27 °C), i.e. up to 0.057 UI of duty change that the forwarded clock does not
see. The fall is the slower direction at every corner.

### 2. Select-dependent delay — reports into T-13. **It is negligible.**

In a repaired direction, wires below `pos` take the `A0` input and wires at or above it take
`A1`, so any difference between the two input-to-output paths is lane-to-lane skew.

| measurement | range over 45 corners |
|---|---|
| `t05_sel_r_s` (m1 − m0, pad rise) | −0.141 ps .. +0.029 ps |
| `t05_sel_f_s` (m1 − m0, pad fall) | +0.053 ps .. **+0.289 ps** |

Worst case **0.289 ps = 0.00029 UI**, against T-13's 0.04 UI bound: **0.7 % of the bound**,
at `mos_ss` 1.08 V −40 °C. The cell's two input paths are symmetric enough that the repair
state of a wire is not a meaningful skew contributor. This is a *reported input* to T-13, not
a grade of it — T-13 is a `SIM-MC` row (#136) whose campaign is where the number is used.

### 3. Added load on the serializer output — it is **negative**

The baseline serializer drives `aib_tx_data`'s `DIN`, which is four transistor gates directly
(`XMnd1p`, `XMnd1n`, `XMnr1p`, `XMnr1n`, 18 µm of gate width). The with-mux serializer drives
two `sg13g2_mux2_1` inputs instead, which is far less:

| | range over 45 corners |
|---|---|
| `t05_b_cl_f` — baseline load (one `DIN`) | 29.60 .. 33.60 fF |
| `t05_m0_cl_f` — with-mux load (two mux inputs) | 4.50 .. 5.32 fF |
| `t05_dcl_f` — **added** load | **−28.73 .. −24.90 fF** |

Each figure is the charge the serializer output delivers over one whole clock period (one
rise and one fall, so the integration window needs no settled endpoint) divided by 2·VDD.
The serializer's own 10–90 % edge accordingly gets **76 to 224 ps faster** (`t05_dtr_s`,
`t05_dtf_s`), and its delay to the serialized node drops by 39 to 88 ps (`t05_load_r_s`,
`t05_load_f_s`, both negative at every corner).

So the added delay is not a loading effect at all. It splits as:

| | rise | fall |
|---|---|---|
| load term (`t05_load_*`, at the serializer output) | −87.6 .. −40.7 ps | −82.2 .. −39.1 ps |
| remap stage term (`t05_stage_*`) | +94.5 .. +214.1 ps | +110.3 .. +259.9 ps |
| **net at the pad** (`t05_add_*`) | **+53.8 .. +128.2 ps** | **+71.1 .. +183.9 ps** |

The whole cost is the remap stage having to drive the ~30 fF `DIN` load that the serializer
used to drive — with the *same minimum-strength cell*. The remap inherits the load; it does
not add one.

### The corners the spec row calls out

`spec/target-spec.md` asks skew-class rows for the mixed MOS corners as well as the fast and
slow pairs, so both are read here even though neither is this record's extreme.

| corner group | `t05_add_r_s` | `t05_add_f_s` | worst \|`t05_sel_*`\| |
|---|---|---|---|
| `mos_sf` (9 corners) | 63.2 .. 103.9 ps | 84.5 .. 132.1 ps | 0.167 ps |
| `mos_fs` (9 corners) | 64.2 .. 103.1 ps | 93.7 .. 152.4 ps | 0.258 ps |
| slow pair `mos_ss` 1.08 V 125 °C | 126.6 ps | 176.2 ps | 0.235 ps |
| slow pair `mos_ss` 1.08 V −40 °C (grid worst) | 128.2 ps | 183.9 ps | 0.289 ps |
| nominal `mos_tt` 1.20 V 27 °C | 79.5 ps | 111.7 ps | 0.131 ps |

The unmatched-N/P corners do **not** open up the select-dependent term — `mos_sf` and
`mos_fs` stay inside 0.26 ps, the same order as every other corner — and they are not where
the common term binds either; the slow pair is. The remap's two input paths share the same
output inverter, so an N/P skew moves both of them together.

## What this record does not settle

- **The stand-in is the minimum-strength cell.** `sg13g2_mux2_1` is drive strength 1 and the
  stage term above is dominated by it driving ~30 fF. `sg13g2_mux2_2` exists in the same
  library, as do `sg13g2_buf_1..16`. Whether a sized or buffered remap brings the common term
  inside the T-20 allocation is **not measured here** — DR-0023 fixes one stand-in so that a
  later comparison has a baseline, and does not claim it is the eventual implementation. #232
  owns that question, together with the alternative placement below.
- **The placement is declared, not implemented.** Moving the remap ahead of the TX input
  register (a mux on each slice's `d0`/`d1`) would make the in-lane term zero by construction.
  DR-0023 rejects assuming it here precisely because this record is the evidence for or
  against that change. It is a spec change of its own.
- **Skew across the column** is #136's Monte Carlo campaign. One lane is simulated here, with
  no mismatch; the select-dependent term above is a *systematic* path difference, not a
  statistical one.
- **Post-layout.** These are schematic-level numbers; the extracted leg of item 7 is blocked
  on `2AMLogic/klayout-tools#5491` (`layout/pex/README.md`).
- **The RX-side remap** (`rx_remap`) is not measured. The row's leg names load and delay in
  the lane to the TX cell.

## Provenance

Submitted once at 15:46 UTC; the fleet was at capacity and launched 14 of 15 shards inside
the `--wait-for-capacity 600` window, leaving one job submitted but never launched. The
harness refused to write a record from a partial grid (`sim/harness/batch_record.sh` exit 6)
and printed its `REDUNDANCY_MUX_WORK=… REDUNDANCY_MUX_RESUME=1` retry line; the record here
is that resume, which launched the remaining job and collected all 15. `klt.stderr` shows
one `had been submitted but never launched; launched it` line — klt's **per-shard recovery**
notice, not its unlaunched-jobs summary sentence, which is the distinction
`sim/harness/batch_record.sh` matches on. `environment.resume.resumed_corners` is 0 and all
45 corners carry `status: pass`.

Only `report.json.gz` is committed, with no decompressed copy beside it: the pinned grader
(0.9.0) cannot read a `.json.gz` citation (`2AMLogic/klayout-tools#5452`), but this envelope
is **not cited** — T-05 is a declared gap — so there is nothing to make readable. If a later
decision cites it, a byte-identical `report.json` can be added beside the `.gz` then, the way
the channel-eye and clock-path records gained theirs.
