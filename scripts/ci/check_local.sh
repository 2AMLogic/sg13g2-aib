#!/usr/bin/env bash
# The one list of PDK-free checks. Both jobs in .github/workflows/ci.yml call
# this script (`rtl` and `evidence`), so there is no hand-kept copy to drift:
# a new checker is one line here and ci.yml stays byte-stable.
#
#   scripts/ci/check_local.sh            # both parts (what `npm run check:ci` runs)
#   scripts/ci/check_local.sh rtl        # cocotb + Icarus benches and the two
#                                        # negative controls (needs iverilog and
#                                        # an importable cocotb)
#   scripts/ci/check_local.sh evidence   # the python3 -I checkers (stdlib only)
#
# Deliberately NOT here, and CI-only: the three `klt signoff` steps (manifest
# re-grade, item 9 re-attest, item 10 re-attest). They need the pinned grader.
set -eu
cd "$(dirname "$0")/../.."

usage() {
  echo "usage: ${0##*/} [rtl|evidence|all]" >&2
  exit 2
}

[ "$#" -le 1 ] || usage
case "${1-all}" in
  rtl)      want_rtl=1; want_evidence=0 ;;
  evidence) want_rtl=0; want_evidence=1 ;;
  all)      want_rtl=1; want_evidence=1 ;;
  *)        usage ;;
esac

# One collapsible section per check in the CI log; a plain banner locally.
group_begin() {
  if [ -n "${GITHUB_ACTIONS-}" ]; then printf '::group::%s\n' "$1"; else printf '== %s ==\n' "$1"; fi
}

group_end() {
  if [ -n "${GITHUB_ACTIONS-}" ]; then printf '::endgroup::\n'; fi
}

# The failure line is printed outside the group, so a red job names the check
# even with every group still collapsed.
fail() {
  if [ -n "${GITHUB_ACTIONS-}" ]; then printf '::error::%s\n' "$1" >&2; else printf '%s\n' "$1" >&2; fi
  exit 1
}

# run <label> <argv...> — must exit 0.
run() {
  label="$1"; shift
  group_begin "$label"
  rc=0
  "$@" || rc=$?
  group_end
  [ "$rc" = 0 ] || fail "$label exited $rc, expected 0"
}

# run_neg <label> <argv...> — must exit exactly 1: the suite ran and a test
# failed. A build or import error (exit 2) also exits non-zero while proving
# nothing, so it must not satisfy a negative control.
run_neg() {
  label="$1"; shift
  group_begin "$label"
  rc=0
  "$@" || rc=$?
  group_end
  [ "$rc" = 1 ] || fail "$label exited $rc, expected exactly 1"
}

if [ "$want_evidence" = 1 ]; then
  run "Self-test the checkers" \
    python3 -I scripts/ci/test_checkers.py

  # The shared sim record harness, against a stubbed `klt sim`: no PDK and no
  # batch fleet, so it belongs in the PDK-free list like every checker above.
  run "Self-test the shared sim record harness (stubbed klt sim)" \
    python3 -I sim/harness/test_write_record.py
  run "Self-test the shared batch record harness (stubbed klt sim)" \
    sim/harness/test_batch_record.sh
  run "Check evidence structure and sim/ record format" \
    python3 -I scripts/ci/check_evidence_format.py
  run "Check the committed netlist is fresh against the RTL and the attestation chain" \
    python3 -I scripts/ci/check_design_sources.py
  run "Check the item 6 digital not_applicable documents are fresh against the spec" \
    python3 -I scripts/ci/gen_item6_digital.py
  run "Check the Monte Carlo requests against the generator" \
    python3 -I sim/mc/gen_mc.py --check
  run "Check the dc-static requests against the generator" \
    python3 -I sim/dc-static/gen_dc_static.py --check
  run "Check the item 7 pex benches against the generator" \
    python3 -I layout/pex/gen_pex_benches.py --check
  run "Self-test the item 7 pex benches (pin lists, one .include, row split)" \
    python3 -I layout/pex/test_pex_benches.py
  run "Check the derived item 7 SDFs are pinned and reproduce from the routed SDF" \
    python3 -I scripts/ci/check_item7_sdf.py
  run "Check the committed routed SPEF and DEF match their manifest pins" \
    python3 -I scripts/ci/check_pnr_pins.py

  # CI passes the PR base (or the pre-push SHA) in BASE; locally fall back to
  # the merge-base with origin/main. An empty or all-zero base (a new branch)
  # is skipped by the checker, so do not substitute a merge-base for one.
  base="${BASE-}"
  [ -n "$base" ] || base="$(git merge-base origin/main HEAD 2>/dev/null || true)"
  run "Check sim/ records are append-only" \
    python3 -I scripts/ci/check_sim_append_only.py --base "$base"

  run "Check the item 8 characterization report is fresh and pinned" \
    python3 -I scripts/ci/gen_characterization_report.py --check
fi

if [ "$want_rtl" = 1 ]; then
  # Plain python3, not -I: -I hides a user-site cocotb.
  run "Run the shift-redundancy bench (expect 41/41)" \
    python3 verification/run_tb.py
  run_neg "Negative control must exit exactly 1" \
    python3 verification/run_tb.py --define INJECT_BUG_SHIFT_EDGE=1

  for n in 20 8; do
    run "Run the datapath bench at N = $n (expect 8/8)" \
      python3 verification/run_tb.py --bench datapath --param "N=$n"
  done
  run_neg "Latency negative control must exit exactly 1" \
    python3 verification/run_tb.py --bench datapath --define INJECT_EXTRA_STAGE=1
fi
