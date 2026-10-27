#!/usr/bin/env bash
# run_clock_path.sh -- PVT-FULL clock-path family (T-17 / T-04 / T-02 SIM half), CH-3MM-RC.
#
#   sim/clock-path/run_clock_path.sh
#
# One `klt sim` request over the 45-corner grid on the batch fleet; there is no local loop and no
# fallback: a failed submit is reported and the script exits non-zero. Writes a new, never-overwritten
# record under sim/clock-path/records/<UTC>/. Needs PDK_ROOT (see sim/README.md) and uvx.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HERE}/.." && pwd)"
REPO="$(cd "${SIM_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SIM_DIR}/harness/env.sh" >/dev/null
: "${PDK_ROOT:?run_clock_path.sh: no PDK install resolved; see sim/README.md}"
KLT=(uvx --from "klayout-tools==$(cat "${REPO}/signoff/KLT_VERSION")" klt)

python3 -I "${HERE}/gen_clock_path.py" --check || { echo "run_clock_path.sh: generated files are stale" >&2; exit 4; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REC="${HERE}/records/${STAMP}"
[[ -e "${REC}" ]] && { echo "run_clock_path.sh: ${REC} exists (records are append-only)" >&2; exit 4; }
mkdir -p "${REC}"
WORK="${CLOCK_PATH_WORK:-$(mktemp -d)}"   # kept on a batch error so `klt sim --resume` can reuse it

cd "${HERE}"
rc=0
"${KLT[@]}" sim request.json --backend batch --max-units-per-job 3 -o "${WORK}/out" ${CLOCK_PATH_RESUME:+--resume} \
  --report-out "${REC}/report.json.gz" --format json > "${WORK}/stdout" 2> "${WORK}/stderr" || rc=$?
# progress lines name the fleet bucket (an account id): keep them out of the record
sed -E 's#s3://[^ /]+#s3://<bucket>#g' "${WORK}/stderr" > "${REC}/klt.stderr"
# exit 0 = every limit met, 3 = some limit failed (a result), 4 = unmeasurable corners (a result);
# anything else is a tool/fleet error: report it, do not fall back to a local run.
if [[ "${rc}" -ne 0 && "${rc}" -ne 3 && "${rc}" -ne 4 ]] || [[ ! -s "${REC}/report.json.gz" ]]; then
  echo "run_clock_path.sh: klt sim failed (exit ${rc}); batch error, no local fallback:" >&2
  tail -5 "${REC}/klt.stderr" >&2
  echo "run_clock_path.sh: retry the same batch jobs with CLOCK_PATH_WORK=${WORK} CLOCK_PATH_RESUME=1" >&2
  rm -rf "${REC}"
  exit 6
fi
# a request whose jobs were submitted but never launched reports every corner as an error: not a result
if grep -q 'never launched' "${REC}/klt.stderr"; then
  echo "run_clock_path.sh: batch jobs were submitted but never launched; no record written." >&2
  echo "run_clock_path.sh: retry with CLOCK_PATH_WORK=${WORK} CLOCK_PATH_RESUME=1" >&2
  rm -rf "${REC}"
  exit 6
fi
rm -rf "${WORK}"

cp "${HERE}/request.json" "${HERE}/tb_clock_path.cir" "${HERE}/clock_stim.inc" "${REC}/"
python3 -I "${SIM_DIR}/channel-eye/channel_eye_post.py" "${REC}/report.json.gz" --request request.json \
  --label clock-path > "${REC}/rows.json"

PDKTAG="$(grep -o '"release_tag": *"[^"]*"' "${SIM_DIR}/pdk.json" | head -1 | cut -d'"' -f4)"
python3 -I - "${REC}" "${STAMP}" "${PDKTAG}" "${rc}" <<'PY'
import gzip, json, sys
rec, stamp, pdktag, rc = sys.argv[1:5]
rep = json.load(gzip.open(f"{rec}/report.json.gz", "rt"))
rows = json.load(open(f"{rec}/rows.json"))["rows"]
row_of = {m["name"]: m["spec_row"] for m in json.load(open(f"{rec}/request.json"))["measurements"]}
ranges = {}  # report-only measurements: min and max over the grid, with the corner of each
for c in rep["corners"]:
    for m in c["measurements"]:
        v = m.get("value")
        if m.get("status") == "pass" and m.get("margin") is None and isinstance(v, (int, float)):
            r = ranges.setdefault(m["name"], {"spec_row": row_of.get(m["name"]), "min": (v, c["corner_id"]), "max": (v, c["corner_id"])})
            r["min"] = min(r["min"], (v, c["corner_id"]))
            r["max"] = max(r["max"], (v, c["corner_id"]))
remote = rep.get("environment", {}).get("remote", {})
out = {
    "record": "clock-path", "utc_stamp": stamp, "kind": "simulated",
    "claim_scope": "CH (modeled channel CH-3MM-RC, nominal); stimulus is an ideal 50 % complementary 500 MHz clock",
    "pdk": {"release_tag": pdktag},
    "klt_exit_code": int(rc), "corners": len(rep["corners"]),
    "rows": {r: {k: v[k] for k in ("verdict", "pass", "fail", "error", "binding")} for r, v in rows.items()},
    "report_only_ranges": {n: {"spec_row": r["spec_row"], "min": list(r["min"]), "max": list(r["max"])} for n, r in sorted(ranges.items())},
    "t04_bound": "none: spec/target-spec.md T-04 states no numeric crossing bound; crossing level and latency are reported",
    "t02_bound": "none: SIM half reports data-to-clock edge times; the capture aperture (T-19) and margin (T-20) are not graded here",
    "batch_job_id": remote.get("job_id"), "runner_klt_version": remote.get("runner_klt_version"),
}
json.dump(out, open(f"{rec}/record.json", "w"), indent=2)
open(f"{rec}/record.json", "a").write("\n")
print(json.dumps({"record": f"records/{stamp}", "rows": {r: v["verdict"] for r, v in out["rows"].items()}}, indent=2))
PY
