#!/usr/bin/env python3
"""The one write-or-check implementation the repo's file generators share.

Stdlib only; imported, never run. Every generator in `sim/` and `layout/` builds a
`path -> text` mapping and then either writes those files or, with `--check`, compares
them to the committed ones and fails if they differ. That loop was copied once per
generator, and the copies had drifted into three report formats, two output streams and
two ways of reading the flag: three of them tested `"--check" in argv`, so any other
argument meant "write" and a mistyped `--check` silently regenerated a stale tree
instead of reporting it (#227). `write_or_check` is that loop, once.

This module sits next to `sim/pvt_full.py`, which is already the repo's one encoding of
the PVT-FULL corner table and is already imported from both trees -- `layout/` reaches
`sim/` by a `sys.path` insert (`layout/pex/gen_pex_benches.py` does it too).

`seed` lives here for the same reason: `sim/mc/gen_mc.py` and `layout/lvs/gen_reference.py`
both derive a negative control by one anchored substitution, and both carried their own
byte-for-byte copy of it. So do `pwl` and `level_pwl`, the PWL stimulus builders the
clock-path, channel-eye and redundancy-mux generators had each copied (#256) -- the ramp
width and the stimulus end time are parameters here because that is all the three copies
differed in.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _display(path: Path) -> str:
    """`path` relative to the repo root when it is under it, so a report reads
    `STALE: sim/mc/request_t15.json` whatever directory the generator was run from."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def write_or_check(outputs, argv=None, base=None, description=None) -> int:
    """Write every generated file, or with `--check` report the stale ones.

    outputs:     {path -> text}. A relative path is resolved against `base`; an absolute
                 one is used as it is. Parent directories are created on write.
    argv:        the argument list, defaulting to `sys.argv[1:]`. Parsed with argparse, so
                 an unknown flag exits 2 having written nothing -- a mistyped `--check`
                 can never regenerate.
    base:        the directory relative output paths are resolved against.
    description: the parser's description, for `--help`.

    Returns 0 when the files were written or every one is fresh, and 1 when `--check`
    found a stale file. Each stale file is one `STALE: <path>` line on stderr; success is
    silent. Callers depend on the exit code, not on the report text.
    """
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if a generated file is stale, writing nothing")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    paths = []
    for key, text in outputs.items():
        path = Path(key)
        if not path.is_absolute():
            if base is None:
                raise ValueError(f"relative output {str(key)!r} needs a base directory")
            path = Path(base) / path
        paths.append((path, text))

    stale = []
    for path, text in paths:
        if args.check:
            if not path.exists() or path.read_text() != text:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    for path in stale:
        print(f"STALE: {_display(path)}", file=sys.stderr)
    return 1 if stale else 0


def pwl(points) -> str:
    """`points` as the body of a ngspice `pwl(...)` card: `(t_ps, level)` pairs, times in
    picoseconds, written in seconds to six significant figures."""
    return " ".join(f"{t * 1e-12:.6g} {v}" for t, v in points)


def level_pwl(edges, tr_ps, end_ps, init=0):
    """`(t_ps, level)` points for a piecewise-constant level sequence with ramped edges.

    edges:   [(start_ps, level)] -- each edge holds the level it was at until `start_ps`,
             then ramps to `level` over `tr_ps`. An empty list is a flat `init`.
    tr_ps:   the ramp width. A parameter, not a constant, because the stimulus that wants
             it is the generator's, not this module's.
    end_ps:  the stimulus end time; the last level is held out to it so the card covers
             the whole transient rather than ending at the final ramp.
    init:    the level at t = 0, before the first edge.
    """
    pts, cur = [(0, init)], init
    for t, v in edges:
        pts += [(t, cur), (t + tr_ps, v)]
        cur = v
    pts.append((end_ps, cur))
    return pts


def seed(text: str, old: str, new: str, what: str) -> str:
    """`text` with `old` replaced by `new`, which must match exactly once: a seeded defect.

    The anchor spans the line it changes (or the part of it the defect is in), so a source
    edit that moves it fails loudly here instead of silently producing a control with no
    defect, two defects, or a defect in the wrong place."""
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{what}: anchor {old!r} matched {n} times in its source, expected 1")
    return text.replace(old, new)
