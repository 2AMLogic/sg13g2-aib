#!/usr/bin/env python3
"""Self-tests: each checker must accept a good input and reject a seeded-bad one.

Run before the checkers in CI: python3 -I scripts/ci/test_checkers.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FMT = HERE / "check_evidence_format.py"
APP = HERE / "check_sim_append_only.py"
SRC = HERE / "check_design_sources.py"
GEN = HERE / "gen_characterization_report.py"
SDF7 = HERE / "check_item7_sdf.py"
PNR_PINS = HERE / "check_pnr_pins.py"
CORNERS = HERE / "check_corner_bundles.py"
REPO = HERE.parent.parent
DIRS = ("spec", "design", "rtl", "verification", "sim", "layout", "measurements")
GOOD = {"record": "x", "utc_stamp": "20260101T000000Z", "pdk": {"release_tag": "v0.3.0"}, "log": "ngspice.log"}


def run(*cmd, cwd=None):
    return subprocess.run([sys.executable, "-I", *map(str, cmd)], cwd=cwd, capture_output=True, text=True)


def git(cwd, *args):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       cwd=cwd, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def make_tree(root: Path, record=None):
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        (root / d / "README.md").write_text("# " + d + "\n")
    if record is not None:
        p = root / "sim/s/records/20260101T000000Z"
        p.mkdir(parents=True)
        (p / "record.json").write_text(json.dumps(record))


class FormatTests(unittest.TestCase):
    def check(self, record=None, mutate=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make_tree(root, record)
            if mutate:
                mutate(root)
            return run(FMT, "--root", root).returncode

    def test_good_no_records(self):
        self.assertEqual(self.check(), 0)

    def test_good_record(self):
        self.assertEqual(self.check(GOOD), 0)

    def test_missing_readme(self):
        self.assertNotEqual(self.check(mutate=lambda r: (r / "layout/README.md").unlink()), 0)

    def test_missing_field(self):
        self.assertNotEqual(self.check({k: v for k, v in GOOD.items() if k != "utc_stamp"}), 0)

    def test_missing_pdk_revision(self):
        self.assertNotEqual(self.check({**GOOD, "pdk": {"source": "x"}}), 0)

    def test_absolute_path(self):
        self.assertNotEqual(self.check({**GOOD, "log": "/home/ubuntu/run/ngspice.log"}), 0)

    def test_invalid_json(self):
        def bad(r):
            (r / "sim/s/records/20260101T000000Z/record.json").write_text("{")
        self.assertNotEqual(self.check(GOOD, bad), 0)


class AppendOnlyTests(unittest.TestCase):
    REC = "sim/s/records/20260101T000000Z/record.json"

    def scenario(self, change):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            git(root, "init", "-q", "-b", "main")
            make_tree(root, GOOD)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "base")
            base = git(root, "rev-parse", "HEAD")
            change(root)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "change")
            return run(APP, "--base", base, cwd=root).returncode

    def test_add_passes(self):
        def add(r):
            p = r / "sim/s/records/20260102T000000Z"
            p.mkdir(parents=True)
            (p / "record.json").write_text(json.dumps(GOOD))
        self.assertEqual(self.scenario(add), 0)

    def test_harness_edit_passes(self):
        self.assertEqual(self.scenario(lambda r: (r / "sim/README.md").write_text("changed\n")), 0)

    def test_edit_fails(self):
        self.assertNotEqual(self.scenario(lambda r: (r / self.REC).write_text("{}")), 0)

    def test_delete_fails(self):
        self.assertNotEqual(self.scenario(lambda r: (r / self.REC).unlink()), 0)

    def test_rename_fails(self):
        def mv(r):
            dst = r / "sim/s/records/20260103T000000Z"
            dst.mkdir(parents=True)
            (r / self.REC).rename(dst / "record.json")
        self.assertNotEqual(self.scenario(mv), 0)

    def test_zero_base_skips(self):
        self.assertEqual(run(APP, "--base", "0" * 40).returncode, 0)

    def scenario_missing_base(self, change):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            git(root, "init", "-q", "-b", "main")
            make_tree(root, GOOD)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "base")
            git(root, "checkout", "-qb", "feature")
            change(root)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "change")
            return run(APP, "--base", "1" * 40, "--fallback-ref", "main", cwd=root).returncode

    def test_missing_base_falls_back_ok(self):
        self.assertEqual(self.scenario_missing_base(lambda r: (r / "sim/README.md").write_text("x\n")), 0)

    def test_missing_base_falls_back_detects_edit(self):
        self.assertNotEqual(self.scenario_missing_base(lambda r: (r / self.REC).write_text("{}")), 0)


class CharacterizationReportTests(unittest.TestCase):
    """The item 8 report and envelope must reproduce; a stale or tampered one must fail."""
    FILES = ("spec/target-spec.md", "measurements/row-evidence.json", "measurements/characterization-report.md",
             "signoff/attest/item8.json", "signoff/block-manifest.json", "layout/pnr/request.report.json",
             "signoff/attest/item5-digital")

    @classmethod
    def populate(cls, root):
        """Copy FILES plus every record the evidence rows cite, so a new record needs no edit here."""
        rows = json.loads((REPO / "measurements/row-evidence.json").read_text())["rows"]
        cited = {e["record"] for entries in rows.values() for e in entries}
        for f in cls.FILES + tuple(sorted(cited - set(cls.FILES))):
            dst = root / f
            dst.parent.mkdir(parents=True, exist_ok=True)
            if (REPO / f).is_dir():
                shutil.copytree(REPO / f, dst)
            else:
                shutil.copy(REPO / f, dst)

    def scenario(self, change=None, *args):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.populate(root)
            if change:
                change(root)
            return run(GEN, "--root", root, *args)

    def test_committed_report_is_fresh(self):
        self.assertEqual(self.scenario(None, "--check").returncode, 0)

    def test_report_edit_without_repin_fails(self):
        def edit(r):
            p = r / "measurements/characterization-report.md"
            p.write_text(p.read_text() + "x")
        self.assertNotEqual(self.scenario(edit, "--check").returncode, 0)

    def test_stale_manifest_hash_fails(self):
        def edit(r):
            p = r / "signoff/block-manifest.json"
            before = p.read_text()
            d = json.loads(before)
            entry = d["evidence"]["8.analog"]
            h = entry["content_hash"]
            # flip the last hex digit: independent of layout and leading digit
            entry["content_hash"] = h[:-1] + ("0" if h[-1] != "0" else "1")
            p.write_text(json.dumps(d, indent=2) + "\n")
            self.assertNotEqual(p.read_text(), before)
        self.assertNotEqual(self.scenario(edit, "--check").returncode, 0)

    def test_changed_record_makes_report_stale(self):
        def edit(r):
            p = r / "signoff/attest/item5-digital/sta_clk.json"
            p.write_text(p.read_text().replace("1647.47", "1647.48"))
        self.assertNotEqual(self.scenario(edit, "--check").returncode, 0)

    def test_failing_row_writes_fail_envelope(self):
        def edit(r):
            p = r / "signoff/attest/item5-digital/fv_shift_redundancy.json"
            d = json.loads(p.read_text())
            d["failed_count"] = 1
            p.write_text(json.dumps(d))
            self.assertEqual(run(GEN, "--root", r).returncode, 0)
            self.assertEqual(json.loads((r / "signoff/attest/item8.json").read_text())["status"], "fail")
        self.assertNotEqual(self.scenario(edit, "--check").returncode, 0)

    def test_row_without_record_is_listed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.populate(root)
            run(GEN, "--root", root)
            rows = [l for l in (root / "measurements/characterization-report.md").read_text().splitlines() if l.startswith("| T-")]
            self.assertEqual(len(rows), 30)
            self.assertIn("not-yet-measured", rows[0])


class DesignSourcesTests(unittest.TestCase):
    """The committed netlist chain must pass, and a seeded-stale input must fail."""

    def check(self, mutate=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for d in ("rtl", "design/synth", "signoff/attest"):
                shutil.copytree(REPO / d, root / d)
            shutil.copy(REPO / "signoff/block-manifest.json", root / "signoff/block-manifest.json")
            if mutate:
                mutate(root)
            return run(SRC, "--root", root).returncode

    def test_good(self):
        self.assertEqual(self.check(), 0)

    def test_edited_rtl_fails(self):
        def edit(r):
            with open(r / "rtl/aib_datapath.v", "a") as f:
                f.write("// x\n")
        self.assertNotEqual(self.check(edit), 0)

    def test_stale_netlist_fails(self):
        def edit(r):
            nl = next((r / "design/synth/.klt").rglob("aib_datapath_synth.v"))
            with open(nl, "a") as f:
                f.write("// x\n")
        self.assertNotEqual(self.check(edit), 0)

    def test_edited_inventory_fails(self):
        def edit(r):
            p = r / "signoff/attest/item1-digital.inventory.json"
            p.write_text(p.read_text().replace("aib_datapath", "aib_datapathX", 1))
        self.assertNotEqual(self.check(edit), 0)

    def test_stale_manifest_pin_fails(self):
        def edit(r):
            p = r / "signoff/block-manifest.json"
            m = json.loads(p.read_text())
            m["evidence"]["1.digital"]["content_hash"] = "sha256:" + "0" * 64
            p.write_text(json.dumps(m))
        self.assertNotEqual(self.check(edit), 0)


class Item7SdfTests(unittest.TestCase):
    """The derived SDFs must reproduce from the pinned source; drift must fail."""

    def check(self, mutate=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for d in ("verification/klt", "signoff/attest/item7-digital", "layout/pnr/.klt/place-and-route"):
                (root / d).mkdir(parents=True)
            shutil.copy(REPO / "verification/klt/run_evidence.py", root / "verification/klt/run_evidence.py")
            shutil.copy(REPO / "signoff/KLT_VERSION", root / "signoff/KLT_VERSION")
            shutil.copy(REPO / "signoff/block-manifest.json", root / "signoff/block-manifest.json")
            shutil.copy(REPO / "layout/pnr/.klt/place-and-route/aib_datapath_route.sdf",
                        root / "layout/pnr/.klt/place-and-route/aib_datapath_route.sdf")
            for f in (REPO / "signoff/attest/item7-digital").glob("*.sdf"):
                shutil.copy(f, root / "signoff/attest/item7-digital" / f.name)
            if mutate:
                mutate(root)
            return run(SDF7, "--root", root).returncode

    def test_good(self):
        self.assertEqual(self.check(), 0)

    def test_edited_derived_sdf_fails(self):
        def edit(r):
            with open(r / "signoff/attest/item7-digital/aib_datapath_route.tb.sdf", "a") as f:
                f.write("\n")
        self.assertNotEqual(self.check(edit), 0)

    def test_edited_source_sdf_fails(self):
        def edit(r):
            with open(r / "layout/pnr/.klt/place-and-route/aib_datapath_route.sdf", "a") as f:
                f.write("\n")
        self.assertNotEqual(self.check(edit), 0)

    def test_stale_pin_fails(self):
        def edit(r):
            p = r / "signoff/block-manifest.json"
            m = json.loads(p.read_text())
            m["derived_inputs"]["7.digital"]["files"][0]["content_hash"] = "sha256:" + "0" * 64
            p.write_text(json.dumps(m))
        self.assertNotEqual(self.check(edit), 0)

    def test_missing_pins_fail(self):
        def edit(r):
            p = r / "signoff/block-manifest.json"
            m = json.loads(p.read_text())
            del m["derived_inputs"]
            p.write_text(json.dumps(m))
        self.assertNotEqual(self.check(edit), 0)


class PnrPinTests(unittest.TestCase):
    """The committed routed SPEF and DEF must match their manifest pins."""

    def check(self, mutate=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            pnr = root / "layout/pnr/.klt/place-and-route"
            pnr.mkdir(parents=True)
            (root / "signoff").mkdir()
            shutil.copy(REPO / "signoff/block-manifest.json", root / "signoff/block-manifest.json")
            for n in ("aib_datapath_route.spef", "aib_datapath.def"):
                shutil.copy(REPO / "layout/pnr/.klt/place-and-route" / n, pnr / n)
            if mutate:
                mutate(root)
            return run(PNR_PINS, "--root", root).returncode

    def edit_manifest(self, fn):
        def edit(r):
            p = r / "signoff/block-manifest.json"
            m = json.loads(p.read_text())
            fn(m["derived_inputs"])
            p.write_text(json.dumps(m))
        return edit

    def test_good(self):
        self.assertEqual(self.check(), 0)

    def test_edited_spef_fails(self):
        def edit(r):
            with open(r / "layout/pnr/.klt/place-and-route/aib_datapath_route.spef", "a") as f:
                f.write("\n")
        self.assertNotEqual(self.check(edit), 0)

    def test_edited_def_fails(self):
        def edit(r):
            with open(r / "layout/pnr/.klt/place-and-route/aib_datapath.def", "a") as f:
                f.write("\n")
        self.assertNotEqual(self.check(edit), 0)

    def test_stale_pin_fails(self):
        def stale(d):
            d["pnr.digital"]["files"][0]["content_hash"] = "sha256:" + "0" * 64
        self.assertNotEqual(self.check(self.edit_manifest(stale)), 0)

    def test_missing_block_fails(self):
        self.assertNotEqual(self.check(self.edit_manifest(lambda d: d.pop("pnr.digital"))), 0)

    def test_one_file_pinned_fails(self):
        def drop(d):
            del d["pnr.digital"]["files"][1]
        self.assertNotEqual(self.check(self.edit_manifest(drop)), 0)



class CornerBundleTests(unittest.TestCase):
    """Every committed request under sim/ must agree with the one PVT-FULL table."""

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

    def test_every_generator_is_fresh_against_the_table(self):
        for gen in ("sim/channel-eye/gen_channel_eye.py", "sim/clock-path/gen_clock_path.py",
                    "sim/mc/gen_mc.py", "sim/dc-static/gen_dc_static.py"):
            r = run(REPO / gen, "--check")
            self.assertEqual(r.returncode, 0, f"{gen} --check: {r.stdout}{r.stderr}")

    def test_only_shape_restricts_the_grid(self):
        self.assertEqual([e["name"] for e in self.pvt.process(only=("tt",))], ["mos_tt"])

    def test_unknown_style_is_refused(self):
        with self.assertRaises(ValueError):
            self.pvt.process(style="sections")

if __name__ == "__main__":
    unittest.main(verbosity=2)
