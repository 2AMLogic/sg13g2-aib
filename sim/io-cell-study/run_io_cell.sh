#!/usr/bin/env bash
# run_io_cell.sh -- PVT-FULL pin study of the PDK sg13g2_io pad cells (issue #196, T-24 / T-08).
#
#   sim/io-cell-study/run_io_cell.sh
#
# One `klt sim` request (request.json, 45 corners) on the batch fleet through the shared
# procedure in sim/harness/batch_record.sh; there is no local loop and no fallback, and
# `--wait-for-capacity 600` is always passed by that procedure. Writes a new, never-overwritten
# record under sim/io-cell-study/records/<UTC>/. Needs PDK_ROOT (see sim/README.md) and uvx.
#
# The request carries no `limits`: it is an extraction, graded in the study record against
# T-24's two columns and T-08, so `rows` is empty by construction and --allow-empty-rows is
# stated here, in the entry point, not inferred (#267/#281).
#
# Why --max-units-per-job 9: each unit solves 38 analysis steps on a deck holding eleven PDK
# pad cells, about 2-3 minutes of ngspice under load; options.timeout_s is 200 and the fleet's
# whole-job ceiling is 3600 s, so nine units per job (five jobs) stay well inside it.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
head_fields='{"claim_scope": "BOTH, for the cell only: the PDK sg13g2_io pad cell is the pin in the channel and in the test configuration. No bond pad, no PEX, no channel model is used here.",
       "variant": "PDK sg13g2_IOPadInOut{4,16,30}mA and sg13g2_IOPadIn from libs.ref/sg13g2_io/spice/sg13g2_io.spi, instantiated unmodified. design/ is not touched.",
       "modes": "p: iovdd = 2.75 x VDDIO (the PDK-characterised 3.3 V point, 2.97-3.63 V over the grid). a: iovdd = VDDIO (AIB 1.2 V signalling level; not a point the PDK characterises)."}'
tail_fields='{"row_source": "no rows: the request carries no limits, so every measurement is report-only (see report_only_ranges).",
       "t25_note": "T-25 is not evaluated: no ESD level is derived from this record. See the study record for what ESD evidence exists for the PDK cell."}'

exec "${HERE}/../harness/batch_record.sh" \
  --self run_io_cell.sh \
  --dir "${HERE}" \
  --record io-cell-study \
  --request request.json \
  --generator gen_io_cell.py \
  --post-label io-cell \
  --max-units-per-job 9 \
  --env-prefix IO_CELL \
  --fields-head "${head_fields}" \
  --fields-tail "${tail_fields}" \
  --report-only-ranges \
  --allow-empty-rows \
  "$@"
