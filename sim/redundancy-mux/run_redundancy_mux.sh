#!/usr/bin/env bash
# run_redundancy_mux.sh -- PVT-FULL redundancy-mux family (T-05 SIM leg), CH-3MM-RC.
#
#   sim/redundancy-mux/run_redundancy_mux.sh
#
# The submit-and-record procedure is shared with sim/clock-path/run_clock_path.sh and
# sim/channel-eye/run_channel_eye.sh and lives in sim/harness/batch_record.sh; this script only
# names what is specific to this family. The deck carries six lanes: baseline, control, the
# drive-1 remap stand-in selected to A0 and A1, and the two sized remap stages weighed by
# spec/decisions/0024-*.md (sg13g2_mux2_2, and sg13g2_mux2_1 followed by sg13g2_buf_4).
# One `klt sim` request over the 45-corner grid on the batch fleet; there is no local loop
# and no fallback: a failed submit is reported and the script exits non-zero.
# `--wait-for-capacity 600` is mandatory on this fleet (it is vCPU-budgeted) and the shared
# procedure passes it. Writes a new, never-overwritten record under
# sim/redundancy-mux/records/<UTC>/. After a fleet error no record is written and the failing run
# prints the REDUNDANCY_MUX_WORK=... REDUNDANCY_MUX_RESUME=1 line that retries the same batch
# jobs. Needs PDK_ROOT (see sim/README.md) and uvx.
#
# Check the bench on one corner first -- it needs no fleet and takes about 25 s:
#   cd sim/redundancy-mux && klt sim request_tt.json --backend local \
#       --report-out /tmp/rm_tt.json --format json
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

head_fields='{"claim_scope": "CH (modeled channel CH-3MM-RC, nominal) for the lane loading; the reported deltas are lane-internal differences measured inside one simulation, not channel claims"}'
tail_fields='{"t05_bound": "none: spec/target-spec.md T-05 states no bound for the SIM leg and DR-0023 invents none. Every measurement is reported. The common added delay reports into T-20 and the select-dependent delay into T-13; neither row is graded here",
       "negative_control": "t05_ctl_* -- lane c is lane b built a second time (the remap stage shorted out) and must reproduce it; it is the noise floor the added-delay terms are read against, and claims nothing about the design",
       "remap_variants": "t05_add_* is the drive-1 sg13g2_mux2_1 stand-in DR-0023 declared; t05_add2_* is sg13g2_mux2_2 (drive 2) and t05_add3_* is sg13g2_mux2_1 followed by sg13g2_buf_4, the two sized stages spec/decisions/0024-*.md weighs. All three are measured against the same baseline lane b inside one simulation"}'

exec "${HERE}/../harness/batch_record.sh" \
  --self run_redundancy_mux.sh \
  --dir "${HERE}" \
  --record redundancy-mux \
  --request request.json \
  --generator gen_redundancy_mux.py \
  --post-label redundancy-mux \
  --max-units-per-job 3 \
  --env-prefix REDUNDANCY_MUX \
  --copy redundancy_mux_stim.inc \
  --copy sg13g2_mux2_1.inc \
  --copy sg13g2_mux2_2.inc \
  --copy sg13g2_buf_4.inc \
  --fields-head "${head_fields}" \
  --fields-tail "${tail_fields}" \
  --report-only-ranges \
  "$@"
