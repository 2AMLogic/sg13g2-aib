# sim

Simulation toolchain pin and the PDK/OSDI smoke. No design value lives here.

## PDK pin

`sim/pdk.json` names the IHP-Open-PDK release (`v0.3.0`), its tarball SHA-256,
and the OSDI toolchain (OpenVAF-Reloaded `v24.0.1mob`). Every record under
`sim/` traces to it. Records are append-only: a new run is a new directory,
and an earlier record is never edited.

## OSDI device models

The PDK ships the PSP103 and `r3_cmc` Verilog-A sources, not `.osdi` binaries.
`sim/harness/common/build-osdi.sh` is vendored byte-for-byte from
`2AMLogic/sg13g2-bandgap` at `52535387e6ccf0a89f6490901a9abb2b78144176`
(`sim/tools/build-osdi.sh`; pinned in `reuse.lock.json`). It sources
`sim/harness/env.sh`. No `.osdi` is committed; `sim/build/` is gitignored.

## Reproduce

From a clean checkout:

```bash
sim/harness/common/fetch-pdk.sh                  # checksum-verified fetch into sim/build/pdk
source sim/harness/env.sh                        # exports PDK_ROOT, PDK
SG13G2_TOOLS_CACHE=$PWD/sim/build/cache sim/harness/common/build-osdi.sh
sim/pdk-smoke/run_smoke.sh                       # writes sim/pdk-smoke/records/<UTC>/
```

A tarball checksum mismatch aborts `fetch-pdk.sh` (exit 4) and leaves no
install behind. `build-osdi.sh` likewise refuses an unverified compiler.

## pdk-smoke

`sim/pdk-smoke/` runs one corner (`mos_tt`, 27 C) with a single local
`ngspice -b`: DC operating point and an Id-Vgs sweep for `sg13_lv_nmos`,
`sg13_lv_pmos`, `sg13_hv_nmos` and `sg13_hv_pmos`. **Smoke only**: W/L,
supplies and sweep ranges are arbitrary and set no spec value. Each record
holds `netlist.cir` (deck snapshot), `ngspice.log`, and `record.json` (PDK
tag, ngspice and OpenVAF-R versions, per-device convergence).

Tool note: the worker's `ngspice` is `ngspice-46`; it loads the PSP103 OSDI
models built by the pinned OpenVAF-R. The PDK's `versions.txt` documents 43.

## rtl-synth

`sim/rtl-synth/run_synth.sh` elaborates `rtl/aib_datapath.v` with Yosys and maps it to
`sg13g2_stdcell` (typ 1.20 V 25 C liberty from the pinned PDK) for N = 20 and N = 8.
**Smoke only**: it records the Yosys version, the liberty file (relative to the PDK
root), the cell counts and the exit code; there is no timing and no area claim. Each
run writes `sim/rtl-synth/records/<UTC>/` with the `.ys` scripts, Yosys logs and
`record.json`, append-only like the other records.

## channel-eye

`sim/channel-eye/` is the PVT-FULL channel-transient family of the T1 item 5 (analog)
campaign (#42, #53): PRBS-7 at 1 Gb/s through four lanes (data A, its complement B, and the
clk/clkb forwarded-clock pair), each `aib_tx_data` -> `aib_pad_esd` -> link ->
`aib_pad_esd` -> `aib_rx_data` (`.include`d from `design/`, never copied). Rows:
T-01 (bit transfer: DOUT edge count over one PRBS period), T-18 (best 0.40 UI window of
the RX-pin eye, height >= 90 mV), T-09 (overshoot/undershoot peak and dwell, four RX
pins), T-26 (supply energy per bit of TX, RX and the clock lane shared over N = 20
wires; **simulated**, the record says so), and the single-instance halves of T-15
(opposite-polarity edges on A/B) and T-16 (data edge to center-aligned clock edge, nominal
0.5 UI). The array and Monte Carlo halves of T-14/T-15/T-16 are #44's.

Two separate requests keep the claims apart: `request_ch_1g.json` is **CH-3MM-RC**
(`spec/channel/channel_rc.cir`, nominal kr = kc = 1); `request_tc_1g.json` is the **L2
wire-bond loopback** of `spec/test-configuration.md` (2 nH per wire, 0.5 pF per pin,
declared). TC grades only T-09 (expected to fail there; recorded, not relaxed); its T-01 and
T-26 are report-only, and T-15/T-16/T-18 are not observable in L2 and are not requested.
`gen_channel_eye.py` writes `prbs7_stim.inc` and the requests (`--check` for staleness);
the 75 CH measurements are generated, not hand-written.

```bash
python3 -I sim/channel-eye/test_channel_eye.py        # generator + post-processor self-tests
cd sim/channel-eye && klt sim request_ch_1g.json --dry-run   # 45 corners
sim/channel-eye/run_channel_eye.sh ch                 # batch fleet; writes records/<UTC>-ch/
sim/channel-eye/run_channel_eye.sh tc
```

Corners: `mos_{tt,ss,ff,sf,fs}` x VDDIO 1.08/1.20/1.32 V x -40/27/125 C; the resistor and
diode sections follow the MOS corner (tt/sf/fs: `res_typ`/`dio_tt`, ss: `res_wcs`/`dio_ss`,
ff: `res_bcs`/`dio_ff`). Six supply sources (A/B/clock, TX/RX) sweep together so the energy
of each block is separable.

**Status: no 45-corner record exists yet, and no row is claimed.** Findings from bringing
the bench up on the batch fleet (2026-10-27, `mos_tt`, 1.20 V, 27 C):

1. *`design/aib_tx_data.spice` output PMOS does not conduct.* `XMp ... w=1u ng=28` sources
   no current with the PDK v0.3.0 PSP103 model: with a 10 kohm load, `sg13_lv_pmos
   w=1u` conducts for ng <= 10, is weak at ng = 12 and dead for ng >= 16, while `w=2u ng=14`
   works. With DIN high the pad stays at ~0 V. Every row therefore fails at every corner
   until the cell is fixed (#35's files; not edited here). `control/aib_tx_data_ctl.spice`
   is a diagnostic copy with that one device changed to `w=2u ng=14` (same 28 um total) and
   `tb_ctl_ch.cir` / `request_ctl_ch_tt.json` use it. It is **not design evidence**.
2. *Even with that copy the four-lane transient does not complete.* At the first clock
   edge the solve aborts (`Timestep too small ... trouble with node "vdd_crx#branch"`,
   ~0.83 ns). Single-lane isolation runs of 3 ns: TX -> channel -> RX without the pad ESD
   cell completes; the pad ESD cell with the RX completes; TX + ESD + channel + ESD + RX did
   not finish in 11 min. The pad ESD path is the suspect; the cause is not isolated.
   **Bisect (issue #60, one corner `mos_tt` 1.20 V 27 C, local, an unrecorded debug probe;
   the netlists came from a probe script, `bisect_esd.py`, at commit `a540af4`, no longer in the tree).** Driver check on `main` @ `85832ba`: with
   DIN = OE = VDDIO the pad is 1.1999 V into 1 Mohm and 1.1918 V into 10 kohm, so finding 1
   is fixed by `5584f0b`. One lane, 3 ns, `tran 2p 3n 0 5p`: no ESD cell completes in 1 s;
   ESD on the TX side only aborts at 2.30 ns, on the RX side only at 0.82 ns, on both at
   1.03 ns (`Timestep too small ... "vrx#branch"`, which names the supply branch, not the
   culprit). Removing one `aib_pad_esd` element from the TX-side-only case: `XMclamp`,
   `XResd`, `XDp1`, `XDn1`, `XDp2` still abort; removing `XDn2` (the 2u x 2u `dantenna`
   on the inner node) completes, as does replacing it with 1 Tohm or 1 fF. With `XDn2` kept
   as a plain diode on the `darea` card, dropping any one of `tt`, `bv`/`ibv`, `rs` also
   completes, while dropping `cj0` makes it abort earlier (0.61 ns). The abort time does not
   move with `gmin`, `abstol`, `vntol`, `reltol` 1e-2, `method=gear`, `klu` or `pivtol`,
   and `reltol` 1e-4 or `tmax` 1-2 ps do not abort but crawl past 100 s. The diode alone,
   driven by a similar RC edge, converges. Reading: the abort coincides with the PDK
   `dantenna` model (long `tt`, large `rs`, breakdown card) on the inner pad node, and is
   marginal rather than tied to one parameter; a bench option does not clear it and a cell
   change in `design/` (#35's lineage) is not made here. Not established: whether the
   PSP/OSDI side or the diode card is at fault, and any other corner.
   **Candidate `XDn2` variants (issue #60, same corner, local, serial, 150 s cap per run,
   ngspice-47 with OSDI; the `v_*`/`vb_*` netlists came from `bisect_esd.py` at commit `a540af4`, no longer in the tree).** Baseline `b10` aborts at
   2.298 ns in <1 s. `dantenna` 1u x 1u, 0.78u x 0.78u (minimum), and 2u x 2u behind a 100 ohm
   or 1 kohm `rppd`: no abort but no completion in 150 s (crawl), so not usable. A
   grounded-gate `sg13_lv_nmos w=1u l=0.13u` with its drain on `PADI` (`XMn2`, the drain
   junction as the diode) completes in <1 s with the ESD cell on the TX side only
   (`vmax` RX pin 1.147 V) and on both pads (1.108 V). Chosen; `design/aib_pad_esd.*` carries it.
   *Design-risk note (reduced ESD is a named risk).* DC at `mos_tt` 27 C, model only: the old
   `dantenna` forward branch is series-resistance limited (5.6 uA at -1 V, 0.19 uA at -0.7 V);
   `XMn2` carries 3.7 mA at -1 V and 0.10 mA at -0.7 V, and leaks 24 pA vs 86 pA at +1.1 V.
   So the model-level clamp to VSS at `PADI` is stronger, not weaker; no ESD level (T-25) or
   capacitance (T-24) is claimed, and an NMOS drain junction is not a characterised ESD
   structure in the PDK. The four-lane transient and other corners are not re-run here (fleet,
   #53). These results are the test configuration (pad ESD in the loop), not the modeled
   channel. Local host note: `/usr/bin/ngspice` 42 cannot load the OSDI v0.4 models; the
   variant runs used an ngspice-47 build.
   **Four-lane abort bisect (issue #94, fleet, `klt` 0.8.0, `--backend batch`, one corner
   `mos_tt` / all supplies 1.20 V / 27 C, `main` @ `3c031e9`; unrecorded debug probes, no
   PVT record).** The four-lane CH (`klt-sim-e77210c8bec8`) and TC (`klt-sim-1a7716fd7b44`)
   requests abort with `timestep_too_small` (CH at 22.4664 ns, TC at 5.69152 ns). The probes
   are `tb_ch.cir` / `tb_tc.cir` with lanes deleted from a copy of `tb_body.inc` (same 141 ns
   `tran 2p 141n 0 5p`, one scratch measurement; the 45-corner requests are unchanged).
   | Probe | Job | Result |
   |---|---|---|
   | CH, lane A only | `klt-sim-881a4cb2c152` | abort at 22.4664 ns, `vdd_arx#branch` |
   | CH, lanes A+B | `klt-sim-0d4b3f644ae7` | abort at 22.4664 ns, `vdd_brx#branch` |
   | CH, lanes C+CB only (the shared `vdd_crx` pair) | `klt-sim-6e3aaf599c15` | completes, 141 ns |
   | CH, lane A, TX-side `aib_pad_esd` replaced by 1 mohm | `klt-sim-d5dc022168c7` | completes |
   | CH, lane A, RX-side `aib_pad_esd` replaced by 1 mohm | `klt-sim-a88d7f1f4a40` | completes |
   | TC, lane A only | `klt-sim-9a51a802416f` | abort at 22.7029 ns, `vdd_arx#branch` |
   | TC, lanes C+CB only | `klt-sim-87b22d364017` | completes |
   Measured: (1) the shared `vdd_crx` supply is not the cause in CH: the C+CB pair alone
   completes, and a single data lane aborts with no shared supply at all, so splitting
   `vdd_crx`/`vdd_cbrx` in `tb_body.inc` would not clear it. (2) The abort sits in the data
   lane, at the same instant with one lane or two (22.4664 ns), 1.4 ns after the first fall
   that ends the 7-UI run of ones (UI 14-20, fall at 21 ns); the alternating clock lanes
   never see such a run. (3) With either pad-ESD cell removed from the lane the transient
   completes, so the abort needs the ESD cell on both pads in the loop, as the #60 bisect
   found for the earlier `XDn2`. The `XMn2` replacement is therefore not shown to be clean
   in a long-run PRBS bench; the earlier 3 ns one-lane check never reached such a run.
   Not established: which `aib_pad_esd` element is marginal now (`XMn2` vs the
   `dpantenna` / `dantenna` / `rppd` / clamp devices), why the four-lane TC aborts at 5.69 ns
   while lane A alone aborts at 22.7 ns (the lane subsets A and C+CB do not reproduce the
   early abort, so it depends on the full lane set), any other corner, and whether the
   marginality is the PSP/OSDI model or the cell. Conclusion for #53: its Revision step 1
   is **not** satisfied; a bench partition does not fix it, and the next step is a cell-level
   bisect of `aib_pad_esd` on lane A (this stimulus) through the `design/` path. No bound
   changed, nothing under `design/` or `spec/` edited, no grid submitted.
   **Cell-level `aib_pad_esd` bisect (issue #94, fleet, `klt` 0.8.0, `--backend batch`, one
   corner `mos_tt` / 1.20 V / 27 C, `main` @ `c3f3f65`; unrecorded debug probes, no PVT record).**
   Lane A only, CH stimulus and channel, both lane-A `aib_pad_esd` instances replaced by a
   scratch copy with one element changed (scratch copies only; `design/` untouched);
   `tran 2p 24n 0 5p`, one scratch measurement (`vecmax(v(douta))`). "Completes" means it passed
   22.4664 ns and reached 24 ns, not that it would survive 141 ns.
   | Probe (both pad-ESD cells) | Job | Result |
   |---|---|---|
   | unchanged cell (control) | `klt-sim-ead411c70b7c` | abort 22.4664 ns, node `xesdr.xdn1.d1#internal` |
   | `XDn1` removed | `klt-sim-992cdbae733c` | completes to 24 ns |
   | `XResd` replaced by 1 mohm | `klt-sim-494cd46dbadd` | completes to 24 ns |
   | `XMclamp` removed | `klt-sim-82799cc6d272` | abort 22.4664 ns, same node (clamp not involved) |
   | `XDp1` / `XDp2` / `XMn2` removed | `klt-sim-1fe34ddf7807` / `-d47a63aeadbc` / `-d2ca69614614` | abort earlier (3.32 / 3.46 / 7.46 ns, `vdd_arx#branch`): these clamp the overshoot, so removal is a different failure and says nothing about the 22.47 ns one |
   | `XDn1` `l=5u w=20u` (same 100 um2) | `klt-sim-0203bb24dda9` | completes to 24 ns |
   | `XDn1` `l=5u w=5u m=4` / `l=3.16u w=3.16u m=10` | `klt-sim-add17770a9e4` / `-4254fe4da764` | abort 3.46 / 3.46 ns (`vdd_arx#branch` / TX `xdn1.d1#internal`) |
   | four-lane CH, `XDn1` `l=5u w=20u`, full 141 ns bench | `klt-sim-6a9f70cebf67` | abort 29.4206 ns, node `pa_09` |
   | four-lane TC, same cell | `klt-sim-039e35b4f3f7` | abort 22.7033 ns, node `pa_09` |
   Measured: (1) the 22.4664 ns abort is localised to the `dantenna` `XDn1` (PAD to VSS, 10u x 10u)
   in series with the `rppd` `XResd`: the trouble node is the RX-side `XDn1` internal diode node,
   and removing `XDn1` or collapsing `XResd` clears it, while removing the clamp does not move it.
   (2) The `dantenna` model is geometry-sensitive: the same 100 um2 as 5u x 20u moves the lane-A
   abort past 24 ns, and the same area as m=4 or m=10 aborts at 3.5 ns. (3) That geometry change
   is **not a fix**: on the full four-lane bench CH only moves from 22.4664 to 29.4206 ns and TC
   stays at 22.70 ns, and both now report the stimulus node `pa_09` (a PWL source node, not a cell
   node), so the lane-A 24 ns "completes" rows are not evidence of convergence over 141 ns.
   Not established: why the abort moves to `pa_09`; whether it is the PSP/OSDI `dantenna` model
   with the PWL stimulus breakpoints, or a real overshoot the ESD diode is clamping; any other
   corner. No `design/` or `spec/` change was made: a `dantenna` geometry change would also alter
   the drawn diode and the `layout/lvs/*.ref.spice` references (`A=100P P=40U`) and was not a
   fix. Conclusion for #53: Revision step 1 is still **not** satisfied. The next step is a
   stimulus-side bisect (PWL edge / source node `pa_09` behaviour past 22 ns) before touching the
   cell again. No bound changed, no grid submitted.
   **Stimulus-side bisect (issue #94, fleet, `klt` 0.8.0, `--backend batch`, one corner
   `mos_tt` / 1.20 V / 27 C, `main` @ `1078396`; unrecorded debug probes, no PVT record).**
   Lane A only, CH channel, `tran 2p 45n 0 5p`, scratch copies of `prbs7_stim.inc` and (for
   the `5u x 20u` rows) `aib_pad_esd.spice`; `design/`, `spec/`, the committed bench and
   requests are untouched. The stimulus changes are diagnostics, not channel-model inputs: the
   declared 100 ps ramp and PRBS-7 stream stay what the committed requests use.
   | Probe (lane A, CH) | `XDn1` 10u x 10u (as drawn) | `XDn1` 5u x 20u |
   |---|---|---|
   | committed PRBS-7, 100 ps ramp | abort 22.4664 ns, `xa.xesdr.xdn1.d1#internal` (`klt-sim-7059dbe2a56b`) | abort 29.4206 ns, `vdd_arx#branch` (`klt-sim-63b1f487e6df`) |
   | same bits, 50 ps ramp | abort 29.386 ns (`klt-sim-32667c6f4ab7`) | not run |
   | same bits, 200 ps ramp | abort 3.5358 ns (`klt-sim-fee49e070122`) | not run |
   | same bits, 400 ps ramp | abort 7.661 ns, `vdd_arx#branch` (`klt-sim-7dea7e9df817`) | abort 7.661 ns (`klt-sim-51d455a6aa44`) |
   | `1010...` (every UI toggles), 100 ps ramp | completes 45 ns (`klt-sim-9c95ac34c065`) | completes 45 ns (`klt-sim-c2238d878e4e`) |
   | `110110...` (one-UI lows), 100 ps ramp | completes 45 ns (`klt-sim-7ddb11ffa08b`) | not run |
   | `100100...` (two-UI lows), 100 ps ramp | abort 5.4208 ns, `vdd_arx#branch` (`klt-sim-3e0648a837f3`) | not run |
   Pad envelope just before the unchanged-cell abort (`klt-sim-b791d878d2b1`, 20-22.4 ns):
   `rxa` 0.042 to 1.208 V, TX pad 0.041 to 1.205 V, RX `rxi` 0.043 to 1.207 V, TX `txi`
   0.006 to 1.236 V. The 200 ps case (`klt-sim-3b4ad6427781`, 2.5-3.5 ns) has the same low
   level, 0.042 V.
   Measured: (1) Lane A alone reproduces the abort time of the four-lane benches exactly
   (29.4206 ns for the `5u x 20u` cell, 22.4664 ns unchanged), so the abort is intrinsic to
   one lane; the node `pa_09` named in the four-lane reports did not appear in any lane-A run
   (which names `xa.xesdr.xdn1.d1#internal` or `vdd_arx#branch`) and is **not** shown to be a
   stimulus-source node. (2) The pad never goes below ~0.04 V or above ~1.24 V before the abort,
   so the `dantenna` is never forward biased and no overshoot is being clamped: this is not a
   physical clamp event. (3) The abort time is not monotonic in the edge rate (50 / 100 / 200 /
   400 ps ramps abort at 29.4 / 22.5 / 3.5 / 7.7 ns) and the unchanged geometry and the
   `5u x 20u` geometry abort at the same 7.661 ns with a 400 ps ramp: a numerical marginality
   in the time step on the `dantenna`/`rppd` node, not a stimulus threshold. (4) It needs a
   pad that stays low for two or more UI after a fall (`100100...` aborts, `110110...` and
   `1010...` complete); in these probes the abort comes 1.2-1.4 ns after the end of such a
   fall. It is history dependent: the committed stream has two-UI lows at 2.1-4.0 ns that
   pass.
   Not established: whether it is the PSP/OSDI `dantenna` model near zero bias in series with
   `rppd` or the ngspice-46 step control on that node; any other corner; whether a different
   diode type clears it (the #60 variants crawled). A bench edit cannot fix it and none was
   made; a fix is a `design/` change (diode type or geometry, with `layout/lvs/*.ref.spice`
   updated together) and is not made here. Conclusion for #53: Revision step 1 is still
   **not** satisfied. No bound changed, no grid submitted.
   **Grounded-gate NMOS in place of `XDn1` (issue #94 increment 1, fleet, `klt` 0.8.1,
   `--backend batch`, `main` @ `3f99254`; unrecorded scratch probes, not a PVT record).**
   Scratch cell copies in `channel-eye/scratch94/` (`design/` untouched) replace `XDn1`
   (PAD to VSS `dantenna` 10u x 10u) with an `sg13_lv_nmos` whose drain is `PAD` and whose
   gate, source and bulk are `VSS` (the #60 `XMn2` pattern): variant a `w=20u l=0.13u ng=10`,
   variant b `w=4u l=0.13u ng=2` (variant b is the lane A probe row only; its scratch copies were dropped
   from the repo per the #111 operator ruling, and only variant a is kept). All rows `mos_tt` / 1.20 V / 27 C unless stated.
   | Probe | Job | Result |
   |---|---|---|
   | lane A, CH, variant a, `tran 2p 45n` | `klt-sim-0157da63ede9` | completes, 1.9 s (committed cell aborts at 22.4664 ns) |
   | lane A, CH, variant b, `tran 2p 45n` | `klt-sim-b740292bc20f` | completes, 2.1 s |
   | four-lane CH, variant a, full 141 ns | `klt-sim-1cb0be38d989` | status `fail`, **no abort**; 75/75 measurements returned |
   | four-lane TC, variant a, full 141 ns | `klt-sim-62bafaaa6a88` | status `pass`; 22/22 measurements returned |
   | four-lane CH, variant a, `mos_ss` 1.08 V -40 C | `klt-sim-d297e7a8bc69` | status `fail`, no abort; 75/75 returned |
   | four-lane TC, variant a, `mos_ss` 1.08 V -40 C | `klt-sim-208ed55fedb5` | status `pass`; 22/22 returned |
   Measured: (1) the candidate clears the abort on every bench that aborted: lane A, and the
   full four-lane CH and TC runs complete all 141 ns (about 22 s of ngspice, against the ~1100 s
   estimate in item 3 above, which was measured before this change) at both corners. This is
   an NMOS drain junction used as the diode at model level, the same substitution #60 made for
   `XDn2`; it is not a characterised ESD structure and no T-24/T-25 claim is made. (2) T-01 edge
   counts are 64 on both lanes in all four full runs (limits 63.5-64.5), and the `.meas INTEG`
   rows (T-09 dwell, T-26) and T-15/T-16 return values. (3) The CH status `fail` is a measurement
   limit, not a solver failure: `t16_df_cr_long` and `t16_df_cf_long` miss their limit by 1.8 and
   2.0 ps at `mos_tt` (margins -1.787 ps / -1.960 ps) and also fail at `mos_ss` 1.08 V -40 C;
   every other CH row, including T-18 eye height (0.411 V), T-26 (0.425 pJ/bit simulated) and
   T-15, passes at both corners. The `df_*_long` rows are a property of the cell and channel,
   not of this probe, and are for #53 to judge; nothing was loosened. TC rows are the
   test-configuration (L2 wire-bond loopback) rows, CH rows the modeled die-to-die channel.
   Not established: that variant a or b is the right ESD structure (the choice is a T-25
   question for the operator); the full `mos_*`/supply/temperature grid; Monte Carlo. This
   is increment 1 only: no `design/`, `layout/` or `spec/` change was made, so LVS/DRC are
   unchanged and **AC 1 is met only for the scratch cell, not for the committed design**.
   #53 Revision step 1 is therefore still not satisfied on `main`; increment 2 (the `design/`
   change with `gen_io_column.py`, GDS, `layout/lvs` references, LVS and DRC) is next. No bound
   changed, no 45-corner grid submitted.
   **Committed cell (issue #94 increment 2, fleet, `klt` 0.8.0, `--backend batch`, single unit
   each; unrecorded probes, not a PVT record).** `design/aib_pad_esd.spice` now carries the
   increment 1 variant a as `XMn1` (`sg13_lv_nmos w=20u l=0.13u ng=10`, drain `PAD`, gate, source
   and bulk `VSS`) in place of the `dantenna` `XDn1`; layout, references and LVS/DRC changed
   with it (`layout/lvs/README.md`). The unmodified `tb_ch.cir` / `tb_tc.cir` were probed
   (four single-corner request copies, since removed in #117: each is the committed
   `request_{ch,tc}_1g.json` with only `corners` narrowed to one corner, `mos_tt` 1.20 V 27 C
   or `mos_ss` 1.08 V -40 C; regenerated byte for byte before removal by loading the request,
   keeping that one `process` entry, setting every `supply_v` rail list and `temperature_c` to
   the single value, and writing `json.dumps(r, indent=2)` plus a newline), full 141 ns bench:
   | Probe | Job | Result |
   |---|---|---|
   | CH, `mos_tt` 1.20 V 27 C | `klt-sim-949909e6cbbf` | no abort, 25.7 s; status `fail`; 75/75 returned |
   | TC, `mos_tt` 1.20 V 27 C | `klt-sim-5c43c36cb843` | status `pass`; 22/22 returned, 27.9 s |
   | CH, `mos_ss` 1.08 V -40 C | `klt-sim-a5239641b9b8` | no abort, 25.4 s; status `fail`; 75/75 returned |
   | TC, `mos_ss` 1.08 V -40 C | `klt-sim-ea93d09c0e0a` | status `pass`; 22/22 returned, 28.4 s |
   Measured: the abort is gone on the committed cell at both corners for both benches; T-01 edge
   counts are 64 on both lanes in all four runs (limits 63.5-64.5); the `.meas INTEG` rows
   (T-09 dwell, T-26: 0.425 pJ/bit CH and 0.518 pJ/bit TC at `mos_tt`, simulated) and T-15/T-16
   return values; T-18 eye height 0.411 V (`mos_tt`) / 0.322 V (`mos_ss`) on CH. The CH `fail` is
   the same measurement limit as in increment 1, not a solver failure: `t16_df_cr_long` and
   `t16_df_cf_long` miss by 1.8 / 2.0 ps at `mos_tt` and by 26.5 / 26.7 ps at `mos_ss`; nothing
   was loosened and the rows are for #53 to judge. CH rows hold for the modeled channel; TC rows
   are the test configuration. The fix is a cell change, not a bench change, and no limit moved.
   Not established: the full 45-corner grid (not submitted, #53); Monte Carlo; that the NMOS
   drain junction is the right ESD structure (a T-25 question, no T-24/T-25 claim is made).
   #53 Revision step 1 (a single-corner probe that completes) is satisfied on the committed
   design at these two corners.
   **45-corner submit attempt (issue #53, 2026-11-02, `main` @ `918ece4`, fleet only; no
   record written, no row claimed).** `run_channel_eye.sh ch` and `tc` were rejected at first
   submit (`batch_max_units_per_job_invalid`: with `timeout_s` 2400 the fleet allows 1 unit per
   job, not 3); the script now uses 1. Re-run as 45 one-unit jobs each, the fleet launched only
   part of them (`... submitted but never launched`): first attempt CH 15/45 and TC 18/45
   corners ran, second attempt 5 and 7. `--resume` raised TC to 38/45 corners done, then the
   remaining 7 jobs stayed `no status.json yet` for over 20 min; CH `--resume` failed with
   `resume_fingerprint_mismatch`. Partial results are not a PVT record and were not committed.
   Of the CH corners that did run in the first attempt, 9 returned status `fail`
   (the `t16_df_*_long` limits seen above) and 6 `pass`; TC 18 of 18 `pass`. Same fleet
   capacity symptom as reported on #54. The script now keeps its resume directory when jobs
   are left unlaunched.
3. *Cost.* About 8 s of ngspice per ns of stimulus (`mos_tt`): ~1100 s for one 141 ns corner,
   so 45 corners are ~14 serial hours; `run_channel_eye.sh` splits them into jobs of at
   most 3 units (fleet job ceiling 3600 s).
   *Correction (PR #113):* the script now uses 1 unit per job, because with `timeout_s` 2400
   the fleet rejects more (`batch_max_units_per_job_invalid`); the "at most 3 units" above
   is the superseded behaviour, kept as history. The ~1100 s corner cost is also superseded
   (about 22 s per full run, see Measured above).
4. *Tooling.* The fleet runner is klt 0.7.0 and refuses the pinned 0.8.0 client, so the
   requests set `batch.runner_version_check: "warn"`; a 0.7.0 client lacks `--dry-run`,
   `--report-out` and rejects `osdi_preload` on the batch backend. Fleet launches were
   refused at times by the instance cap (`batch_concurrency_cap`).

T-15 note: lanes A and B carry complementary data, so the measured skew is the
rise/fall (opposite-polarity) arrival difference of one instance, not a layout skew.
T-16 note: the clock is launched center aligned, so the graded quantity is the deviation
of the data-to-clock arrival delay from the nominal 0.5 UI.

**Status update (2026-11-08): both 45-corner records exist.** The earlier "no record exists
yet" paragraph and findings above are kept unchanged as evidence. On 2026-11-08, with
`--wait-for-capacity 600` added to `run_channel_eye.sh` (the earlier unlaunched-job runs
did not use it), each request ran as one multi-corner batch `klt sim` (45 jobs of 1 unit,
about 23 s per corner, 45/45 corners with a status; job ids are in each record's
`klt.stderr`, e.g. `klt-sim-ba2c0cbe6bc1`). No local grid was run and `design/` and `spec/`
are untouched.

- CH record `channel-eye/records/20261108T220323Z-ch/` (claims about the modeled channel
  CH-3MM-RC): T-01, T-09, T-15, T-18 and T-26 pass at 45/45 corners. **T-16 fails** at 29 of
  45 corners (`t16_df_cr_long` and `t16_df_cf_long`, 58 failing measurements; the window is
  470-530 ps, 0.5 UI +/- 0.03 UI). Worst case `mos_ss`, 1.08 V, 125 C, where
  `t16_df_cf_long` is 435 ps (65 ps from nominal against the 30 ps bound). The bound is not
  relaxed. T-26 is **simulated** energy per bit (smallest margin `mos_ff`, 125 C, 0.555 pJ
  against the 1 pJ bound); no measurement exists.
- TC record `channel-eye/records/20261108T221445Z-tc/` (L2 wire-bond loopback, declared
  values; a test-configuration result, never cited for a channel row): T-09 passes at 45/45
  corners; T-01 and T-26 are report-only. The README's earlier expectation that T-09 would
  fail in L2 did not occur in this run.

**T-16 attribution (#161, parent #142):** record `channel-eye/records/20261111T231422Z-t16attr/`
(simulated; eight local single-corner runs, no batch job; `channel-eye/run_t16attr.sh`). The
65 ps binding miss above is the pre-#132 driver; on current `main` (record `20261110T082948Z-ch`)
it is 41.5 ps. At the binding corner the miss is a sum of named terms with zero residual: the TX
cell's rise/fall delay asymmetry (about -22.5 ps, unchanged by #132), channel/pad loading of the TX
(-21.5 ps current, -40.6 ps pre-#132) and under 3 ps of channel line and crossing definition.
The bench measures offset from an unaligned 0.5 UI, which is not the same thing as the spec
row's skew; neither is changed. See the record's `README.md` for the numbers and the recommendation.

**T-16 design fix (#142):** record `channel-eye/records/20261111T235838Z-ch/` (simulated, CH-3MM-RC,
45 corners, batch backend). The rise/fall asymmetry (term A in the t16attr record) sat in the
predriver NOR's series PMOS pull-up (`XMnr1p`/`XMnr2p`, 4u/ng=2 -> 8u/ng=4 in `aib_tx_data`): it
charges the `XMn` gate through two series PMOS, and it was the slow edge. Ideal-connection probe at
mos_ss/1.08 V/125 C (`run_t16attr.sh` requests, local): data delay rise/fall 144/185 ps -> 145/147
ps, `t16_df_cf_long` 477.5 -> 499.0 ps; under the channel 458.5 -> 486.0 ps. T-16 passes 360/360
measurements at 45/45 corners; the binding point is now `mos_ss/mixed/-40C` `t16_dr_cf_long` =
480.9 ps (10.9 ps inside the 470 ps edge). T-01, T-09, T-15, T-18, T-26 still pass 45/45. The bound,
the bench and the spec are unchanged. DIN input capacitance of the cell rises (NOR PMOS gate area
doubled); the upstream driver of DIN is not modelled in this bench.

## clock-path

`sim/clock-path/` is the PVT-FULL clock-path family of the T1 item 5 (analog) campaign
(#42, #54): `aib_tx_clk` -> `aib_pad_esd` -> CH-3MM-RC -> `aib_pad_esd` -> `aib_rx_clk`, plus
one `aib_tx_data` lane for the data-to-clock timing. Rows: T-17 (forwarded-clock duty-cycle
distortion at the TX output, |DCD| <= 3 %, ideal 50 % input so only the TX clock path
contributes), T-04 (clk/clkb crossing at the RX pins and outputs; report-only, since
`spec/target-spec.md` gives no numeric crossing bound) and T-02 (SIM half: data edge versus
both clock edges at the RX; report-only, T-19/T-20 are not graded here). All rows are CH claims.
T-21 and T-29 are declared gaps (no DLL-side model, no loopback mux in `design/`).

```bash
python3 -I sim/clock-path/gen_clock_path.py --check   # generated files fresh?
cd sim/clock-path && klt sim request.json --dry-run   # 45 corners
sim/clock-path/run_clock_path.sh                      # batch fleet; writes records/<UTC>/
```

**Status (2026-11-13): the 45-corner record exists.** Record `clock-path/records/20261113T095936Z/`
(simulated, CH-3MM-RC, 45 corners, batch backend, 15 jobs of 3 corners; job ids in the record's
`batch_job_ids`). `klt sim` exited 0 with 45/45 corners carrying a status. No local grid was run,
and `design/` and `spec/` are untouched.

- **T-17 passes at 45/45 corners** (90/90 graded measurements against the +/-3 % bound: `t17_dcd_c`
  and `t17_dcd_cb` at 45 corners each; the row's other 180 high-time/period measurements carry no
  limits and are reported, not graded). Worst case
  **-1.036 %** at `mos_sf`, 1.08 V, -40 C — one of the two corners the spec row calls out — so
  1.964 % of margin remains. `clk` and `clkb` distort identically. No duty-cycle corrector is
  needed at 1 Gb/s and none is designed here; dll-interface Gap G3 (D-9) is not triggered.
- **T-04 is reported, not graded**: `spec/target-spec.md` T-04 states no numeric crossing bound,
  so none was invented. The pair crosses within 20 mV of VDDIO/2 at the RX **pins** at every
  corner (-19.2 mV .. +9.1 mV); at the RX **outputs** the crossing is up to -646 mV off mid-rail,
  which is the `aib_rx_data` receiver's rise/fall asymmetry, not a channel effect. TX-to-RX
  latency 338.4-629.1 ps.
- **T-02 (SIM half) is reported**: same-direction data/clock edges track to under 0.01 ps, but the
  **alternate DDR half-period at the RX output is off-centre by up to 0.103 UI** (397.4 ps instead
  of 500 ps at `mos_sf`, 1.08 V, -40 C). Only -20.7 ps of that is at the TX pad (T-17); the rest is
  added after the pad, dominantly by the receiver. This does **not** contradict T-16, which
  channel-eye grades at the RX *pins* (before the receiver) and which passes 45/45 on current
  `main` — the two measure different nodes. Whether the T-20 margin still closes is a T-19/T-20
  budget question, filed as #177; this record relaxes no bound.
- **T-21 and T-29 are declared gaps**, not claimed: T-21 needs a DLL-side model this repo does not
  build (scope discipline), and no loopback mux exists in the five `design/` cells for T-29 (which
  is a TC row besides). Follow-ups: #175 (T-21), #176 (T-29).

See the record's `README.md` for the per-corner numbers and the decomposition.

The 2026-10-27 attempt of this same request produced no record: the submit succeeded (15 jobs of 3
units) but the fleet left every job `pending` and never launched it. That run did not pass
`--wait-for-capacity`; the fleet is vCPU-budgeted and refuses a burst with `batch_no_capacity`.
`run_clock_path.sh` now passes `--wait-for-capacity 600` (and `request.json` sets
`batch.capacity_wait_s`), which is what let this run through a busy fleet. **The record committed
here needed no `--resume`**: it is a single fresh run, `environment.resume.resumed_corners` = 0,
all 15 `environment.remote.fleet[]` shards `resumed: false`, and no resume line in its
`klt.stderr`. An earlier attempt on 2026-11-13 did need one `--resume` for shards refused past
that window, but the then-buggy unlaunched-jobs guard matched `--resume`'s own per-shard recovery
line and deleted that record; `run_clock_path.sh` now matches klt's summary sentence
(`were submitted but never launched`) only. No artefacts of that attempt survive, so nothing
here rests on it.

A record file is immutable from its **first push**, not from merge. `ci.yml` runs the
append-only check on both the `pull_request` and the `push` event, and its base differs:
`pull_request.base.sha` (the PR base) versus `github.event.before` (the previously pushed head,
see `signoff/README.md` -> "What CI checks"). So a record directory that is still new relative to
`main` — and therefore an addition the PR-event run accepts — is nevertheless already frozen for
the push-event run as soon as it has been pushed once. Review feedback on a record's own
`README.md` cannot be applied in place afterwards: the edit surfaces as `M` against the pre-push
head and fails, and so does reverting it on the next push. Get a record directory's prose right
in the commit that first pushes it; a correction found later belongs in this file, which is not
under a `records/` directory and may change.

## dc-static

`sim/dc-static/` holds the T-06/T-07/T-08/T-11/T-24/T-28 testbenches and the one 45-corner
`klt sim` request (batch backend). Record `records/20261108T002904Z/` (batch job
`klt-sim-abe0ec2c5d05`, first-cut cells): T-06 (loaded), T-08 and T-24 fail. Record
`records/20261108T004350Z/` (batch job `klt-sim-805dd59f1580`, after the #130 sizing study):
all six rows pass at 45/45. T-24 is an extracted-capacitance estimate; T-25 is not
evaluated. See `sim/dc-static/README.md` and DR-0017.

Re-check after the #142 predriver change: `dc-static/records/20261112T001207Z/` (batch job
`klt-sim-f611a9ac49eb`, same `request.json`): 45/45 corners pass, 810/810 measurements pass,
so T-06/T-08/T-24 (and T-07, T-11, T-28) are unchanged in verdict. Report only, no
`record.json`.
