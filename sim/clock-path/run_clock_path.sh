#!/usr/bin/env bash
# run_clock_path.sh -- PVT-FULL clock-path family (T-17 / T-04 / T-02 SIM half), CH-3MM-RC.
#
#   sim/clock-path/run_clock_path.sh
#
# The submit-and-record procedure is shared with sim/channel-eye/run_channel_eye.sh and lives in
# sim/harness/batch_record.sh; this script only names what is specific to this family. One
# `klt sim` request over the 45-corner grid on the batch fleet; there is no local loop and no
# fallback: a failed submit is reported and the script exits non-zero. `--wait-for-capacity 600`
# is mandatory on this fleet (it is vCPU-budgeted): without it a burst is refused for capacity and
# the jobs are left `pending`, which is what stalled the 2026-10-27 run of this request. Writes a
# new, never-overwritten record under sim/clock-path/records/<UTC>/. After a fleet error no record
# is written and the failing run prints the CLOCK_PATH_WORK=... CLOCK_PATH_RESUME=1 line that
# retries the same batch jobs. Needs PDK_ROOT (see sim/README.md) and uvx.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

head_fields='{"claim_scope": "CH (modeled channel CH-3MM-RC, nominal); stimulus is an ideal 50 % complementary 500 MHz clock"}'
tail_fields='{"t04_bound": "none: spec/target-spec.md T-04 states no numeric crossing bound; crossing level and latency are reported",
       "t02_bound": "none: SIM half reports data-to-clock edge times; the capture aperture (T-19) and margin (T-20) are not graded here"}'

exec "${HERE}/../harness/batch_record.sh" \
  --self run_clock_path.sh \
  --dir "${HERE}" \
  --record clock-path \
  --request request.json \
  --generator gen_clock_path.py \
  --post-label clock-path \
  --max-units-per-job 3 \
  --env-prefix CLOCK_PATH \
  --copy clock_stim.inc \
  --fields-head "${head_fields}" \
  --fields-tail "${tail_fields}" \
  --report-only-ranges \
  "$@"
