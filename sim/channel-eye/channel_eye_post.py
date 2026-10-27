#!/usr/bin/env python3
"""Summarise a `klt sim` channel-eye report per spec row, with the binding corner.

Stdlib only. Usage: python3 -I channel_eye_post.py REPORT.json[.gz] [--request REQUEST.json] [--label ch|tc|control]

Reads `corners[].measurements[]` (each entry carries `spec_row`, `status`, `value`,
`margin`) and prints one JSON object: per spec row, how many corners pass, fail or
error, whether the row passes (every graded measurement passes at every corner, no
errors), and the binding corner (the graded measurement with the smallest margin, or
the first failing/erroring corner). Rows with no limits are `reported`, never `pass`.
Nothing here relaxes a bound: it only reads the verdicts `klt sim` already graded.
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


def summarise(report, row_of=None):
    rows = defaultdict(lambda: {"measurements": set(), "pass": 0, "fail": 0, "error": 0, "graded": 0,
                                "binding": None, "_worst": None})
    spec_of = {}
    for c in report["corners"]:
        cid = short_corner(c["corner_id"])
        for m in c["measurements"]:
            row = m.get("spec_row") or (row_of or {}).get(m["name"])
            if not row:
                continue
            spec_of[m["name"]] = row
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
                    r["binding"] = {"corner": cid, "measurement": m["name"], "value": m.get("value"), "why": "fail"}
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
    res = {"label": label, "corners": len(rep["corners"]), "kind": "simulated", "rows": summarise(rep, row_of)}
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
