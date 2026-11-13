#!/usr/bin/env bash
# run_pex.sh -- the `klt pex` runs for T1 item 7 (post-layout verification, analog).
#
#   layout/pex/run_pex.sh extract        extraction only, all four drawn cells, local
#                                        (`klt pex --extract-only`: no measurement leg)
#   layout/pex/run_pex.sh probe          the one-corner local reproduction of the two
#                                        tool defects that block the delta legs
#   layout/pex/run_pex.sh delta          the PVT-FULL delta campaign on the batch fleet
#                                        -- NEVER COMPLETED, see README "Status"
#
# Each mode writes ONE append-only record under layout/pex/records/<UTC>/ and refuses
# to overwrite an existing one. `extract` and `probe` are single-unit local runs (one
# extraction each, and for `probe` one corner), which is what the host rules allow to
# stay off the fleet; `delta` is a 45-corner request per leg and is submitted with
# `--backend batch --wait-for-capacity 600`, never a local loop.
#
# Everything the run needs beyond this file is generated: the benches, DUTs and
# requests by layout/pex/gen_pex_benches.py, and the extraction arguments (layout,
# deck, label layers, per-top pin lists) by the same script into
# benches/extraction.json -- so this script and the committed record cannot disagree
# about what was run. The generator is checked for staleness before anything runs.
#
# Needs PDK_ROOT (see sim/README.md) and uvx. The grader is the pin in
# signoff/KLT_VERSION, never the host klt.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
MODE="${1:?usage: run_pex.sh extract|probe|delta}"
case "${MODE}" in extract|probe|delta) ;; *) echo "run_pex.sh: unknown mode '${MODE}'" >&2; exit 2 ;; esac

# shellcheck source=/dev/null
source "${ROOT}/sim/harness/env.sh"
[[ -n "${PDK_ROOT:-}" ]] || { echo "run_pex.sh: no PDK_ROOT" >&2; exit 2; }

KLT_VERSION="$(cat "${ROOT}/signoff/KLT_VERSION")"
K=(uvx --from "klayout-tools==${KLT_VERSION}" klt)
EX="${HERE}/benches/extraction.json"

python3 -I "${HERE}/gen_pex_benches.py" --check >/dev/null || {
  echo "run_pex.sh: generated benches are stale; run gen_pex_benches.py first" >&2; exit 4; }

jqf() { python3 -I -c "import json,sys;print(${2})" <<<"$(cat "${1}")"; }
json() { python3 -I -c 'import json,sys;d=json.load(sys.stdin);exec(sys.argv[1])' "${1}" <"${EX}"; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REC="${HERE}/records/${STAMP}"
[[ -e "${REC}" ]] && { echo "run_pex.sh: record ${REC} already exists" >&2; exit 4; }
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

LAYOUT="${HERE}/$(json 'print(d["layout"])')"
DECK="$(json 'print(d["deck"])')"
PDKNAME="$(json 'print(d["pdk"])')"
mapfile -t LABEL_ARGS < <(json 'print("\n".join(f"--label-layer={r}={l}/{dt}" for r,(l,dt) in d["label_layers"].items()))')
mapfile -t TOPS < <(json 'print("\n".join(d["tops"]))')

echo "run_pex.sh: mode=${MODE} klt=${KLT_VERSION} record=${REC#"${ROOT}/"}"
mkdir -p "${WORK}/out"

# --- extraction arguments shared by every mode -------------------------------
pins_of() { json "print(','.join(d['tops']['${1}']['pins']))"; }
extract_args() {
  printf '%s\n' --deck "${DECK}" --pdk "${PDKNAME}" --top "${1}" \
    "${LABEL_ARGS[@]}" --pins "$(pins_of "${1}")" --tie-declared-pins --rename-declared-pins
}

status=0
case "${MODE}" in
extract)
  # One extraction per drawn cell, no measurement leg: `--extract-only` reports
  # extraction/body_bias/provenance and nothing else, and exits 4 (`not_checked`)
  # by contract because it graded nothing. That is a result, not a failure.
  for top in "${TOPS[@]}"; do
    echo "  extract-only ${top}"
    mapfile -t args < <(extract_args "${top}")
    "${K[@]}" pex "${LAYOUT}" "${args[@]}" --extract-only --format json \
      -o "${WORK}/out/${top}.extracted.spice" \
      > "${WORK}/out/${top}.extract.report.json" 2> "${WORK}/out/${top}.extract.stderr" || status=$?
    [[ ${status} -le 4 ]] || { echo "run_pex.sh: ${top} extraction failed" >&2
                               cat "${WORK}/out/${top}.extract.stderr" >&2; exit 6; }
    status=0
  done
  ;;
probe|delta)
  # The delta legs. `probe` narrows the committed request to one corner and keeps
  # it local; `delta` runs the committed 45-corner grid on the batch fleet.
  # `probe` runs each leg twice, which is what makes the record a reproduction of
  # both defects rather than just a failed run:
  #   named       the request as committed, with its `backend` field kept (narrowed
  #               to `local` for one corner). Gets a correct deck, so the schematic
  #               leg produces real values and the run reaches -- and reproduces --
  #               defect 2, the one that actually blocks this item.
  #   envbackend  the same request with the `backend` field deleted, so the backend
  #               is resolved from $KLT_SIM_BACKEND instead. Reproduces defect 1:
  #               `options.osdi_preload` is dropped from the decks even though the
  #               run still executes on the local ngspice, and both legs die with
  #               "Unknown model type psp103va".
  # `delta` only ever runs `named`: every committed request states its backend, so
  # defect 1 does not bite the campaign and there is no workaround to carry.
  variants=(named)
  [[ "${MODE}" == "probe" ]] && variants=(named envbackend)
  for top in aib_io_tx aib_io_rx; do
   for variant in "${variants[@]}"; do
    tag="${top}"
    [[ "${MODE}" == "probe" ]] && tag="${top}.${variant}"
    req="${HERE}/benches/request_dc_static_${top}.json"
    python3 -I - "${req}" "${WORK}/request_${tag}.json" "${MODE}" "${variant}" <<'PY'
import hashlib, json, sys
src, dst, mode, variant = sys.argv[1:5]
r = json.loads(open(src).read())
if mode == "probe":
    # The reproduction is one corner, local: both defects are failures to load a
    # netlist, so they are corner-independent -- 45 of them would say exactly
    # what one says, at 45 times the cost and on fleet capacity other sweeps need.
    r["corners"]["process"] = [c for c in r["corners"]["process"] if c["name"] == "tt"]
    r["corners"]["supply_v"]["vddio"] = [1.2]
    r["corners"]["temperature_c"] = [27]
    r["backend"] = "local"
    r.pop("batch", None)
    r["options"]["keep_artifacts"] = True   # the ngspice log is the evidence
if variant == "envbackend":
    r.pop("backend", None)
    r.pop("batch", None)
text = json.dumps(r, indent=2) + "\n"
open(dst, "w").write(text)
open(dst + ".sha256", "w").write(hashlib.sha256(text.encode()).hexdigest() + "\n")
PY
    cp "${HERE}/benches/tb_dc_static_${top}.cir" "${HERE}/benches/${top}.dut.spice" "${WORK}/"
    echo "  delta ${tag} (${MODE})"
    mapfile -t args < <(extract_args "${top}")
    backend=()
    [[ "${MODE}" == "delta" ]] && backend=(--backend batch --wait-for-capacity 600 --max-units-per-job 3)
    "${K[@]}" pex "${LAYOUT}" "${WORK}/request_${tag}.json" "${args[@]}" "${backend[@]}" \
      --format json --outdir "${WORK}/out/${tag}" -o "${WORK}/out/${tag}/extracted.spice" \
      > "${WORK}/out/${tag}.pex.report.json" 2> "${WORK}/out/${tag}.pex.stderr" || status=$?
    # klt pex's own 0 (every delta row within tolerance), 3 (a row failed) and 4
    # (a row could not be measured) are all results and are recorded. Anything
    # else is a tool or fleet error: no record is written.
    [[ ${status} -le 4 ]] || { echo "run_pex.sh: ${tag} pex failed (exit ${status})" >&2
                               cat "${WORK}/out/${tag}.pex.stderr" >&2; exit 6; }
    echo "${status}" > "${WORK}/out/${tag}.pex.exit"
    status=0
   done
  done
  ;;
esac

# --- write the record --------------------------------------------------------
mkdir -p "${REC}"
for f in "${WORK}"/out/*.report.json "${WORK}"/out/*.exit; do
  [[ -e "${f}" ]] && cp "${f}" "${REC}/"
done
# klt's stderr only when it said something: a clean run leaves an empty file,
# and an empty file in an append-only record is noise, not evidence.
for f in "${WORK}"/out/*.stderr; do
  [[ -s "${f}" ]] && cp "${f}" "${REC}/"
done
for f in "${WORK}"/request_*.sha256; do [[ -e "${f}" ]] && cp "${f}" "${REC}/"; done
cp "${EX}" "${REC}/extraction.json"
# The decisive ngspice output of each leg, which is what names the defect. The
# whole work tree is not kept: it is tens of MB of staged model inputs.
if [[ "${MODE}" != "extract" ]]; then
  for top in aib_io_tx aib_io_rx; do
    cp "${HERE}/benches/tb_dc_static_${top}.cir" "${HERE}/benches/${top}.dut.spice" \
       "${HERE}/benches/request_dc_static_${top}.json" "${REC}/"
    for variant in "${variants[@]}"; do
      tag="${top}"
      [[ "${MODE}" == "probe" ]] && tag="${top}.${variant}"
      for side in schematic extracted; do
        log="$(find "${WORK}/out/${tag}" -path "*/${side}/*" -name ngspice.log -print -quit 2>/dev/null || true)"
        [[ -n "${log}" ]] && cp "${log}" "${REC}/${tag}.${side}.ngspice.log"
      done
    done
  done
fi

python3 -I - "${REC}" "${MODE}" "${KLT_VERSION}" "${LAYOUT}" <<'PY'
import hashlib, json, os, sys
rec, mode, klt_version, layout = sys.argv[1:5]
record = {
    "record": "pex",
    "mode": mode,
    "item": "7.analog",
    "klt_version": klt_version,
    "layout_sha256": hashlib.sha256(open(layout, "rb").read()).hexdigest(),
    "generated_by": "layout/pex/run_pex.sh",
    "reports": sorted(f for f in os.listdir(rec) if f.endswith(".report.json")),
}
if mode != "extract":
    record["request_modifications"] = {
        "_comment": "What run_pex.sh changed in the committed "
                    "benches/request_dc_static_<top>.json before each run. Each "
                    "request as it ran is pinned by request_<tag>.json.sha256.",
        **({"named": {"corners": "narrowed to the single corner tt/1.200V/27C",
                      "backend": "local",
                      "options.keep_artifacts": True},
            "envbackend": {"corners": "narrowed to the single corner tt/1.200V/27C",
                           "backend": "field deleted, so it resolves from "
                                      "$KLT_SIM_BACKEND (defect 1 reproduction)",
                           "options.keep_artifacts": True}}
           if mode == "probe" else
           {"named": {"backend": "batch, as committed",
                      "flags": "--wait-for-capacity 600 --max-units-per-job 3"}}),
    }
for name in record["reports"]:
    r = json.load(open(os.path.join(rec, name)))
    e = r.get("extraction") or {}
    delta = r.get("delta") or []
    summary = {
        "status": r.get("status"),
        "device_count": e.get("device_count"),
        "net_count": e.get("net_count"),
        "body_bias": (r.get("body_bias") or {}).get("status"),
        "input_content_hash": (r.get("provenance", {}).get("input") or {}).get("content_hash"),
        "delta_rows": len(delta),
        "delta_errors": sum(1 for row in delta if row.get("status") == "error"),
    }
    errs = {(row["error"]["side"], row["error"]["code"]) for row in delta
            if row.get("error")}
    if errs:
        summary["delta_error_sides"] = sorted(f"{s}:{c}" for s, c in errs)
    record.setdefault("summary", {})[name] = summary
open(os.path.join(rec, "record.json"), "w").write(json.dumps(record, indent=2) + "\n")
print(json.dumps(record["summary"], indent=2))
PY

echo "run_pex.sh: wrote ${REC#"${ROOT}/"}"
