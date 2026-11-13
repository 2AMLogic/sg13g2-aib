# clock-path PVT-FULL record 20261113T095936Z (T-17 / T-04 / T-02 SIM half)

**Simulated.** 45 corners (5 MOS x VDDIO 1.08/1.20/1.32 V x -40/27/125 C), one `klt sim`
request on the Spot batch fleet, split into 15 jobs of 3 corners; every job id is in
`record.json` -> `batch_job_ids`, runner klt 0.9.0, PDK v0.3.0. `klt sim` exited 0:
45/45 corners carry a status, 0 failed, 0 errored. No local grid was run.

**Claim scope: CH** — the declared die-to-die channel CH-3MM-RC
(`spec/channel/channel_rc.cir`, nominal `kr = kc = 1`), not the test configuration. There is
no die-to-die assembly to measure; this is a modeled-channel result, not silicon.
Reproduce with `sim/clock-path/run_clock_path.sh`.

Path under test: `aib_tx_clk` -> `aib_pad_esd` -> CH-3MM-RC -> `aib_pad_esd` -> `aib_rx_clk`,
plus one `aib_tx_data` -> ... -> `aib_rx_data` lane for the data-to-clock timing. Stimulus is
an **ideal complementary 50 % 500 MHz** forwarded clock (1 Gb/s DDR), so the duty-cycle
distortion measured at the TX output is what the TX clock path itself adds — the stimulus
contributes none.

## T-17 — forwarded-clock duty-cycle distortion at the TX output: PASS at 45/45

270/270 graded measurements pass the +/-3 % bound of `spec/target-spec.md` T-17.

| | value | corner |
|---|---|---|
| worst \|DCD\| | **-1.036 %** (margin 1.964 %) | `mos_sf`, 1.08 V, -40 C |
| next | -0.739 % | `mos_sf`, 1.08 V, 27 C |
| high time / period at the binding corner | 979.3 ps / 2000.0 ps | |

`clk` and `clkb` distort identically (`t17_dcd_c` == `t17_dcd_cb` to six digits) — the two
halves of `aib_tx_clk` are the same `aib_tx_data` cell driven by complementary inputs. The
binding corner is one of the two the spec row calls out explicitly (`mos_sf`/`mos_fs` at
-40 C). **No duty-cycle corrector is needed for T-17 at 1 Gb/s**, and none is designed here
(repo scope discipline). Gap G3 / D-9 of `spec/dll-interface.md` is **not** triggered.

## T-04 — clk/clkb crossing at the RX: reported (no numeric bound in the spec)

`spec/target-spec.md` T-04 names `SIM` evidence of the clk/clkb crossing over PVT-FULL but
states no numeric crossing bound, so these 225 measurements are reported, never graded.
No bound was invented. Crossing level is given as an offset from VDDIO/2.

| quantity | range over 45 corners | worst corner |
|---|---|---|
| crossing offset at the RX **pins** | -19.2 mV .. +9.1 mV | `mos_sf` 1.08 V -40 C / `mos_fs` 1.32 V 125 C |
| crossing offset at the RX **outputs** | -646.1 mV .. -2.3 mV | `mos_sf` 1.32 V -40 C |
| TX-input-crossing to RX-output-crossing latency | 338.4 ps .. 629.1 ps | `mos_ff` 1.32 V 27 C / `mos_ss` 1.08 V -40 C |

The quasi-differential pair crosses essentially at mid-rail **at the pins** (within 20 mV of
VDDIO/2 at every corner) — the channel and the pad ESD preserve the crossing. The large
offset **at the RX outputs** is not a channel effect: it is the rise/fall asymmetry of the
`aib_rx_data` two-inverter receiver, which separates the two single-ended outputs in time, so
their crossing lands far from mid-rail. See the T-02 finding below, which is the same effect
measured in the time domain.

## T-02 — DDR data-exchange timing, SIM half: reported

180 measurements, report-only: the spec's T-02 row defines the DDR *format*, and the numeric
capture budget lives in T-19 (aperture) and T-20 (margin), neither of which is graded here.

Data edge versus the forwarded clock's edges, both at the **RX outputs** (the nodes an RTL
capture flop would see), nominal 0.5 UI = 500 ps:

| measurement | range over 45 corners | worst corner |
|---|---|---|
| `t02_dr_cr` (data rise -> clock rise) | 499.992 .. 500.001 ps | — |
| `t02_df_cf` (data fall -> clock fall) | 499.988 .. 500.002 ps | — |
| `t02_cr_df` (clock rise -> data fall) | **397.4** .. 499.8 ps | `mos_sf`, 1.08 V, -40 C |
| `t02_cf_dr` (clock fall -> data rise) | 500.2 .. **602.6** ps | `mos_sf`, 1.08 V, -40 C |

### Finding: the DDR half-UI is off-centre by up to 0.103 UI at the RX output

Same-direction edges track to under 0.01 ps — the data lane and the clock lane are the same
cells on the same channel, so their rise delays (and their fall delays) cancel exactly.
**Opposite-direction** edges do not: `t02_cr_df` is 102.6 ps early and `t02_cf_dr` 102.6 ps
late at `mos_sf`/1.08 V/-40 C, i.e. the alternate DDR half-period at the capture node is
397.4 ps instead of 500 ps (**0.103 UI** of static off-centring, before any jitter or
mismatch).

That residue is the end-to-end rise/fall delay asymmetry of one lane. It is **not** mostly
the TX: T-17 above measures only -20.7 ps of it at the TX pad (-1.036 % of 2 ns) at that same
corner. The remaining ~82 ps is added after the pad, and dominantly by the `aib_rx_data`
receiver — two inverters whose pull-up and pull-down are not matched at `mos_sf`, where the
PMOS is fast and the NMOS slow.

**This does not contradict T-16.** `sim/channel-eye` grades T-16 (0.5 UI +/- 0.03 UI) at the
**RX pins** (`rxa`, `rxc`/`rxcb`), before the receiver, and it passes 45/45 there on current
`main`. This record measures **after** the receiver. The two are complementary, and the
difference between them is the receiver's contribution.

**Consequence for the budget, not graded here.** `spec/target-spec.md`'s timing budget charges
0.150 UI to T-19 (capture aperture) and leaves 0.1075 UI of T-20 margin. 0.103 UI of static
off-centring at the capture node is of that order, so whether T-20 still closes depends on
where T-19's aperture is referenced. That is a T-19/T-20 question for the budget owner
(#42), not a clock-path row: this record reports the number and does not relax, re-derive, or
re-allocate any bound. Filed as #177.

## T-21 and T-29 — declared gaps, not covered

Both are declared gaps with follow-up issues (#175 for T-21, #176 for T-29), as the
curation of #54 decided:

- **T-21** (forwarded-clock alignment / DLL interface, `SIM` of the contract in
  `spec/dll-interface.md`) needs a DLL-side model. This repo has no `consumes:` edge and does
  not design a DLL; the contract is compared against the SG13G2 DLL canary by name and
  commit, which is not this bench's job.
- **T-29** (loopback modes L1/L2) has no loopback mux in any of the five `design/*.spice`
  cells, so there is nothing here to exercise. It is also a **TC** row, while this record is
  CH-scoped.

Neither is cheaply expressible on this bench, and neither is claimed.

## Files

| file | what it is |
|---|---|
| `report.json.gz` | the `klt sim` report, 45 corners, verbatim |
| `rows.json` | per-spec-row roll-up (`channel_eye_post.py`) |
| `record.json` | the record fact sheet: verdicts, binding corners, report-only ranges, batch job ids |
| `request.json`, `tb_clock_path.cir`, `clock_stim.inc` | the exact inputs this record was produced from |
| `klt.stderr` | fleet progress log (bucket names redacted) |
