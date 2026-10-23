#!/usr/bin/env bash
# run_synth.sh -- Yosys synthesis smoke: elaborate rtl/aib_datapath.v and map it to
# sg13g2_stdcell (typ 1.20 V 25 C liberty) for N = 20 and N = 8. SMOKE ONLY: it shows
# the module synthesizes to library cells with no undriven or conflicting nets. No
# timing, no area claim, no clock-tree or negedge-flop sizing judgement.
#
#   sim/harness/common/fetch-pdk.sh
#   source sim/harness/env.sh
#   sim/rtl-synth/run_synth.sh
#
# Writes sim/rtl-synth/records/<UTC-stamp>/{synth_n20.ys,yosys_n20.log,synth_n8.ys,yosys_n8.log,record.json}.
# Records are append-only: every run is a new directory; none is ever edited.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HERE}/.." && pwd)"
ROOT="$(cd "${SIM_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SIM_DIR}/harness/env.sh" >/dev/null
[[ -n "${PDK_ROOT:-}" ]] || { echo "run_synth.sh: no PDK install (run fetch-pdk.sh)" >&2; exit 3; }
LIB_REL="${PDK}/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib"
[[ -f "${PDK_ROOT}/${LIB_REL}" ]] || { echo "run_synth.sh: ${LIB_REL} missing under the PDK root" >&2; exit 3; }

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
rec="${HERE}/records/${stamp}"
[[ ! -e "${rec}" ]] || { echo "run_synth.sh: ${rec} exists; records are append-only" >&2; exit 3; }
mkdir -p "${rec}"

# Drop the ", GNU /usr/bin/c++ ..." build tail: the evidence checker rejects absolute paths.
yosys_version="$(yosys -V | sed -E 's/, GNU [^)]*\)/)/')"
for n in 20 8; do
  # Committed snapshot shows the machine-specific PDK root as $PDK_ROOT.
  cat > "${rec}/synth_n${n}.ys" <<YS
read_liberty -lib \$PDK_ROOT/${LIB_REL}
read_verilog rtl/aib_tx_slice.v rtl/aib_rx_slice.v rtl/aib_datapath.v
hierarchy -top aib_datapath -chparam N ${n}
synth -top aib_datapath -flatten
dfflibmap -liberty \$PDK_ROOT/${LIB_REL}
abc -liberty \$PDK_ROOT/${LIB_REL}
opt_clean -purge
check -assert
stat -liberty \$PDK_ROOT/${LIB_REL}
YS
  rc=0
  ( cd "${ROOT}" && yosys -l "${rec}/yosys_n${n}.raw" -s <(sed "s#\\\$PDK_ROOT#${PDK_ROOT}#g" "${rec}/synth_n${n}.ys") > /dev/null 2>&1 ) || rc=$?
  sed -e "s#${PDK_ROOT}#\$PDK_ROOT#g" -e "s#${HOME}#\$HOME#g" "${rec}/yosys_n${n}.raw" > "${rec}/yosys_n${n}.log"
  rm -f "${rec}/yosys_n${n}.raw"
  echo "${rc}" > "${rec}/.rc_n${n}"
done

python3 -I - "${SIM_DIR}/pdk.json" "${rec}" "${stamp}" "${yosys_version}" "${LIB_REL}" <<'PY'
import json, os, re, sys
pin_path, rec, stamp, yosys_version, lib_rel = sys.argv[1:6]
pin = json.load(open(pin_path))
runs, ok = {}, True
for n in (20, 8):
    log = open(os.path.join(rec, f"yosys_n{n}.log")).read()
    rc = int(open(os.path.join(rec, f".rc_n{n}")).read())
    os.remove(os.path.join(rec, f".rc_n{n}"))
    cells = {m.group(2): int(m.group(1))
             for m in re.finditer(r"^\s+(\d+)\s+[\d.E+]+\s+(sg13g2_\w+)\s*$", log, re.M)}
    area = re.search(r"Chip area for module '\\aib_datapath': ([\d.]+)", log)
    problems = re.findall(r"Found and reported (\d+) problems", log)
    flops = sum(v for k, v in cells.items() if "df" in k)
    good = rc == 0 and bool(cells) and bool(area) and all(p == "0" for p in problems)
    ok = ok and good
    runs[f"n{n}"] = {
        "yosys_exit_code": rc,
        "check_problems": sum(int(p) for p in problems),
        "mapped_cells": cells,
        "mapped_cell_total": sum(cells.values()),
        "flip_flops": flops,
        "cell_area_um2": float(area.group(1)) if area else None,
        "elaborated_and_mapped": good,
    }
out = {
    "record": "rtl-synth",
    "utc_stamp": stamp,
    "smoke_only": True,
    "note": "Elaboration and technology mapping only; no timing or area claim.",
    "pdk": {k: pin[k] for k in ("source", "release_tag", "tarball_sha256")},
    "tools": {"yosys": yosys_version},
    "liberty": lib_rel,
    "top": "aib_datapath",
    "sources": ["rtl/aib_tx_slice.v", "rtl/aib_rx_slice.v", "rtl/aib_datapath.v"],
    "runs": runs,
    "all_runs_ok": ok,
}
json.dump(out, open(os.path.join(rec, "record.json"), "w"), indent=2)
open(os.path.join(rec, "record.json"), "a").write("\n")
print(f"rtl-synth: {'ok' if ok else 'FAILED'}; record {os.path.basename(rec)}")
sys.exit(0 if ok else 1)
PY
