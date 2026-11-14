#!/usr/bin/env python3
"""Self-tests: each checker must accept a good input and reject a seeded-bad one.

Run before the checkers in CI: python3 -I scripts/ci/test_checkers.py
"""
import contextlib
import fnmatch
import io
import json
import posixpath
import re
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

# The seven generators that share the one write-or-check helper (#227, #239), each with one
# of its committed outputs, used to assert that a refused run writes nothing.
GENERATORS = {
    "sim/channel-eye/gen_channel_eye.py": "sim/channel-eye/prbs7_stim.inc",
    "sim/clock-path/gen_clock_path.py": "sim/clock-path/clock_stim.inc",
    "sim/mc/capture_window/gen_t19.py": "sim/mc/capture_window/tb_t19.cir",
    "sim/mc/gen_mc.py": "sim/mc/tb_t10_ctl.cir",
    "sim/dc-static/gen_dc_static.py": "sim/dc-static/request.json",
    "layout/lvs/gen_reference.py": "layout/lvs/aib_io_tx.ref.spice",
    "layout/pex/gen_pex_benches.py": "layout/pex/benches/extraction.json",
}


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

    PEX_REC = "layout/pex/records/20260101T000000Z/record.json"

    def test_pex_record_add_passes(self):
        def add(r):
            p = r / "layout/pex/records/20260102T000000Z"
            p.mkdir(parents=True)
            (p / "record.json").write_text(json.dumps(GOOD))
        self.assertEqual(self.scenario(add), 0)

    def test_pex_record_edit_fails(self):
        def edit(r):
            p = r / self.PEX_REC
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        # The base tree has no pex record, so seed one, then edit it.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            git(root, "init", "-q", "-b", "main")
            make_tree(root, GOOD)
            (root / self.PEX_REC).parent.mkdir(parents=True)
            (root / self.PEX_REC).write_text(json.dumps(GOOD))
            git(root, "add", "-A")
            git(root, "commit", "-qm", "base")
            base = git(root, "rev-parse", "HEAD")
            edit(root)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "change")
            self.assertNotEqual(run(APP, "--base", base, cwd=root).returncode, 0)

    def test_pex_generator_edit_passes(self):
        def edit(r):
            p = r / "layout/pex/gen_pex_benches.py"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# changed\n")
        self.assertEqual(self.scenario(edit), 0)

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
            mapped = json.loads((root / "measurements/row-evidence.json").read_text())["rows"]
            unmapped = [l for l in rows if l.split("|")[1].strip() not in mapped]
            self.assertTrue(unmapped, "expected at least one spec row with no map entry")
            for line in unmapped:
                self.assertIn("not-yet-measured", line)

    def test_manifest_cited_row_missing_from_map_fails(self):
        """A row the manifest cites as evidence must be graded, not silently not-yet-measured."""
        def drop(r):
            p = r / "measurements/row-evidence.json"
            d = json.loads(p.read_text())
            man = json.loads((r / "signoff/block-manifest.json").read_text())["evidence"]
            cited = [row for k in ("5.analog", "6.analog") for e in man[k] for row in e["rows"]]
            victim = next(row for row in cited if row in d["rows"])
            del d["rows"][victim]
            p.write_text(json.dumps(d, indent=2) + "\n")
        out = self.scenario(drop, "--check")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("does not grade", out.stderr)

    def test_map_citing_a_superseded_record_fails(self):
        """Citing some other record for a cited row is the same drift: the manifest's own record must be graded."""
        def repoint(r):
            p = r / "measurements/row-evidence.json"
            d = json.loads(p.read_text())
            man = json.loads((r / "signoff/block-manifest.json").read_text())["evidence"]
            cited = [(e["file"], row) for k in ("5.analog", "6.analog") for e in man[k] for row in e["rows"]]
            f, victim = next((f, row) for f, row in cited if row in d["rows"])
            keep = posixpath.dirname(f)
            for entry in d["rows"][victim]:
                if posixpath.dirname(entry["record"]) == keep:
                    entry["record"] = posixpath.join(keep + "-superseded", posixpath.basename(entry["record"]))
            p.write_text(json.dumps(d, indent=2) + "\n")
        out = self.scenario(repoint, "--check")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("does not grade", out.stderr)


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

    def test_every_generator_is_fresh_against_the_table(self):
        for gen in ("sim/channel-eye/gen_channel_eye.py", "sim/clock-path/gen_clock_path.py",
                    "sim/mc/gen_mc.py", "sim/dc-static/gen_dc_static.py",
                    "sim/redundancy-mux/gen_redundancy_mux.py"):
            r = run(REPO / gen, "--check")
            self.assertEqual(r.returncode, 0, f"{gen} --check: {r.stdout}{r.stderr}")

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


class EveryGeneratorParsesItsFlagsStrictlyTests(unittest.TestCase):
    """A mistyped --check must report, never silently regenerate (#227).

    Three of the six used to test `"--check" in argv`, so any other argument meant "write":
    `gen_clock_path.py --chek` rewrote the generated files and exited 0 on a stale tree.
    """

    def test_an_unknown_flag_exits_2_and_writes_nothing(self):
        for gen, generated in GENERATORS.items():
            with self.subTest(gen=gen):
                before = (REPO / generated).stat().st_mtime_ns
                r = run(REPO / gen, "--chek")
                self.assertEqual(r.returncode, 2, f"{gen} --chek: {r.stdout}{r.stderr}")
                self.assertEqual((REPO / generated).stat().st_mtime_ns, before,
                                 f"{gen} --chek rewrote {generated}")


# ---------------------------------------------------------------------------
# Completeness of the one check list (#236)
#
# scripts/ci/check_local.sh calls itself "the one list of PDK-free checks", but
# it is kept by hand, so a checker can be added to the tree and never reach it.
# That happened twice (#173, #219) before anything asserted otherwise. The test
# below is that assertion: every self-test and every checkable generator in the
# tracked tree is either *listed* in check_local.sh, *covered* by a listed file
# that runs it, or *exempt* with a stated reason. Adding a 31st candidate
# without doing one of the three fails this test.
#
# Discovery is by file NAME, deliberately, not by grepping for a `--check`
# literal: scripts/ci/gen_item6_digital.py has no --check flag (checking is its
# default mode, --regenerate rewrites), and since #227 the flag handling lives
# in sim/gen_common.py rather than in each generator.
#
# layout/attest_item2.py is deliberately OUTSIDE the discovery set: it matches
# none of the four globs, and widening them to reach it would also pull in
# every other non-checker script in the tree. It needs the pinned klt
# environment (it imports klayout_tools.signoff), so it is the same class as
# the layout/check_io_column.py exemption below and would be exempt anyway.
# ---------------------------------------------------------------------------

CHECK_LIST = "scripts/ci/check_local.sh"
CANDIDATE_GLOBS = ("gen_*.py", "check_*.py", "test_*.py", "test_*.sh")

# candidate -> (file that runs it, why no line of its own is wanted).
# The covering file must itself be listed in check_local.sh, and must mention
# the candidate by name -- otherwise the coverage claim has quietly lapsed.
COVERED = {
    "sim/channel-eye/gen_channel_eye.py": (
        "scripts/ci/test_checkers.py",
        "--check runs in test_every_generator_is_fresh_against_the_table",
    ),
    "sim/clock-path/gen_clock_path.py": (
        "scripts/ci/test_checkers.py",
        "--check runs in test_every_generator_is_fresh_against_the_table",
    ),
    "sim/redundancy-mux/gen_redundancy_mux.py": (
        "scripts/ci/test_checkers.py",
        "--check runs in test_every_generator_is_fresh_against_the_table",
    ),
    "sim/mc/capture_window/gen_t19.py": (
        "sim/mc/capture_window/test_t19.py",
        "test_generated_files_are_fresh compares both T-19 netlists, the same comparison --check makes",
    ),
}

# candidate -> why it is not a check this list can run at all.
EXEMPT = {
    "verification/test_datapath.py":
        "cocotb bench module, imported by verification/run_tb.py; not a standalone suite",
    "verification/test_shift_redundancy.py":
        "cocotb bench module, imported by verification/run_tb.py; not a standalone suite",
    "layout/check_io_column.py":
        "needs the pinned klt environment (imports klayout.db); CI-only, like the klt signoff steps",
    "layout/gen_io_column.py": "generator with no check mode",
    "layout/erc/gen_specs.py": "generator with no check mode",
    "sim/channel-eye/gen_t16attr.py": "generator with no check mode",
    "sim/gen_common.py": "the shared write-or-check helper (#227); imported, never run",
}


def strip_sh_comments(text):
    """Drop `#` comments so a path named only in prose does not count as listed.

    A `#` starts a comment at the start of a line or after whitespace, which
    keeps `${0##*/}` intact. This is a heuristic, not a shell parser: a `#`
    inside a quoted string after a space would over-strip. That bias is the
    safe one -- over-stripping reports a listed check as unlisted (loud), while
    under-stripping reports an unlisted check as listed (silent), which is the
    exact failure this whole test exists to catch.
    """
    return "\n".join(re.sub(r"(?:^|(?<=\s))#.*$", "", line) for line in text.splitlines())


def discover_candidates(tracked):
    """Every tracked path whose basename matches one of CANDIDATE_GLOBS."""
    return sorted(p for p in tracked
                  if any(fnmatch.fnmatch(posixpath.basename(p), g) for g in CANDIDATE_GLOBS))


def completeness_errors(tracked, check_list_text, covered, exempt, read_text):
    """Return a sorted list of ways the check list and its table disagree with the tree.

    Pure: every input is passed in, so the failure modes can be tested against
    a fixture without touching the real tree. `read_text` maps a repo-relative
    path to its contents and is only called for covering files.
    """
    tracked = set(tracked)
    code = strip_sh_comments(check_list_text)
    errors = []

    def is_listed(path):
        return path in code

    # The table must not rot: it may only name tracked files that are not
    # already listed on a command line of their own.
    for path in sorted(set(covered) | set(exempt)):
        if path in covered and path in exempt:
            errors.append(f"{path}: in both COVERED and EXEMPT; it must be exactly one")
        if path not in tracked:
            errors.append(f"{path}: table entry names a path that is no longer tracked; drop it")
        elif is_listed(path):
            errors.append(f"{path}: table entry is now listed in {CHECK_LIST}; drop its table entry")

    for path in discover_candidates(tracked):
        if is_listed(path):
            continue
        if path in exempt:
            if not exempt[path].strip():
                errors.append(f"{path}: EXEMPT entry needs a reason")
            continue
        if path in covered:
            cover, reason = covered[path]
            if not reason.strip():
                errors.append(f"{path}: COVERED entry needs a reason")
            if cover not in tracked:
                errors.append(f"{path}: covering file {cover} is not tracked")
            elif not is_listed(cover):
                errors.append(f"{path}: covering file {cover} is not itself in {CHECK_LIST}, "
                              "so nothing runs it")
            elif posixpath.basename(path) not in read_text(cover):
                errors.append(f"{path}: covering file {cover} never mentions "
                              f"{posixpath.basename(path)}; the coverage claim has lapsed")
            continue
        errors.append(f"{path}: in neither {CHECK_LIST} nor the COVERED/EXEMPT table in "
                      "scripts/ci/test_checkers.py -- add a run line, or a table entry with a reason")
    return sorted(errors)


class CheckListCompletenessTests(unittest.TestCase):
    """#236: assert the one check list has not fallen behind the tree again."""

    @classmethod
    def setUpClass(cls):
        cls.tracked = git(REPO, "ls-files").splitlines()
        cls.text = (REPO / CHECK_LIST).read_text()

    def read(self, path):
        return (REPO / path).read_text()

    # -- the real tree -------------------------------------------------------

    def test_every_tracked_checker_is_listed_covered_or_exempt(self):
        errors = completeness_errors(self.tracked, self.text, COVERED, EXEMPT, self.read)
        self.assertEqual(errors, [], "\n" + "\n".join(errors))

    def test_discovery_finds_both_the_shell_and_no_flag_classes(self):
        # A discovery key of "*.py" would miss the shell self-test, and one of
        # "has a --check flag" would miss the checker whose check is default.
        found = discover_candidates(self.tracked)
        self.assertIn("sim/harness/test_batch_record.sh", found)
        self.assertIn("scripts/ci/gen_item6_digital.py", found)
        # Both are listed outright, so neither needs a table entry.
        code = strip_sh_comments(self.text)
        self.assertIn("sim/harness/test_batch_record.sh", code)
        self.assertIn("scripts/ci/gen_item6_digital.py", code)

    def test_the_lvs_reference_check_is_listed(self):
        # Step 1 of #236; also the guard on the derived neg/ controls (#202).
        self.assertIn("layout/lvs/gen_reference.py", strip_sh_comments(self.text))

    def test_run_tb_self_test_is_listed_not_exempt(self):
        # Its two cocotb neighbours are exempt, but it is a standalone suite:
        # a blanket "exclude verification/test_*.py" would be wrong.
        self.assertIn("verification/test_run_tb.py", strip_sh_comments(self.text))
        self.assertNotIn("verification/test_run_tb.py", EXEMPT)
        self.assertNotIn("verification/test_run_tb.py", COVERED)

    def test_the_cocotb_bench_modules_are_exempt_with_reasons(self):
        for mod in ("verification/test_datapath.py", "verification/test_shift_redundancy.py"):
            self.assertIn(mod, EXEMPT)
            self.assertIn("cocotb", EXEMPT[mod])

    def test_attest_item2_is_outside_the_discovery_set(self):
        # Stated in the comment above: it matches no glob, and needs pinned klt.
        self.assertIn("layout/attest_item2.py", self.tracked)
        self.assertNotIn("layout/attest_item2.py", discover_candidates(self.tracked))

    # -- the failure modes, against a fixture tree ---------------------------
    #
    # Each case patches the inputs rather than editing the real tree, so a
    # failing assertion here can never leave the working tree dirty.

    FIX_TRACKED = ["scripts/ci/check_local.sh", "scripts/ci/test_checkers.py",
                   "sim/a/gen_a.py", "sim/b/test_b.py", "sim/c/gen_c.py"]
    FIX_LIST = ('run "self-test" python3 -I scripts/ci/test_checkers.py\n'
                'run "b" python3 -I sim/b/test_b.py\n')

    def fixture(self, tracked=None, text=None, covered=None, exempt=None, files=None):
        files = files or {}
        return completeness_errors(
            tracked if tracked is not None else self.FIX_TRACKED,
            text if text is not None else self.FIX_LIST,
            covered or {}, exempt or {},
            lambda p: files.get(p, ""))

    def test_a_new_candidate_that_is_neither_listed_nor_tabled_fails(self):
        errors = self.fixture()
        self.assertTrue(any(e.startswith("sim/a/gen_a.py:") for e in errors), errors)
        self.assertTrue(any(e.startswith("sim/c/gen_c.py:") for e in errors), errors)
        self.assertFalse(any(e.startswith("sim/b/test_b.py:") for e in errors), errors)

    def test_a_covered_entry_whose_covering_file_is_unlisted_fails(self):
        # sim/c/gen_c.py is tracked but has no run line, so it cannot cover.
        errors = self.fixture(
            covered={"sim/a/gen_a.py": ("sim/c/gen_c.py", "why")},
            exempt={"sim/b/test_b.py": "n/a"},   # keep the rest quiet
            files={"sim/c/gen_c.py": "gen_a.py"})
        self.assertTrue(any("covering file sim/c/gen_c.py is not itself in" in e for e in errors),
                        errors)

    def test_a_covered_entry_whose_covering_file_never_mentions_it_fails(self):
        errors = self.fixture(
            covered={"sim/a/gen_a.py": ("sim/b/test_b.py", "why")},
            exempt={"sim/c/gen_c.py": "no check mode"},
            files={"sim/b/test_b.py": "this file runs something else entirely"})
        self.assertTrue(any("the coverage claim has lapsed" in e for e in errors), errors)

    def test_a_table_entry_for_an_untracked_path_fails(self):
        errors = self.fixture(
            covered={"sim/gone/gen_gone.py": ("sim/b/test_b.py", "why")},
            exempt={"sim/a/gen_a.py": "r", "sim/c/gen_c.py": "r"})
        self.assertTrue(any("no longer tracked" in e for e in errors), errors)

    def test_a_table_entry_for_a_now_listed_file_fails(self):
        # sim/b/test_b.py has a run line; an exemption for it is stale.
        errors = self.fixture(
            exempt={"sim/a/gen_a.py": "r", "sim/c/gen_c.py": "r", "sim/b/test_b.py": "r"})
        self.assertTrue(any("drop its table entry" in e for e in errors), errors)

    def test_a_candidate_named_only_in_a_comment_is_not_listed(self):
        # The live case: #235 added a comment block naming gen_clock_path.py,
        # which is now its only mention in check_local.sh.
        text = '# see sim/a/gen_a.py for why\nrun "b" python3 -I sim/b/test_b.py\n'
        errors = self.fixture(text=text, exempt={"sim/c/gen_c.py": "r"})
        self.assertTrue(any(e.startswith("sim/a/gen_a.py:") for e in errors), errors)
        # ...and a trailing comment on a real run line does not hide the line.
        text2 = self.FIX_LIST + 'run "a" python3 -I sim/a/gen_a.py  # the A check\n'
        self.assertEqual(self.fixture(text=text2, exempt={"sim/c/gen_c.py": "r"}), [])

    def test_strip_sh_comments_keeps_a_parameter_expansion(self):
        self.assertEqual(strip_sh_comments('echo "${0##*/}"  # usage'), 'echo "${0##*/}"  ')

    def test_a_clean_fixture_tree_reports_nothing(self):
        self.assertEqual(
            self.fixture(covered={"sim/a/gen_a.py": ("sim/b/test_b.py", "run inside it")},
                         exempt={"sim/c/gen_c.py": "generator with no check mode"},
                         files={"sim/b/test_b.py": "subprocess.run(['gen_a.py', '--check'])"}),
            [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
