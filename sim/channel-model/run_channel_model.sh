#!/usr/bin/env bash
# run_channel_model.sh -- T-12 channel-model conformance family (PVT-FULL x 15 length/spread rows).
#
#   sim/channel-model/run_channel_model.sh
#
# One `klt sim` request on the batch fleet; the submit-and-record procedure is the shared
# sim/harness/batch_record.sh (it passes --wait-for-capacity 600). No local loop and no
# fallback: a failed submit is reported and the script exits non-zero. The grid is 45 PVT
# corners x 15 (length, kr, kc) rows = 675 units of a passive network; they are packed
# UNITS_PER_JOB per job (gen_channel_model.py). Writes a new, never-overwritten record under
# sim/channel-model/records/<UTC>/. Needs PDK_ROOT (see sim/README.md) and uvx.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
units="$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import gen_channel_model as g; print(g.UNITS_PER_JOB)' "${HERE}")"

head_fields='{"claim_scope": "CH (modeled channel): the committed netlist spec/channel/channel_rc.cir implements the declared table spec/channel-model.md; it does NOT validate the table against silicon (T-12 CH only)"}'

exec "${HERE}/../harness/batch_record.sh" \
  --self run_channel_model.sh \
  --dir "${HERE}" \
  --record channel-model \
  --request request_channel_model.json \
  --generator gen_channel_model.py \
  --post-label channel-model \
  --max-units-per-job "${units}" \
  --env-prefix CHANNEL_MODEL \
  --row-map '{"t12_": "T-12"}' \
  --fields-head "${head_fields}" \
  "$@"
