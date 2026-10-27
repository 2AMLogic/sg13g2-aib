#!/usr/bin/env bash
# run_channel_eye.sh -- PVT-FULL channel-eye family (T-01 / T-09 / T-15 / T-16 / T-18 / T-26).
#
#   sim/channel-eye/run_channel_eye.sh ch      # CH-3MM-RC, 45 corners (claims about the modeled channel)
#   sim/channel-eye/run_channel_eye.sh tc      # L2 wire-bond loopback, 45 corners (test configuration; never a CH claim)
#   sim/channel-eye/run_channel_eye.sh control  # bench positive control, one corner, fixed-PMOS TX copy (not design evidence)
#
# Every run is a `klt sim` request on the batch fleet; there is no local loop and no
# fallback: a failed submit is reported and the script exits non-zero. 45 corners x ~1100 s
# of ngspice each is split into jobs of at most 3 units so none outruns the fleet's
# 3600 s whole-job ceiling. Writes a new, never-overwritten record under
# sim/channel-eye/records/<UTC>-<kind>/. Needs PDK_ROOT (see sim/README.md) and uvx.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HERE}/.." && pwd)"
REPO="$(cd "${SIM_DIR}/.." && pwd)"
kind="${1:?usage: run_channel_eye.sh ch|tc|control}"
case "${kind}" in
  ch) req=request_ch_1g.json ;;
  tc) req=request_tc_1g.json ;;
  control) req=request_ctl_ch_tt.json ;;
  *) echo "run_channel_eye.sh: unknown kind '${kind}'" >&2; exit 2 ;;
esac
# shellcheck source=/dev/null
source "${SIM_DIR}/harness/env.sh" >/dev/null
: "${PDK_ROOT:?run_channel_eye.sh: no PDK install resolved; see sim/README.md}"
KLT=(uvx --from "klayout-tools==$(cat "${REPO}/signoff/KLT_VERSION")" klt)

python3 -I "${HERE}/gen_channel_eye.py" --check || { echo "run_channel_eye.sh: generated files are stale" >&2; exit 4; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REC="${HERE}/records/${STAMP}-${kind}"
[[ -e "${REC}" ]] && { echo "run_channel_eye.sh: ${REC} exists (records are append-only)" >&2; exit 4; }
mkdir -p "${REC}"
WORK="$(mktemp -d)"; trap 'rm -rf "${WORK}"' EXIT

cd "${HERE}"
rc=0
"${KLT[@]}" sim "${req}" --backend batch --max-units-per-job 3 -o "${WORK}/out" \
  --report-out "${REC}/report.json.gz" --format json > "${WORK}/stdout" 2> "${WORK}/stderr" || rc=$?
# progress lines name the fleet bucket (an account id): keep them out of the record
sed -E 's#s3://[^ /]+#s3://<bucket>#g' "${WORK}/stderr" > "${REC}/klt.stderr"
# exit 0 = every limit met, 3 = some limit failed (a result), 4 = unmeasurable corners (a result);
# anything else is a tool/fleet error: report it, do not fall back to a local run.
if [[ "${rc}" -ne 0 && "${rc}" -ne 3 && "${rc}" -ne 4 ]] || [[ ! -s "${REC}/report.json.gz" ]]; then
  echo "run_channel_eye.sh: klt sim ${kind} failed (exit ${rc}); batch error, no local fallback:" >&2
  tail -5 "${REC}/klt.stderr" >&2
  exit 6
fi

cp "${HERE}/${req}" "${REC}/request.json"
cp "${HERE}/tb_body.inc" "${HERE}/prbs7_stim.inc" "${REC}/"
cp "${HERE}/$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["netlist"])' "${HERE}/${req}")" "${REC}/"
python3 -I "${HERE}/channel_eye_post.py" "${REC}/report.json.gz" --request "${req}" --label "${kind}" > "${REC}/rows.json"

PDKTAG="$(grep -o '"release_tag": *"[^"]*"' "${SIM_DIR}/pdk.json" | head -1 | cut -d'"' -f4)"
python3 -I - "${REC}" "${STAMP}" "${PDKTAG}" "${kind}" "${rc}" <<'PY'
import gzip, json, sys
rec, stamp, pdktag, kind, rc = sys.argv[1:6]
rep = json.load(gzip.open(f"{rec}/report.json.gz", "rt"))
rows = json.load(open(f"{rec}/rows.json"))["rows"]
remote = rep.get("environment", {}).get("remote", {})
claim = {"ch": "CH (modeled channel CH-3MM-RC)", "tc": "TC (L2 wire-bond loopback, declared values)",
         "control": "none: bench positive control with a modified TX copy"}[kind]
out = {
    "record": "channel-eye", "utc_stamp": stamp, "kind": "simulated", "family": kind, "claim_scope": claim,
    "pdk": {"release_tag": pdktag},
    "klt_exit_code": int(rc), "corners": len(rep["corners"]),
    "rows": {r: {k: v[k] for k in ("verdict", "pass", "fail", "error", "binding")} for r, v in rows.items()},
    "batch_job_id": remote.get("job_id"), "runner_klt_version": remote.get("runner_klt_version"),
    "energy_label": "T-26 energy per bit is SIMULATED; no measurement exists",
}
json.dump(out, open(f"{rec}/record.json", "w"), indent=2)
open(f"{rec}/record.json", "a").write("\n")
print(json.dumps({"record": f"records/{stamp}-{kind}", "rows": {r: v["verdict"] for r, v in out["rows"].items()}}, indent=2))
PY
