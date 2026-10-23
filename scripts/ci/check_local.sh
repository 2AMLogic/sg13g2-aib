#!/usr/bin/env bash
# Local mirror of the PDK-free checks in .github/workflows/ci.yml.
# The klt signoff re-grade stays CI-only: it needs the pinned grader.
set -eu
cd "$(dirname "$0")/../.."

python3 -I scripts/ci/test_checkers.py
python3 -I scripts/ci/check_evidence_format.py

# Same base as CI's pull_request run; empty base is skipped by the checker.
base="$(git merge-base origin/main HEAD 2>/dev/null || true)"
python3 -I scripts/ci/check_sim_append_only.py --base "$base"

# cocotb + Icarus bench (needs iverilog and cocotb). Plain python3: -I hides a user-site cocotb.
python3 verification/run_tb.py
rc=0
python3 verification/run_tb.py --define INJECT_BUG_SHIFT_EDGE=1 || rc=$?
if [ "$rc" != 1 ]; then
  echo "negative control exited $rc, expected exactly 1" >&2
  exit 1
fi
