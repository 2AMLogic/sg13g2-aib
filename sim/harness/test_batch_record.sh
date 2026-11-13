#!/usr/bin/env bash
# test_batch_record.sh -- offline self-test of sim/harness/batch_record.sh.
#
# Run: sim/harness/test_batch_record.sh
#
# No PDK, no ngspice, no fleet and no network: PDK_ROOT points at an empty tree with the
# one directory sim/harness/env.sh probes for, and a stub `uvx` on PATH answers the
# `klt sim` submit by copying a committed report.json.gz to --report-out. The family
# directory is a throwaway under $TMPDIR, so nothing under sim/**/records/ is written.
#
# What it pins down (the four fleet behaviours the channel-eye copy was missing before the
# two runners were merged onto this one procedure -- see issue #189):
#   1. a clean submit writes the record, scrubs the bucket name and leaves no work dir;
#   2. klt's summary sentence "N of M batch job(s) were submitted but never launched"
#      means NO record (exit 6) -- a partial grid is not a result;
#   3. a successful --resume, which prints "had been submitted but never launched;
#      launched it" per shard it RECOVERS, still writes the record;
#   4. a tool/fleet exit code is exit 6 with the record directory removed, and the
#      PREFIX_WORK / PREFIX_RESUME retry line names a work directory that still exists;
# plus: klt's own exit 3 (a limit failed) is a result and is still recorded, and a stale
# generator refuses to submit anything at all.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$(cd "${HERE}/.." && pwd)"
SRC_REC="${SIM_DIR}/clock-path/records/20261113T095936Z"
FAILED=0

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
# cases 2 and 4 deliberately leave the work dir behind for a --resume; keep those inside
# ${TMP} so the trap still collects them.
export TMPDIR="${TMP}"

ok()   { echo "  ok   -- $1"; }
fail() { echo "  FAIL -- $1" >&2; FAILED=1; }
check() { if [[ "$2" == "$3" ]]; then ok "$1"; else fail "$1: expected '$3', got '$2'"; fi; }
# want "<message>" <command...>  /  want_not "<message>" <command...>
want()     { local m="$1"; shift; if "$@"; then ok "${m}"; else fail "${m}"; fi; }
want_not() { local m="$1"; shift; if "$@"; then fail "${m}"; else ok "${m}"; fi; }

# --- a fake PDK install, enough for sim/harness/env.sh to resolve --------------------
export PDK=ihp-sg13g2
export PDK_ROOT="${TMP}/pdk"
mkdir -p "${PDK_ROOT}/${PDK}/libs.tech/ngspice"

# --- a throwaway family directory, borrowing a committed request and bench ----------
FAM="${TMP}/fam"
mkdir -p "${FAM}"
cp "${SRC_REC}/request.json" "${SIM_DIR}/clock-path/tb_clock_path.cir" \
   "${SIM_DIR}/clock-path/clock_stim.inc" "${FAM}/"
printf '%s\n' 'import sys; sys.exit(0)' > "${FAM}/gen_stub.py"

# --- a stub `uvx` standing in for the fleet ------------------------------------------
export PATH="${TMP}/bin:${PATH}"
mkdir -p "${TMP}/bin"
cat > "${TMP}/bin/uvx" <<'UVX'
#!/usr/bin/env bash
set -euo pipefail
out="" ; prev=""
for a in "$@"; do [[ "${prev}" == "--report-out" ]] && out="${a}" ; prev="${a}" ; done
printf '%s\n' "$@" > "${STUB_ARGV}"
[[ -z "${out}" ]] || cp "${STUB_REPORT}" "${out}"
# klt's progress lines name the fleet bucket (an account id)
echo "uploading units to s3://2am-fleet-012345678901/klt-sim-abc" >&2
[[ -z "${STUB_STDERR_EXTRA:-}" ]] || printf '%s\n' "${STUB_STDERR_EXTRA}" >&2
exit "${STUB_RC:-0}"
UVX
chmod +x "${TMP}/bin/uvx"
export STUB_REPORT="${SRC_REC}/report.json.gz"
export STUB_ARGV="${TMP}/argv"

run_harness() {  # run_harness -> prints the exit code, leaves ${TMP}/stderr
  local rc=0
  "${HERE}/batch_record.sh" --self test-family --dir "${FAM}" --record test-family \
    --request request.json --generator gen_stub.py --post-label clock-path \
    --max-units-per-job 3 --env-prefix TESTFAM --copy clock_stim.inc \
    --fields-head '{"claim_scope": "test"}' --fields-tail '{"note": "offline stub"}' \
    --report-only-ranges > "${TMP}/stdout" 2> "${TMP}/stderr" || rc=$?
  echo "${rc}"
}
# shellcheck disable=SC2012  # the names are UTC stamps this script just created
latest_record() { ls -1d "${FAM}"/records/*/ 2>/dev/null | tail -1; }

# --- 1. a clean submit writes the record ---------------------------------------------
echo "case 1: clean submit"
rc="$(run_harness)"
check "exit code is 0" "${rc}" "0"
REC="$(latest_record)"
if [[ -z "${REC}" ]]; then
  fail "a record directory was written"
else
  ok "a record directory was written"
  for f in record.json report.json.gz rows.json request.json klt.stderr clock_stim.inc tb_clock_path.cir; do
    want "record holds ${f}" test -f "${REC}/${f}"
  done
  check "the fleet bucket is scrubbed" \
    "$(grep -c 's3://<bucket>' "${REC}/klt.stderr")" "1"
  if grep -q '2am-fleet-012345678901' "${REC}/klt.stderr"; then
    fail "the account id leaked into klt.stderr"
  else
    ok "no account id in klt.stderr"
  fi
  # shellcheck disable=SC2317  # invoked indirectly, through want() below
  record_matches() { python3 -I - "${REC}" "${SRC_REC}" <<'PY'
import json, sys
got = json.loads(open(f"{sys.argv[1]}/record.json").read())
want = json.loads(open(f"{sys.argv[2]}/record.json").read())
assert got["record"] == "test-family", got["record"]
assert got["claim_scope"] == "test" and got["note"] == "offline stub"
assert got["batch_job_ids"] == want["batch_job_ids"], got["batch_job_ids"]
assert got["runner_klt_version"] == want["runner_klt_version"], got["runner_klt_version"]
assert got["rows"] == want["rows"]
assert got["report_only_ranges"] == want["report_only_ranges"]
assert got["corners"] == want["corners"]
PY
  }
  want "job ids, runner version and rows match the committed report" record_matches
  want_not "no --resume without TESTFAM_RESUME" grep -q -- '--resume' "${STUB_ARGV}"
  want "--wait-for-capacity is always passed (the fleet is vCPU-budgeted)" \
    grep -q -- '--wait-for-capacity' "${STUB_ARGV}"
  rm -rf "${FAM}/records"
fi

# --- 2. klt's summary sentence: no record ---------------------------------------------
echo "case 2: jobs submitted but never launched"
rc="$(STUB_STDERR_EXTRA='3 of 15 batch job(s) were submitted but never launched' run_harness)"
check "exit code is 6" "${rc}" "6"
check "no record directory is left behind" "$(latest_record)" ""
want "the retry line names the work dir and resume flag" \
  grep -q 'TESTFAM_WORK=.* TESTFAM_RESUME=1' "${TMP}/stderr"
WORKDIR="$(sed -n 's/.*TESTFAM_WORK=\([^ ]*\) .*/\1/p' "${TMP}/stderr" | tail -1)"
want "the work dir survives for the retry" test -d "${WORKDIR}"

# --- 3. a successful --resume says the same words per recovered shard -----------------
echo "case 3: a successful --resume (the bug the bare 'never launched' grep caused)"
rc="$(STUB_STDERR_EXTRA='job klt-sim-abc had been submitted but never launched; launched it' \
      TESTFAM_RESUME=1 run_harness)"
check "exit code is 0" "${rc}" "0"
want "the recovered run still writes its record" test -n "$(latest_record)"
want "TESTFAM_RESUME passes --resume" grep -q -- '--resume' "${STUB_ARGV}"
rm -rf "${FAM}/records"

# --- 4. a tool/fleet error: no record, no local fallback ------------------------------
echo "case 4: a fleet error exit code"
rc="$(STUB_RC=70 run_harness)"
check "exit code is 6" "${rc}" "6"
check "no record directory is left behind" "$(latest_record)" ""
want "the error names the no-fallback rule" grep -q 'no local fallback' "${TMP}/stderr"

# --- 5. klt exit 3 is a RESULT, not an error -------------------------------------------
echo "case 5: some limit failed (klt exit 3)"
rc="$(STUB_RC=3 run_harness)"
check "the script still exits 0" "${rc}" "0"
REC="$(latest_record)"
if [[ -z "${REC}" ]]; then
  fail "a failing limit is still a record"
else
  ok "a failing limit is still a record"
  check "klt_exit_code is recorded" \
    "$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["klt_exit_code"])' "${REC}/record.json")" "3"
fi
rm -rf "${FAM}/records"

# --- 6. a stale generator refuses to submit anything ----------------------------------
echo "case 6: stale generated files"
printf '%s\n' 'import sys; sys.exit(1)' > "${FAM}/gen_stub.py"
rc="$(run_harness)"
check "exit code is 4" "${rc}" "4"
check "no record directory is left behind" "$(latest_record)" ""

echo
if [[ "${FAILED}" -eq 0 ]]; then echo "test_batch_record.sh: OK"; else echo "test_batch_record.sh: FAILED" >&2; fi
exit "${FAILED}"
