#!/usr/bin/env bash
# run_t16sizing.sh -- T-16 pad-loading sizing study (issue #251), batch fleet only.
#
#   sim/channel-eye/run_t16sizing.sh screen-dpa   # kr=kc=1.2, ss+fs, 1.08 V, -40/125 C, dpantenna candidates
#   sim/channel-eye/run_t16sizing.sh screen-2kv   # same, diodevdd_2kv candidates
#   sim/channel-eye/run_t16sizing.sh fin-<ID>     # finalist ID (S.. or K..): PVT-FULL x 4 (kr, kc) pairs
#
# Every run is one `klt sim` request on the batch fleet (sim/harness/batch_record.sh); no local
# loop, no fallback. Writes a new append-only record sim/channel-eye/records/<UTC>-t16sz-<kind>/.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kind="${1:?usage: run_t16sizing.sh screen-dpa|screen-2kv|fin-<ID>}"
shift
case "${kind}" in
  screen-dpa) req=request_t16sz_dpa.json ; fam=dpa ; units=8 ;;
  screen-2kv) req=request_t16sz_2kv.json ; fam=2kv ; units=8 ;;
  fin-*) id="${kind#fin-}"
    req="request_t16sz_fin_${id}.json"
    python3 -I "${HERE}/gen_t16sizing.py" --finalist "${id}" >/dev/null
    case "${id}" in S*) fam=dpa ;; *) fam=2kv ;; esac
    units="$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import gen_channel_eye as g; print(g.SPREAD_UNITS_PER_JOB)' "${HERE}")" ;;
  dc-dpa|dc-2kv) req=none ; fam=none ; units=0 ;;
  *) echo "run_t16sizing.sh: unknown kind '${kind}'" >&2; exit 2 ;;
esac
head_fields="$(python3 -I -c 'import json,sys; print(json.dumps({"family": "t16-sizing-"+sys.argv[1], "claim_scope": "CH (modeled channel CH-3MM-RC), simulated; a sizing study of the pad ESD cell levers (#251), not a spec claim"}))' "${kind}")"
tail_fields='{"energy_label": "T-26 energy per bit is SIMULATED; no measurement exists"}'
if [[ "${kind}" == dc-* ]]; then
  fam="${kind#dc-}"
  row_map='{"t06_": "T-06", "t07_t28_": ["T-07", "T-28"], "t08_": "T-08", "t11_": "T-11", "t24_": "T-24", "t28_": "T-28"}'
  exec "${HERE}/../harness/batch_record.sh" \
    --self run_t16sizing.sh --dir "${HERE}/../dc-static" --record dc-static --request "request_t16sz_${fam}.json" \
    --generator ../channel-eye/gen_t16sizing.py --post-label "t16sz-${kind}" --record-suffix "-t16sz-${kind}" \
    --max-units-per-job 45 --env-prefix T16SZ_DC \
    --copy tb_drive.cir --copy tb_pin.cir --copy tb_rx_hyst.cir --copy "../channel-eye/esd_sz_${fam}.inc" \
    --fields-head '{"claim_scope": "BOTH rows, simulated; pad-cell sizing study for #251 (T-24 is an extracted-capacitance estimate at 500 MHz, no bond pad)"}' \
    --fields-tail '{"t25_note": "T-25 (ESD level) is not evaluated by this record."}' \
    --row-map "${row_map}" --report-only-ranges "$@"
fi
exec "${HERE}/../harness/batch_record.sh" \
  --self run_t16sizing.sh --dir "${HERE}" --record channel-eye --request "${req}" \
  --generator gen_t16sizing.py --post-label "t16sz-${kind}" --record-suffix "-t16sz-${kind}" \
  --max-units-per-job "${units}" --env-prefix T16SZ \
  --copy tb_body.inc --copy prbs7_stim.inc --copy "esd_sz_${fam}.inc" \
  --fields-head "${head_fields}" --fields-tail "${tail_fields}" "$@"
