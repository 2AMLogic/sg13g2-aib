#!/usr/bin/env python3
"""Self-tests of the signoff, attestation and pin checkers: each must accept a
good input and reject a seeded-bad one.

Stdlib only; PDK-free. Run alone: python3 -I scripts/ci/test_signoff_pins.py
python3 -I drops this directory from sys.path, hence the inserts below (the
check_design_sources.py idiom).
"""
import hashlib
import json
import posixpath
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest_pins  # noqa: E402  (the one manifest pin definition, #283)
from _checker_test_helpers import HERE, REPO, run  # noqa: E402

ATTESTED = HERE / "check_attested_paths.py"
KLT_PIN = HERE / "check_inventory_klt_pin.py"
GEN = HERE / "gen_characterization_report.py"
SRC = HERE / "check_design_sources.py"
SDF7 = HERE / "check_item7_sdf.py"
PNR_PINS = HERE / "check_pnr_pins.py"
EV_PINS = HERE / "check_evidence_pins.py"


class AttestedPathsTests(unittest.TestCase):
    """The hash-bound attested-path guard: a good tree passes, drift bites.

    The fixture keeps the two skip classes hostile on purpose: the inventory
    file holds invalid JSON (so ever reading it as an envelope would fail the
    good tree) and the envelope with no attestation block is bare.
    """

    ENV = "signoff/attest/item10.json"

    def scenario(self, mutate=None, extra=None):
        """One consistent envelope over README.md; `extra` adds fixtures,
        `mutate` seeds the bad state. Returns the checker's CompletedProcess."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            att = root / "signoff/attest"
            att.mkdir(parents=True)
            (root / "README.md").write_text("# attest me\n")
            digest = hashlib.sha256((root / "README.md").read_bytes()).hexdigest()
            env = {
                "schema_version": 1, "kind": "generic", "status": "pass", "t1_item": 10,
                "source": "signoff/attest/item10.inventory.json",
                "attestation": {
                    "producer": "klt signoff --attest",
                    "hash_algorithm": "sha256-raw-bytes",
                    "checks": [
                        {"check": "present", "role": "hygiene", "path": "README.md",
                         "passed": True, "content_hash": "sha256:" + digest},
                        {"check": "command", "role": "audit", "name": "self-test",
                         "argv": ["/usr/bin/python3", "-I", "scripts/ci/test_checkers.py"],
                         "cwd": ".", "exit_status": 0, "passed": True},
                    ],
                },
            }
            (att / "item10.json").write_text(json.dumps(env))
            (att / "item10.inventory.json").write_text("{ not even json")
            (att / "item8.json").write_text(json.dumps({"t1_item": 8, "status": "pass"}))
            if extra:
                extra(root)
            if mutate:
                mutate(root)
            return run(ATTESTED, "--root", root)

    def test_good_tree_passes(self):
        self.assertEqual(self.scenario().returncode, 0)

    def test_drifted_bytes_fail_and_name_the_repair(self):
        def bad(r):
            (r / "README.md").write_text("# edited without re-attesting\n")
        p = self.scenario(bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("README.md", p.stderr)
        self.assertIn(self.ENV, p.stderr)
        self.assertIn("klt signoff --attest", p.stderr)
        self.assertIn("KLT_VERSION", p.stderr)

    def test_deleted_attested_path_fails(self):
        p = self.scenario(lambda r: (r / "README.md").unlink())
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("README.md", p.stderr)

    def test_subdirectory_envelopes_are_walked(self):
        def extra(r):
            target = r / "verification/tb_top.v"
            target.parent.mkdir(parents=True)
            target.write_text("module tb_top; endmodule\n")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            env = {"t1_item": 5, "source": "signoff/attest/item5-digital/x.inventory.json",
                   "attestation": {"hash_algorithm": "sha256-raw-bytes", "checks": [
                       {"check": "present", "role": "testbench", "path": "verification/tb_top.v",
                        "passed": True, "content_hash": "sha256:" + digest}]}}
            (r / "signoff/attest/item5-digital").mkdir()
            (r / "signoff/attest/item5-digital/fv_top.json").write_text(json.dumps(env))
        self.assertEqual(self.scenario(extra=extra).returncode, 0)

        def bad(r):
            (r / "verification/tb_top.v").write_text("changed\n")
        p = self.scenario(extra=extra, mutate=bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("verification/tb_top.v", p.stderr)

    def test_envelope_without_present_members_is_skipped(self):
        def extra(r):
            env = {"t1_item": 2, "attestation": {"checks": [
                {"check": "command", "role": "audit", "name": "x",
                 "argv": ["true"], "exit_status": 0, "passed": True}]}}
            (r / "signoff/attest/item2-analog.json").write_text(json.dumps(env))
        self.assertEqual(self.scenario(extra=extra).returncode, 0)

    def test_unparseable_envelope_fails_naming_the_file(self):
        def bad(r):
            (r / self.ENV).write_text("{")
        p = self.scenario(bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.ENV, p.stderr)

    def test_unsupported_hash_algorithm_fails(self):
        def extra(r):
            env_path = r / self.ENV
            env = json.loads(env_path.read_text())
            env["attestation"]["checks"][0]["content_hash"] = "md5:abc"
            env_path.write_text(json.dumps(env))
        p = self.scenario(extra=extra)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("unsupported hash", p.stderr)

    def test_present_entry_without_hash_fails(self):
        def extra(r):
            env_path = r / self.ENV
            env = json.loads(env_path.read_text())
            del env["attestation"]["checks"][0]["content_hash"]
            env_path.write_text(json.dumps(env))
        p = self.scenario(extra=extra)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("no content_hash", p.stderr)

    def test_zero_attested_paths_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p = run(ATTESTED, "--root", t)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(str(Path(t).resolve()), p.stderr)
        self.assertIn("0 attested path(s) across 0 envelope(s)", p.stderr)

    def test_empty_attest_dir_fails(self):
        # distinct code path: the attest.is_dir() guard passes here and fails
        # in test_zero_attested_paths_fails
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "signoff/attest").mkdir(parents=True)
            p = run(ATTESTED, "--root", t)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("0 attested path(s) across 0 envelope(s)", p.stderr)

    def test_renamed_present_discriminator_fails(self):
        # the case an envelopes == 0 guard would miss: the envelope parses and
        # counts, but nothing is verified
        def bad(r):
            env_path = r / self.ENV
            env = json.loads(env_path.read_text())
            env["attestation"]["checks"][0]["check"] = "exists"
            env_path.write_text(json.dumps(env))
        p = self.scenario(bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("0 attested path(s) across 1 envelope(s)", p.stderr)

    def test_missing_hash_algorithm_fails(self):
        def bad(r):
            env_path = r / self.ENV
            env = json.loads(env_path.read_text())
            del env["attestation"]["hash_algorithm"]
            env_path.write_text(json.dumps(env))
        p = self.scenario(bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.ENV, p.stderr)

    def test_declared_algorithm_mismatch_fails_without_reattest_advice(self):
        # not test_unsupported_hash_algorithm_fails: that name is taken by the
        # per-entry content_hash prefix case, whose message carries the
        # re-attest repair on purpose. This one is a toolchain/checker gap --
        # the message must name the declared value and carry no such advice.
        def bad(r):
            env_path = r / self.ENV
            env = json.loads(env_path.read_text())
            env["attestation"]["hash_algorithm"] = "sha256-normalized"
            env_path.write_text(json.dumps(env))
        p = self.scenario(bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.ENV, p.stderr)
        self.assertIn("sha256-normalized", p.stderr)
        self.assertNotIn("klt signoff --attest", p.stderr)
        self.assertNotIn("re-attest", p.stderr)


class InventoryKltPinTests(unittest.TestCase):
    """The inventory-pin/envelope-version guard: a good tree passes, drift bites.

    The fixture mirrors the item 9 pair shape the guard exists for: the
    carrying inventory pins klt "0.9.0" and ngspice "ngspice-46", its paired
    envelope records the same klt version as provenance, and two skip-class
    inventories keep the hostility honest -- one valid inventory with no pins
    block (item 10's shape) and one carrying no klt pin next to an envelope
    that does not exist (item 1's shape), so ever pairing a non-carrying
    inventory would fail the good tree. The ngspice pin is compared against
    the newest pdk-smoke record instead, so the fixture seeds one under
    `sim/pdk-smoke/records/` by default.
    """

    INV = "signoff/attest/item9-analog.inventory.json"
    ENV = "signoff/attest/item9-analog.json"
    NEWEST_STAMP = "20261119T042213Z"

    def scenario(self, pin="0.9.0", version="0.9.0", ngspice_pin="ngspice-46",
                 records=None, mutate=None):
        """The item 9 analog pair plus the two skip-class inventories.

        `records` maps pdk-smoke stamp directory names to the tools.ngspice
        each record carries (a None value omits the field); None seeds the
        one landed newest record, {} seeds none.
        """
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            att = root / "signoff/attest"
            att.mkdir(parents=True)
            inv = {
                "schema_version": 1, "kind": "t1-attestation-inventory", "t1_item": 9,
                "testbenches": ["sim/bench.sh"], "cold_start": {"argv": ["sim/bench.sh"]},
                "pins": {"pdk": {"name": "IHP-Open-PDK"},
                         "tools": {"klt": pin, "ngspice": ngspice_pin}},
            }
            (att / "item9-analog.inventory.json").write_text(json.dumps(inv))
            env = {
                "schema_version": 1, "kind": "generic", "status": "pass", "t1_item": 9,
                "provenance": {"klt_version": version, "klayout_version": None},
            }
            (att / "item9-analog.json").write_text(json.dumps(env))
            (att / "item10.inventory.json").write_text(
                json.dumps({"schema_version": 1, "kind": "t1-attestation-inventory",
                            "t1_item": 10}))
            (att / "item1-digital.inventory.json").write_text(
                json.dumps({"schema_version": 1, "kind": "t1-attestation-inventory",
                            "t1_item": 1, "pins": {"tools": {"iverilog": "13.0"}}}))
            if records is None:
                records = {self.NEWEST_STAMP: "ngspice-46"}
            for stamp, ngspice in records.items():
                rec_dir = root / "sim/pdk-smoke/records" / stamp
                rec_dir.mkdir(parents=True)
                tools = {"ngspice": ngspice} if ngspice is not None else {}
                (rec_dir / "record.json").write_text(json.dumps(
                    {"record": "pdk-smoke", "utc_stamp": stamp, "tools": tools}))
            if mutate:
                mutate(root)
            return run(KLT_PIN, "--root", root)

    def test_good_tree_passes(self):
        self.assertEqual(self.scenario().returncode, 0)

    def test_pin_below_provenance_fails_and_names_the_repair(self):
        # The filed drift: inventory pinned 0.8.0, envelope produced by 0.9.0.
        p = self.scenario(pin="0.8.0")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.INV, p.stderr)
        self.assertIn(self.ENV, p.stderr)
        self.assertIn("0.8.0", p.stderr)
        self.assertIn("0.9.0", p.stderr)
        self.assertIn("klt signoff --attest 9", p.stderr)
        self.assertIn("KLT_VERSION", p.stderr)

    def test_pin_ahead_of_provenance_fails(self):
        # The mirror drift: pin bumped without the re-attest.
        p = self.scenario(version="0.8.0")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.INV, p.stderr)

    def test_missing_paired_envelope_fails(self):
        def bad(r):
            (r / self.ENV).unlink()
        p = self.scenario(mutate=bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.ENV, p.stderr)
        self.assertIn("missing", p.stderr)

    def test_null_klt_version_fails_without_reattest_advice(self):
        # A grader that stops recording provenance.klt_version is a
        # toolchain/checker gap, not tree drift: name it, carry no repair.
        def bad(r):
            env_path = r / self.ENV
            env = json.loads(env_path.read_text())
            env["provenance"]["klt_version"] = None
            env_path.write_text(json.dumps(env))
        p = self.scenario(mutate=bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.ENV, p.stderr)
        self.assertNotIn("re-attest", p.stderr)

    def test_unparseable_carrying_inventory_fails(self):
        def bad(r):
            (r / self.INV).write_text("{ not even json")
        p = self.scenario(mutate=bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.INV, p.stderr)

    def test_non_carrying_inventories_are_skipped(self):
        # item 1's shape: pins without klt, and no envelope to pair. The good
        # tree already proves the skip; this asserts it survives a missing
        # envelope for exactly that shape.
        self.assertEqual(self.scenario().returncode, 0)

    def test_zero_population_fails_loudly(self):
        # A schema rename that strips every pins.tools.klt must not turn the
        # guard into a silent pass.
        def bad(r):
            p = r / self.INV
            inv = json.loads(p.read_text())
            del inv["pins"]["tools"]["klt"]
            p.write_text(json.dumps(inv))
        p = self.scenario(mutate=bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("0 inventory klt pin", p.stderr)

    def test_renamed_suffix_leaves_zero_inventories_fails_loudly(self):
        # The zero-population shape a filename-suffix rename produces: no
        # *.inventory.json left at all, so "inventories present, none
        # carrying" never applies. Gating the guard on inventories existing
        # would exit 0 here.
        def bad(r):
            for f in sorted((r / "signoff/attest").glob("*.inventory.json")):
                f.rename(f.with_name(f.name.replace(".inventory.json", ".inv.json")))
        p = self.scenario(mutate=bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("0 inventory klt pin", p.stderr)
        self.assertIn("filename suffix", p.stderr)

    def test_ngspice_pin_vs_newest_record_drift_fails_and_names_both_fixes(self):
        # The filed drift (#368): the newest smoke record ran ngspice-47
        # while the inventory pinned ngspice-46.
        p = self.scenario(records={"20261017T215144Z": "ngspice-46",
                                   "20261119T042213Z": "ngspice-47"})
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(self.INV, p.stderr)
        self.assertIn(self.NEWEST_STAMP, p.stderr)
        self.assertIn("ngspice-46", p.stderr)
        self.assertIn("ngspice-47", p.stderr)
        self.assertIn("append-only", p.stderr)
        self.assertIn("re-run", p.stderr)
        self.assertIn("re-attest", p.stderr)

    def test_older_record_drift_is_not_checked(self):
        # Append-only history may legitimately differ; only the newest
        # record is compared.
        p = self.scenario(records={"20261017T215144Z": "ngspice-47",
                                   "20261119T042213Z": "ngspice-46"})
        self.assertEqual(p.returncode, 0)

    def test_same_day_stamp_ordering_picks_the_later_record(self):
        # Stamp directories sort lexicographically and their stamps are UTC,
        # so a later time-of-day stamp on the same date is the newest. The
        # older same-day record drifted; the guard must compare the newer
        # one and pass.
        p = self.scenario(records={"20261119T000247Z": "ngspice-47",
                                   "20261119T042213Z": "ngspice-46"})
        self.assertEqual(p.returncode, 0)

    def test_record_without_tools_ngspice_fails(self):
        # A record that drops the field must not read as a silent match.
        p = self.scenario(records={self.NEWEST_STAMP: None})
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("tools.ngspice", p.stderr)

    def test_no_records_fails_loudly(self):
        # Zero population must fail, not pass vacuously: a renamed records
        # path must not turn the ngspice guard off silently.
        p = self.scenario(records={})
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("no pdk-smoke record", p.stderr)

    def test_zero_ngspice_population_fails_loudly(self):
        # A schema rename stripping every pins.tools.ngspice must not turn
        # the guard into a silent pass (the klt vacuous-guard precedent).
        def bad(r):
            p = r / self.INV
            inv = json.loads(p.read_text())
            del inv["pins"]["tools"]["ngspice"]
            p.write_text(json.dumps(inv))
        p = self.scenario(mutate=bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("0 inventory ngspice pin", p.stderr)


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
            return run(SDF7, "--root", root)

    def test_good(self):
        self.assertEqual(self.check().returncode, 0)

    def test_edited_derived_sdf_fails(self):
        def edit(r):
            with open(r / "signoff/attest/item7-digital/aib_datapath_route.tb.sdf", "a") as f:
                f.write("\n")
        self.assertNotEqual(self.check(edit).returncode, 0)

    def test_edited_source_sdf_fails(self):
        def edit(r):
            with open(r / "layout/pnr/.klt/place-and-route/aib_datapath_route.sdf", "a") as f:
                f.write("\n")
        self.assertNotEqual(self.check(edit).returncode, 0)

    def test_stale_pin_fails(self):
        def edit(r):
            p = r / "signoff/block-manifest.json"
            m = json.loads(p.read_text())
            m["derived_inputs"]["7.digital"]["files"][0]["content_hash"] = "sha256:" + "0" * 64
            p.write_text(json.dumps(m))
        self.assertNotEqual(self.check(edit).returncode, 0)

    def test_missing_pins_fail(self):
        def edit(r):
            p = r / "signoff/block-manifest.json"
            m = json.loads(p.read_text())
            del m["derived_inputs"]
            p.write_text(json.dumps(m))
        self.assertNotEqual(self.check(edit).returncode, 0)

    def test_missing_output_file_is_reported_not_crashed(self):
        # The pre-consolidation checker read a pinned output unguarded, so an
        # absent file died in a traceback instead of reporting it (#283). The
        # exit code alone cannot tell those apart (both are 1); the stderr can.
        def edit(r):
            (r / "signoff/attest/item7-digital/aib_datapath_route.tb.sdf").unlink()
        r = self.check(edit)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("file is missing", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


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


class EvidencePinsTests(unittest.TestCase):
    """Every cited record must bind the stream the repo ships (#273).

    The fixture is a synthetic manifest plus fake records: the real
    block-manifest.json cites 34 records and their streams, too heavy to
    stage. It seeds every shape the resolution table covers, records the
    population must skip, and a stale record that is uncited -- the case a
    path glob over records/ would flag but the citation-driven population
    must not.
    """

    STREAM = "layout/aib_stream.gds"
    NETLIST = "design/synth/aib_netlist.v"
    SCHEMS = ("design/a_pad.sch", "design/b_pad.sch", "design/c_pad.sch")
    RECORD = "layout/pex/records/20260101T000000Z/aib_io_tx.extract.report.json"
    PNR = "layout/pnr/request.report.json"
    MULTI = "signoff/attest/item1-analog.json"
    FV = "signoff/fv_post_route.json"
    STALE = "layout/pex/records/20250101T000000Z/superseded.extract.report.json"
    SPEC = "signoff/item6/digital-spec.json"
    STATEMENT = "signoff/item6/digital-statement.json"

    def check(self, mutate=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.tree(root)
            if mutate:
                mutate(root)
            r = run(EV_PINS, "--root", root)
            self.assertNotIn("Traceback", r.stderr)
            return r

    def put(self, root, rel, obj):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=1) + "\n")
        return p

    def put_raw(self, root, rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def tree(self, root):
        for rel, text in [(self.STREAM, "stream bytes v1\n"),
                          (self.NETLIST, "module m; endmodule\n"),
                          *[(s, f"schematic {s}\n") for s in self.SCHEMS]]:
            self.put_raw(root, rel, text)
        self.put(root, self.RECORD, {
            "layout": {"path": self.STREAM, "scope": "repo"},
            "netlist": {"path": None, "scope": "external"},
            "provenance": {"input": {
                "content_hash": manifest_pins.sha((root / self.STREAM).read_bytes()),
                "role": "layout"}},
        })
        self.put(root, self.PNR, {
            "file": None,
            "layout": {"path": None, "scope": "external"},
            "netlist": {"path": self.NETLIST, "scope": "repo"},
            "verilog_path": "/scratch/old-tree/layout/pnr/.klt/aib_datapath.v",
            "provenance": {"input": {
                "content_hash": manifest_pins.sha((root / self.NETLIST).read_bytes()),
                "role": "netlist"}},
        })
        self.put(root, self.MULTI, {
            "provenance": {"input": {
                "content_hash": "sha256:" + "4" * 64,
                "paths": [{"path": {"path": s, "scope": "repo"},
                           "content_hash": manifest_pins.sha((root / s).read_bytes())}
                          for s in self.SCHEMS],
            }},
        })
        self.put(root, self.FV, {"status": "pass"})
        self.put(root, self.SPEC, {"rows": [1, 2]})
        self.put(root, self.STATEMENT, {"statement": "ok"})
        self.put(root, self.STALE, {
            "layout": {"path": self.STREAM, "scope": "repo"},
            "provenance": {"input": {"content_hash": "sha256:" + "0" * 64,
                                     "role": "layout"}},
        })
        self.put(root, "signoff/block-manifest.json", {
            "evidence": {
                "7.analog": [{"file": self.RECORD}],
                "11.digital": [{"file": self.PNR}],
                "1.analog": {"file": self.MULTI, "content_hash": "sha256:" + "1" * 64},
                "5.digital": [{"file": self.FV}],
                "6.digital": {"not_applicable": {
                    "spec": {"file": self.SPEC, "content_hash": "sha256:" + "2" * 64},
                    "statement": {"file": self.STATEMENT,
                                  "content_hash": "sha256:" + "3" * 64},
                }},
            },
        })

    def test_good(self):
        self.assertEqual(self.check().returncode, 0)

    def test_the_uncited_stale_record_is_not_reported(self):
        r = self.check()
        self.assertEqual(r.returncode, 0)
        self.assertNotIn(self.STALE, r.stderr)

    def test_edited_stream_fails(self):
        def edit(r):
            with open(r / self.STREAM, "a") as f:
                f.write("edited\n")
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.RECORD, r.stderr)
        self.assertIn(self.STREAM, r.stderr)

    def test_edited_netlist_fails(self):
        def edit(r):
            with open(r / self.NETLIST, "a") as f:
                f.write("// edited\n")
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.PNR, r.stderr)

    def test_edited_multi_source_path_fails(self):
        def edit(r):
            with open(r / self.SCHEMS[1], "a") as f:
                f.write("edited\n")
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.SCHEMS[1], r.stderr)

    def test_a_record_matching_no_resolution_key_fails_closed(self):
        def edit(r):
            p = r / self.RECORD
            rec = json.loads(p.read_text())
            rec["layout"] = {"path": None, "scope": "repo"}
            p.write_text(json.dumps(rec))
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.RECORD, r.stderr)
        self.assertIn("tried provenance.input.path, file, layout, netlist, verilog_path",
                      r.stderr)

    def test_an_empty_multi_source_paths_list_fails_closed(self):
        def edit(r):
            p = r / self.MULTI
            rec = json.loads(p.read_text())
            rec["provenance"]["input"]["paths"] = []
            p.write_text(json.dumps(rec))
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.MULTI, r.stderr)

    def test_multi_source_without_aggregate_hash_still_checks_its_pins(self):
        def edit(r):
            p = r / self.MULTI
            rec = json.loads(p.read_text())
            del rec["provenance"]["input"]["content_hash"]
            rec["provenance"]["input"]["paths"][1]["content_hash"] = "sha256:" + "0" * 64
            p.write_text(json.dumps(rec))
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.MULTI, r.stderr)
        self.assertIn(self.SCHEMS[1], r.stderr)

    def test_multi_source_without_aggregate_hash_passes_when_pins_are_good(self):
        def edit(r):
            p = r / self.MULTI
            rec = json.loads(p.read_text())
            del rec["provenance"]["input"]["content_hash"]
            p.write_text(json.dumps(rec))
        r = self.check(edit)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn(self.MULTI, r.stderr)

    def test_an_empty_paths_list_without_aggregate_is_skipped(self):
        def edit(r):
            p = r / self.MULTI
            rec = json.loads(p.read_text())
            del rec["provenance"]["input"]["content_hash"]
            rec["provenance"]["input"]["paths"] = []
            p.write_text(json.dumps(rec))
        r = self.check(edit)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn(self.MULTI, r.stderr)

    def test_a_non_list_paths_fails_closed(self):
        def edit(r):
            p = r / self.MULTI
            rec = json.loads(p.read_text())
            del rec["provenance"]["input"]["content_hash"]
            rec["provenance"]["input"]["paths"] = {"0": "not a list"}
            p.write_text(json.dumps(rec))
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.MULTI, r.stderr)
        self.assertIn("provenance.input.paths is not a list", r.stderr)

    def test_missing_cited_record_fails(self):
        def edit(r):
            (r / self.RECORD).unlink()
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn("cited record file is missing", r.stderr)

    def test_missing_stream_fails(self):
        def edit(r):
            (r / self.STREAM).unlink()
        r = self.check(edit)
        self.assertEqual(r.returncode, 1)
        self.assertIn("which is missing", r.stderr)

    def test_missing_manifest_fails(self):
        def edit(r):
            (r / "signoff/block-manifest.json").unlink()
        self.assertEqual(self.check(edit).returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
