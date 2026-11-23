#!/usr/bin/env python3
"""Self-tests of the sim and generator infrastructure: the one PVT-FULL corner
table, the shared write-or-check helper and the clock-path structure check.

Stdlib only; PDK-free. Run alone: python3 -I scripts/ci/test_sim_infra.py
python3 -I drops this directory from sys.path, hence the insert below (the
check_record_not_ignored.py idiom).
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _checker_test_helpers import HERE, REPO, run  # noqa: E402

CORNERS = HERE / "check_corner_bundles.py"
HOSTPATHS = HERE / "check_no_host_paths.py"


class HostPathTests(unittest.TestCase):
    """check_no_host_paths.py: a host path in a committed record fails, a baselined one passes."""

    def tree(self, root, doc, gz=True):
        import gzip
        d = root / "sim/fam/records/20260101T000000Z"
        d.mkdir(parents=True)
        if gz:
            (d / "report.json.gz").write_bytes(gzip.compress(json.dumps(doc).encode()))
        else:
            (d / "report.json").write_text(json.dumps(doc))
        return d

    def check(self, root, baseline=()):
        b = root / "baseline.json"
        b.write_text(json.dumps({"files": list(baseline)}))
        return run(HOSTPATHS, "--root", root, "--baseline", b)

    def test_the_repository_passes_today(self):
        self.assertEqual(run(HOSTPATHS).returncode, 0)

    def test_a_clean_record_passes(self):
        with tempfile.TemporaryDirectory() as t:
            self.tree(Path(t), {"environment": {"ngspice_binary": "/usr/local/bin/ngspice",
                                                "scratch": "/tmp/x/y.json"}})
            self.assertEqual(self.check(Path(t)).returncode, 0)

    def test_a_host_path_fails_naming_file_and_json_path(self):
        for gz in (True, False):
            with tempfile.TemporaryDirectory() as t:
                self.tree(Path(t), {"environment": {"c": [{"client_ngspice_binary": "/home/u/.local/bin/ngspice"}]}}, gz)
                r = self.check(Path(t))
                self.assertEqual(r.returncode, 1)
                self.assertIn("/environment/c/0/client_ngspice_binary", r.stderr)
                self.assertIn("records/20260101T000000Z/report.json", r.stderr)

    def test_a_macos_home_path_fails_too(self):
        with tempfile.TemporaryDirectory() as t:
            self.tree(Path(t), {"p": "/Users/dev/pdk/x.lib"})
            self.assertEqual(self.check(Path(t)).returncode, 1)

    def test_a_baselined_offender_passes_and_a_stale_entry_fails(self):
        with tempfile.TemporaryDirectory() as t:
            self.tree(Path(t), {"p": "/home/u/x/y"})
            rel = "sim/fam/records/20260101T000000Z/report.json.gz"
            self.assertEqual(self.check(Path(t), [rel]).returncode, 0)
            self.assertEqual(self.check(Path(t), [rel, "sim/fam/records/gone/report.json.gz"]).returncode, 1)


class CornerBundleTests(unittest.TestCase):
    """Every committed request under sim/ or layout/ agrees with the PVT-FULL table."""

    def bundle(self, corner, res, dio):
        return {"name": corner, "sections": [
            {"lib": "libs.tech/ngspice/models/cornerMOSlv.lib", "section": "mos_" + corner},
            {"lib": "libs.tech/ngspice/models/cornerRES.lib", "section": res},
            {"lib": "libs.tech/ngspice/models/cornerDIO.lib", "section": dio}]}

    def check(self, corners):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "sim/fam").mkdir(parents=True)
            (root / "sim/fam/request.json").write_text(json.dumps({"corners": corners}))
            return run(CORNERS, "--root", root).returncode

    def grid(self, *bundles, supply=None, temps=None):
        return {"process": list(bundles),
                "supply_v": {"vddio": supply or [1.08, 1.2, 1.32]},
                "temperature_c": temps or [-40, 27, 125]}

    def test_the_repo_conforms(self):
        self.assertEqual(run(CORNERS, "--root", REPO).returncode, 0)

    def test_matching_bundle_passes(self):
        self.assertEqual(self.check(self.grid(self.bundle("ss", "res_wcs", "dio_ss"))), 0)

    def test_reduced_grid_passes(self):
        self.assertEqual(self.check(self.grid(self.bundle("tt", "res_typ", "dio_tt"),
                                              supply=[1.2], temps=[27])), 0)

    def test_held_diode_section_fails(self):
        # the drift of #184: dio_tt kept at a slow/fast MOS corner
        self.assertNotEqual(self.check(self.grid(self.bundle("ss", "res_wcs", "dio_tt"))), 0)
        self.assertNotEqual(self.check(self.grid(self.bundle("ff", "res_bcs", "dio_tt"))), 0)

    def test_wrong_resistor_section_fails(self):
        self.assertNotEqual(self.check(self.grid(self.bundle("ss", "res_typ", "dio_ss"))), 0)

    def test_missing_diode_section_fails(self):
        b = self.bundle("ss", "res_wcs", "dio_ss")
        del b["sections"][2]
        self.assertNotEqual(self.check(self.grid(b)), 0)

    def test_off_grid_supply_or_temperature_fails(self):
        good = self.bundle("tt", "res_typ", "dio_tt")
        self.assertNotEqual(self.check(self.grid(good, supply=[1.0, 1.2, 1.32])), 0)
        self.assertNotEqual(self.check(self.grid(good, temps=[-40, 25, 125])), 0)

    def test_records_are_not_checked(self):
        # append-only evidence keeps the request it ran with
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = root / "sim/fam/records/20260101T000000Z"
            d.mkdir(parents=True)
            (d / "request.json").write_text(json.dumps(
                {"corners": self.grid(self.bundle("ss", "res_wcs", "dio_tt"))}))
            self.assertEqual(run(CORNERS, "--root", root).returncode, 0)

    def test_layout_requests_are_checked(self):
        # #81: the item 7 pex benches carry the same corner object as item 5's,
        # so a held dio_tt there is the same #184 defect in a second tree.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "layout/pex/benches").mkdir(parents=True)
            (root / "layout/pex/benches/request_dc_static_top.json").write_text(json.dumps(
                {"corners": self.grid(self.bundle("ss", "res_wcs", "dio_tt"))}))
            r = run(CORNERS, "--root", root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("dio_tt", r.stdout + r.stderr)

    def test_layout_records_are_not_checked(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = root / "layout/pex/records/20260101T000000Z"
            d.mkdir(parents=True)
            (d / "request_dc_static_top.json").write_text(json.dumps(
                {"corners": self.grid(self.bundle("ss", "res_wcs", "dio_tt"))}))
            self.assertEqual(run(CORNERS, "--root", root).returncode, 0)

    def test_no_request_tree_at_all_is_an_error(self):
        # a root with neither sim/ nor layout/ is a mis-invocation, not a pass
        with tempfile.TemporaryDirectory() as t:
            self.assertNotEqual(run(CORNERS, "--root", Path(t)).returncode, 0)

    def test_unparseable_json_is_reported_not_skipped(self):
        # a malformed request must not pass the check unexamined
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "sim/fam").mkdir(parents=True)
            (root / "sim/fam/request.json").write_text("{not json")
            r = run(CORNERS, "--root", root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("not readable as JSON", r.stdout + r.stderr)


class PvtFullTableTests(unittest.TestCase):
    """The shared table emits both request shapes the benches use."""

    def setUp(self):
        sys.path.insert(0, str(REPO / "sim"))
        import pvt_full
        self.pvt = pvt_full

    def test_45_unit_grid(self):
        c = self.pvt.corners(["vddio"])
        units = len(c["process"]) * len(c["supply_v"]["vddio"]) * len(c["temperature_c"])
        self.assertEqual(units, self.pvt.N_UNITS)
        self.assertEqual(units, 45)

    def test_inline_shape_is_the_transient_bench_shape(self):
        e = self.pvt.process()[1]
        self.assertEqual(e["name"], "mos_ss")
        self.assertEqual(e["sections"][0], "mos_ss")
        self.assertEqual([s["section"] for s in e["sections"][1:]], ["res_wcs", "dio_ss"])

    def test_explicit_mismatch_shape_is_the_monte_carlo_shape(self):
        e = self.pvt.process(style="explicit", mismatch=True)[1]
        self.assertEqual(e["name"], "ss")
        self.assertEqual(e["sections"][0], {"lib": self.pvt.LIB_MOS, "section": "mos_ss_mismatch"})
        self.assertEqual([s["section"] for s in e["sections"][1:]], ["res_wcs", "dio_ss"])

    def test_diode_follows_the_mos_corner(self):
        # sim/README.md: the resistor and diode sections follow the MOS corner
        self.assertEqual({c: d for c, (_, d) in self.pvt.PROCESS.items()},
                         {"tt": "dio_tt", "ss": "dio_ss", "ff": "dio_ff",
                          "sf": "dio_tt", "fs": "dio_tt"})
    def test_only_shape_restricts_the_grid(self):
        self.assertEqual([e["name"] for e in self.pvt.process(only=("tt",))], ["mos_tt"])

    def test_unknown_style_is_refused(self):
        with self.assertRaises(ValueError):
            self.pvt.process(style="sections")


class WriteOrCheckHelperTests(unittest.TestCase):
    """sim/gen_common.py is the one write-or-check implementation the generators share (#227)."""

    def setUp(self):
        sys.path.insert(0, str(REPO / "sim"))
        import gen_common
        self.gc = gen_common

    def test_write_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            rc = self.gc.write_or_check({"neg/a.txt": "x\n", "b.txt": "y\n"}, [], base=base)
            self.assertEqual(rc, 0)
            self.assertEqual((base / "neg/a.txt").read_text(), "x\n")
            self.assertEqual((base / "b.txt").read_text(), "y\n")

    def test_an_absolute_output_path_needs_no_base(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "sub" / "a.txt"
            self.assertEqual(self.gc.write_or_check({p: "x\n"}, []), 0)
            self.assertEqual(p.read_text(), "x\n")

    def test_check_is_quiet_and_zero_when_every_file_is_fresh(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            self.gc.write_or_check({"a.txt": "x\n"}, [], base=base)
            err, out = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = self.gc.write_or_check({"a.txt": "x\n"}, ["--check"], base=base)
            self.assertEqual(rc, 0)
            self.assertEqual(err.getvalue() + out.getvalue(), "")

    def test_check_names_each_stale_file_on_stderr_and_returns_1(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            self.gc.write_or_check({"a.txt": "x\n", "b.txt": "y\n"}, [], base=base)
            (base / "a.txt").write_text("edited\n")          # content drift
            (base / "b.txt").unlink()                        # missing entirely
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = self.gc.write_or_check({"a.txt": "x\n", "b.txt": "y\n"}, ["--check"], base=base)
            self.assertEqual(rc, 1)
            self.assertEqual(err.getvalue().count("STALE:"), 2)
            self.assertIn("a.txt", err.getvalue())
            self.assertIn("b.txt", err.getvalue())

    def test_check_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            with contextlib.redirect_stderr(io.StringIO()):
                rc = self.gc.write_or_check({"a.txt": "x\n"}, ["--check"], base=base)
            self.assertEqual(rc, 1)
            self.assertFalse((base / "a.txt").exists())

    def test_a_stale_file_under_the_repo_is_named_relative_to_it(self):
        # --check writes nothing, so naming a path that does not exist is safe here.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = self.gc.write_or_check({"no_such_generated_file": "x"}, ["--check"], base=REPO / "sim")
        self.assertEqual(rc, 1)
        self.assertIn("STALE: sim/no_such_generated_file", err.getvalue())

    def test_an_unknown_flag_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    self.gc.write_or_check({"a.txt": "x\n"}, ["--chek"], base=base)
            self.assertEqual(cm.exception.code, 2)
            self.assertFalse((base / "a.txt").exists())

    def test_a_relative_output_without_a_base_is_refused(self):
        with self.assertRaises(ValueError):
            self.gc.write_or_check({"a.txt": "x\n"}, [])

    def test_seed_substitutes_an_anchor_that_matches_exactly_once(self):
        self.assertEqual(self.gc.seed("a b c", "b", "B", "what"), "a B c")

    def test_seed_refuses_an_anchor_that_does_not_match_once(self):
        for text, anchor, n in (("a b c", "zz", 0), ("a b b", "b", 2)):
            with self.assertRaises(SystemExit) as cm:
                self.gc.seed(text, anchor, "X", "what")
            self.assertIn(f"matched {n} times", str(cm.exception))
            self.assertIn("what", str(cm.exception))

    # -- the shared PWL builders (#256) --------------------------------------

    def test_pwl_writes_picosecond_times_in_seconds(self):
        self.assertEqual(self.gc.pwl([(0, 0), (500, 1)]), "0 0 5e-10 1")

    def test_level_pwl_ramps_each_edge_over_tr_and_holds_to_the_end(self):
        # One edge to 1 at 500 ps, a 100 ps ramp, a 2000 ps stimulus.
        self.assertEqual(self.gc.level_pwl([(500, 1)], 100, 2000),
                         [(0, 0), (500, 0), (600, 1), (2000, 1)])

    def test_level_pwl_starts_from_init(self):
        self.assertEqual(self.gc.level_pwl([(500, 0)], 100, 2000, init=1),
                         [(0, 1), (500, 1), (600, 0), (2000, 0)])

    def test_level_pwl_holds_a_flat_level_across_the_whole_span(self):
        self.assertEqual(self.gc.level_pwl([], 100, 2000, init=1), [(0, 1), (2000, 1)])

    def test_level_pwl_ramp_width_is_the_tr_that_was_passed(self):
        # The parameter is why one helper can serve stimuli with different ramps.
        for tr in (50, 100, 250):
            self.assertEqual(self.gc.level_pwl([(500, 1)], tr, 2000)[2], (500 + tr, 1))


class ClkPairStructureTests(unittest.TestCase):
    """sim/clock-path/check_clk_pair.py (DR-0027): passes on the committed netlists and fails
    when the clkb leg is broken at the TX cell, the channel or the RX cell."""

    SCRIPT = REPO / "sim/clock-path/check_clk_pair.py"
    FILES = ("design/aib_tx_clk.spice", "design/aib_rx_clk.spice", "sim/clock-path/tb_clock_path.cir")

    def check(self, rel=None, old=None, new=None, edits=()):
        edits = list(edits) + ([(rel, old, new)] if rel else [])
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for f in self.FILES:
                (root / f).parent.mkdir(parents=True, exist_ok=True)
                text = (REPO / f).read_text()
                for r, o, n in edits:
                    if f == r:
                        self.assertIn(o, text)
                        text = text.replace(o, n)
                (root / f).write_text(text)
            return run(self.SCRIPT, "--root", root).returncode

    def test_committed_netlists_pass(self):
        self.assertEqual(self.check(), 0)

    def test_clkb_cut_in_the_channel_fails(self):
        self.assertEqual(self.check(self.FILES[2], "Xlcb  txpcb rxpcb 0 link", "Xlcb  txpcb nc 0 link"), 1)

    def test_clkb_pad_shorted_to_clk_in_the_tx_cell_fails(self):
        self.assertEqual(self.check(self.FILES[0], "Xclkb CLKB_D OE PUN PD CLKB_PAD", "Xclkb CLKB_D OE PUN PD CLK_PAD"), 1)

    def test_rx_clkb_output_unconverted_fails(self):
        self.assertEqual(self.check(self.FILES[1], "Xclkb CLKB_PAD CLKB_O", "Xclkb CLKB_PAD CLK_O"), 1)

    def test_data_receiver_in_a_clock_leg_fails(self):
        # A clock leg must use the clock-pair inverter receiver, not the supply-referenced data one.
        self.assertEqual(self.check(self.FILES[1], "Xclk CLK_PAD CLK_O VDDIO VSS aib_rx_inv",
                                    "Xclk CLK_PAD CLK_O VDDIO VSS aib_rx_data"), 1)

    TB = FILES[2]

    def test_subckt_local_nets_do_not_bridge_a_cut_clkb_leg(self):
        # The testbench's `link` subckt has formal ports txp/rxp. Name the clkb leg's channel
        # nets the same and cut that leg: a parser that returns the subckt-local Xch would
        # add a txp-rxp edge and bridge the cut, a false pass.
        self.assertEqual(self.check(edits=[
            (self.TB, "txpcb", "txp"), (self.TB, "rxpcb", "rxp"),
            (self.TB, "Xlcb  txp rxp 0 link", "Xlcb  txp nc 0 link")]), 1)

    def test_trailing_param_on_a_cell_instance_keeps_it_recognised(self):
        # The model is the last positional token, so a key=value tail changes nothing.
        self.assertEqual(self.check(self.TB, "vdd_rx 0 aib_rx_clk", "vdd_rx 0 aib_rx_clk m=1"), 0)

    def test_trailing_param_on_a_cell_instance_still_fails_a_shorted_pair(self):
        self.assertEqual(self.check(edits=[
            (self.TB, "vdd_rx 0 aib_rx_clk", "vdd_rx 0 aib_rx_clk m=1"),
            (self.TB, "Xlcb  txpcb rxpcb 0 link", "Xlcb  txpcb rxpc 0 link")]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
