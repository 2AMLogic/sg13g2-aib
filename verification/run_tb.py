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


def load_request(path: Path) -> dict:
    """Read a klt functional-verification request into the arguments cocotb needs.

    Paths resolve against the request file's own directory, as klt resolves them.
    """
    raw = path.read_text()
    if PLACEHOLDER.search(raw):
        raise Unsupported(f"{path} holds an unresolved placeholder "
                          f"({PLACEHOLDER.search(raw).group(0)}); it needs the PDK and the "
                          "pinned klt — run verification/klt/run_evidence.py")
    req = json.loads(raw)
    options = req.get("options", {})
    if "sdf" in options:
        raise Unsupported(f"{path} annotates an SDF; the post-route run needs the PDK and the "
                          "pinned klt — run verification/klt/run_evidence.py")
    engine = req.get("engine")
    if engine != "icarus":
        raise Unsupported(f"{path} asks for engine {engine!r}; this runner only drives icarus")

    here = path.parent
    testbench = req["testbench"]
    timescale = options.get("timescale", ["1ns", "1ps"])
    return dict(
        sources=[(here / s).resolve() for s in req["sources"]],
        toplevel=req["hdl_toplevel"],
        test_module=testbench["module"],
        test_dir=(here / testbench.get("search_path", ".")).resolve(),
        parameters=req.get("parameters", {}),
        defines=options.get("defines", {}),
        timescale=(timescale[0], timescale[1]),
        seed=options.get("random_seed", 1),
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
    except (OSError, json.JSONDecodeError, KeyError, Unsupported) as exc:
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
