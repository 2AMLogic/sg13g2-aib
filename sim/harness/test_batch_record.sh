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
#
# Cases 7 and 8 cover the dc-static entry point (#228), the third family on this procedure
# and the one that needs `--row-map`: 7 is its resolved `--dry-run` configuration, 8 drives
# the whole procedure over a real committed dc-static report and checks that the prefix map
# reproduces the six spec rows that record asserts by hand. The other two entry points'
# dry-run cases live in sim/harness/test_write_record.py, where each is compared against a
# committed record of its own family; every dc-static record predates this harness, so there
# is no harness-shaped record there to compare against -- hence the case belongs here.
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

# --- 7. the dc-static entry point's resolved configuration ----------------------------
echo "case 7: the dc-static entry point (--dry-run, no PDK and no fleet)"
DC_RUNNER="${SIM_DIR}/dc-static/run_dc_static.sh"
dc_dry() { "${DC_RUNNER}" "$1" --dry-run; }
# shellcheck disable=SC2317  # invoked indirectly, through want() below
dc_dry_quiet() { dc_dry "$1" >/dev/null; }
for kind in nominal 2kv esd-diode; do
  want "the ${kind} kind resolves a configuration" dc_dry_quiet "${kind}"
done
# shellcheck disable=SC2317  # invoked indirectly, through want() below
dc_config_matches() { python3 -I - "$(dc_dry nominal)" <<'PY'
import json, sys
cfg = json.loads(sys.argv[1])
assert cfg["record"] == "dc-static", cfg["record"]
assert cfg["record_suffix"] == "", cfg["record_suffix"]
assert cfg["request"] == "request.json", cfg["request"]
assert cfg["generator"] == "gen_dc_static.py", cfg["generator"]
assert cfg["env_prefix"] == "DC_STATIC", cfg["env_prefix"]
# one unsharded job: options.timeout_s 60 puts the fleet's own ceiling at 58 units
assert cfg["max_units_per_job"] == "45", cfg["max_units_per_job"]
assert cfg["report_only_ranges"] is True
# the three sub-benches tb_dc_static.cir .includes; the netlist itself is always copied
assert set(cfg["copy"]) == {"tb_drive.cir", "tb_pin.cir", "tb_rx_hyst.cir"}, cfg["copy"]
# the committed request declares no spec_row, so rows come from the prefix map
assert set(cfg["row_map"]) == {"t06_", "t07_t28_", "t08_", "t11_", "t24_", "t28_"}, cfg["row_map"]
assert cfg["row_map"]["t07_t28_"] == ["T-07", "T-28"], "one measurement grades T-07 and T-28"
PY
}
want "the nominal configuration is the dc-static one" dc_config_matches
# shellcheck disable=SC2317  # invoked indirectly, through want() below
dc_esd_claims_nothing() { python3 -I - "$(dc_dry esd-diode)" <<'PY'
import json, sys
cfg = json.loads(sys.argv[1])
assert cfg["record_suffix"] == "-esd-diode", cfg["record_suffix"]
assert cfg["row_map"] == {}, "extraction only: nothing is graded, so no row is claimed"
assert cfg["fields_head"]["claim_scope"].startswith("none:"), cfg["fields_head"]
PY
}
want "the esd-diode kind grades no row and claims none" dc_esd_claims_nothing
rc=0
"${DC_RUNNER}" nope --dry-run >/dev/null 2>&1 || rc=$?
check "an unknown kind is refused with exit 2" "${rc}" "2"

# --- 8. the row map, over a real committed dc-static report ----------------------------
echo "case 8: --row-map groups a real dc-static report by spec row"
# sim/dc-static/records/20261112T001207Z/ is the record signoff/block-manifest.json cites for
# item 5 / analog. It was built by hand and holds no record.json, so this is also the first
# check that the harness reproduces the six rows that manifest asserts on its own word.
SRC_DC="${SIM_DIR}/dc-static/records/20261112T001207Z/report.json"
FAM2="${TMP}/dcfam"
mkdir -p "${FAM2}"
cp "${SIM_DIR}/dc-static/request.json" "${SIM_DIR}/dc-static/tb_dc_static.cir" \
   "${SIM_DIR}/dc-static/tb_drive.cir" "${SIM_DIR}/dc-static/tb_pin.cir" \
   "${SIM_DIR}/dc-static/tb_rx_hyst.cir" "${FAM2}/"
printf '%s\n' 'import sys; sys.exit(0)' > "${FAM2}/gen_stub.py"
gzip -c "${SRC_DC}" > "${TMP}/dc-static-report.json.gz"
# read the map out of the entry point rather than restating it, so this cannot drift from
# what the runner actually passes.
DC_ROW_MAP="$(python3 -I -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["row_map"]))' "$(dc_dry nominal)")"
rc=0
STUB_REPORT="${TMP}/dc-static-report.json.gz" "${HERE}/batch_record.sh" \
  --self test-dc-static --dir "${FAM2}" --record test-dc-static \
  --request request.json --generator gen_stub.py --post-label nominal \
  --max-units-per-job 45 --env-prefix TESTDC \
  --copy tb_drive.cir --copy tb_pin.cir --copy tb_rx_hyst.cir \
  --row-map "${DC_ROW_MAP}" --report-only-ranges \
  > "${TMP}/stdout" 2> "${TMP}/stderr" || rc=$?
check "exit code is 0" "${rc}" "0"
# shellcheck disable=SC2012  # the names are UTC stamps this script just created
REC2="$(ls -1d "${FAM2}"/records/*/ 2>/dev/null | tail -1)"
if [[ -z "${REC2}" ]]; then
  fail "a dc-static record directory was written"
else
  ok "a dc-static record directory was written"
  for f in record.json rows.json request.json tb_dc_static.cir tb_drive.cir tb_pin.cir tb_rx_hyst.cir; do
    want "the record holds ${f}" test -f "${REC2}/${f}"
  done
  # shellcheck disable=SC2317  # invoked indirectly, through want() below
  dc_rows_match() { python3 -I - "${REC2}" <<'PY'
import json, sys
rec = json.loads(open(f"{sys.argv[1]}/record.json").read())
rows = rec["rows"]
# exactly the six rows sim/dc-static/README.md and the manifest name for this family
assert set(rows) == {"T-06", "T-07", "T-08", "T-11", "T-24", "T-28"}, sorted(rows)
assert all(r["verdict"] == "pass" for r in rows.values()), rows
# the 45/45-corner counts: 4 T-06 measurements, 2 T-08, 3 pin-current, 3 cap, 1 hysteresis,
# and T-28 takes the 3 pin-current ones plus its own 2 weak-pull ones.
assert [rows[k]["pass"] for k in ("T-06", "T-07", "T-08", "T-11", "T-24", "T-28")] == \
    [180, 135, 90, 45, 135, 225], {k: rows[k]["pass"] for k in rows}
# one measurement counted into BOTH of the rows it grades
rj = json.loads(open(f"{sys.argv[1]}/rows.json").read())["rows"]
assert "lk_0.t07_t28_ipin_a" in rj["T-07"]["measurements"]
assert "lk_0.t07_t28_ipin_a" in rj["T-28"]["measurements"]
assert "pu_on.t28_rpu_ohm" in rj["T-28"]["measurements"]
assert "pu_on.t28_rpu_ohm" not in rj["T-07"]["measurements"]
# the binding corner the hand-written record 20261108T004350Z noted for T-24:
# "96.42 fF (pad=VDDIO/2, fs/1.32V/125C)"
b = rows["T-24"]["binding"]
assert b["measurement"] == "cap_5.t24_cpin_ff", b
assert abs(b["value"] - 96.41907) < 1e-5, b
assert b["corner"].startswith("fs/") and b["corner"].endswith("/125C"), b
# the three ungraded receiver trip points grade no row and land in the ranges instead
assert set(rec["report_only_ranges"]) == {"rx_dn.vth_dn", "rx_up.vddio_v", "rx_up.vth_up"}, \
    sorted(rec["report_only_ranges"])
PY
  }
  want "the prefix map reproduces the six rows the cited record asserts" dc_rows_match
fi

echo
if [[ "${FAILED}" -eq 0 ]]; then echo "test_batch_record.sh: OK"; else echo "test_batch_record.sh: FAILED" >&2; fi
exit "${FAILED}"
