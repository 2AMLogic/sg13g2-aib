#!/usr/bin/env bash
# run_rx_threshold.sh -- receiver-threshold sizing study (issue #386; T-10 input stage).
#
#   sim/rx-threshold-study/run_rx_threshold.sh screen     # DC screen, all candidates, 45 corners
#   sim/rx-threshold-study/run_rx_threshold.sh hyst       # T-11: as-drawn vs selected, one ramp
#   sim/rx-threshold-study/run_rx_threshold.sh pin        # T-24: two pins, AC at three biases
#   sim/rx-threshold-study/run_rx_threshold.sh clk        # clock path twice, t02 opposite-edge pairs
#   sim/rx-threshold-study/run_rx_threshold.sh t16-base   # T-16 nominal channel, as-drawn receiver
#   sim/rx-threshold-study/run_rx_threshold.sh t16-cand   # T-16 nominal channel, selected candidate
#   sim/rx-threshold-study/run_rx_threshold.sh t16-mixed  # T-16 nominal channel, candidate in data lanes, as-drawn clock lanes
#   sim/rx-threshold-study/run_rx_threshold.sh mc         # T-10 Monte Carlo pair for SELECTED
#
# The screen/hyst/pin/clk/t16 legs go through the shared sim/harness/batch_record.sh
# procedure (one `klt sim` request each, `--backend batch --wait-for-capacity 600`,
# append-only record under records/<UTC>-<leg>/); there is no local loop and no
# fallback. The mc leg is the pinned sim/mc/README.md flow -- two batch requests
# (nominal 120 draws/corner seed 4410, negative control 20 draws/corner seed 4411)
# joined by `klt yield-samples` and graded by `klt yield` -- assembled into one
# record directory in the layout of sim/mc/records/20261108T035315Z-t10/. The
# record.json and per-corner table of an mc record are written by hand from the
# yield verdict after the run (see the study README), so the runner moves the
# assembled directory into records/ only once every artifact is on disk.
#
# Candidates are study cells inlined in the benches (cand_cells.inc lists them all);
# design/ and layout/ are untouched by this study. Needs PDK_ROOT (sim/README.md)
# and uvx.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="$(cd "${HERE}/../harness" && pwd)"
KLT_VER="$(cat "${HERE}/../../signoff/KLT_VERSION")"

case "${1:-}" in
screen|hyst|pin|clk)
  case "${1}" in
    screen) req=request_screen.json ; suffix="-screen" ; copies=(cand_cells.inc)
            extra=(--report-only-ranges --allow-empty-rows) ; units=45 ;;
    hyst)   req=request_hyst.json ; suffix="-hyst" ; copies=() ; extra=() ; units=45 ;;
    pin)    req=request_pin.json ; suffix="-pin" ; copies=() ; extra=()
            # the graded t24 capacitances are step-level measurements (like
            # dc-static's), so the post-processor needs the prefix row map
            extra+=(--row-map '{"t24_cpin": "T-24"}') ; units=45 ;;
    clk)    req=request_clk.json ; suffix="-clk" ; copies=()
            # 4-lane tran with options.timeout_s 1100: 3 units per job, as the
            # clock-path family packs its same-shaped bench.
            extra=(--report-only-ranges --allow-empty-rows) ; units=3 ;;
  esac
  head_fields='{"claim_scope": "BOTH, for the study cell only: the receiver input stage at ideal DC/AC/tran stimulus; the channel legs (clk, t16-*) additionally carry the declared CH-3MM-RC model.", "study": "issue #386 receiver-threshold sizing study; candidates are study cells, design/ is untouched"}'
  cpargs=()
  for f in ${copies[@]+"${copies[@]}"}; do cpargs+=(--copy "$f"); done
  exec "${HARNESS}/batch_record.sh" \
    --self run_rx_threshold.sh \
    --dir "${HERE}" \
    --record rx-threshold-study \
    --request "${req}" \
    --generator gen_rx_threshold.py \
    --post-label rx-threshold \
    --record-suffix "${suffix}" \
    --max-units-per-job "${units}" \
    --env-prefix RX_THR \
    --fields-head "${head_fields}" \
    ${cpargs[@]+"${cpargs[@]}"} \
    ${extra[@]+"${extra[@]}"} \
    "${@:2}"
  ;;
t16-base|t16-cand|t16-mixed)
  case "${1}" in
    t16-base) req=request_t16_base.json ; variant="as-drawn receiver (self-check against the committed channel-eye ch record)" ;;
    t16-cand) req=request_t16_cand.json ; variant="selected study candidate inlined as aib_rx_data in all four lanes" ;;
    t16-mixed) req=request_t16_mixed.json ; variant="adoptable split: selected study candidate in the data lanes A/B, as-drawn receiver in the clock lanes C/CB" ;;
  esac
  head_fields="$(python3 -I -c 'import json,sys; print(json.dumps({"claim_scope": "CH (declared channel CH-3MM-RC, nominal kr = kc = 1)", "study": "issue #386 receiver-threshold sizing study", "variant": sys.argv[1]}))' "${variant}")"
  # the request is gen_channel_eye.request("ch") with the netlist swapped, so it
  # inherits timeout_s 2400 and the fleet's 1-unit-per-job ceiling of that family.
  exec "${HARNESS}/batch_record.sh" \
    --self run_rx_threshold.sh \
    --dir "${HERE}" \
    --record rx-threshold-study \
    --request "${req}" \
    --generator gen_rx_threshold.py \
    --post-label rx-threshold \
    --record-suffix "-${1}" \
    --max-units-per-job 1 \
    --env-prefix "RX_THR_${1//-/}" \
    --copy prbs7_stim.inc \
    --fields-head "${head_fields}" \
    "${@:2}"
  ;;
mc)
  shift
  KLT=(uvx --from "klayout-tools==${KLT_VER}" klt)
  KLT_Y=(uvx --from "klayout-tools[yield]==${KLT_VER}" klt)
  python3 -I "${HERE}/gen_rx_threshold.py" --check || { echo "run_rx_threshold.sh: generated files are stale" >&2; exit 4; }
  # shellcheck source=/dev/null
  source "${HARNESS}/env.sh" >/dev/null
  : "${PDK_ROOT:?run_rx_threshold.sh: no PDK install resolved; see sim/README.md}"
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  WORK="${RX_THR_MC_WORK:-$(mktemp -d)}"
  ASSEMBLE="${WORK}/mc-rec"
  REC="${HERE}/records/${STAMP}-mc"
  [[ -e "${REC}" ]] && { echo "run_rx_threshold.sh: ${REC} exists (records are append-only)" >&2; exit 4; }
  mkdir -p "${ASSEMBLE}"
  cd "${HERE}"
  submit() {  # submit <request> <report-out-name>
    local rc=0
    "${KLT[@]}" sim "${1}" --backend batch --max-units-per-job 348 --wait-for-capacity 600 \
      -o "${WORK}/out-${2}" ${RX_THR_MC_RESUME:+--resume} \
      --report-out "${ASSEMBLE}/${2}" --format json > "${WORK}/${2}.stdout" 2> "${WORK}/${2}.stderr" || rc=$?
    sed -E 's#s3://[^ /]+#s3://<bucket>#g' "${WORK}/${2}.stderr" > "${ASSEMBLE}/${2}.stderr"
    if [[ "${rc}" -ne 0 && "${rc}" -ne 3 && "${rc}" -ne 4 ]] || [[ ! -s "${ASSEMBLE}/${2}" ]]; then
      echo "run_rx_threshold.sh: klt sim ${1} failed (exit ${rc}); batch error, no local fallback:" >&2
      tail -5 "${ASSEMBLE}/${2}.stderr" >&2
      echo "retry the same batch jobs with RX_THR_MC_WORK=${WORK} RX_THR_MC_RESUME=1 $0 mc" >&2
      exit 6
    fi
    if grep -q 'were submitted but never launched' "${ASSEMBLE}/${2}.stderr"; then
      echo "run_rx_threshold.sh: batch jobs were submitted but never launched; no record written." >&2
      echo "retry with RX_THR_MC_WORK=${WORK} RX_THR_MC_RESUME=1 $0 mc" >&2
      exit 6
    fi
    echo "run_rx_threshold.sh: ${1} -> ${2} (klt exit ${rc})"
  }
  submit request_mc.json report.json.gz
  submit request_mc_ctl.json report_ctl.json.gz
  gunzip -c "${ASSEMBLE}/report.json.gz" > "${WORK}/report.json"
  gunzip -c "${ASSEMBLE}/report_ctl.json.gz" > "${WORK}/report_ctl.json"
  ( cd "${WORK}" && "${KLT_Y[@]}" yield-samples report.json --negative-control report_ctl.json \
      --description "input-side NMOS 4x narrower (the tb_mc_ctl.cir seeded degradation)" \
      --measurement t10_offset_mv --format json > "${ASSEMBLE}/samples.json" )
  "${KLT_Y[@]}" yield "${ASSEMBLE}/samples.json" --format json > "${ASSEMBLE}/yield.json"
  cp request_mc.json request_mc_ctl.json tb_mc.cir tb_mc_ctl.cir "${ASSEMBLE}/"
  # host paths out of every JSON artifact before the record exists (#437)
  python3 -I "${HARNESS}/write_record.py" "${ASSEMBLE}" --scrub-only
  # every artifact is on disk: the record directory appears atomically, so no
  # half-written directory can sit under records/ (#276)
  mv "${ASSEMBLE}" "${REC}"
  echo "run_rx_threshold.sh: mc record at ${REC} (add record.json + per_corner.md per the study README)"
  ;;
*)
  echo "usage: $0 screen|hyst|pin|clk|t16-base|t16-cand|t16-mixed|mc" >&2
  exit 2
  ;;
esac
