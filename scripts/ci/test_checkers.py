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


if __name__ == "__main__":
    unittest.main(verbosity=2)
