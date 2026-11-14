#!/usr/bin/env python3
"""Summarise a `klt sim` report per spec row, with the binding corner.

Stdlib only. Usage:
  python3 -I channel_eye_post.py REPORT.json[.gz] [--request REQUEST.json]
      [--label ch|tc|control|...] [--row-map JSON]

Reads `corners[].measurements[]` (each entry carries `spec_row`, `status`, `value`,
`margin`) and prints one JSON object: per spec row, how many corners pass, fail or
error, whether the row passes (every graded measurement passes at every corner, no
errors), and the binding corner (the graded measurement with the smallest margin, or
the first failing/erroring corner). Rows with no limits are `reported`, never `pass`.
Nothing here relaxes a bound: it only reads the verdicts `klt sim` already graded.

A request with a `corners.params` axis runs the whole PVT grid once per parameter row
(T-12's channel +-20 % R/C spread: 45 PVT corners at each of four (kr, kc) pairs). For
one of those, a second key `param_groups` carries the same per-row summary once per
parameter corner, because a pooled summary cannot say which parameter corner a failure
belongs to. It is absent for a request without the axis.

A measurement is attached to its spec row(s) by `resolve_rows`, which tries three
sources in order: the `spec_row` the report echoes, the `spec_row` the request
declares for that name (`--request`), and a name-prefix map (`--row-map`). The
prefix map exists for a family whose graded measurements are all step-level and
carry no tag -- dc-static is one -- because a report names a step measurement
`<step>.<name>` while a request declares it `<name>`, so neither of the first two
sources can reach it without editing the committed request. One prefix may name
several rows (dc-static's `t07_t28_ipin_a` grades T-07 and T-28), in which case the
measurement counts into each.

Flags are parsed with argparse, so an unknown or value-less one exits 2 having printed
nothing on stdout, and a summary that attaches no measurement to any spec row is refused
the same way (#267). Scanning `argv` for each flag instead meant a mistyped `--request`
was never looked for: it exited 0 printing `rows: {}`, which `sim/harness/write_record.py`
passes through into an append-only `record.json` that `scripts/ci/check_evidence_format.py`
accepts -- a batch run committable as evidence with no row verdicts at all. The typo-free
path is the same: a family whose request declares no `spec_row` and which is missing its
`--row-map` grades nothing either. Neither may produce a `rows.json`.
"""
import argparse
import gzip
import json
import sys
from collections import defaultdict


def load(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        return json.load(f)


PARAMS_SEG = "params:"


def split_params(cid):
    """(corner id without its parameter segment, that segment's text or None).

    `corners.params` appends a `params:<name>=<value>,...` segment to every corner id
    (`mos_tt/vdd_...V/-40C/params:ch_kc=0.8,ch_kr=0.8`). Splitting it off keeps the PVT
    part positional, which is what lets `short_corner` still find the temperature in the
    last PVT segment instead of printing the parameters in its place.
    """
    parts = cid.split("/")
    pvt = [s for s in parts if not s.startswith(PARAMS_SEG)]
    params = [s[len(PARAMS_SEG):] for s in parts if s.startswith(PARAMS_SEG)]
    return "/".join(pvt), (",".join(params) if params else None)


def short_corner(cid):
    """mos_tt/vdd_...=1.200_...V/27C -> mos_tt/1.20V/27C (all supplies swing together).

    A parameter segment is split off first and re-appended after the temperature, so a
    spread corner reads `mos_tt/1.200V/-40C/ch_kc=0.8,ch_kr=0.8`. Taking `parts[-1]` as
    the temperature without that split printed the parameters as the temperature and
    dropped the temperature entirely.
    """
    cid, params = split_params(cid)
    parts = cid.split("/")
    volts = sorted({p.split("=")[1] for p in parts[1].split("_") if "=" in p}) if len(parts) > 2 else []
    v = volts[0] if len(volts) == 1 else "mixed"
    short = f"{parts[0]}/{v}/{parts[-1]}" if len(parts) > 2 else cid
    return f"{short}/{params}" if params else short


def resolve_rows(m, row_of=None, row_map=None):
    """The spec rows one measurement grades; [] when it grades none.

    `row_map` maps a measurement-name PREFIX to one row or to a list of rows, and is
    matched against the last dotted component of the report name (`<step>.<name>`),
    longest prefix first -- so dc-static's `t07_t28_` wins over `t07_`/`t28_` for
    `lk_0.t07_t28_ipin_a`. A tag on the measurement or in the request always wins
    over the map: the map is a fallback for a family that has neither.
    """
    tag = m.get("spec_row") or (row_of or {}).get(m["name"])
    if tag:
        return [tag]
    if not row_map:
        return []
    leaf = m["name"].rsplit(".", 1)[-1]
    hits = [p for p in row_map if leaf.startswith(p)]
    if not hits:
        return []
    rows = row_map[max(hits, key=len)]
    return [rows] if isinstance(rows, str) else list(rows)


def summarise(report, row_of=None, row_map=None):
    rows = defaultdict(lambda: {"measurements": set(), "pass": 0, "fail": 0, "error": 0, "graded": 0,
                                "binding": None, "_worst": None})
    for c in report["corners"]:
        cid = short_corner(c["corner_id"])
        for m in c["measurements"]:
            # one measurement may grade several rows (dc-static's t07_t28_ipin_a);
            # it then counts into each of them.
            for row in resolve_rows(m, row_of, row_map):
                r = rows[row]
                r["measurements"].add(m["name"])
                st = m["status"]
                if st == "error":
                    r["error"] += 1
                    r["binding"] = r["binding"] or {"corner": cid, "measurement": m["name"], "why": "error"}
                    r["_worst"] = -1e300
                elif st == "fail":
                    r["fail"] += 1
                    r["graded"] += 1
                    mg = m.get("margin")
                    key = mg if isinstance(mg, (int, float)) else -1e299
                    if r["_worst"] is None or key < r["_worst"]:
                        r["_worst"] = key
                        r["binding"] = {"corner": cid, "measurement": m["name"], "value": m.get("value"),
                                        "why": "fail"}
                elif st == "pass":
                    r["pass"] += 1
                    if m.get("margin") is not None:
                        r["graded"] += 1
                        if r["_worst"] is None or m["margin"] < r["_worst"]:
                            r["_worst"] = m["margin"]
                            r["binding"] = {"corner": cid, "measurement": m["name"], "value": m.get("value"),
                                            "why": "smallest margin"}
    out = {}
    for row, r in sorted(rows.items()):
        if r["error"] or r["fail"]:
            verdict = "fail"
        elif r["graded"]:
            verdict = "pass"
        else:
            verdict = "reported"
        out[row] = {"verdict": verdict, "measurements": sorted(r["measurements"]), "pass": r["pass"],
                    "fail": r["fail"], "error": r["error"], "binding": r["binding"]}
    return out


def param_groups(report, row_of=None, row_map=None):
    """One `summarise` result per parameter corner; `{}` without a `corners.params` axis.

    A request with that axis runs the whole PVT grid once per parameter row, so the
    pooled `rows` summary mixes the parameter corners together and cannot say which one
    a failure belongs to. Grouping by the `params:` segment of the corner id and
    summarising each group on its own reports a row that passes at three spread corners
    and fails at the fourth as failing *at that corner* -- which is the result T-12's
    grid column asks for. Nothing is relaxed or re-graded: the groups re-read the same
    per-corner verdicts `klt sim` produced.
    """
    buckets = defaultdict(list)
    for c in report["corners"]:
        _, params = split_params(c["corner_id"])
        if params is not None:
            buckets[params].append(c)
    return {k: {"corners": len(cs), "rows": summarise({"corners": cs}, row_of, row_map)}
            for k, cs in sorted(buckets.items())}


def parse_row_map(text):
    """`--row-map`'s JSON object of prefix -> row or [rows], as an argparse `type=`.

    Malformed JSON and a well-formed value of the wrong shape are both argparse errors,
    so each exits 2 having printed nothing on stdout rather than raising a traceback or
    reaching `resolve_rows` as a silent `None`.
    """
    try:
        row_map = json.loads(text)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"--row-map is not valid JSON: {exc}")
    if not isinstance(row_map, dict) or not all(
            isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))
            for v in row_map.values()):
        raise argparse.ArgumentTypeError("--row-map must be an object of prefix -> row or [rows]")
    return row_map


def row_sources(report, row_of, row_map):
    """What each of `resolve_rows`' three sources had to offer, for the refusal message.

    A summary that grades nothing is almost always one missing source -- a request that
    declares no `spec_row` for a report that echoes none either, with no prefix map to
    fall back on -- so naming all three says which one to supply.
    """
    echoed = sum(1 for c in report["corners"] for m in c["measurements"] if m.get("spec_row"))
    declared = "--request not given" if row_of is None else f"{len(row_of)} name(s)"
    mapped = "--row-map not given" if row_map is None else f"{len(row_map)} prefix(es)"
    return (f"report-echoed spec_row: {echoed} of "
            f"{sum(len(c['measurements']) for c in report['corners'])} measurement(s); "
            f"request-declared spec_row: {declared}; prefix map: {mapped}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", help="the `klt sim` report, .json or .json.gz")
    ap.add_argument("--label", help="family label written to the summary's `label` field")
    ap.add_argument("--request",
                    help="the `klt sim` request, whose measurements declare the `spec_row` a "
                         "report does not echo")
    ap.add_argument("--row-map", type=parse_row_map,
                    help="JSON object of measurement-name PREFIX -> spec row (or [rows]), for a "
                         "family whose graded measurements carry no tag at all")
    args = ap.parse_args(argv)

    rep = load(args.report)
    row_of = None
    if args.request:  # the report does not echo spec_row; the request declares it
        with open(args.request) as fh:
            req = json.load(fh)
        row_of = {m["name"]: m["spec_row"] for m in req["measurements"] if "spec_row" in m}
    rows = summarise(rep, row_of, args.row_map)
    if not rows:
        # Refuse rather than print `rows: {}`: write_record.py:83 takes that as-is,
        # check_evidence_format.py requires only record/utc_stamp/pdk.release_tag, and
        # check_sim_append_only.py then freezes it -- a run committed as evidence with no
        # row verdicts at all. The docstring above promises a summary per spec row; on
        # this path there is none to make, so there is nothing to record.
        print(f"{args.report}: no measurement reached a spec row, so this summary would grade "
              f"nothing; refusing to write it. {row_sources(rep, row_of, args.row_map)}",
              file=sys.stderr)
        return 2
    res = {"label": args.label, "corners": len(rep["corners"]), "kind": "simulated",
           "rows": rows}
    groups = param_groups(rep, row_of, args.row_map)
    if groups:  # only a request with a `corners.params` axis has any
        res["param_groups"] = groups
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
