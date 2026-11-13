#!/usr/bin/env python3
"""PDK-free runner for the cocotb + Icarus benches under verification/.

Local runner, not the gf180-polysynth one (see spec/decisions/0015-local-cocotb-runner.md).
It keeps that runner's exit contract:

    0  every test passed
    1  the suite ran and at least one test failed
    2  the suite did not run (build error, simulator error, no results)

A negative control must require exactly 1: a build or import error also exits
non-zero while proving nothing.

The bench is defined once, by a `klt functional-verification` request under
verification/klt/ — the same file the item 5 digital envelopes cite. This runner
reads the sources, top, test module, parameters, defines, timescale and seed
from it; there is no second copy of any of them here.

    python3 verification/run_tb.py                                       # shift redundancy
    python3 verification/run_tb.py verification/klt/neg_shift_edge.json  # expect exit 1
    python3 verification/run_tb.py verification/klt/datapath_n8.json
    python3 verification/run_tb.py verification/klt/neg_extra_stage.json # expect exit 1

A post-route request (`options.sdf`, or an unresolved `@PDK_ROOT@`-style
placeholder) needs the PDK and the pinned klt: it is refused here with exit 2
and stays with verification/klt/run_evidence.py.

Every other way a request can fail to load exits 2 as well -- a missing file,
malformed JSON, and a request that parses but is the wrong shape (a missing or
wrong-typed field). Exit 1 is reserved for a suite that ran and failed, which is
what a negative control requires, so a wrong-shaped neg_*.json must never reach
it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_REQUEST = HERE / "klt" / "shift_redundancy.json"
PLACEHOLDER = re.compile(r"@[A-Z][A-Z0-9_]*@")

EXIT_OK, EXIT_FAILED, EXIT_DID_NOT_RUN = 0, 1, 2


class Unsupported(Exception):
    """The request is well-formed but not something this runner can run."""


def _describe(value) -> str:
    """Name a JSON value's type the way the request file spells it."""
    for kind, name in ((bool, "a boolean"), (str, "a string"), (dict, "an object"),
                       (list, "an array"), (int, "a number"), (float, "a number")):
        if isinstance(value, kind):
            return name
    return "null" if value is None else repr(value)


def _require(ok: bool, path: Path, message: str) -> None:
    """Raise Unsupported unless `ok`, so the caller exits 2 rather than 1."""
    if not ok:
        raise Unsupported(f"{path}: {message}")


def load_request(path: Path) -> dict:
    """Read a klt functional-verification request into the arguments cocotb needs.

    Paths resolve against the request file's own directory, as klt resolves them.

    Every shape error raises Unsupported, so a request that is valid JSON but
    wrong-shaped exits 2 (the suite did not run) and never 1. That matters most
    for the negative controls: exit 1 is what `run_neg` requires, so a shape
    mistake in neg_shift_edge.json or neg_extra_stage.json must not be able to
    satisfy the control with the bench never built.
    """
    raw = path.read_text()
    if PLACEHOLDER.search(raw):
        raise Unsupported(f"{path} holds an unresolved placeholder "
                          f"({PLACEHOLDER.search(raw).group(0)}); it needs the PDK and the "
                          "pinned klt — run verification/klt/run_evidence.py")
    req = json.loads(raw)
    _require(isinstance(req, dict), path,
             f"the request is {_describe(req)}, expected an object")

    options = req.get("options", {})
    _require(isinstance(options, dict), path,
             f"options is {_describe(options)}, expected an object")
    if "sdf" in options:
        raise Unsupported(f"{path} annotates an SDF; the post-route run needs the PDK and the "
                          "pinned klt — run verification/klt/run_evidence.py")
    engine = req.get("engine")
    if engine != "icarus":
        raise Unsupported(f"{path} asks for engine {engine!r}; this runner only drives icarus")

    sources = req.get("sources")
    _require(isinstance(sources, list) and bool(sources), path,
             f"sources is {_describe(sources)}, expected a non-empty array")
    _require(all(isinstance(s, str) for s in sources), path,
             "every entry in sources must be a string")

    toplevel = req.get("hdl_toplevel")
    _require(isinstance(toplevel, str), path,
             f"hdl_toplevel is {_describe(toplevel)}, expected a string")

    testbench = req.get("testbench")
    _require(isinstance(testbench, dict), path,
             f"testbench is {_describe(testbench)}, expected an object")
    test_module = testbench.get("module")
    _require(isinstance(test_module, str), path,
             f"testbench.module is {_describe(test_module)}, expected a string")
    search_path = testbench.get("search_path", ".")
    _require(isinstance(search_path, str), path,
             f"testbench.search_path is {_describe(search_path)}, expected a string")

    parameters = req.get("parameters", {})
    _require(isinstance(parameters, dict), path,
             f"parameters is {_describe(parameters)}, expected an object")
    defines = options.get("defines", {})
    _require(isinstance(defines, dict), path,
             f"options.defines is {_describe(defines)}, expected an object")

    # Required, not defaulted. A fallback literal here would be a second copy of
    # a value the request file is supposed to be the only home for, and nothing
    # checks it against what klt assumes when the key is absent. All seven
    # committed requests set both.
    timescale = options.get("timescale")
    _require(isinstance(timescale, list) and len(timescale) == 2
             and all(isinstance(t, str) for t in timescale), path,
             f"options.timescale is {_describe(timescale)}, expected a two-string array "
             'such as ["1ns", "1ps"]')
    seed = options.get("random_seed")
    _require(isinstance(seed, int) and not isinstance(seed, bool), path,
             f"options.random_seed is {_describe(seed)}, expected an integer")

    here = path.parent
    return dict(
        sources=[(here / s).resolve() for s in sources],
        toplevel=toplevel,
        test_module=test_module,
        test_dir=(here / search_path).resolve(),
        parameters=parameters,
        defines=defines,
        timescale=(timescale[0], timescale[1]),
        seed=seed,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("request", nargs="?", type=Path, default=DEFAULT_REQUEST,
                    help="klt functional-verification request (default: %(default)s)")
    ap.add_argument("--seed", type=int, default=None,
                    help="override the request's options.random_seed")
    ap.add_argument("--testcase", default=None)
    args = ap.parse_args(argv)

    try:
        from cocotb_tools.runner import get_results, get_runner
    except ImportError as exc:
        print(f"cocotb is not importable: {exc}", file=sys.stderr)
        return EXIT_DID_NOT_RUN

    try:
        bench = load_request(args.request)
    # json.JSONDecodeError is a ValueError. The types beyond Unsupported are a
    # backstop: load_request validates the shape itself, and anything it still
    # lets through must exit 2 (did not run), never 1 (a test failed).
    except (OSError, ValueError, TypeError, AttributeError, IndexError, KeyError,
            Unsupported) as exc:
        print(f"the request did not load: {exc}", file=sys.stderr)
        return EXIT_DID_NOT_RUN

    toplevel, timescale = bench["toplevel"], bench["timescale"]
    build_dir = HERE / "sim_build"
    runner = get_runner("icarus")
    try:
        runner.build(verilog_sources=bench["sources"], defines=bench["defines"],
                     parameters=bench["parameters"], hdl_toplevel=toplevel,
                     build_dir=build_dir, timescale=timescale, always=True)
    except Exception as exc:
        print(f"the design did not build: {exc}", file=sys.stderr)
        return EXIT_DID_NOT_RUN

    # cocotb's runner overwrites PYTHONPATH with sys.path, so the test dir goes here.
    test_dir = bench["test_dir"]
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))
    try:
        results_xml = runner.test(hdl_toplevel=toplevel, test_module=bench["test_module"],
                                  test_dir=test_dir, build_dir=build_dir,
                                  seed=args.seed if args.seed is not None else bench["seed"],
                                  timescale=timescale, testcase=args.testcase,
                                  extra_env={"PYTHONDONTWRITEBYTECODE": "1"},
                                  results_xml=str(build_dir / "results.xml"))
    except Exception as exc:
        print(f"the simulator did not run: {exc}", file=sys.stderr)
        return EXIT_DID_NOT_RUN

    try:
        num_tests, num_failed = get_results(Path(results_xml))
    except (RuntimeError, OSError) as exc:
        print(f"the suite produced no results: {exc}", file=sys.stderr)
        return EXIT_DID_NOT_RUN
    print(f"icarus: {num_tests - num_failed}/{num_tests} passed", file=sys.stderr)
    if num_tests == 0:
        return EXIT_DID_NOT_RUN
    return EXIT_FAILED if num_failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
