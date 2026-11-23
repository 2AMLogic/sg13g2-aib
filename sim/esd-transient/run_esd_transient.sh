#!/usr/bin/env bash
# run_esd_transient.sh -- the T-25 SIM leg: one 0.5 A ESD discharge transient (issue #196,
# DR-0030).
#
#   sim/esd-transient/run_esd_transient.sh
#
# One `klt sim` request (request.json, the single nominal corner tt/1.20 V/27 C) on the
# local backend: T-25's grid column is n/a, so this is a single-configuration bench -- one
# unit, no `--backend batch`, no fleet, no capacity wait (CLAUDE.md: klt sim keeps
# single-unit runs local). Writes a new, never-overwritten record under
# sim/esd-transient/records/<UTC>/. Needs PDK_ROOT (see sim/README.md) and uvx; ngspice
# and the OSDI models come from the pinned toolchain the PDK install carries.
#
# The record procedure mirrors sim/harness/batch_record.sh (resolve the PDK, check the
# generated request is fresh, refuse an existing record directory, copy the request and
# bench into the record, post-process the report with the shared channel_eye_post.py,
# write record.json with the shared write_record.py) minus the fleet handling: a failed
# klt sim here is a tool error, so there is nothing to resume and no record is written.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HERE}/.." && pwd)"
REPO="$(cd "${SIM_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SIM_DIR}/harness/env.sh" >/dev/null
[[ -n "${PDK_ROOT:-}" ]] || { echo "run_esd_transient.sh: no PDK install (run fetch-pdk.sh)" >&2; exit 3; }
KLT=(uvx --from "klayout-tools==$(cat "${REPO}/signoff/KLT_VERSION")" klt)

python3 -I "${HERE}/gen_esd_transient.py" --check \
  || { echo "run_esd_transient.sh: generated files are stale" >&2; exit 4; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REC="${HERE}/records/${STAMP}"
[[ -e "${REC}" ]] && { echo "run_esd_transient.sh: ${REC} exists (records are append-only)" >&2; exit 4; }
mkdir -p "${REC}"
cleanup_abort() {
  local rc=$?
  trap - ERR
  if [[ -d "${REC}" ]]; then
    echo "run_esd_transient.sh: aborted (exit ${rc}); no record written" >&2
    rm -rf "${REC}"
  fi
  exit "${rc}"
}
trap cleanup_abort ERR
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

cd "${HERE}"
rc=0
"${KLT[@]}" sim request.json --backend local -o "${WORK}/out" \
  --report-out "${REC}/report.json.gz" --format json > "${WORK}/stdout" 2> "${WORK}/stderr" || rc=$?
sed -E 's#s3://[^ /]+#s3://<bucket>#g' "${WORK}/stderr" > "${REC}/klt.stderr" || true
# exit 0 = every limit met, 3 = some limit failed (a result), 4 = unmeasurable corners
# (a result); anything else is a tool error: report it, no record.
if [[ "${rc}" -ne 0 && "${rc}" -ne 3 && "${rc}" -ne 4 ]] || [[ ! -s "${REC}/report.json.gz" ]]; then
  echo "run_esd_transient.sh: klt sim failed (exit ${rc}); tool error, no record:" >&2
  tail -5 "${WORK}/stderr" >&2
  rm -rf "${REC}"
  exit 6
fi

cp request.json tb_esd_transient.cir "${REC}/"
# the manifest cites the plain report.json (the clock-path record carries both); the
# gz is the run artifact
# provenance hygiene (docs/design-evidence-tiers.md): no home-directory path in the record
gzip -dc "${REC}/report.json.gz" | sed -E 's#"ngspice_binary": "/home/[^"]*"#"ngspice_binary": "/usr/local/bin/ngspice"#' > "${REC}/report.json"
gzip -n -c "${REC}/report.json" > "${REC}/report.json.gz"

# T-25 rows: the graded measurements are step-level (the report names them
# `<step>.t25_*`), so the row attaches by the --row-map leaf-prefix fallback, the same
# mechanism dc-static uses; the derived recovery ratios carry the spec_row tag and need
# no map.
python3 -I "${SIM_DIR}/channel-eye/channel_eye_post.py" "${REC}/report.json.gz" \
  --request request.json --label esd-transient \
  --row-map '{"t25_": "T-25"}' > "${REC}/rows.json"

PDKTAG="$(grep -o '"release_tag": *"[^"]*"' "${SIM_DIR}/pdk.json" | head -1 | cut -d'"' -f4)"
head_fields="$(python3 -I -c 'import json,sys; print(json.dumps({
  "claim_scope": "T-25 SIM leg only, at the single nominal corner (grid is n/a for this row). Simulated; no MEAS exists and no CDM level is claimed from a transient.",
  "pulse": "0.5 A triangular current pulse into PAD, 200 ps rise, 400 ps fall, ~400 ps at half amplitude, both polarities, VDDIO powered (1.20 V) and unpowered (0 V), fixed by DR-0030 before the run",
  "bounds": "DR-0030 s5, stated before the run and not edited after: peak |V(PAD)| <= 7.0 V positive / <= 3.0 V negative, peak |V(PADI)| <= 3.5 V either polarity, protected branch <= 0.05 A either polarity, recovery ratio (|V(PAD)| 1 ns after its crest over its own peak) <= 0.40 either polarity",
  "credited_models": "diodevdd_2kv forward conduction and the XMn1/XMclamp PSP103 drain-body junctions; the gate-grounded snapback path is neither credited nor verified (DR-0030 s3)"}))')"
tail_fields="$(python3 -I -c 'import json,sys; print(json.dumps({
  "row_source": "the graded measurements are step-level, so T-25 attaches by the --row-map leaf-prefix fallback of the runner (the mechanism dc-static uses); the derived recovery ratios carry the spec_row tag and need no map",
  "mc_note": "the mc_dio_fwd / mc_dio_fwd_novdd / mc_xmn1_neg steps are the model check: the first sweep voltage at which each credited path carries 0.5 A, same PDK cards, sizes as committed; report-only, graded by no spec row",
  "t25_note": "T-25 SIM leg only. Not shown: no MEAS, no CDM level, no LAYOUT current-path check, no ESD rules in the DRC deck (2AMLogic/klayout-tools#3854), ideal stiff rails, single nominal corner (DR-0030, What is not shown)"}))')"

python3 -I "${SIM_DIR}/harness/write_record.py" "${REC}" \
  --record esd-transient --stamp "${STAMP}" \
  --pdk-tag "${PDKTAG}" --klt-exit-code "${rc}" \
  --fields-head "${head_fields}" --fields-tail "${tail_fields}"
echo "run_esd_transient.sh: record ${REC} (klt exit ${rc})"
