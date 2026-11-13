#!/usr/bin/env bash
# batch_record.sh -- submit ONE `klt sim` request to the batch fleet and write ONE
# append-only record under <family dir>/records/.
#
# This is the shared procedure behind the sim/<family>/run_<family>.sh entry points
# (channel-eye, clock-path, dc-static); those stay the entry points and pass only what
# really differs between the families. It is never called directly by an operator.
#
# There is no local loop and no fallback: a failed submit is reported and the script
# exits non-zero. `--wait-for-capacity 600` is mandatory on this fleet (it is
# vCPU-budgeted): without it a burst is refused for capacity and the jobs are left
# `pending`, which is what stalled the 2026-10-27 run of the clock-path request.
#
# Needs PDK_ROOT (see sim/README.md) and uvx.
#
# Usage (all paths bar --env-prefix are relative to --dir):
#   batch_record.sh --dir DIR --record NAME --request FILE --generator FILE
#                   --post-label LABEL --max-units-per-job N --env-prefix PREFIX
#                   [--self NAME] [--record-suffix SUFFIX] [--copy FILE]...
#                   [--fields-head JSON] [--fields-tail JSON] [--row-map JSON]
#                   [--report-only-ranges]
#
#   --dir                family directory (sim/channel-eye, sim/clock-path, sim/dc-static)
#   --record             the record.json "record" field
#   --request            the klt sim request, copied into the record as request.json
#   --generator          python generator run with --check before anything is submitted
#   --post-label         --label handed to sim/channel-eye/channel_eye_post.py
#   --max-units-per-job  corners per batch job (see sim/README.md for why it is 1 or 3)
#   --env-prefix         PREFIX_WORK / PREFIX_RESUME: reuse a work dir and pass --resume
#   --self               name used in messages (defaults to the caller's basename)
#   --record-suffix      appended to the UTC stamp in the record dir name
#   --copy               extra bench file copied into the record (repeatable); the
#                        request's own "netlist" is always copied
#   --fields-head        JSON object of family record.json fields, placed after "kind"
#   --fields-tail        JSON object of family record.json fields, placed after "rows"
#   --row-map            JSON object of measurement-name PREFIX -> spec row (or [rows]),
#                        for a family whose graded measurements carry no `spec_row` and
#                        so cannot be grouped from the request (dc-static: a report names
#                        a step measurement `<step>.<name>`, the request declares it
#                        `<name>`, and the committed request declares no row). It only
#                        reaches `rows`; `--report-only-ranges` still takes its `spec_row`
#                        from the request, which is correct as long as a prefix map names
#                        only graded measurements
#   --report-only-ranges record the min/max over the grid of every ungraded measurement
#   --dry-run            print the resolved configuration as JSON and exit, touching nothing
#                        (needs no PDK and no fleet; this is what the self-tests check the
#                        entry points with)
#
# Exit codes: 2 bad usage, 4 stale generated files or a record dir that already exists,
# 6 a batch/fleet error (no record is written), otherwise 0. klt sim's own 0 (every limit
# met), 3 (some limit failed) and 4 (unmeasurable corners) are all results: the record is
# written either way and carries the code as record.json's `klt_exit_code`.
set -euo pipefail

SELF="$(basename "${0}")"
DIR="" ; RECORD="" ; REQUEST="" ; GENERATOR="" ; POST_LABEL="" ; MAX_UNITS="" ; ENV_PREFIX=""
SUFFIX="" ; FIELDS_HEAD="{}" ; FIELDS_TAIL="{}" ; ROW_MAP="{}" ; RANGES=0 ; DRY=0
COPY=()
while [[ $# -gt 0 ]]; do
  case "${1}" in
    --dir) DIR="${2}"; shift 2 ;;
    --record) RECORD="${2}"; shift 2 ;;
    --request) REQUEST="${2}"; shift 2 ;;
    --generator) GENERATOR="${2}"; shift 2 ;;
    --post-label) POST_LABEL="${2}"; shift 2 ;;
    --max-units-per-job) MAX_UNITS="${2}"; shift 2 ;;
    --env-prefix) ENV_PREFIX="${2}"; shift 2 ;;
    --self) SELF="${2}"; shift 2 ;;
    --record-suffix) SUFFIX="${2}"; shift 2 ;;
    --copy) COPY+=("${2}"); shift 2 ;;
    --fields-head) FIELDS_HEAD="${2}"; shift 2 ;;
    --fields-tail) FIELDS_TAIL="${2}"; shift 2 ;;
    --row-map) ROW_MAP="${2}"; shift 2 ;;
    --report-only-ranges) RANGES=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,52p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "${SELF}: unknown argument '${1}'" >&2; exit 2 ;;
  esac
done
for need in "DIR:--dir" "RECORD:--record" "REQUEST:--request" "GENERATOR:--generator" \
            "POST_LABEL:--post-label" "MAX_UNITS:--max-units-per-job" "ENV_PREFIX:--env-prefix"; do
  var="${need%%:*}"
  [[ -n "${!var}" ]] || { echo "${SELF}: ${need##*:} is required" >&2; exit 2; }
done

if [[ ${DRY} -eq 1 ]]; then
  # also the only validation of --fields-head / --fields-tail / --row-map: json.loads
  # rejects a typo.
  python3 -I -c 'import json,sys
k = ("self", "dir", "record", "request", "generator", "post_label", "record_suffix",
     "max_units_per_job", "env_prefix")
cfg = dict(zip(k, sys.argv[1:1 + len(k)]))
cfg["report_only_ranges"] = sys.argv[1 + len(k)] == "1"
cfg["fields_head"] = json.loads(sys.argv[2 + len(k)])
cfg["fields_tail"] = json.loads(sys.argv[3 + len(k)])
cfg["row_map"] = json.loads(sys.argv[4 + len(k)])
cfg["copy"] = sys.argv[5 + len(k):]
print(json.dumps(cfg, indent=2))' \
    "${SELF}" "${DIR}" "${RECORD}" "${REQUEST}" "${GENERATOR}" "${POST_LABEL}" "${SUFFIX}" \
    "${MAX_UNITS}" "${ENV_PREFIX}" "${RANGES}" "${FIELDS_HEAD}" "${FIELDS_TAIL}" "${ROW_MAP}" \
    ${COPY[@]+"${COPY[@]}"}
  exit 0
fi

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HARNESS}/.." && pwd)"
REPO="$(cd "${SIM_DIR}/.." && pwd)"
DIR="$(cd "${DIR}" && pwd)"
# shellcheck source=/dev/null
source "${HARNESS}/env.sh" >/dev/null
: "${PDK_ROOT:?${SELF}: no PDK install resolved; see sim/README.md}"
KLT=(uvx --from "klayout-tools==$(cat "${REPO}/signoff/KLT_VERSION")" klt)

python3 -I "${DIR}/${GENERATOR}" --check || { echo "${SELF}: generated files are stale" >&2; exit 4; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REC="${DIR}/records/${STAMP}${SUFFIX}"
[[ -e "${REC}" ]] && { echo "${SELF}: ${REC} exists (records are append-only)" >&2; exit 4; }
mkdir -p "${REC}"
WORK_VAR="${ENV_PREFIX}_WORK" ; RESUME_VAR="${ENV_PREFIX}_RESUME"
WORK="${!WORK_VAR:-$(mktemp -d)}"   # kept on a batch error so `klt sim --resume` can reuse it
RESUME="${!RESUME_VAR:-}"
RETRY="${SELF}: retry the same batch jobs with ${WORK_VAR}=${WORK} ${RESUME_VAR}=1"

cd "${DIR}"
rc=0
# shellcheck disable=SC2086  # ${RESUME:+--resume} is a deliberate single-word expansion
"${KLT[@]}" sim "${REQUEST}" --backend batch --max-units-per-job "${MAX_UNITS}" --wait-for-capacity 600 \
  -o "${WORK}/out" ${RESUME:+--resume} \
  --report-out "${REC}/report.json.gz" --format json > "${WORK}/stdout" 2> "${WORK}/stderr" || rc=$?
# progress lines name the fleet bucket (an account id): keep them out of the record
sed -E 's#s3://[^ /]+#s3://<bucket>#g' "${WORK}/stderr" > "${REC}/klt.stderr"
# exit 0 = every limit met, 3 = some limit failed (a result), 4 = unmeasurable corners (a result);
# anything else is a tool/fleet error: report it, do not fall back to a local run.
if [[ "${rc}" -ne 0 && "${rc}" -ne 3 && "${rc}" -ne 4 ]] || [[ ! -s "${REC}/report.json.gz" ]]; then
  echo "${SELF}: klt sim ${POST_LABEL} failed (exit ${rc}); batch error, no local fallback:" >&2
  tail -5 "${REC}/klt.stderr" >&2
  echo "${RETRY}" >&2
  rm -rf "${REC}"
  exit 6
fi
# a request whose jobs were submitted but never launched reports every corner as an error: not a result.
# Match klt's summary sentence only ("N of M batch job(s) were submitted but never launched"): a
# --resume prints "had been submitted but never launched; launched it" per shard it RECOVERS, and a
# bare 'never launched' grep throws away the record of a successful resume.
if grep -q 'were submitted but never launched' "${REC}/klt.stderr"; then
  echo "${SELF}: batch jobs were submitted but never launched; no record written." >&2
  echo "${RETRY}" >&2
  rm -rf "${REC}"
  exit 6
fi
rm -rf "${WORK}"

cp "${DIR}/${REQUEST}" "${REC}/request.json"
for f in ${COPY[@]+"${COPY[@]}"}; do cp "${DIR}/${f}" "${REC}/"; done
cp "${DIR}/$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["netlist"])' "${DIR}/${REQUEST}")" "${REC}/"
POST=(python3 -I "${SIM_DIR}/channel-eye/channel_eye_post.py" "${REC}/report.json.gz"
      --request "${REQUEST}" --label "${POST_LABEL}")
[[ "${ROW_MAP}" == "{}" ]] || POST+=(--row-map "${ROW_MAP}")
"${POST[@]}" > "${REC}/rows.json"

PDKTAG="$(grep -o '"release_tag": *"[^"]*"' "${SIM_DIR}/pdk.json" | head -1 | cut -d'"' -f4)"
WRITE=(python3 -I "${HARNESS}/write_record.py" "${REC}" --record "${RECORD}" --stamp "${STAMP}"
       --pdk-tag "${PDKTAG}" --klt-exit-code "${rc}"
       --fields-head "${FIELDS_HEAD}" --fields-tail "${FIELDS_TAIL}")
[[ ${RANGES} -eq 1 ]] && WRITE+=(--report-only-ranges)
"${WRITE[@]}"
