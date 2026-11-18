#!/usr/bin/env bash
# run_smoke.sh -- PDK/OSDI smoke: DC operating point and Id-Vgs convergence for
# sg13_lv_nmos, sg13_lv_pmos, sg13_hv_nmos, sg13_hv_pmos at mos_tt, 27 C.
# One corner, one local `ngspice -b`. SMOKE ONLY: no design value is set here.
#
#   sim/harness/common/fetch-pdk.sh
#   source sim/harness/env.sh
#   SG13G2_TOOLS_CACHE=$PWD/sim/build/cache sim/harness/common/build-osdi.sh
#   sim/pdk-smoke/run_smoke.sh
#
# Writes sim/pdk-smoke/records/<UTC-stamp>/{netlist.cir,ngspice.log,record.json}.
# Records are append-only: every run is a new directory; none is ever edited.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HERE}/.." && pwd)"
# shellcheck source=/dev/null
source "${SIM_DIR}/harness/env.sh" >/dev/null
[[ -n "${PDK_ROOT:-}" ]] || { echo "run_smoke.sh: no PDK install (run fetch-pdk.sh)" >&2; exit 3; }
OSDI_DIR="${PDK_ROOT}/${PDK}/libs.tech/ngspice/osdi"
for m in psp103 psp103_nqs r3_cmc mosvar; do
  [[ -f "${OSDI_DIR}/${m}.osdi" ]] || { echo "run_smoke.sh: ${m}.osdi missing; run build-osdi.sh" >&2; exit 3; }
done

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
rec="${HERE}/records/${stamp}"
[[ ! -e "${rec}" ]] || { echo "run_smoke.sh: ${rec} exists; records are append-only" >&2; exit 3; }
work="${SIM_DIR}/.work/pdk-smoke-${stamp}"
mkdir -p "${rec}" "${work}"

sed -e "s#@PDK_ROOT@#${PDK_ROOT}#g" -e "s#@OSDI_DIR@#${OSDI_DIR}#g" \
  "${HERE}/tb_pdk_smoke.cir.in" > "${work}/tb.cir"
# Committed snapshot: same deck with the machine-specific root shown as $PDK_ROOT.
sed -e "s#@PDK_ROOT@#\$PDK_ROOT#g" -e "s#@OSDI_DIR@#\$PDK_ROOT/${PDK}/libs.tech/ngspice/osdi#g" \
  "${HERE}/tb_pdk_smoke.cir.in" > "${rec}/netlist.cir"

rc=0
ngspice_version="$(ngspice --version 2>&1 | grep -o 'ngspice-[0-9.]*' | head -1)"
( cd "${work}" && ngspice -b tb.cir > ngspice.log 2>&1 ) || rc=$?
cp "${work}/ngspice.log" "${rec}/ngspice.log"

python3 -I - "${SIM_DIR}/pdk.json" "${work}" "${rec}/record.json" "${stamp}" "${rc}" "${ngspice_version:-unknown}" <<'PY'
import json, math, re, sys, os
pin_path, work, out, stamp, rc, ngspice_version = sys.argv[1:7]
pin = json.load(open(pin_path))
log = open(os.path.join(work, "ngspice.log")).read()
ops = {k: float(v) for k, v in re.findall(r"^i\((v\w+)\) = (\S+)", log, re.M)}
dev = {  # device -> (data file, op source)
    "sg13_lv_nmos": ("idvgs_lv_nmos.dat", "vdnl"),
    "sg13_lv_pmos": ("idvgs_lv_pmos.dat", "vdpl"),
    "sg13_hv_nmos": ("idvgs_hv_nmos.dat", "vdnh"),
    "sg13_hv_pmos": ("idvgs_hv_pmos.dat", "vdph"),
}
devices, ok = {}, int(rc) == 0 and "SMOKE_DONE" in log
for name, (f, src) in dev.items():
    rows = []
    p = os.path.join(work, f)
    if os.path.exists(p):
        rows = [tuple(map(float, l.split())) for l in open(p) if l.strip()]
    finite = bool(rows) and all(math.isfinite(x) for r in rows for x in r)
    i_op = ops.get(src)
    good = finite and i_op is not None and math.isfinite(i_op)
    ok = ok and good
    devices[name] = {
        "op_converged": i_op is not None,
        "op_drain_current_a": i_op,
        "idvgs_points": len(rows),
        "idvgs_all_finite": finite,
        "idvgs_first": rows[0] if rows else None,
        "idvgs_last": rows[-1] if rows else None,
        "converged": good,
    }
rec = {
    "record": "pdk-smoke", "utc_stamp": stamp, "smoke_only": True,
    "note": "W/L, supplies and Vgs ranges are arbitrary; no design value.",
    "pdk": {"source": pin["source"], "release_tag": pin["release_tag"],
            "tarball_sha256": pin["tarball_sha256"]},
    "corner": "mos_tt", "temp_c": 27,
    "tools": {
        "ngspice": ngspice_version,
        "openvaf_reloaded_tag": pin["osdi_toolchain"]["compiler_tag"],
        "openvaf_r_asset_sha256_linux_x86_64": pin["osdi_toolchain"]["compiler_asset_sha256"]["openvaf-r-v24.0.1mob-linux-x86_64.tar.gz"],
    },
    "ngspice_exit_code": int(rc),
    "devices": devices,
    "all_converged": ok,
}
json.dump(rec, open(out, "w"), indent=2)
open(out, "a").write("\n")
print(json.dumps({k: rec[k] for k in ("utc_stamp", "all_converged")}))
sys.exit(0 if ok else 1)
PY
