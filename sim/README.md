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
   `bisect_esd.py` regenerates the netlists).** Driver check on `main` @ `85832ba`: with
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
3. *Cost.* About 8 s of ngspice per ns of stimulus (`mos_tt`): ~1100 s for one 141 ns corner,
   so 45 corners are ~14 serial hours; `run_channel_eye.sh` splits them into jobs of at
   most 3 units (fleet job ceiling 3600 s).
4. *Tooling.* The fleet runner is klt 0.7.0 and refuses the pinned 0.8.0 client, so the
   requests set `batch.runner_version_check: "warn"`; a 0.7.0 client lacks `--dry-run`,
   `--report-out` and rejects `osdi_preload` on the batch backend. Fleet launches were
   refused at times by the instance cap (`batch_concurrency_cap`).

T-15 note: lanes A and B carry complementary data, so the measured skew is the
rise/fall (opposite-polarity) arrival difference of one instance, not a layout skew.
T-16 note: the clock is launched center aligned, so the graded quantity is the deviation
of the data-to-clock arrival delay from the nominal 0.5 UI.

## dc-static

`sim/dc-static/` holds the T-06/T-07/T-08/T-11/T-24/T-28 testbenches and the one 45-corner
`klt sim` request (batch backend). Testbenches and request only so far: the fleet runner
predates `analysis_steps`, so no record exists. See `sim/dc-static/README.md`.
