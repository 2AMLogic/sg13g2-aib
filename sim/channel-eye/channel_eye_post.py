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

A measurement is attached to its spec row(s) by `resolve_rows`, which tries three
sources in order: the `spec_row` the report echoes, the `spec_row` the request
declares for that name (`--request`), and a name-prefix map (`--row-map`). The
prefix map exists for a family whose graded measurements are all step-level and
carry no tag -- dc-static is one -- because a report names a step measurement
`<step>.<name>` while a request declares it `<name>`, so neither of the first two
sources can reach it without editing the committed request. One prefix may name
several rows (dc-static's `t07_t28_ipin_a` grades T-07 and T-28), in which case the
measurement counts into each.
"""
import gzip
import json
import sys
from collections import defaultdict


def load(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        return json.load(f)


def short_corner(cid):
    """mos_tt/vdd_...=1.200_...V/27C -> mos_tt/1.20V/27C (all supplies swing together)."""
    parts = cid.split("/")
    volts = sorted({p.split("=")[1] for p in parts[1].split("_") if "=" in p}) if len(parts) > 2 else []
    v = volts[0] if len(volts) == 1 else "mixed"
    return f"{parts[0]}/{v}/{parts[-1]}" if len(parts) > 2 else cid


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


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    rep = load(argv[0])
    label = argv[argv.index("--label") + 1] if "--label" in argv else None
    row_of = None
    if "--request" in argv:  # the report does not echo spec_row; the request declares it
        req = json.load(open(argv[argv.index("--request") + 1]))
        row_of = {m["name"]: m["spec_row"] for m in req["measurements"] if "spec_row" in m}
    row_map = None
    if "--row-map" in argv:  # a family whose graded measurements carry no tag at all
        row_map = json.loads(argv[argv.index("--row-map") + 1])
        if not isinstance(row_map, dict) or not all(
                isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))
                for v in row_map.values()):
            print("--row-map must be an object of prefix -> row or [rows]", file=sys.stderr)
            return 2
    res = {"label": label, "corners": len(rep["corners"]), "kind": "simulated",
           "rows": summarise(rep, row_of, row_map)}
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
