#!/usr/bin/env bash
# run_t16attr.sh -- T-16 attribution probes (issue #161) for the CURRENT design.
#
#   sim/channel-eye/run_t16attr.sh OUTDIR
#
# Four single-corner, single-unit `klt sim` runs on the local backend (ch/id x ss/tt), one after
# another, each capped at OMP_NUM_THREADS=2 (shared host: ngspice otherwise takes every core).
# Then t16attr_post.py prints the attribution table. For another design revision, export that
# revision's design/ and spec/channel/ plus tb_body.inc and prbs7_stim.inc into a scratch tree
# next to a copy of this directory's t16attr files and run the same requests there (the
# pre-#132 half of record *-t16attr was made from `git archive 394bb86`).
# Not a grid and not for corner sweeps: those go through `klt sim --backend batch`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HERE}/.." && pwd)"
REPO="$(cd "${SIM_DIR}/.." && pwd)"
OUT="${1:?usage: run_t16attr.sh OUTDIR}"
# shellcheck source=/dev/null
source "${SIM_DIR}/harness/env.sh" >/dev/null
: "${PDK_ROOT:?run_t16attr.sh: no PDK install resolved; see sim/README.md}"
export OMP_NUM_THREADS=2
KLT=(uvx --from "klayout-tools==$(cat "${REPO}/signoff/KLT_VERSION")" klt)

python3 -I "${HERE}/gen_t16attr.py" "${HERE}"
mkdir -p "${OUT}"
cd "${HERE}"
for v in ch_ss ch_tt id_ss id_tt; do
  "${KLT[@]}" sim "request_t16attr_${v}.json" --backend local -o "${OUT}/${v}" \
    --report-out "${OUT}/${v}.json.gz" --format json > "${OUT}/${v}.stdout" 2> "${OUT}/${v}.stderr"
done
python3 -I "${HERE}/t16attr_post.py" "cur=${OUT}"
