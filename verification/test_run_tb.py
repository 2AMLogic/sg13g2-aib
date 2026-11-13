#!/usr/bin/env python3
"""Self-test for the request loader in verification/run_tb.py.

The contract under test is the DR-0015 exit code, not the benches: a request
that does not load must exit 2 (the suite did not run), never 1 (the suite ran
and a test failed). Exit 1 is what `run_neg` in scripts/ci/check_local.sh
requires of a negative control, so if a wrong-shaped neg_*.json could produce
it, the control would pass with the bench never built -- the "exits non-zero
while proving nothing" case DR-0015 exists to rule out.

It also covers the unknown-key refusal (issue #231): a request key the runner
does not read exits 2 rather than being ignored, so the bench the item 5 digital
envelopes cite cannot drift from the bench a green `rtl` job runs.

No PDK, no klt, and no cocotb needed for the loader cases.

    python3 -I verification/test_run_tb.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I implies -P, so the script dir is not on sys.path

import run_tb  # noqa: E402

KLT = HERE / "klt"
RUNNABLE = ("shift_redundancy", "datapath_n8", "datapath_n20",
            "neg_shift_edge", "neg_extra_stage")
REFUSED = ("post_route", "neg_post_route_timing")

VALID = {
    "schema": "klt.functional_verification.request/1",
    "engine": "icarus",
    "sources": ["../../rtl/shift_redundancy.v", "../tb_top.v"],
    "hdl_toplevel": "tb_top",
    "testbench": {"module": "test_shift_redundancy", "search_path": ".."},
    "options": {"timescale": ["1ns", "1ps"], "random_seed": 1},
}

# (label, mutation) -- each produces valid JSON that is the wrong shape.
# `None` as a value means "delete this key".
WRONG_SHAPES = [
    ("top level is an array", [1, 2]),
    ("top level is a string", "shift_redundancy"),
    ("top level is null", None),
    ("top level is a number", 3),
]

MUTATIONS = [
    ("sources missing", lambda r: r.pop("sources")),
    ("sources is a string", lambda r: r.__setitem__("sources", "../tb_top.v")),
    ("sources is empty", lambda r: r.__setitem__("sources", [])),
    ("sources holds a non-string", lambda r: r.__setitem__("sources", ["a.v", 7])),
    ("hdl_toplevel missing", lambda r: r.pop("hdl_toplevel")),
    ("hdl_toplevel is a list", lambda r: r.__setitem__("hdl_toplevel", ["tb_top"])),
    ("testbench missing", lambda r: r.pop("testbench")),
    ("testbench is a string", lambda r: r.__setitem__("testbench", "m")),
    ("testbench is an array", lambda r: r.__setitem__("testbench", ["m"])),
    ("testbench.module missing", lambda r: r["testbench"].pop("module")),
    ("testbench.module is a number", lambda r: r["testbench"].__setitem__("module", 1)),
    ("testbench.search_path is a number",
     lambda r: r["testbench"].__setitem__("search_path", 2)),
    ("parameters is an array", lambda r: r.__setitem__("parameters", [])),
    ("options is null", lambda r: r.__setitem__("options", None)),
    ("options is an array", lambda r: r.__setitem__("options", [])),
    ("options.defines is an array", lambda r: r["options"].__setitem__("defines", [])),
    ("options.timescale missing", lambda r: r["options"].pop("timescale")),
    ("options.timescale has one entry",
     lambda r: r["options"].__setitem__("timescale", ["1ns"])),
    ("options.timescale has three entries",
     lambda r: r["options"].__setitem__("timescale", ["1ns", "1ps", "1fs"])),
    ("options.timescale is a string",
     lambda r: r["options"].__setitem__("timescale", "1ns")),
    ("options.timescale holds a non-string",
     lambda r: r["options"].__setitem__("timescale", ["1ns", 1])),
    ("options.random_seed missing", lambda r: r["options"].pop("random_seed")),
    ("options.random_seed is a string",
     lambda r: r["options"].__setitem__("random_seed", "1")),
    ("options.random_seed is a boolean",
     lambda r: r["options"].__setitem__("random_seed", True)),
    ("options.random_seed is a float",
     lambda r: r["options"].__setitem__("random_seed", 1.5)),
]

# (label, mutation, name) -- each adds a key load_request does not read, and
# `name` is the path-qualified key the refusal must name. The first three are the
# ones reported on issue #231. `testbench.testcase`, `options.includes`,
# `options.coverage`, `options.trace`, `options.build_args` and
# `options.initial_state` are keys the pinned klt itself honours, which is what
# makes an ignored key drift rather than a harmless typo; `simulator`, `module`
# and `testbench.toplevel_lang` stand for the misplaced/misspelled class.
UNKNOWN_KEYS = [
    ("testbench.testcase",
     lambda r: r["testbench"].__setitem__("testcase", "no_such_test"),
     "testbench.testcase"),
    ("options.includes",
     lambda r: r["options"].__setitem__("includes", ["/nonexistent"]),
     "options.includes"),
    ("options.plusargs",
     lambda r: r["options"].__setitem__("plusargs", ["+x"]), "options.plusargs"),
    ("top-level unknown key",
     lambda r: r.__setitem__("simulator", "icarus"), "simulator"),
    ("top-level key spelled like a nested one",
     lambda r: r.__setitem__("module", "test_shift_redundancy"), "module"),
    ("testbench unknown key",
     lambda r: r["testbench"].__setitem__("toplevel_lang", "verilog"),
     "testbench.toplevel_lang"),
    ("options.coverage",
     lambda r: r["options"].__setitem__("coverage", True), "options.coverage"),
    ("options.trace", lambda r: r["options"].__setitem__("trace", True), "options.trace"),
    ("options.build_args",
     lambda r: r["options"].__setitem__("build_args", ["-g2012"]), "options.build_args"),
    ("options.initial_state",
     lambda r: r["options"].__setitem__("initial_state", "x"), "options.initial_state"),
]

# Every key the three allow-lists permit, all at once: the allow-lists must not
# be narrower than what load_request reads, or a committed request would be
# refused for a key the runner honours.
EVERY_ALLOWED_KEY = {
    "schema": "klt.functional_verification.request/1",
    "engine": "icarus",
    "sources": ["../../rtl/shift_redundancy.v", "../tb_top.v"],
    "hdl_toplevel": "tb_top",
    "testbench": {"module": "test_shift_redundancy", "search_path": ".."},
    "parameters": {"N": 8},
    "options": {"timescale": ["1ns", "1ps"], "random_seed": 1, "defines": {"FOO": 1}},
}


def load_obj(obj, directory: Path):
    """Write `obj` as a request in `directory` and load it."""
    path = directory / "request.json"
    path.write_text(json.dumps(obj))
    return run_tb.load_request(path)


class LoaderRejectsWrongShapes(unittest.TestCase):
    """Nothing but Unsupported escapes load_request for a wrong-shaped request."""

    def test_wrong_top_level_types(self):
        with tempfile.TemporaryDirectory() as d:
            for label, obj in WRONG_SHAPES:
                with self.subTest(label), self.assertRaises(run_tb.Unsupported):
                    load_obj(obj, Path(d))

    def test_wrong_field_shapes(self):
        with tempfile.TemporaryDirectory() as d:
            for label, mutate in MUTATIONS:
                req = copy.deepcopy(VALID)
                mutate(req)
                with self.subTest(label), self.assertRaises(run_tb.Unsupported):
                    load_obj(req, Path(d))

    def test_the_unmutated_base_loads(self):
        """Guards the table above: the cases must fail for their mutation alone."""
        with tempfile.TemporaryDirectory() as d:
            bench = load_obj(copy.deepcopy(VALID), Path(d))
        self.assertEqual(bench["toplevel"], "tb_top")
        self.assertEqual(bench["timescale"], ("1ns", "1ps"))
        self.assertEqual(bench["seed"], 1)

    def test_committed_wrong_shape_fixture(self):
        """The fixture check_local.sh asserts exit 2 on is genuinely wrong-shaped."""
        fixture = HERE / "testdata/wrong_shape_request.json"
        json.loads(fixture.read_text())  # valid JSON, so exit 2 is about the shape
        with self.assertRaises(run_tb.Unsupported):
            run_tb.load_request(fixture)


class LoaderRejectsUnknownKeys(unittest.TestCase):
    """A key klt honours and this runner ignores must not load (issue #231).

    #217 made the request file the only bench definition so a green `rtl` job
    runs what the item 5 digital envelopes cite. A key the runner silently
    ignores reintroduces exactly that drift, so it exits 2 rather than warning.
    """

    def test_unknown_keys_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for label, mutate, _name in UNKNOWN_KEYS:
                req = copy.deepcopy(VALID)
                mutate(req)
                with self.subTest(label), self.assertRaises(run_tb.Unsupported):
                    load_obj(req, Path(d))

    def test_the_refusal_names_the_key_with_its_path(self):
        """`options.includes`, not `includes`: the message says where to look."""
        with tempfile.TemporaryDirectory() as d:
            for label, mutate, name in UNKNOWN_KEYS:
                req = copy.deepcopy(VALID)
                mutate(req)
                with self.subTest(label):
                    with self.assertRaises(run_tb.Unsupported) as caught:
                        load_obj(req, Path(d))
                    self.assertIn(name, str(caught.exception))

    def test_every_allowed_key_still_loads(self):
        """Guards the allow-lists against being narrower than what is read."""
        with tempfile.TemporaryDirectory() as d:
            bench = load_obj(copy.deepcopy(EVERY_ALLOWED_KEY), Path(d))
        self.assertEqual(bench["parameters"], {"N": 8})
        self.assertEqual(bench["defines"], {"FOO": 1})

    def test_the_allow_lists_are_what_load_request_reads(self):
        """A key added to an allow-list without being read would reopen the gap."""
        self.assertEqual(run_tb.ALLOWED_TOP, frozenset(EVERY_ALLOWED_KEY))
        self.assertEqual(run_tb.ALLOWED_TESTBENCH,
                         frozenset(EVERY_ALLOWED_KEY["testbench"]))
        self.assertEqual(run_tb.ALLOWED_OPTIONS,
                         frozenset(EVERY_ALLOWED_KEY["options"]))

    def test_the_sdf_refusal_still_wins(self):
        """options.sdf is itself an unknown key; its own message is the useful one."""
        for label, mutate, _name in UNKNOWN_KEYS:
            req = copy.deepcopy(VALID)
            mutate(req)
            req["options"]["sdf"] = "../../pnr/out/routed.sdf"
            with tempfile.TemporaryDirectory() as d, self.subTest(label):
                with self.assertRaises(run_tb.Unsupported) as caught:
                    load_obj(req, Path(d))
                self.assertIn("annotates an SDF", str(caught.exception))

    def test_the_placeholder_refusal_still_wins(self):
        req = copy.deepcopy(VALID)
        req["testbench"]["testcase"] = "no_such_test"
        req["sources"] = ["@PDK_ROOT@/tb_top.v"]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(run_tb.Unsupported) as caught:
                load_obj(req, Path(d))
        self.assertIn("unresolved placeholder", str(caught.exception))


class LoaderAcceptsTheCommittedRequests(unittest.TestCase):
    """The requests under verification/klt/ are the only bench definition."""

    def test_runnable_requests_load(self):
        for stem in RUNNABLE:
            with self.subTest(stem):
                bench = run_tb.load_request(KLT / f"{stem}.json")
                self.assertTrue(bench["sources"])
                self.assertTrue(bench["toplevel"])
                self.assertTrue(bench["test_module"])
                self.assertEqual(len(bench["timescale"]), 2)

    def test_post_route_requests_are_refused(self):
        for stem in REFUSED:
            with self.subTest(stem), self.assertRaises(run_tb.Unsupported):
                run_tb.load_request(KLT / f"{stem}.json")

    def test_every_committed_request_is_covered(self):
        """A new request under klt/ must be classified here, not silently skipped."""
        self.assertEqual(sorted(p.stem for p in KLT.glob("*.json")),
                         sorted(RUNNABLE + REFUSED))


def cocotb_available():
    try:
        import cocotb_tools.runner  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(cocotb_available(), "needs cocotb; the rtl lane has it")
class MainReturnsTwo(unittest.TestCase):
    """End to end: the exit code, not just the exception."""

    def test_missing_file(self):
        self.assertEqual(run_tb.main([str(HERE / "testdata/does_not_exist.json")]), 2)

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.json"
            bad.write_text("not json at all")
            self.assertEqual(run_tb.main([str(bad)]), 2)

    def test_wrong_shape_fixture(self):
        self.assertEqual(run_tb.main([str(HERE / "testdata/wrong_shape_request.json")]), 2)

    def test_every_wrong_shape(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "request.json"
            for label, mutate in MUTATIONS:
                req = copy.deepcopy(VALID)
                mutate(req)
                path.write_text(json.dumps(req))
                with self.subTest(label):
                    self.assertEqual(run_tb.main([str(path)]), 2)

    def test_every_unknown_key(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "request.json"
            for label, mutate, _name in UNKNOWN_KEYS:
                req = copy.deepcopy(VALID)
                mutate(req)
                path.write_text(json.dumps(req))
                with self.subTest(label):
                    self.assertEqual(run_tb.main([str(path)]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
