#!/usr/bin/env bash
# run_dc_static.sh -- PVT-FULL dc-static family (T-06 / T-07 / T-08 / T-11 / T-24 / T-28).
#
#   sim/dc-static/run_dc_static.sh nominal     # request.json, the committed cells (the cited record)
#   sim/dc-static/run_dc_static.sh 2kv         # request_2kv.json, the DR-0018 diodevdd_2kv variant
#   sim/dc-static/run_dc_static.sh esd-diode   # request_esd_diode.json, pad-diode extraction only
#
# The submit-and-record procedure is shared with sim/channel-eye/run_channel_eye.sh and
# sim/clock-path/run_clock_path.sh and lives in sim/harness/batch_record.sh; this script only
# names what is specific to this family. One `klt sim` request over the 45-corner grid on the
# batch fleet; there is no local loop and no fallback: a failed submit is reported and the
# script exits non-zero. `--wait-for-capacity 600` is mandatory on this fleet (it is
# vCPU-budgeted) and the shared procedure always passes it. Writes a new, never-overwritten
# record under sim/dc-static/records/<UTC>[-<kind>]/. After a fleet error no record is written
# and the failing run prints the DC_STATIC_WORK=... DC_STATIC_RESUME=1 line that retries the
# same batch jobs. Needs PDK_ROOT (see sim/README.md) and uvx.
#
# Before this script, a dc-static record was built by hand from a README recipe, and the four
# committed records have four different shapes -- none of them holding the request, the bench
# or klt's exit code (#228). Those four are append-only evidence and are left exactly as they
# are; this is the procedure for the next run.
#
# Why --max-units-per-job 45, i.e. one unsharded job: with options.timeout_s 60 the fleet's own
# ceiling for this request is 58 units per job (environment.remote.job_ceiling of every
# committed record), and the whole grid costs about 51 s of ngspice. Every dc-static run so far
# was a single job; channel-eye and clock-path shard only because their per-corner cost does
# not fit one.
#
# Why --row-map: `rows` is grouped by spec row, and the committed requests declare no
# `spec_row` -- all the graded measurements are step-level, so the report names them
# `<step>.tNN_*` while a request would declare them `tNN_*`. The prefix map resolves them
# without touching the committed request bytes the cited record was run from; adding
# `spec_row` tags there would be a separate, deliberate re-run. `t07_t28_` names two rows
# because one pin-current measurement grades both T-07 and T-28.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kind="${1:?usage: run_dc_static.sh nominal|2kv|esd-diode}"
shift

# T-06, T-08, T-11, T-24, T-28 and the two-row T-07/T-28 pin current; the ungraded
# rx_up/rx_dn trip points carry no tNN_ prefix and so grade nothing.
row_map='{"t06_": "T-06",
          "t07_t28_": ["T-07", "T-28"],
          "t08_": "T-08",
          "t11_": "T-11",
          "t24_": "T-24",
          "t28_": "T-28"}'
t24_label='extracted-capacitance estimate from model small-signal admittance at 500 MHz; no bond pad (PDK bondpad is an empty placeholder); post-layout PEX out of scope'
row_source='rows are grouped by the --row-map prefix map in run_dc_static.sh, not by a spec_row tag: the committed request declares none and its graded measurements are step-level. signoff/block-manifest.json still asserts these six rows for item 5 / analog (tool gap 2AMLogic/klayout-tools#5462).'
t25_note='T-25 (ESD level) is not evaluated by this record: no ESD-transient simulation is run here. See spec/decisions/0017-driver-series-resistor-and-esd-diode-area.md.'

case "${kind}" in
  nominal)
    req=request.json ; suffix="" ; rec=dc-static
    copy=(--copy tb_drive.cir --copy tb_pin.cir --copy tb_rx_hyst.cir)
    head_fields="$(python3 -I -c 'import json,sys; print(json.dumps(
      {"claim_scope": "BOTH (channel and test configuration); no channel model used",
       "t24_label": sys.argv[1]}))' "${t24_label}")"
    tail_fields="$(python3 -I -c 'import json,sys; print(json.dumps(
      {"row_source": sys.argv[1], "t25_note": sys.argv[2]}))' "${row_source}" "${t25_note}")"
    ;;
  2kv)
    req=request_2kv.json ; suffix="-2kv" ; rec=dc-static-2kv
    copy=(--copy tb_drive.cir --copy tb_pin.cir --copy tb_rx_hyst.cir)
    head_fields="$(python3 -I -c 'import json,sys; print(json.dumps(
      {"claim_scope": "BOTH (channel and test configuration); no channel model used",
       "variant": "DR-0018 probe: tb_dc_static_2kv.cir includes design/aib_pad_esd_2kv.spice (XDp1 = diodevdd_2kv). The committed design/aib_pad_esd.spice is NOT changed by this record.",
       "t24_label": sys.argv[1]}))' "${t24_label}")"
    tail_fields="$(python3 -I -c 'import json,sys; print(json.dumps(
      {"row_source": sys.argv[1], "t25_note": sys.argv[2]}))' "${row_source}" "${t25_note}")"
    ;;
  esd-diode)
    # extraction only: request_esd_diode.json carries no `limits` anywhere, so nothing is
    # graded, `rows` is empty by construction and the numbers live in report_only_ranges.
    req=request_esd_diode.json ; suffix="-esd-diode" ; rec=dc-static-esd-diode
    copy=() ; row_map='{}'
    head_fields='{"claim_scope": "none: pad-diode device extraction only. No limits, no spec row is graded, and this record is not design evidence for any row."}'
    tail_fields='{"row_source": "no rows: the request carries no limits, so every measurement is report-only (see report_only_ranges).",
       "t25_note": "T-25 is not evaluated: pad capacitance and forward dynamic resistance only; the 0.5 A clamp transient (SIM) and the LAYOUT area/current-path check are not run."}'
    ;;
  *) echo "run_dc_static.sh: unknown kind '${kind}'" >&2; exit 2 ;;
esac

exec "${HERE}/../harness/batch_record.sh" \
  --self run_dc_static.sh \
  --dir "${HERE}" \
  --record "${rec}" \
  --request "${req}" \
  --generator gen_dc_static.py \
  --post-label "${kind}" \
  --record-suffix "${suffix}" \
  --max-units-per-job 45 \
  --env-prefix DC_STATIC \
  ${copy[@]+"${copy[@]}"} \
  --fields-head "${head_fields}" \
  --fields-tail "${tail_fields}" \
  --row-map "${row_map}" \
  --report-only-ranges \
  "$@"
