#!/usr/bin/env python3
"""PDK-free runner for the cocotb + Icarus benches under verification/.

Local runner, not the gf180-polysynth one (see spec/decisions/0015-local-cocotb-runner.md).
It keeps that runner's exit contract:

    0  every test passed
    1  the suite ran and at least one test failed
    2  the suite did not run (build error, simulator error, no results)

A negative control must require exactly 1: a build or import error also exits
non-zero while proving nothing.

    python3 verification/run_tb.py
    python3 verification/run_tb.py --define INJECT_BUG_SHIFT_EDGE=1   # expect exit 1
    python3 verification/run_tb.py --bench datapath --param N=8
    python3 verification/run_tb.py --bench datapath --define INJECT_EXTRA_STAGE=1   # expect exit 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RTL = ROOT / "rtl"
BENCHES = {
    "shift_redundancy": dict(
        sources=[RTL / "shift_redundancy.v", HERE / "tb_top.v"],
        toplevel="tb_top", test_module="test_shift_redundancy"),
    "datapath": dict(
        sources=[RTL / "aib_tx_slice.v", RTL / "aib_rx_slice.v", RTL / "aib_datapath.v",
                 HERE / "tb_datapath.v"],
        toplevel="tb_datapath", test_module="test_datapath"),
}
DEFAULT_BENCH = "shift_redundancy"

EXIT_OK, EXIT_FAILED, EXIT_DID_NOT_RUN = 0, 1, 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--bench", choices=sorted(BENCHES), default=DEFAULT_BENCH)
    ap.add_argument("--param", action="append", default=[], metavar="NAME=VALUE",
                    help="toplevel parameter, e.g. N=8")
    ap.add_argument("--define", action="append", default=[], metavar="NAME[=VALUE]")
    ap.add_argument("--testcase", default=None)
    args = ap.parse_args(argv)

    try:
        from cocotb_tools.runner import get_results, get_runner
    except ImportError as exc:
        print(f"cocotb is not importable: {exc}", file=sys.stderr)
        return EXIT_DID_NOT_RUN

    defines: dict[str, object] = {}
    for item in args.define:
        name, _, value = item.partition("=")
        defines[name] = value or 1

    parameters: dict[str, object] = {}
    for item in args.param:
        name, _, value = item.partition("=")
        parameters[name] = int(value)

    bench = BENCHES[args.bench]
    sources, toplevel, test_module = bench["sources"], bench["toplevel"], bench["test_module"]
    build_dir = HERE / "sim_build"
    runner = get_runner("icarus")
    try:
        runner.build(verilog_sources=sources, defines=defines, parameters=parameters, hdl_toplevel=toplevel,
                     build_dir=build_dir, timescale=("1ns", "1ps"), always=True)
    except Exception as exc:
        print(f"the design did not build: {exc}", file=sys.stderr)
        return EXIT_DID_NOT_RUN

    # cocotb's runner overwrites PYTHONPATH with sys.path, so the test dir goes here.
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    try:
        results_xml = runner.test(hdl_toplevel=toplevel, test_module=test_module, test_dir=HERE,
                                  build_dir=build_dir, seed=args.seed, timescale=("1ns", "1ps"),
                                  testcase=args.testcase,
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
