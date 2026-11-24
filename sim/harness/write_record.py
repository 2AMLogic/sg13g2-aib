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
  python3 -I sim/harness/write_record.py REC --scrub-only

--scrub-only scrubs every .json and .json.gz in REC and exits, writing no record.json: the
one-line call for a record writer that does not go through batch_record.sh (sim/mc campaigns,
the rx-threshold mc leg, layout/pex), and for a record assembled by hand. Run it on a record
directory that is still being written, before it is committed.

Host paths: before anything is read, report.json.gz and rows.json in REC are scrubbed of
any string value that is a path into a user's home directory (/home, /Users, /root), the
one scrub every bench family inherits (#437).

REC must already hold report.json.gz, rows.json and request.json (the copy
batch_record.sh makes). Nothing outside REC is read or written, and REC itself
is never re-read once written: records are append-only evidence.

The key order of the emitted object is fixed:

  record, utc_stamp, kind, <--fields-head, in order>, pdk, klt_exit_code,
  corners, rows, [param_groups], [report_only_ranges], <--fields-tail, in order>,
  batch_job_ids, runner_klt_version

`param_groups` is carried through from rows.json when the post-processor emitted it,
which it does only for a request with a `corners.params` axis (T-12's channel +-20 %
R/C spread): the same per-row summary once per parameter corner, so the record says
which spread corner a verdict belongs to instead of pooling all of them.

Job ids: a single batch job reports environment.remote.job_id, a sharded one
reports environment.remote.fleet[]. Both are collected, so a sharded run (what
--max-units-per-job 1 always produces) records its ids instead of a null.
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

# A string value that is a path into some user's home directory. Matched by value over the
# whole JSON tree, never by field name: the fields that carry one (`client_ngspice_binary`,
# `ngspice_binary`, a PDK `path`) have already drifted past a per-field scrub once (#437).
# scripts/ci/check_no_host_paths.py re-implements this one regex on purpose, so the check
# stays independent of the scrub it polices.
HOST_PATH = re.compile(r"^/(?:home|Users|root)/[^/]+/(.*)$", re.DOTALL)
NGSPICE_PLACEHOLDER = "/usr/local/bin/ngspice"


def scrub_value(s):
    """The portable form of one string: a host-home path loses its home prefix."""
    m = HOST_PATH.match(s)
    if not m:
        return s
    if s.rsplit("/", 1)[-1] == "ngspice":
        return NGSPICE_PLACEHOLDER
    return "<home>/" + m.group(1)


def scrub_host_paths(obj):
    """`obj` with every host-home path string rewritten, recursing through dicts and lists."""
    if isinstance(obj, dict):
        return {k: scrub_host_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_host_paths(v) for v in obj]
    if isinstance(obj, str):
        return scrub_value(obj)
    return obj


def scrub_json_file(path: Path):
    """Scrub one .json or .json.gz file in place; a file with nothing to scrub stays byte-identical."""
    gz = path.name.endswith(".gz")
    raw = gzip.decompress(path.read_bytes()) if gz else path.read_bytes()
    doc = json.loads(raw)
    clean = scrub_host_paths(doc)
    if clean == doc:
        return
    out = json.dumps(clean, indent=2).encode() + b"\n"
    if gz:
        # mtime=0: the same report always compresses to the same bytes
        with open(path, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as fh:
            fh.write(out)
    else:
        path.write_bytes(out)


def scrub_record_files(rec: Path):
    """Scrub the record's own report.json.gz and rows.json in place, before anything is read.

    Only called on a record directory that is still being written; a committed record is
    never passed here.
    """
    scrub_json_file(rec / "report.json.gz")
    scrub_json_file(rec / "rows.json")


def scrub_record_dir(rec: Path):
    """Scrub every .json and .json.gz directly in REC (the --scrub-only entry point).

    For the record writers that do not go through batch_record.sh (the mc campaign, the
    rx-threshold mc leg, layout/pex). A file that is not a JSON document is left alone.
    Returns the names rewritten.
    """
    changed = []
    for p in sorted(rec.iterdir()):
        if p.is_file() and (p.name.endswith(".json") or p.name.endswith(".json.gz")):
            before = p.read_bytes()
            try:
                scrub_json_file(p)
            except (ValueError, OSError):
                continue
            if p.read_bytes() != before:
                changed.append(p.name)
    return changed


def job_identity(report):
    """(job ids, runner klt versions) of a run, single-job or sharded.

    A `fleet` entry may be null (a shard the report carries a placeholder for,
    e.g. a unit-level error row); those are skipped, not dereferenced -- the
    rx-threshold study's t16-mixed leg lost an otherwise complete record to the
    AttributeError on one (issue #386).
    """
    remote = report.get("environment", {}).get("remote") or {}
    shards = [s for s in (remote.get("fleet") or []) if isinstance(s, dict)]
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


ROW_FIELDS = ("verdict", "pass", "fail", "error", "binding")


def row_summaries(rows):
    """The record's view of a rows.json row map: the graded fields, measurements aside."""
    return {r: {k: v[k] for k in ROW_FIELDS} for r, v in rows.items()}


def build(rec: Path, record, stamp, pdk_tag, klt_exit_code, fields_head, fields_tail, with_ranges):
    with gzip.open(rec / "report.json.gz", "rt") as fh:
        rep = json.load(fh)
    rows_doc = json.loads((rec / "rows.json").read_text())
    rows = rows_doc["rows"]
    job_ids, runner_vs = job_identity(rep)

    out = {"record": record, "utc_stamp": stamp, "kind": "simulated"}
    out.update(fields_head)
    out["pdk"] = {"release_tag": pdk_tag}
    out["klt_exit_code"] = int(klt_exit_code)
    out["corners"] = len(rep["corners"])
    out["rows"] = row_summaries(rows)
    if rows_doc.get("param_groups"):
        # present only for a request with a `corners.params` axis; the pooled `rows`
        # above cannot say which parameter corner a verdict belongs to
        out["param_groups"] = {g: {"corners": v["corners"], "rows": row_summaries(v["rows"])}
                               for g, v in rows_doc["param_groups"].items()}
    if with_ranges:
        # the report does not echo spec_row; the request declares it -- and a request may
        # declare none at all (#281: request_esd_diode.json has no `measurements` key),
        # which leaves every range's spec_row null instead of raising
        request = json.loads((rec / "request.json").read_text())
        row_of = {m["name"]: m["spec_row"] for m in request.get("measurements", []) if "spec_row" in m}
        out["report_only_ranges"] = report_only_ranges(rep, row_of)
    out.update(fields_tail)
    out["batch_job_ids"] = job_ids
    out["runner_klt_version"] = runner_vs
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rec", help="record directory holding report.json.gz, rows.json, request.json")
    ap.add_argument("--scrub-only", action="store_true",
                    help="scrub host paths from every .json/.json.gz in REC and exit")
    ap.add_argument("--record", help="family name written to the 'record' field")
    ap.add_argument("--stamp", help="UTC stamp of the run")
    ap.add_argument("--pdk-tag", help="PDK release tag (sim/pdk.json)")
    ap.add_argument("--klt-exit-code", type=int)
    ap.add_argument("--fields-head", default="{}",
                    help="JSON object of family fields placed after 'kind'")
    ap.add_argument("--fields-tail", default="{}",
                    help="JSON object of family fields placed after 'rows'")
    ap.add_argument("--report-only-ranges", action="store_true",
                    help="include the computed report_only_ranges block")
    args = ap.parse_args(argv)

    rec = Path(args.rec)
    if args.scrub_only:
        for name in scrub_record_dir(rec):
            print(f"scrubbed {rec.name}/{name}")
        return 0
    missing = [f for f in ("record", "stamp", "pdk_tag", "klt_exit_code") if getattr(args, f) is None]
    if missing:
        ap.error("required unless --scrub-only: " + ", ".join("--" + m.replace("_", "-") for m in missing))
    scrub_record_files(rec)
    out = build(rec, args.record, args.stamp, args.pdk_tag, args.klt_exit_code,
                json.loads(args.fields_head), json.loads(args.fields_tail),
                args.report_only_ranges)
    (rec / "record.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"record": f"records/{rec.name}",
                      "rows": {r: v["verdict"] for r, v in out["rows"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
