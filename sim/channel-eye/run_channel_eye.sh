#!/usr/bin/env bash
# run_channel_eye.sh -- PVT-FULL channel-eye family (T-01 / T-09 / T-15 / T-16 / T-18 / T-26).
#
#   sim/channel-eye/run_channel_eye.sh ch      # CH-3MM-RC, 45 corners (claims about the modeled channel)
#   sim/channel-eye/run_channel_eye.sh tc      # L2 wire-bond loopback, 45 corners (test configuration; never a CH claim)
#   sim/channel-eye/run_channel_eye.sh control  # bench positive control, one corner, fixed-PMOS TX copy (not design evidence)
#
# The submit-and-record procedure is shared with sim/clock-path/run_clock_path.sh and lives in
# sim/harness/batch_record.sh; this script only names what is specific to this family. Every run
# is a `klt sim` request on the batch fleet; there is no local loop and no fallback: a failed
# submit is reported and the script exits non-zero. The 45 corners are split into jobs of 1 unit
# each: with timeout_s 2400 the fleet rejects more per job (batch_max_units_per_job_invalid).
# Per-corner ngspice cost was ~1100 s before the Mn1 change and about 22 s after it
# (sim/README.md, channel-eye section, items 3 and the "Measured" paragraph). Writes a new,
# never-overwritten record under sim/channel-eye/records/<UTC>-<kind>/. After a fleet error no
# record is written and the failing run prints the CHANNEL_EYE_WORK=... CHANNEL_EYE_RESUME=1 line
# that retries the same batch jobs. Needs PDK_ROOT (see sim/README.md) and uvx.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kind="${1:?usage: run_channel_eye.sh ch|tc|control}"
shift
case "${kind}" in
  ch) req=request_ch_1g.json ; claim="CH (modeled channel CH-3MM-RC)" ;;
  tc) req=request_tc_1g.json ; claim="TC (L2 wire-bond loopback, declared values)" ;;
  control) req=request_ctl_ch_tt.json ; claim="none: bench positive control with a modified TX copy" ;;
  *) echo "run_channel_eye.sh: unknown kind '${kind}'" >&2; exit 2 ;;
esac

head_fields="$(python3 -I -c 'import json,sys; print(json.dumps({"family": sys.argv[1], "claim_scope": sys.argv[2]}))' \
  "${kind}" "${claim}")"
tail_fields='{"energy_label": "T-26 energy per bit is SIMULATED; no measurement exists"}'

exec "${HERE}/../harness/batch_record.sh" \
  --self run_channel_eye.sh \
  --dir "${HERE}" \
  --record channel-eye \
  --request "${req}" \
  --generator gen_channel_eye.py \
  --post-label "${kind}" \
  --record-suffix "-${kind}" \
  --max-units-per-job 1 \
  --env-prefix CHANNEL_EYE \
  --copy tb_body.inc \
  --copy prbs7_stim.inc \
  --fields-head "${head_fields}" \
  --fields-tail "${tail_fields}" \
  "$@"
