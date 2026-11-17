#!/usr/bin/env bash
# test_run_pex.sh -- offline self-test of layout/pex/run_pex.sh's abort contract.
#
# Run: layout/pex/test_run_pex.sh
#
# No PDK, no klayout-tools and no network: PDK_ROOT points at an empty tree with the
# one directory sim/harness/env.sh probes for, and a stub `uvx` on PATH answers every
# `klt pex` call. The run happens inside a throwaway copy of layout/pex (the rest of
# the tree is symlinked), so nothing under layout/pex/records/ is written.
#
# What it pins down (issue #315; the reproduction in the issue is the shape of case 2):
#   1. a clean extract run writes ONE record -- record.json plus the four reports --
#      and the EXIT trap leaves a completed record alone;
#   2. a recordable klt exit (4) whose report file came back EMPTY is refused with
#      exit 6 before the record-writing python runs, and no records/<stamp>/ is left
#      behind -- before the guard that run json.load-ed the empty file, crashed, and
#      abandoned the partial directory to the append-only freeze;
#   3. a tool/usage exit (2) stops the run with exit 6 and leaves no record either.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${HERE}/../.." && pwd)"
FAILED=0

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

ok()   { echo "  ok   -- $1"; }
fail() { echo "  FAIL -- $1" >&2; FAILED=1; }
check() { if [[ "$2" == "$3" ]]; then ok "$1"; else fail "$1: expected '$3', got '$2'"; fi; }
want() { local m="$1"; shift; if "$@"; then ok "${m}"; else fail "${m}"; fi; }

# --- a throwaway tree: layout/pex copied, everything the generator reads linked ------
TREE="${TMP}/tree"
mkdir -p "${TREE}/layout"
cp -r "${REPO}/layout/pex" "${TREE}/layout/pex"
rm -rf "${TREE}/layout/pex/records"
ln -s "${REPO}/sim" "${TREE}/sim"
ln -s "${REPO}/design" "${TREE}/design"
ln -s "${REPO}/layout/lvs" "${TREE}/layout/lvs"
ln -s "${REPO}/layout/aib_io_column.gds" "${TREE}/layout/aib_io_column.gds"
ln -s "${REPO}/signoff" "${TREE}/signoff"

# --- a fake PDK install, enough for sim/harness/env.sh to resolve --------------------
export PDK=ihp-sg13g2
export PDK_ROOT="${TMP}/pdk"
mkdir -p "${PDK_ROOT}/${PDK}/libs.tech/ngspice"

# --- a stub `uvx` standing in for klt pex --------------------------------------------
# Writes ${STUB_REPORT} (if set) to stdout -- which run_pex.sh redirects into the
# report file -- and exits ${STUB_RC}.
export PATH="${TMP}/bin:${PATH}"
mkdir -p "${TMP}/bin"
cat > "${TMP}/bin/uvx" <<'UVX'
#!/usr/bin/env bash
[[ -z "${STUB_REPORT:-}" ]] || printf '%s\n' "${STUB_REPORT}"
exit "${STUB_RC:-0}"
UVX
chmod +x "${TMP}/bin/uvx"

# shellcheck disable=SC2012  # the names are UTC stamps this script just created
count_records() { ls -1d "${TREE}/layout/pex/records"/*/ 2>/dev/null | wc -l; }
run_extract() {  # run_extract -> prints the exit code, leaves ${TMP}/stdout+stderr
  local rc=0
  "${TREE}/layout/pex/run_pex.sh" extract > "${TMP}/stdout" 2> "${TMP}/stderr" || rc=$?
  echo "${rc}"
}
# shellcheck disable=SC2012  # the names are UTC stamps this script just created
latest_record() { ls -1d "${TREE}/layout/pex/records"/*/ 2>/dev/null | tail -1; }

# --- 1. a clean run writes one record, and the trap leaves it alone -------------------
echo "case 1: clean extract run"
rc="$(STUB_REPORT='{}' STUB_RC=0 run_extract)"
check "exit code is 0" "${rc}" "0"
REC="$(latest_record)"
if [[ -z "${REC}" ]]; then
  fail "a record directory was written"
else
  ok "a record directory was written"
  want "the completed record keeps its record.json" test -f "${REC}/record.json"
  # shellcheck disable=SC2317  # invoked indirectly, through want() below
  record_is_complete() { python3 -I - "${REC}" <<'PY'
import json, os, sys
rec = sys.argv[1]
r = json.loads(open(f"{rec}/record.json").read())
assert r["record"] == "pex" and r["mode"] == "extract", r
assert len(r["reports"]) == 4, r["reports"]
assert all(os.path.isfile(os.path.join(rec, f)) for f in r["reports"]), r["reports"]
PY
  }
  want "the record lists the four report files, all present" record_is_complete
  want "the run says it wrote the record" grep -q "wrote layout/pex/records" "${TMP}/stdout"
  sleep 1   # the next case must not collide with this stamp
  rm -rf "${TREE}/layout/pex/records"
fi

# --- 2. an empty report on a recordable exit is refused, nothing left behind ----------
echo "case 2: recordable exit (4) with an empty report"
rc="$(STUB_RC=4 run_extract)"
check "exit code is 6" "${rc}" "6"
check "no record directory is left behind" "$(count_records)" "0"
want "the refusal names the empty report" grep -q "empty report" "${TMP}/stderr"

# --- 3. a tool/usage exit stops the run with no record --------------------------------
echo "case 3: tool exit (2)"
rc="$(STUB_RC=2 run_extract)"
check "exit code is 6" "${rc}" "6"
check "no record directory is left behind" "$(count_records)" "0"

echo
if [[ "${FAILED}" -eq 0 ]]; then echo "test_run_pex.sh: OK"; else echo "test_run_pex.sh: FAILED" >&2; fi
exit "${FAILED}"
