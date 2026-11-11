# T-16 attribution record (issue #161, parent #142)

Kind: **simulated**, CH-3MM-RC and an ideal connection. Append-only: the CH records
`20261108T220323Z-ch` and `20261110T082948Z-ch` are read, never edited. No spec row, bound
or decision record is touched. Reproduce: `sim/channel-eye/run_t16attr.sh`.

## What was run

Eight single-corner, single-unit `klt sim` runs on the **local** backend (klayout-tools
0.9.0 via `uvx`, ngspice 46, PDK v0.3.0): 2 designs x 2 links x 2 corners. No grid, no
batch job (so no `environment.remote` job id). Seven runs were capped with
`OMP_NUM_THREADS=2`; the first (`cur/ch_ss`) ran uncapped and used about 8 threads for 32 s
before the cap was added.

- Designs: `cur` = `main` @ `ed04503` (includes #132's driver, merge `282a9d4`); `pre132` =
  `design/` and `spec/channel/` exported from `394bb86`, the commit of the CH record the issue
  cites (`git archive 394bb86 design spec/channel`). The stimulus and `tb_body.inc` are
  byte-identical at both commits.
- Links: `ch` = `tb_t16attr_ch.cir` (= `tb_ch.cir` plus probes); `id` = `tb_t16attr_id.cir`,
  a 0 V short in place of the channel (no R, L, C and no 0.1 pF far-end load).
- Corners: `ss` = mos_ss, 1.08 V, 125 C (binding); `tt` = mos_tt, 1.20 V, 27 C.
- Each request carries the eight unchanged bench `t16_*` cards **and** absolute 50 %
  crossing times at four stages per lane (`t16attr_probes.inc`): 0 ideal stimulus, 1 TX cell
  output, 2 TX pad (after the TX ESD resistor), 3 RX-side pin after the link; plus `csig`.
- Self-check: the probe-built t16 equals the bench card within 0.9 ps in all 64 pairs
  (`residual` in `attribution.json`; the largest, 0.83 ps, is on a `*_cr_long` pair, where
  a 1 ps-scale ngspice WHEN/TRIG interpolation difference is the likely cause). `pre132/ch_ss`
  `t16_df_cf_long` = 434.8 ps, the issue's number, to the digit; `cur/ch_ss` = 458.5 ps =
  the 20261110 record's 458.455 ps.

## Finding 0: the 65 ps predates #132

The issue and its curator note guess the 65 ps already includes #132's driver. It does not.
`9e2577b` (driver 28/14 um -> 54/22 um with series resistors, `Dp1` 10 um -> 4.5 um) is not an
ancestor of `394bb86`; it reached `main` with merge `282a9d4` on 2026-11-10, and the
20261110 CH record is the first on it. #132 changes exactly the TX path analysed here:
binding `t16_df_cf_long` 434.8 -> 458.5 ps (+23.7 ps), 29 -> 8 failing corners (by any
T-16 edge outside 470-530 ps; the record's own count is 58 -> 16 failing measurements).
**On current `main` the binding miss is 41.5 ps, not 65 ps.** Both are decomposed below.

## Attribution at the binding corner (mos_ss, 1.08 V, 125 C, `t16_df_cf_long`)

Sign: negative = data edge late against the clock. Terms telescope along the path: t16 =
500 + stimulus + driver + esd_tx + link + diff_x (definitions in `t16attr_post.py`).

| Contributor (ps) | pre-#132 (`394bb86`) | current (`ed04503`) | source |
|---|---|---|---|
| Stimulus offset error | 0.0 | 0.0 | ideal sources, 500 ps by construction |
| **A. TX cell rise/fall asymmetry**, link-independent (ideal connection: driver + esd_tx + diff_x) | -22.7 (-23.3 -2.2 +2.8) | -22.5 (-21.0 -0.1 -1.4) | `id_ss` |
| **B. Same cell under channel + pad loading** (driver term, channel minus ideal) | -15.6 | -8.9 | `ch_ss` - `id_ss` |
| **C. Data-dependent delay at the TX pad** (esd_tx term, channel minus ideal; run-length) | -25.0 | -12.6 | `ch_ss` - `id_ss` |
| D. Channel line itself (pad to RX pin) | 0.0 | +0.4 | `ch_ss` link term |
| E. Differential-vs-single-ended crossing definition (`csig` against mean of the two clock pins) | -1.9 | +2.1 | `ch_ss` - `id_ss` diff_x |
| **Sum** | **-65.2** | **-41.5** | |
| t16 bench card, minus 500 | -65.2 | -41.5 | |
| **Residual** (sum - bench card) | **0.0** | **0.0** | arithmetic is exact: -22.7-15.6-25.0+0.0-1.9 = -65.2; -22.5-8.9-12.6+0.4+2.1 = -41.5 |

Reading it:

- **A is the TX cell's rise/fall delay difference, halved.** At the cell output (ideal
  connection, current design) a falling data edge is 41 ps later than a rising one (185 vs
  144 ps from the stimulus; pre-#132 156 vs 112 ps). The forwarded clock is a quasi-differential pair:
  its `csig` crossing is where a rising lane meets a falling lane, so it sits midway between the
  rise and fall delays. A single-ended data edge sees only one of them: half the difference,
  about 21 ps, with opposite sign on rising data (ideal connection: `t16_dr_*` are about +19 ps
at this corner). At
  mos_tt/1.2 V/27 C it is about 14 ps. It is fixed by the cell, not the channel, and is
  unchanged by #132 (-22.7 vs -22.5).
- **B + C are channel- and pad-loading terms** and are what #132 recovered (B +6.7, C +12.4
  ps). C is run-length dependent: the same pad stage contributes +1.9 ps on the short-run
  `t16_df_cf_short` pair (-12.7 vs -2.3 ps current; -27.2 vs +1.9 pre-#132). The clock lanes
  toggle every UI and always behave like the short-run case; a long-run data edge starts from a
  fully settled rail. The mechanism inside the pad (series R with channel C, junction
  capacitance, line L) was not separated; only its size and run-length dependence are measured.
- **D and E are small**: the line adds under 1 ps of skew (it delays data and clock lanes
  alike), and the bench's differential crossing definition adds under 3 ps. The channel is not
  the cause; its loading of the TX is (B and C).
- Measurement artefact or channel are therefore ruled out as the dominant terms: the
  ideal connection alone already misses by 22.5 ps (477.5 ps), 75 % of the allowed 30 ps.

Typical corner (mos_tt, 1.20 V, 27 C, `t16_df_cf_long`, current design): 477.0 ps = 500 -
23.0; ideal connection 484.9 (-15.1), so the cell term A is about -15 and channel loading
B + C about -8 (driver -17.2 -(-14.5)= -2.7, esd_tx -6.9 -0.1 = -7.0, link +0.6, diff_x +0.5 +0.8
= +1.3). Full tables for all 8 pairs x 2 links x 2 corners x 2 designs: `attribution.json`.

## Trend over the 45 corners (`trend.json`, from the two existing CH records)

Largest |t16 - 500 ps| over the eight edge pairs:

| | by process | by supply | by temperature |
|---|---|---|---|
| pre-#132 | ff 33.5, sf 45.2, fs 45.2, tt 44.8, **ss 65.2** | **1.08 V 65.2**, 1.20 V 48.7, 1.32 V 40.0 | -40 C 56.7, 27 C 59.4, **125 C 65.2** |
| current | ff 19.9, sf 24.0, tt 29.6, fs 34.9, **ss 41.5** | **1.08 V 41.5**, 1.20 V 33.4, 1.32 V 28.1 | -40 C 39.6, 27 C 41.3, **125 C 41.5** |

The offset grows toward slow process and low supply (both slow the cell, which grows A
and B); temperature is a weak effect (ss, 1.08 V: `t16_df_cf_long` 460.4 / 458.7 / 458.5 ps at
-40 / 27 / 125 C current). At ss/125 C `t16_df_cf_long` is 458.5 / 466.6 / 471.9 ps at 1.08 /
1.20 / 1.32 V. A fix is judged against the whole set: current design, the 8 corners with a miss
are mos_ss at 1.08 V (all three temperatures, 39.6-41.5 ps), mos_ss at 1.20 V (27 and 125 C,
31.8 and 33.4 ps) and mos_fs at 1.08 V (all three temperatures, 33.9-34.9 ps).

## Does the bench's T-16 match the spec row? No, not exactly.

Spec row T-16 (`spec/target-spec.md:58`): "Data-to-clock skew, RX input, <= 0.03 UI", basis AIB
1.2 §2.1.3.3 Table 7 tDCS, **STAT** (DR-0013: a corner sweep sees only the systematic part),
and in the timing budget it is one line subtracted from the 0.40 UI eye, alongside a separate
alignment placement error (T-21). The bench measures something different:

1. It measures the **signed offset of each data edge from 0.5 UI**, with the limit applied as
   500 ps +/- 30 ps. 0.5 UI is where the *stimulus* puts the clock (center-aligned at the
   TX); the bench has **no forwarded-clock alignment**, so the 500 ps nominal assumes none.
2. The spec's own interface (`spec/dll-interface.md` D-12) says static phase is not required:
   alignment is relative and found by calibration sweep. A static offset common to every data
   edge is therefore calibrated away in the product, and what remains as "skew" is the spread
   between edges. The bench does not separate the two.
3. Edge selection: a single-ended data pin crossing `VDD/2` (`dsa`) against the differential
   clock crossing (`csig`); eight pairs (rise/fall, short/long run, clock rise/fall). Spec
   text does not say single-ended vs differential reference.

Neither the bench nor the row is changed here. The numbers an operator needs if this is
taken as a spec question, at the binding corner (eight measured pairs only; a full PRBS has
more edges): spread across the eight pairs = **69.5 ps current** (458.5 to 528.0) and 94.8 ps
pre-#132 (434.8 to 529.6). With a calibrated center the half-spread is 34.8 ps current
(47.4 pre-#132) against the 30 ps bound; so even under the "calibrated" reading the current design
misses by 4.8 ps, and the ideal-connection-only spread (cell term alone) is 41 ps (+/-20.5).

## Recommendation

**Design change (preferred; the cell term is the largest single contributor and survives #132):**
balance rising and falling propagation in the TX data cell, `design/aib_tx_data.spice`
(predriver `XMnd*`/`XMnr*` NAND/NOR stages and output devices `XMp` 54 um / `XMn` 22 um, the
fall path being the slower one at slow corners). The clock lanes are two instances of the same
cell, so they need no separate change. First-order expected recovery at the binding corner,
assuming the asymmetry can be removed without changing the load terms B and C (untested): term
A (-22.5 ps) goes to about 0, taking `t16_df_cf_long` from 458.5 to about 480 ps and
`t16_dr_cr_long` from 509 to about 489 ps; the eight-pair range becomes roughly
480 - 504 ps, inside 470 - 530 ps. Terms B and C (-21.5 ps together, current) remain and are
the margin left; C is run-length dependent and would be reduced by lowering the pad-stage
loading seen at the TX output (not analysed here).

**If design cannot close it**, the operator's inputs are the spread and cell-term numbers in the
previous section, and the question is whether T-16 means offset from an unaligned 0.5 UI
(bench) or spread about an aligned clock (D-12): 41.5 ps miss vs 4.8 ps miss at the binding
corner, current design.

Not done (out of scope): the fix, Monte Carlo (#137), a bench change, a decision record.
Corners other than the two above were not re-simulated; the trend uses the existing records.
