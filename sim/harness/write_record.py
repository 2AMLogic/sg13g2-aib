#!/usr/bin/env python3
"""Write the append-only record.json of one batch `klt sim` record directory.

Stdlib only; no PDK, no ngspice, no fleet. This is the record-writing half of
sim/harness/batch_record.sh, kept as its own entry point so it can be replayed
over an already committed report.json.gz without re-running a grid --
sim/harness/test_write_record.py does exactly that for both families.

Usage:
  python3 -I sim/harness/write_record.py REC --record NAME --stamp UTC \
      --pdk-tag TAG --klt-exit-code N [--fields-head JSON] [--fields-tail JSON] \
      [--report-only-ranges]

REC must already hold report.json.gz, rows.json and request.json (the copy
batch_record.sh makes). Nothing outside REC is read or written, and REC itself
is never re-read once written: records are append-only evidence.

The key order of the emitted object is fixed:

  record, utc_stamp, kind, <--fields-head, in order>, pdk, klt_exit_code,
  corners, rows, [report_only_ranges], <--fields-tail, in order>,
  batch_job_ids, runner_klt_version

Job ids: a single batch job reports environment.remote.job_id, a sharded one
reports environment.remote.fleet[]. Both are collected, so a sharded run (what
--max-units-per-job 1 always produces) records its ids instead of a null.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path


def job_identity(report):
    """(job ids, runner klt versions) of a run, single-job or sharded."""
    remote = report.get("environment", {}).get("remote") or {}
    shards = remote.get("fleet") or []
    job_ids = [j for j in ([remote.get("job_id")] + [s.get("job_id") for s in shards]) if j]
    runner_vs = sorted({v for v in ([remote.get("runner_klt_version")]
                                    + [s.get("runner_klt_version") for s in shards]) if v})
    return job_ids, runner_vs


def report_only_ranges(report, row_of):
    """min and max over the grid of every passing measurement that carries no limit.

    A measurement with a margin is graded by klt and summarised in `rows`; one
    without is reported, not graded, so the record carries its range and the
    corner at each end.
    """
    ranges = {}
    for corner in report["corners"]:
        for m in corner["measurements"]:
            v = m.get("value")
            if m.get("status") == "pass" and m.get("margin") is None and isinstance(v, (int, float)):
                r = ranges.setdefault(m["name"], {"spec_row": row_of.get(m["name"]),
                                                  "min": (v, corner["corner_id"]),
                                                  "max": (v, corner["corner_id"])})
                r["min"] = min(r["min"], (v, corner["corner_id"]))
                r["max"] = max(r["max"], (v, corner["corner_id"]))
    return {n: {"spec_row": r["spec_row"], "min": list(r["min"]), "max": list(r["max"])}
            for n, r in sorted(ranges.items())}


def build(rec: Path, record, stamp, pdk_tag, klt_exit_code, fields_head, fields_tail, with_ranges):
    with gzip.open(rec / "report.json.gz", "rt") as fh:
        rep = json.load(fh)
    rows = json.loads((rec / "rows.json").read_text())["rows"]
    job_ids, runner_vs = job_identity(rep)

    out = {"record": record, "utc_stamp": stamp, "kind": "simulated"}
    out.update(fields_head)
    out["pdk"] = {"release_tag": pdk_tag}
    out["klt_exit_code"] = int(klt_exit_code)
    out["corners"] = len(rep["corners"])
    out["rows"] = {r: {k: v[k] for k in ("verdict", "pass", "fail", "error", "binding")}
                   for r, v in rows.items()}
    if with_ranges:
        # the report does not echo spec_row; the request declares it
        request = json.loads((rec / "request.json").read_text())
        row_of = {m["name"]: m["spec_row"] for m in request["measurements"] if "spec_row" in m}
        out["report_only_ranges"] = report_only_ranges(rep, row_of)
    out.update(fields_tail)
    out["batch_job_ids"] = job_ids
    out["runner_klt_version"] = runner_vs
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rec", help="record directory holding report.json.gz, rows.json, request.json")
    ap.add_argument("--record", required=True, help="family name written to the 'record' field")
    ap.add_argument("--stamp", required=True, help="UTC stamp of the run")
    ap.add_argument("--pdk-tag", required=True, help="PDK release tag (sim/pdk.json)")
    ap.add_argument("--klt-exit-code", required=True, type=int)
    ap.add_argument("--fields-head", default="{}",
                    help="JSON object of family fields placed after 'kind'")
    ap.add_argument("--fields-tail", default="{}",
                    help="JSON object of family fields placed after 'rows'")
    ap.add_argument("--report-only-ranges", action="store_true",
                    help="include the computed report_only_ranges block")
    args = ap.parse_args(argv)

    rec = Path(args.rec)
    out = build(rec, args.record, args.stamp, args.pdk_tag, args.klt_exit_code,
                json.loads(args.fields_head), json.loads(args.fields_tail),
                args.report_only_ranges)
    (rec / "record.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"record": f"records/{rec.name}",
                      "rows": {r: v["verdict"] for r, v in out["rows"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
