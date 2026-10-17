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
