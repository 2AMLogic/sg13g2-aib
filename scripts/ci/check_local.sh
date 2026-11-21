#!/usr/bin/env bash
# The one list of PDK-free checks. Both jobs in .github/workflows/ci.yml call
# this script (`rtl` and `evidence`), so there is no hand-kept copy to drift:
# a new checker is one line here and ci.yml stays byte-stable.
#
#   scripts/ci/check_local.sh            # both parts (what `npm run check:ci` runs)
#   scripts/ci/check_local.sh rtl        # cocotb + Icarus benches and the two
#                                        # negative controls, through the pinned
#                                        # klt (needs iverilog; uvx or KLT=klt)
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

# run_rc <label> <want> <argv...> — must exit exactly <want>. For a refusal
# path, where the point of the check is the specific code and not just failure.
run_rc() {
  label="$1"; want="$2"; shift 2
  group_begin "$label"
  rc=0
  "$@" || rc=$?
  group_end
  [ "$rc" = "$want" ] || fail "$label exited $rc, expected exactly $want"
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
  run "Check every attested path matches its envelope's content_hash" \
    python3 -I scripts/ci/check_attested_paths.py
  run "Check the item 6 digital not_applicable documents are fresh against the spec" \
    python3 -I scripts/ci/gen_item6_digital.py
  run "Check the Monte Carlo requests against the generator" \
    python3 -I sim/mc/gen_mc.py --check
  run "Check the rx-threshold-study benches and requests against the generator" \
    python3 -I sim/rx-threshold-study/gen_rx_threshold.py --check
  run "Check the per-corner Monte Carlo tables against the committed records" \
    python3 -I sim/mc/gen_per_corner.py --check
  run "Check the dc-static requests against the generator" \
    python3 -I sim/dc-static/gen_dc_static.py --check
  run "Check T-04's clk/clkb arrangement is wired through the clock-path netlists (DR-0027)" \
    python3 -I sim/clock-path/check_clk_pair.py

  # The two sim bench self-tests. Each covers its post-processor -- the code
  # that turns a recorded report into a pass/fail -- and asserts its generated
  # files are fresh against the generator, so neither needs its own
  # `gen_*.py --check` line: test_channel_eye.py compares all four
  # channel-eye outputs and test_t19.py both T-19 netlists, the same
  # comparison those --check modes make. The one sim generator not reached
  # that way, sim/clock-path/gen_clock_path.py --check, runs inside
  # test_checkers.py above (with gen_channel_eye, gen_mc and gen_dc_static).
  run "Self-test the channel-eye bench and its pass/fail post-processor" \
    python3 -I sim/channel-eye/test_channel_eye.py
  run "Self-test the T-19 capture-window bench and its aperture post-processor" \
    python3 -I sim/mc/capture_window/test_t19.py
  run "Check every committed sim/ and layout/ request against the one PVT-FULL corner table" \
    python3 -I scripts/ci/check_corner_bundles.py
  run "Check the T-12 channel-model conformance bench against the generator" \
    python3 -I sim/channel-model/gen_channel_model.py --check
  run "Self-test the T-12 channel-model bench (netlist-text solver, seeded netlist edits)" \
    python3 -I sim/channel-model/test_channel_model.py
  run "Check the item 7 pex benches against the generator" \
    python3 -I layout/pex/gen_pex_benches.py --check
  run "Self-test the item 7 pex benches (pin lists, one .include, row split)" \
    python3 -I layout/pex/test_pex_benches.py

  # The pex record runner's abort contract, against a stubbed `klt pex`: no PDK
  # and no network, so it belongs in the PDK-free list like every checker above
  # (#315 -- the empty-report refusal and the no-partial-record EXIT trap).
  run "Self-test the pex record runner's abort contract (stubbed klt pex)" \
    layout/pex/test_run_pex.sh

  # The assembled I/O-cell LVS reference netlists AND the seeded negative
  # controls under layout/lvs/neg/. #202 made those controls derived rather
  # than hand-copied so that a change to a source is carried into the control;
  # this is the check that the carrying actually happened. It reads committed
  # files only (design/*.spice and layout/pnr/.klt/place-and-route/), so it is
  # PDK-free and belongs in this list rather than beside the klt signoff steps.
  run "Check the LVS reference netlists and the derived neg/ controls are fresh" \
    python3 -I layout/lvs/gen_reference.py --check
  run "Check the derived item 7 SDFs are pinned and reproduce from the routed SDF" \
    python3 -I scripts/ci/check_item7_sdf.py
  run "Check the committed routed SPEF and DEF match their manifest pins" \
    python3 -I scripts/ci/check_pnr_pins.py

  # The #248 incident: a stream regeneration left the cited pex reports
  # declaring the pre-regeneration input hash and the grader re-graded
  # byte-identically (#273). This walks the manifest citations -- not a
  # records/ glob, which would flag the uncited stale and probe records --
  # and fails when a cited record's declared input hash is not the shipped
  # stream's sha256.
  run "Check every cited evidence record binds the shipped stream" \
    python3 -I scripts/ci/check_evidence_pins.py

  # `klt signoff --attest` records an inventory's tool pins verbatim and its
  # own version as provenance, and never compares the two (#324): a pin left
  # behind by a grader bump attests a version the evidence was not produced
  # with. Each inventory that pins klt is checked against the envelope built
  # from it -- never against signoff/KLT_VERSION, which is the pin for the
  # *next* attestation, not a retroactive truth about landed evidence. The
  # same script compares an inventory's ngspice pin against the newest
  # pdk-smoke record (#368): only the newest, because committed records are
  # append-only and an older record under another simulator is history.
  run "Check each inventory's tool pins match the evidence that used them" \
    python3 -I scripts/ci/check_inventory_klt_pin.py

  # The #260 defect at class level: a tracked evidence file that an ignore
  # rule still matches is a record a plain `git add` silently drops (its
  # committed siblings were only tracked because someone force-added them).
  # One hand-written negation per evidence family, so every rename or new
  # record family can re-open the hole; this is the check that catches it.
  run "Check no tracked record file is matched by an ignore rule" \
    python3 -I scripts/ci/check_record_not_ignored.py

  # CI passes a base SHA in BASE plus the event facts the checker needs to
  # choose between it and the merge-base with the default branch (#255; see the
  # checker's docstring). Locally there is no event, so fall back to the
  # merge-base with origin/main directly -- which is the same question CI now
  # asks on every event. An empty or all-zero base (a new branch) is skipped by
  # the checker, so do not substitute a merge-base for one.
  base="${BASE-}"
  [ -n "$base" ] || base="$(git merge-base origin/main HEAD 2>/dev/null || true)"
  run "Check sim/ records are append-only" \
    python3 -I scripts/ci/check_sim_append_only.py --base "$base" \
      --event-name "${EVENT_NAME-}" --push-ref "${PUSH_REF-}" \
      --default-branch "${DEFAULT_BRANCH:-main}"

  run "Check the item 8 characterization report is fresh and pinned" \
    python3 -I scripts/ci/gen_characterization_report.py --check

  # The README is hand-written prose carrying one volatile number (the T1 met
  # count); this is the check that the prose and the record cannot drift apart.
  run "Check the README status statement against the signoff record" \
    python3 -I scripts/ci/check_readme_status.py
fi

if [ "$want_rtl" = 1 ]; then
  # Each bench is defined once, by the klt functional-verification request the
  # item 5 digital envelopes cite, and is run by the same pinned klt that graded
  # that evidence (signoff/KLT_VERSION). CI installs it with the
  # functional-verification extra and sets KLT=klt; locally the default fetches
  # the pin with uvx. A klt that cannot be fetched fails loudly, never skips.
  #
  # PDK_ROOT is unset: these five requests are PDK-free, and a set PDK_ROOT is
  # not something the check should depend on.
  KLT="${KLT:-uvx --from klayout-tools[functional-verification]==$(cat signoff/KLT_VERSION) klt}"
  fv_out="$(mktemp -d)"
  trap 'rm -rf "$fv_out"' EXIT

  # fv <request-stem> — one klt functional-verification run. klt exits 0 when
  # every test passed, 3 when the suite ran and a test failed, and 1 when the
  # bench did not build; the three callers below depend on that split.
  fv() {
    # $KLT is deliberately unquoted: it is a command line, not one word.
    # shellcheck disable=SC2086
    env -u PDK_ROOT $KLT functional-verification "verification/klt/$1.json" \
      -o "$fv_out/$1" --format json > "$fv_out/$1.stdout"
  }

  # run_neg_fv <label> <stem> — must exit exactly 3: the suite ran and a test
  # failed. A build error exits 1 and proves nothing, so it must not satisfy a
  # negative control.
  run_neg_fv() {
    run_rc "$1" 3 fv "$2"
  }

  # fv_counted <request-stem> <want> — fv, then the suite must have run exactly
  # <want> tests and passed all of them. Exit 0 from klt alone does not say the
  # bench still has its tests: a bench shrunk to fewer (non-zero) tests still
  # exits 0. A report with missing keys or non-JSON stdout fails, never passes.
  # The count lives here, once, and the run label below is built from it.
  fv_counted() {
    fv "$1" || return $?
    python3 -I - "$1" "$2" "$fv_out/$1.stdout" <<'PY'
import json, sys
stem, want, path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
try:
    with open(path) as f:
        r = json.load(f)
    got = {k: r[k] for k in ("test_count", "passed_count", "failed_count")}
except (OSError, ValueError, KeyError, TypeError) as e:
    sys.exit(f"{stem}: no usable test counts in klt report ({e!r})")
if got["test_count"] != want or got["passed_count"] != want or got["failed_count"] != 0:
    sys.exit(f"{stem}: expected {want}/{want} passed, 0 failed; klt reported "
             f"test_count={got['test_count']} passed_count={got['passed_count']} "
             f"failed_count={got['failed_count']}")
PY
  }

  want_shift=41
  run "Run the shift-redundancy bench (expect $want_shift/$want_shift)" \
    fv_counted shift_redundancy "$want_shift"
  run_neg_fv "Negative control must exit exactly 3" neg_shift_edge

  want_dp=8
  for req in datapath_n20 datapath_n8; do
    run "Run the datapath bench from $req.json (expect $want_dp/$want_dp)" \
      fv_counted "$req" "$want_dp"
  done
  run_neg_fv "Latency negative control must exit exactly 3" neg_extra_stage
fi
