#!/usr/bin/env python3
"""Self-tests: each checker must accept a good input and reject a seeded-bad one.

Run before the checkers in CI: python3 -I scripts/ci/test_checkers.py
"""
import contextlib
import fnmatch
import hashlib
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
EV_PINS = HERE / "check_evidence_pins.py"
CORNERS = HERE / "check_corner_bundles.py"
ATTESTED = HERE / "check_attested_paths.py"
IGN = HERE / "check_record_not_ignored.py"
REPO = HERE.parent.parent
DIRS = ("spec", "design", "rtl", "verification", "sim", "layout", "measurements")
GOOD = {"record": "x", "utc_stamp": "20260101T000000Z", "pdk": {"release_tag": "v0.3.0"}, "log": "ngspice.log"}

# layout/attest_item2.py is not a generator: it writes no generated file, it builds a
# `klt signoff --attest 2` command line. Its write targets are the two committed signoff
# envelopes, which is why its own mistyped-flag fall-through was worse than a stale bench
# file (#265) -- and why it gets an assertion of its own below.
ATTEST_ITEM2 = "layout/attest_item2.py"
ATTEST_ENVELOPES = ("signoff/attest/item2-analog.json", "signoff/attest/item2-digital.json")


def run(*cmd, cwd=None):
    return subprocess.run([sys.executable, "-I", *map(str, cmd)], cwd=cwd, capture_output=True, text=True)


def git(cwd, *args):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       cwd=cwd, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def make_tree(root: Path, record=None, record_readme=False):
    """A minimal evidence tree; `record` seeds one sim record under sim/s/records/.

    `record_readme` also writes that record's own README.md -- the narrative file
    the append-only tests need present in the base commit. It is off by default
    because only AppendOnlyTests cares whether it exists.
    """
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        (root / d / "README.md").write_text("# " + d + "\n")
    if record is not None:
        p = root / "sim/s/records/20260101T000000Z"
        p.mkdir(parents=True)
        (p / "record.json").write_text(json.dumps(record))
        if record_readme:
            (p / "README.md").write_text("# landed record\n")


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

    def test_record_dir_without_record_or_readme_fails(self):
        # the abort leftover (#276): a records/<stamp>/ directory with a rows file but
        # no record.json is not evidence and must not be committable
        def bad(r):
            p = r / "sim/s/records/20260102T000000Z"
            p.mkdir(parents=True)
            (p / "rows.json").write_text("{}")
        self.assertNotEqual(self.check(mutate=bad), 0)

    def test_record_dir_readme_only_passes(self):
        # a record directory that carries its own README.md is a deliberate,
        # ungraded study -- the t16attr shape
        def add(r):
            p = r / "sim/s/records/20260102T000000Z"
            p.mkdir(parents=True)
            (p / "README.md").write_text("# deliberately ungraded study\n")
        self.assertEqual(self.check(mutate=add), 0)

    def test_pex_record_readme_only_passes(self):
        # a pex record directory that carries its own README.md is accepted,
        # matching the sim behaviour (#315)
        def add(r):
            p = r / "layout/pex/records/20260102T000000Z"
            p.mkdir(parents=True)
            (p / "README.md").write_text("# deliberately ungraded study\n")
        self.assertEqual(self.check(mutate=add), 0)

    def test_pex_record_without_sim_schema_passes(self):
        # the committed pex records carry no utc_stamp and no pdk and are
        # append-only frozen: the sim schema must not be demanded of them (#315)
        def add(r):
            p = r / "layout/pex/records/20260101T000000Z"
            p.mkdir(parents=True)
            (p / "record.json").write_text(json.dumps({"record": "pex", "mode": "extract"}))
        self.assertEqual(self.check(mutate=add), 0)

    def test_pex_record_dir_without_record_or_readme_fails(self):
        # the run_pex.sh abort leftover (#315): layout/pex is a record root too,
        # so a records/<stamp>/ with a report but no record.json must fail there
        def bad(r):
            p = r / "layout/pex/records/20260102T000000Z"
            p.mkdir(parents=True)
            (p / "aib_io_tx.extract.report.json").write_text("")
        self.assertNotEqual(self.check(mutate=bad), 0)

    def test_empty_records_dir_passes(self):
        def add(r):
            (r / "sim/s/records").mkdir(parents=True, exist_ok=True)
        self.assertEqual(self.check(mutate=add), 0)

    def test_count_line_counts_walked_dirs(self):
        def add_readme_only(r):
            p = r / "sim/s/records/20260102T000000Z"
            p.mkdir(parents=True)
            (p / "README.md").write_text("# deliberately ungraded study\n")
        def add_pex_record(r):
            p = r / "layout/pex/records/20260103T000000Z"
            p.mkdir(parents=True)
            (p / "record.json").write_text(json.dumps({"record": "pex", "mode": "extract"}))
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            make_tree(root, GOOD)
            add_readme_only(root)
            add_pex_record(root)
            r = run(FMT, "--root", root)
            self.assertEqual(r.returncode, 0)
            # both roots are walked and the line no longer says "sim" (#315)
            self.assertIn("(3 record(s) checked)", r.stdout)
            self.assertNotIn("sim record(s)", r.stdout)


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


class AppendOnlyTests(unittest.TestCase):
    REC = "sim/s/records/20260101T000000Z/record.json"

    def scenario(self, change):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            git(root, "init", "-q", "-b", "main")
            make_tree(root, GOOD, record_readme=True)
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

    # --- a record's own README.md is a record file, not harness prose (#255) ---

    REC_README = "sim/s/records/20260101T000000Z/README.md"

    def test_record_readme_edit_fails(self):
        """The README *inside* a record directory is frozen with the data beside it."""
        self.assertNotEqual(self.scenario(lambda r: (r / self.REC_README).write_text("x\n")), 0)

    def test_record_readme_delete_fails(self):
        """Nothing else would notice: check_evidence_format.py checks only the seven top dirs."""
        self.assertNotEqual(self.scenario(lambda r: (r / self.REC_README).unlink()), 0)

    def test_new_record_readme_add_passes(self):
        """A README arriving with its own new record is an addition."""
        self.assertEqual(self.scenario(self.add_new_record), 0)

    def test_family_readme_edit_passes(self):
        """A README *above* a record directory is harness prose and may change."""
        def edit(r):
            p = r / "sim/s/README.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("family prose\n")
        self.assertEqual(self.scenario(edit), 0)

    # --- base selection per event (#255) ---
    #
    # A push event reports the *previously pushed head* as its base, which would
    # freeze a record from its own first push. The checker takes the event facts
    # as flags so both rows below are drivable from here rather than from a
    # ci.yml expression this suite cannot reach.

    NEW_REC = "sim/s/records/20260102T000000Z"
    FEATURE_PUSH = ("--event-name", "push", "--push-ref", "refs/heads/feature",
                    "--default-branch", "main", "--fallback-ref", "main")
    DEFAULT_PUSH = ("--event-name", "push", "--push-ref", "refs/heads/main",
                    "--default-branch", "main", "--fallback-ref", "main")

    def add_new_record(self, r):
        p = r / self.NEW_REC
        p.mkdir(parents=True)
        (p / "record.json").write_text(json.dumps(GOOD))
        (p / "README.md").write_text("# new record\n")

    def amend_new_record_readme(self, r):
        (r / self.NEW_REC / "README.md").write_text("# new record, corrected\n")

    def touch_harness(self, r):
        (r / "sim/README.md").write_text("harness prose\n")

    @contextlib.contextmanager
    def feature_branch(self, first, second):
        """A temp repo whose feature branch carries two pushes over a seeded main.

        Yields (root, before): `before` is the first push's head, i.e. exactly
        what a push event reports as `github.event.before` for the second push.
        """
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            git(root, "init", "-q", "-b", "main")
            make_tree(root, GOOD, record_readme=True)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "base")
            git(root, "checkout", "-qb", "feature")
            first(root)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "first push")
            before = git(root, "rev-parse", "HEAD")
            second(root)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "second push")
            yield root, before

    def test_prepush_base_fails_on_amendment_within_the_branch(self):
        """The seeded-bad case: the pre-push base is what freezes a record too early.

        Correcting a brand-new record's README inside its own branch touches
        nothing that is on main, yet reads as M against the previously pushed
        head. This is the asymmetry #255 reports; the flags are omitted so the
        base is used as given.
        """
        with self.feature_branch(self.add_new_record, self.amend_new_record_readme) as (root, before):
            self.assertNotEqual(run(APP, "--base", before, cwd=root).returncode, 0)

    def test_push_to_feature_branch_uses_merge_base(self):
        """Same tree, same base SHA, with the event facts: the merge-base accepts it."""
        with self.feature_branch(self.add_new_record, self.amend_new_record_readme) as (root, before):
            r = run(APP, "--base", before, *self.FEATURE_PUSH, cwd=root)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("merge-base", r.stdout)

    def test_push_to_feature_branch_fails_on_landed_record(self):
        """What the merge-base rule must still catch: rewriting evidence from main."""
        with self.feature_branch(self.touch_harness,
                                 lambda r: (r / self.REC).write_text("{}")) as (root, before):
            self.assertNotEqual(run(APP, "--base", before, *self.FEATURE_PUSH, cwd=root).returncode, 0)

    def test_push_to_feature_branch_fails_on_landed_record_readme(self):
        with self.feature_branch(self.touch_harness,
                                 lambda r: (r / self.REC_README).write_text("rewritten\n")) as (root, before):
            self.assertNotEqual(run(APP, "--base", before, *self.FEATURE_PUSH, cwd=root).returncode, 0)

    def test_push_to_feature_branch_fails_on_landed_record_deletion(self):
        """A deletion must not be read as an addition once the base moves."""
        with self.feature_branch(self.touch_harness,
                                 lambda r: (r / self.REC).unlink()) as (root, before):
            self.assertNotEqual(run(APP, "--base", before, *self.FEATURE_PUSH, cwd=root).returncode, 0)

    def push_to_main(self, change, *flags):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            git(root, "init", "-q", "-b", "main")
            make_tree(root, GOOD, record_readme=True)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "base")
            before = git(root, "rev-parse", "HEAD")
            change(root)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "direct push")
            return run(APP, "--base", before, *flags, cwd=root).returncode

    def test_push_to_default_branch_keeps_prepush_base(self):
        """On main, merge-base(main, HEAD) is HEAD and the diff would go empty.

        The pre-push SHA is kept there, so a direct push that rewrites landed
        evidence still fails instead of passing vacuously.
        """
        self.assertNotEqual(
            self.push_to_main(lambda r: (r / self.REC).write_text("{}"), *self.DEFAULT_PUSH), 0)

    def test_push_with_unknown_ref_keeps_prepush_base(self):
        """A missing event fact degrades to the stricter base, never to a skip."""
        self.assertNotEqual(
            self.push_to_main(lambda r: (r / self.REC).write_text("{}"),
                              "--event-name", "push", "--fallback-ref", "main"), 0)

    def test_push_to_default_branch_passes_a_clean_push(self):
        self.assertEqual(self.push_to_main(self.touch_harness, *self.DEFAULT_PUSH), 0)


class RecordNotIgnoredTests(unittest.TestCase):
    """A tracked record file an ignore rule still matches (#260, #263).

    The seed is the force-add mask itself: the two evidence files are committed
    with `git add -f`, so the tree is "clean" to `git status` and only the
    checker can see that their rules are broken. A fix is a negation that
    re-includes the path, the exact shape #262 landed for all four families.
    """

    LOG = "sim/s/records/20260101T000000Z/yosys_n1.log"
    CORNER = "sim/s/corners/tt.json"

    def scenario(self, gitignore, force_add=(LOG, CORNER)):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            git(root, "init", "-q", "-b", "main")
            make_tree(root, GOOD, record_readme=True)
            for f in force_add:
                p = root / f
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x\n")
            (root / ".gitignore").write_text(gitignore)
            git(root, "add", "-A")
            git(root, "add", "-f", *force_add)
            git(root, "commit", "-qm", "seed")
            return run(IGN, cwd=root)

    def test_correct_negations_pass(self):
        self.assertEqual(self.scenario(
            "*.log\n"
            "!sim/s/records/**/*.log\n"
            "sim/s/corners/*.json\n"
            "!sim/s/corners/*.json\n").returncode, 0)

    def test_tracked_but_ignored_fails(self):
        # the negative control: both files committed, rules broken. Exactly 1
        # -- an exit 2 here means the checker never ran, not that it caught it.
        r = self.scenario("*.log\nsim/s/corners/*.json\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn(self.LOG, r.stderr)
        self.assertIn(self.CORNER, r.stderr)
        self.assertIn(".gitignore:", r.stderr)

    def test_negation_fixed_for_one_family_still_flags_the_other(self):
        r = self.scenario("*.log\n!sim/s/records/**/*.log\nsim/s/corners/*.json\n")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn(self.LOG, r.stderr)
        self.assertIn(self.CORNER, r.stderr)

    def test_top_level_records_dir_counts(self):
        # membership is "a records component below the root", so a top-level
        # records/ directory is covered too -- not is_record()'s root-gated set
        r = self.scenario("records/*.json\n", force_add=("records/top.json",))
        self.assertEqual(r.returncode, 1)
        self.assertIn("records/top.json", r.stderr)

    def test_non_record_ignored_file_is_out_of_scope(self):
        r = self.scenario(
            "*.log\n"
            "!sim/s/records/**/*.log\n"
            "sim/s/corners/*.json\n"
            "!sim/s/corners/*.json\n",
            force_add=("sim/s/scratch.log",))
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("scratch.log", r.stderr)

    def test_git_failure_exits_2(self):
        # not a repository: git cannot answer at all, and exit 1 would let a
        # broken environment satisfy the negative control above
        with tempfile.TemporaryDirectory() as t:
            r = run(IGN, cwd=Path(t))
        self.assertEqual(r.returncode, 2)

    PEX_REC = "layout/pex/records/20260101T000000Z/record.json"


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

    def sha(self, root, rel):
        return "sha256:" + hashlib.sha256((root / rel).read_bytes()).hexdigest()

    def tree(self, root):
        for rel, text in [(self.STREAM, "stream bytes v1\n"),
                          (self.NETLIST, "module m; endmodule\n"),
                          *[(s, f"schematic {s}\n") for s in self.SCHEMS]]:
            self.put_raw(root, rel, text)
        self.put(root, self.RECORD, {
            "layout": {"path": self.STREAM, "scope": "repo"},
            "netlist": {"path": None, "scope": "external"},
            "provenance": {"input": {"content_hash": self.sha(root, self.STREAM),
                                     "role": "layout"}},
        })
        self.put(root, self.PNR, {
            "file": None,
            "layout": {"path": None, "scope": "external"},
            "netlist": {"path": self.NETLIST, "scope": "repo"},
            "verilog_path": "/scratch/old-tree/layout/pnr/.klt/aib_datapath.v",
            "provenance": {"input": {"content_hash": self.sha(root, self.NETLIST),
                                     "role": "netlist"}},
        })
        self.put(root, self.MULTI, {
            "provenance": {"input": {
                "content_hash": "sha256:" + "4" * 64,
                "paths": [{"path": {"path": s, "scope": "repo"},
                           "content_hash": self.sha(root, s)} for s in self.SCHEMS],
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



README_STATUS = HERE / "check_readme_status.py"


class ReadmeStatusTests(unittest.TestCase):
    """The README's met-count sentence must match the committed signoff record.

    One anchored sentence — "16 of 22 T1 signoff rows read `met`" — checked
    against t1_met_count / t1_item_count; absent, wrong, or stated twice fail.
    The anchor is the T1/signoff wording, so the item-8 aggregate ("16 pass,
    3 fail, 11 not-yet-measured of 30 spec rows") and the characterization
    report's "16 of 30 rows" cannot satisfy or collide with it (#270).
    """

    MET_SENTENCE = "16 of 22 T1 signoff rows read `met`"

    def check(self, mutate=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "signoff").mkdir(parents=True)
            shutil.copy(REPO / "signoff/block-manifest.signoff.json",
                        root / "signoff/block-manifest.signoff.json")
            (root / "README.md").write_text(
                "Intro.\n\n" + self.MET_SENTENCE + "\n\nOutro.\n")
            if mutate:
                mutate(root)
            return run(README_STATUS, "--root", root).returncode

    def test_the_repo_conforms(self):
        self.assertEqual(run(README_STATUS, "--root", REPO).returncode, 0)

    def test_good_fixture(self):
        self.assertEqual(self.check(), 0)

    def test_wrong_met_count_fails(self):
        def edit(r):
            p = r / "README.md"
            p.write_text(p.read_text().replace("16 of 22", "15 of 22"))
        self.assertNotEqual(self.check(edit), 0)

    def test_wrong_denominator_fails(self):
        def edit(r):
            p = r / "README.md"
            p.write_text(p.read_text().replace("16 of 22", "16 of 21"))
        self.assertNotEqual(self.check(edit), 0)

    def test_sentence_absent_fails(self):
        def edit(r):
            p = r / "README.md"
            p.write_text(p.read_text().replace(self.MET_SENTENCE, "Most T1 rows read `met`."))
        self.assertNotEqual(self.check(edit), 0)

    def test_duplicated_sentence_fails(self):
        def edit(r):
            p = r / "README.md"
            p.write_text(p.read_text() + self.MET_SENTENCE + "\n")
        self.assertNotEqual(self.check(edit), 0)

    def test_characterization_phrasing_does_not_satisfy(self):
        # the aggregate's different denominator must not pass for the T1 count
        def edit(r):
            p = r / "README.md"
            p.write_text(p.read_text().replace(
                self.MET_SENTENCE,
                "16 of 30 rows have a recorded value that meets its target"))
        self.assertNotEqual(self.check(edit), 0)

    def test_item8_summary_does_not_satisfy(self):
        def edit(r):
            p = r / "README.md"
            p.write_text(p.read_text().replace(
                self.MET_SENTENCE,
                "16 pass, 3 fail, 11 not-yet-measured of 30 spec rows"))
        self.assertNotEqual(self.check(edit), 0)

    def test_missing_record_fails(self):
        def edit(r):
            (r / "signoff/block-manifest.signoff.json").unlink()
        self.assertNotEqual(self.check(edit), 0)



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

    def test_every_check_capable_generator_is_fresh(self):
        # Derived, not hand-kept (#266): every tracked gen_*.py that has a --check
        # flag must report fresh. The filter is EXEMPT plus NO_CHECK_FLAG -- the two
        # freshness questions -- never STRICTNESS_UNASSERTABLE, which answers flag
        # strictness, a different property.
        for gen in FRESHNESS_SUBJECTS:
            r = run(REPO / gen, "--check", cwd=REPO)
            self.assertEqual(r.returncode, 0, f"{gen} --check: {r.stdout}{r.stderr}")

    def test_no_check_flag_entries_are_real_and_reasoned(self):
        # The freshness exemption is hand-kept, so it gets the completeness
        # treatment too: every entry still tracked, with a stated reason. And it is
        # a freshness exemption only -- an entry has no --check flag yet still
        # parses strictly, so it stays a strict-flag subject (#266).
        tracked = set(git(REPO, "ls-files").splitlines())
        for path, reason in NO_CHECK_FLAG.items():
            with self.subTest(path=path):
                self.assertIn(path, tracked, "NO_CHECK_FLAG entry is no longer tracked; drop it")
                self.assertTrue(reason.strip(), "NO_CHECK_FLAG entry needs a reason")
                self.assertNotIn(path, FRESHNESS_SUBJECTS)
                self.assertIn(path, STRICT_FLAG_SUBJECTS)

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


class EveryGeneratorParsesItsFlagsStrictlyTests(unittest.TestCase):
    """A mistyped --check must report, never silently regenerate (#227).

    Three of the six used to test `"--check" in argv`, so any other argument meant "write":
    `gen_clock_path.py --chek` rewrote the generated files and exited 0 on a stale tree.
    The consolidation fixed the tree (#227, #239, #256, #265); gen_specs.py read no
    argv at all, parsing bare because regenerating its two committed specs needs the
    pinned klt environment, until #277 moved its klayout import into the call path.
    #266 fixed the test: its subjects used to be hand-kept tables of generators already
    known to pass (GENERATORS, plus STRICT_WITHOUT_COMMITTED_OUTPUT for the ones with
    no committed output to key an mtime on, #271), so a generator could join the tree
    unasserted until its author remembered the table -- the exact rot the check-list
    completeness test below exists for (#173, #219).
    Subjects are now every tracked gen_*.py minus STRICTNESS_UNASSERTABLE, and a refused
    run must leave `git status --porcelain` byte-identical -- not merely leave one named
    output's mtime alone.
    """

    def test_attest_item2_refuses_an_unknown_flag_and_writes_no_envelope(self):
        # #265: `attest_item2.py digital --chek` used to take the write branch, rewrite
        # signoff/attest/item2-digital.json and exit 0 printing "status: pass", so the
        # operator who typed it read a check report over a freshly regenerated envelope.
        # It now parses its arguments before importing klayout_tools, so this assertion
        # holds in PDK-free CI as well as in the pinned klt environment.
        for argv in (("--chek",), ("digital", "--chek"), ("analog", "--chek"), ("bogus",)):
            with self.subTest(argv=argv):
                before = [(REPO / e).stat().st_mtime_ns for e in ATTEST_ENVELOPES]
                r = run(REPO / ATTEST_ITEM2, *argv, cwd=REPO)
                self.assertEqual(r.returncode, 2,
                                 f"{ATTEST_ITEM2} {' '.join(argv)}: {r.stdout}{r.stderr}")
                self.assertEqual([(REPO / e).stat().st_mtime_ns for e in ATTEST_ENVELOPES],
                                 before, f"{ATTEST_ITEM2} {' '.join(argv)} rewrote an envelope")

    def test_an_unknown_flag_exits_2_and_writes_nothing(self):
        # The tree snapshot, not one named output's mtime, is the write assertion
        # (#266): it sees every output and any untracked byproduct visible to
        # `git status --porcelain`. It has two blind shapes (#307): an empty
        # directory -- git tracks no empty directories, so --porcelain never
        # lists one -- and a write into a gitignored path, invisible without
        # --ignored, which on this tree includes anything matching the
        # tree-wide *.raw/*.log/*.vcd/*.vvp rules. cwd is pinned to the repo
        # so a generator writing relative to the process cwd lands inside the
        # snapshot. The two checks below are complementary, and both stay:
        # the snapshot sees writes relative to the repo, the empty-cwd run
        # sees empty-directory and gitignored writes relative to cwd; neither
        # subsumes the other.
        for gen in STRICT_FLAG_SUBJECTS:
            with self.subTest(gen=gen):
                before = git(REPO, "status", "--porcelain")
                r = run(REPO / gen, "--chek", cwd=REPO)
                self.assertEqual(r.returncode, 2, f"{gen} --chek: {r.stdout}{r.stderr}")
                self.assertEqual(git(REPO, "status", "--porcelain"), before,
                                 f"{gen} --chek wrote to the tree")
                # #307: the same refusal from an empty cwd must leave that
                # directory empty -- exactly the shapes the snapshot cannot
                # see (an empty directory, a gitignored name).
                with tempfile.TemporaryDirectory() as t:
                    r = run(REPO / gen, "--chek", cwd=t)
                    self.assertEqual(r.returncode, 2,
                                     f"{gen} --chek from an empty cwd: {r.stdout}{r.stderr}")
                    self.assertEqual(sorted(q.name for q in Path(t).iterdir()), [],
                                     f"{gen} --chek created something in an empty cwd")

    def test_strictness_unassertable_entries_are_real_and_reasoned(self):
        # The one hand-kept table left in the subject selection is the exemption, so
        # it gets the completeness treatment: every entry still tracked, still a
        # gen_*.py script, with a reason that says something.
        tracked = set(git(REPO, "ls-files").splitlines())
        for path, reason in STRICTNESS_UNASSERTABLE.items():
            with self.subTest(path=path):
                self.assertIn(path, tracked,
                              "STRICTNESS_UNASSERTABLE entry is no longer tracked; drop it")
                self.assertTrue(fnmatch.fnmatch(posixpath.basename(path), "gen_*.py"),
                                "STRICTNESS_UNASSERTABLE entry is not a gen_*.py script")
                self.assertTrue(reason.strip(),
                                "STRICTNESS_UNASSERTABLE entry needs a reason")

    def test_the_gen_specs_exemption_does_not_also_claim_loose_flags(self):
        # #277 split the two properties the "generator with no check mode" reason
        # used to answer at once, then moved gen_specs.py's klayout import into the
        # call path: the exemption states no check mode and nothing more, and strict
        # parsing is asserted for it with every other derived subject (#266).
        reason = EXEMPT["layout/erc/gen_specs.py"]
        self.assertIn("no check mode", reason)
        self.assertNotIn("layout/erc/gen_specs.py", STRICTNESS_UNASSERTABLE)
        self.assertIn("layout/erc/gen_specs.py", STRICT_FLAG_SUBJECTS)

    def test_gen_t16attr_refuses_every_argument_shape(self):
        """#271: gen_t16attr.py read its OUTDIR off argv[0], so every argument was a
        valid output path -- `--check` exited 0 having checked nothing and left a
        directory named `--check` behind. The derived test above pins `--chek` for it
        like every other subject; this one keeps the wider argument shapes that defect
        needed. Run from an empty cwd, so a stray relative path shows up as a file in
        it rather than landing in the repo.
        """
        gen = "sim/channel-eye/gen_t16attr.py"
        # no argument at all; an unknown flag; `--check` alone and after a good
        # OUTDIR (ignoring a trailing flag is the same silent accept).
        for argv in ([], ["--chek", "out"], ["--check"], ["out", "--check"]):
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as t:
                r = run(REPO / gen, *argv, cwd=t)
                self.assertEqual(r.returncode, 2,
                                 f"{gen} {' '.join(argv)}: {r.stdout}{r.stderr}")
                self.assertEqual(sorted(q.name for q in Path(t).iterdir()), [],
                                 f"{gen} {' '.join(argv)} created something")

    def test_gen_t16attr_still_writes_when_given_an_outdir(self):
        # The refusals above must not be bought by breaking the generator: its one
        # positional OUTDIR is load-bearing (sim/channel-eye/run_t16attr.sh:25).
        gen = "sim/channel-eye/gen_t16attr.py"
        written = "request_t16attr_ch_ss.json"
        with tempfile.TemporaryDirectory() as t:
            r = run(REPO / gen, t)
            self.assertEqual(r.returncode, 0, f"{gen} OUTDIR: {r.stdout}{r.stderr}")
            self.assertTrue((Path(t) / written).is_file(),
                            f"{gen} OUTDIR did not write {written}")

    def test_the_strict_flag_subjects_are_not_decided_by_exempt_membership(self):
        # #266 derives these subjects from discovery, filtered by
        # STRICTNESS_UNASSERTABLE -- the only reason that actually blocks the
        # assertion. The filter must never be EXEMPT, which answers "has no check
        # mode", a question separate from flag strictness since #271: gen_t16attr.py
        # is the witness, both EXEMPT from the check list and a strict-flag subject.
        self.assertTrue(set(STRICT_FLAG_SUBJECTS) & set(EXEMPT),
                        "no EXEMPT generator is a strict-flag subject any more: being "
                        "EXEMPT has become what decides whether strictness is asserted, "
                        "which is the coupling #271 split apart")
        self.assertIn("sim/channel-eye/gen_t16attr.py", STRICT_FLAG_SUBJECTS)
        self.assertNotIn("layout/gen_io_column.py", STRICT_FLAG_SUBJECTS)


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
        "--check runs in test_every_check_capable_generator_is_fresh",
    ),
    "sim/clock-path/gen_clock_path.py": (
        "scripts/ci/test_checkers.py",
        "--check runs in test_every_check_capable_generator_is_fresh",
    ),
    "sim/io-cell-study/gen_io_cell.py": (
        "scripts/ci/test_checkers.py",
        "--check runs in test_every_check_capable_generator_is_fresh",
    ),
    "sim/redundancy-mux/gen_redundancy_mux.py": (
        "scripts/ci/test_checkers.py",
        "--check runs in test_every_check_capable_generator_is_fresh",
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
    "layout/erc/gen_specs.py":
        "generator with no check mode: its two ERC specs are committed signoff inputs "
        "regenerated only at a klt re-pin (signoff/README.md:429), so proving them fresh "
        "would need the pinned klt environment no CI job runs. Flag strictness is a "
        "separate property and is asserted -- it stays a strict-flag subject (#266)",
    "sim/channel-eye/gen_t16attr.py":
        "generator with no check mode: its four request JSONs are gitignored "
        "(.gitignore:24-27) and run_t16attr.sh regenerates them before every run, so no "
        "committed tree exists for a --check to prove fresh. Flag strictness is a "
        "separate property and is asserted -- it stays a strict-flag subject (#271, #266)",
    "sim/gen_common.py": "the shared write-or-check helper (#227); imported, never run",
}

# Generators for which strict flag parsing cannot be asserted in PDK-free CI, with the
# only reason that can excuse an entry: the script cannot be run here at all. The
# strict-flag test above derives its subjects as every tracked gen_*.py minus this
# table (#266) -- discovered, not hand-kept, so a generator that joins the tree
# without an entry here is asserted, not silently untested. That is the same rule the
# check-list completeness test below applies to checkers (#173, #219). It is a
# different question from EXEMPT above, which answers "has no check mode" (#271
# split the two): gen_t16attr.py is EXEMPT and still a subject.
STRICTNESS_UNASSERTABLE = {
    "layout/gen_io_column.py":
        "imports klayout.db at module import; needs the pinned klt environment, "
        "like layout/check_io_column.py",
    "sim/gen_common.py":
        "the shared write-or-check helper (#227); imported, never run",
}

# gen_*.py candidates the freshness test cannot run `--check` on, with the reason.
# EXEMPT covers the ones with nothing committed to check; this table covers "the
# check is the default mode" -- and the listed-outright case, since the completeness
# check below refuses a table entry for a file check_local.sh runs itself. A
# freshness-exemption reason only: every entry still parses strictly and stays a
# strict-flag subject (#266).
NO_CHECK_FLAG = {
    "scripts/ci/gen_item6_digital.py":
        "no --check flag: checking is its default mode and --regenerate rewrites; "
        "listed outright in check_local.sh, so it cannot carry an EXEMPT entry",
}


def gen_scripts(tracked):
    """Every tracked path whose basename matches gen_*.py: the generator-subject pool."""
    return sorted(p for p in tracked
                  if fnmatch.fnmatch(posixpath.basename(p), "gen_*.py"))


TRACKED_GEN_SCRIPTS = gen_scripts(git(REPO, "ls-files").splitlines())
STRICT_FLAG_SUBJECTS = [p for p in TRACKED_GEN_SCRIPTS if p not in STRICTNESS_UNASSERTABLE]
FRESHNESS_SUBJECTS = [p for p in TRACKED_GEN_SCRIPTS
                      if p not in set(EXEMPT) | set(NO_CHECK_FLAG)]


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

    def test_the_no_check_mode_exemption_does_not_also_claim_loose_flags(self):
        # #271 split two properties this table used to answer at once. The reason has
        # to state why there is no check mode -- nothing committed to check -- without
        # leaving a reader to infer that the script therefore accepts any argument:
        # gen_t16attr.py parses strictly and stays a strict-flag subject (#266).
        reason = EXEMPT["sim/channel-eye/gen_t16attr.py"]
        self.assertIn("gitignored", reason)
        self.assertIn("sim/channel-eye/gen_t16attr.py", STRICT_FLAG_SUBJECTS)

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


# ---------------------------------------------------------------------------
# No generator keeps a private copy of a shared helper (#256)
#
# gen_redundancy_mux.py was written after the #227 consolidation and still
# carried its own write-or-check loop and its own byte-identical `pwl` /
# `level_pwl`. Nothing failed when it did, so the drift was only found by
# reading. This test is that missing assertion: a tracked `gen_*.py` may not
# define a builder whose name is one gen_common already owns, unless it is
# listed below with the reason its version genuinely differs.
# ---------------------------------------------------------------------------

GEN_COMMON = "sim/gen_common.py"
SHARED_BUILDERS = ("pwl", "level_pwl")

# "<path>:<name>" -> why this generator's own version is not the shared one.
PRIVATE_BUILDERS_OK = {
    "sim/mc/capture_window/gen_t19.py:pwl":
        "formats times in ns via its own ns() helper, not seconds; a different card body",
}


def shadowed_helper_errors(tracked, read_text, owner, names, glob_pattern, table, ok,
                           all_tracked=None):
    """Return a sorted list of definitions that shadow a helper `owner` already defines.

    Pure: the tracked set, the reader, the owning module, the guarded names and
    their file glob, the exemption table and its name are all passed in, so each
    guard can be exercised against a fixture without touching the real tree.
    When `tracked` is path-scoped, pass the unfiltered set as `all_tracked` so
    the stale-entry loop can tell "no longer tracked" from "tracked but outside
    this guard's scope".
    """
    tracked = set(tracked)
    known = tracked if all_tracked is None else set(all_tracked)
    defs = re.compile(r"^def (%s)\(" % "|".join(names), re.M)
    errors = []
    for path in sorted(q for q in tracked
                       if q != owner                        # the module that owns them
                       and fnmatch.fnmatch(posixpath.basename(q), glob_pattern)):
        for name in defs.findall(read_text(path)):
            key = f"{path}:{name}"
            if key in ok:
                if not ok[key].strip():
                    errors.append(f"{key}: {table} entry needs a reason")
                continue
            errors.append(f"{key}: a private copy of a {owner} helper -- import it "
                          f"instead, or add a {table} entry saying how it differs")
    for key in sorted(ok):
        path, _, name = key.rpartition(":")
        if path not in known:
            errors.append(f"{key}: entry names a path that is no longer tracked; drop it")
        elif path not in tracked:
            errors.append(f"{key}: entry names a path outside this guard's scope; drop it")
        elif f"def {name}(" not in read_text(path):
            errors.append(f"{key}: entry names a definition that is gone; drop it")
    return sorted(errors)


def private_builder_errors(tracked, read_text, ok=None):
    """Return a sorted list of `gen_*.py` definitions that shadow a gen_common builder."""
    return shadowed_helper_errors(tracked, read_text, GEN_COMMON, SHARED_BUILDERS,
                                  "gen_*.py", "PRIVATE_BUILDERS_OK",
                                  PRIVATE_BUILDERS_OK if ok is None else ok)


class NoPrivateCopyOfASharedBuilderTests(unittest.TestCase):
    """#256: the consolidation must not quietly lapse the next time a generator is added."""

    @classmethod
    def setUpClass(cls):
        cls.tracked = git(REPO, "ls-files").splitlines()

    def read(self, path):
        return (REPO / path).read_text()

    def test_no_tracked_generator_shadows_a_gen_common_builder(self):
        errors = private_builder_errors(self.tracked, self.read)
        self.assertEqual(errors, [], "\n" + "\n".join(errors))

    def test_gen_common_actually_defines_every_name_this_test_guards(self):
        # Otherwise the guard would pass by guarding nothing.
        text = (REPO / "sim/gen_common.py").read_text()
        for name in SHARED_BUILDERS:
            self.assertIn(f"def {name}(", text)

    # -- the detector itself, against a fixture ------------------------------

    def test_an_unlisted_private_copy_is_reported(self):
        errors = private_builder_errors(
            ["sim/x/gen_x.py"], lambda p: "def pwl(points):\n    return 1\n", ok={})
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("sim/x/gen_x.py:pwl", errors[0])

    def test_a_listed_private_copy_is_allowed(self):
        self.assertEqual(
            private_builder_errors(["sim/x/gen_x.py"], lambda p: "def pwl(points):\n    return 1\n",
                                   ok={"sim/x/gen_x.py:pwl": "it formats times differently"}),
            [])

    def test_a_listed_private_copy_still_needs_a_reason(self):
        errors = private_builder_errors(["sim/x/gen_x.py"], lambda p: "def pwl(points):\n    return 1\n",
                                        ok={"sim/x/gen_x.py:pwl": "  "})
        self.assertTrue(any("needs a reason" in e for e in errors), errors)

    def test_a_generator_that_only_calls_the_shared_builder_is_clean(self):
        self.assertEqual(
            private_builder_errors(["sim/x/gen_x.py"],
                                   lambda p: "x = gen_common.pwl(gen_common.level_pwl(e, 100, 2))\n",
                                   ok={}),
            [])

    def test_a_stale_exemption_is_reported(self):
        errors = private_builder_errors(["sim/x/gen_x.py"], lambda p: "def ns(ps):\n    return ps\n",
                                        ok={"sim/x/gen_x.py:pwl": "gone now"})
        self.assertTrue(any("definition that is gone" in e for e in errors), errors)

    def test_gen_common_itself_is_not_its_own_private_copy(self):
        # It matches the gen_*.py glob and defines both builders; it is the owner, not a copy.
        self.assertEqual(
            private_builder_errors([GEN_COMMON], lambda p: "def pwl(x):\n    return 1\n", ok={}),
            [])

    def test_an_exemption_for_an_untracked_path_is_reported(self):
        errors = private_builder_errors([], lambda p: "", ok={"sim/gone/gen_gone.py:pwl": "r"})
        self.assertTrue(any("no longer tracked" in e for e in errors), errors)


# ---------------------------------------------------------------------------
# No checker keeps a private copy of a manifest_pins helper (#283)
#
# manifest_pins.py is the one definition of the derived_inputs pin contract;
# before #283 two checkers each hand-kept a sha() and a pin loop and no test
# compared them against each other. This is the #256 guard again, scoped to the
# check_*.py family: a tracked check_*.py may not define a helper manifest_pins
# already owns, unless it is listed below with the reason its version genuinely
# differs. The generators keep their builder guard above and, since #292, their
# own pin guard below.
# ---------------------------------------------------------------------------

MANIFEST_PINS = "scripts/ci/manifest_pins.py"
SHARED_PIN_HELPERS = ("sha", "manifest_block", "verify_pins")

# "<path>:<name>" -> why this checker's own version is not the shared one.
PIN_HELPERS_OK = {}


def private_pin_helper_errors(tracked, read_text, ok=None):
    """Return a sorted list of `check_*.py` definitions that shadow a manifest_pins helper."""
    return shadowed_helper_errors(tracked, read_text, MANIFEST_PINS, SHARED_PIN_HELPERS,
                                  "check_*.py", "PIN_HELPERS_OK",
                                  PIN_HELPERS_OK if ok is None else ok)


# ---------------------------------------------------------------------------
# No generator beside manifest_pins keeps a private copy of a pin helper (#292)
#
# #283's guard is scoped to check_*.py, so the gap it left regrew: the
# generators under scripts/ci hand-kept the same digest formula again --
# gen_characterization_report.py its own MANIFEST and sha256 line,
# check_design_sources.py the combined-hash formula. This is that guard
# again, scoped to the gen_*.py directly beside manifest_pins. It is
# deliberately narrower than the builder guard above (which reaches every
# tracked gen_*.py): only a generator in this directory imports manifest_pins
# without a cross-tree dependency, and the layout/ and sim/ generators
# compute bare-hex digests with a different formula that must keep their own.
# Only `sha` is guarded: a generator writes artefacts, it does not verify
# pins, so manifest_block/verify_pins are not names a gen_*.py would
# plausibly regrow.
# ---------------------------------------------------------------------------

GEN_PIN_HELPERS = ("sha",)

# "<path>:<name>" -> why this generator's own version is not the shared one.
GEN_PIN_HELPERS_OK = {}


def private_gen_pin_helper_errors(tracked, read_text, ok=None):
    """Return a sorted list of scripts/ci `gen_*.py` defs shadowing a manifest_pins helper."""
    beside_pins = [p for p in tracked if posixpath.dirname(p) == "scripts/ci"]
    return shadowed_helper_errors(beside_pins, read_text, MANIFEST_PINS, GEN_PIN_HELPERS,
                                  "gen_*.py", "GEN_PIN_HELPERS_OK",
                                  GEN_PIN_HELPERS_OK if ok is None else ok,
                                  all_tracked=tracked)


# ---------------------------------------------------------------------------
# No file beside manifest_pins spells the digest formula or manifest path
# constant inline (#304)
#
# The name guards above match `^def <name>(` and so cannot see the forms
# #292's two live defect instances actually took: a private `MANIFEST`
# constant and the digest formula written out as an expression
# (`gen_characterization_report.py` kept both, `check_design_sources.py`
# re-spelled the combined-hash formula). This asserts over the tracked
# scripts/ci *.py that neither spelling regrows. The sha256 pattern is keyed
# on the whole `"sha256:" + hashlib.sha256(` expression, not the bare prefix:
# the prefix alone also matches the `"sha256:" + "0" * 64` fixture literals
# used throughout this file. It is a substring gate, so an occurrence inside
# a comment or docstring is reported like any other -- a commented-out copy
# of the formula should not survive either.
# ---------------------------------------------------------------------------

FORMULA_PATTERNS = {
    "sha256-formula": re.compile(re.escape('"sha256:" + hashlib.sha256('), re.M),
    "manifest-constant": re.compile(r"^MANIFEST\s*=", re.M),
}

# "<path>:<pattern>" -> why this site is the formula's legitimate home.
INLINE_FORMULA_OK = {
    "scripts/ci/manifest_pins.py:sha256-formula":
        "the canonical owner: manifest_pins.sha() spells the digest formula once",
    "scripts/ci/test_checkers.py:sha256-formula":
        "the fixture helper these self-tests drive, not a second definition",
    "scripts/ci/manifest_pins.py:manifest-constant":
        "the canonical owner of the manifest path constant",
}


def inline_formula_errors(tracked, read_text, ok=None):
    """Return a sorted list of scripts/ci files spelling a guarded formula inline.

    Pure: the tracked set, the reader and the exemption table are all passed
    in, so the guard can be exercised against a fixture without touching the
    real tree. `tracked` is the unfiltered tracked set; the guard derives its
    scripts/ci *.py scope from it, so a stale entry naming a tracked file
    elsewhere is reported as out of scope rather than untracked.
    """
    ok = INLINE_FORMULA_OK if ok is None else ok
    beside_pins = [p for p in tracked
                   if posixpath.dirname(p) == "scripts/ci" and p.endswith(".py")]
    known = set(tracked)
    errors = []
    for path in sorted(beside_pins):
        text = read_text(path)
        for name, pattern in FORMULA_PATTERNS.items():
            if not pattern.search(text):
                continue
            key = f"{path}:{name}"
            if key not in ok:
                errors.append(f"{key}: a private copy of a manifest_pins formula -- "
                              f"import it from manifest_pins instead, or add an "
                              f"INLINE_FORMULA_OK entry saying why this site spells it")
            elif not ok[key].strip():
                errors.append(f"{key}: INLINE_FORMULA_OK entry needs a reason")
    for key in sorted(ok):
        path, _, name = key.rpartition(":")
        if name not in FORMULA_PATTERNS:
            errors.append(f"{key}: entry names a pattern this guard does not check; drop it")
        elif path not in known:
            errors.append(f"{key}: entry names a path that is no longer tracked; drop it")
        elif path not in beside_pins:
            errors.append(f"{key}: entry names a path outside this guard's scope; drop it")
        elif not FORMULA_PATTERNS[name].search(read_text(path)):
            errors.append(f"{key}: entry names a formula site that is gone; drop it")
    return sorted(errors)


class NoInlineFormulaDuplicationTests(unittest.TestCase):
    """#304: the digest formula must be spelled exactly once, and by manifest_pins."""

    @classmethod
    def setUpClass(cls):
        cls.tracked = git(REPO, "ls-files").splitlines()

    def read(self, path):
        return (REPO / path).read_text()

    # -- the live tree --------------------------------------------------------

    def test_no_tracked_ci_file_spells_a_guarded_formula_inline(self):
        errors = inline_formula_errors(self.tracked, self.read)
        self.assertEqual(errors, [], "\n" + "\n".join(errors))

    # -- the detector, against a fixture --------------------------------------

    def test_an_unlisted_inline_digest_formula_is_reported(self):
        errors = inline_formula_errors(
            ["scripts/ci/gen_x.py"],
            lambda p: 'return "sha256:" + hashlib.sha256(b).hexdigest()\n', ok={})
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("scripts/ci/gen_x.py:sha256-formula", errors[0])

    def test_a_private_manifest_constant_is_reported(self):
        errors = inline_formula_errors(
            ["scripts/ci/gen_x.py"],
            lambda p: 'MANIFEST = "signoff/block-manifest.json"\n', ok={})
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("scripts/ci/gen_x.py:manifest-constant", errors[0])

    def test_the_anchored_manifest_pattern_stays_off_the_prefixed_names(self):
        # MANIFEST_KEY (check_design_sources.py) and MANIFEST_PINS (this file)
        # are different constants; the ^ anchor is what keeps them out.
        text = 'MANIFEST_KEY = "1.digital"\nMANIFEST_PINS = "scripts/ci/manifest_pins.py"\n'
        self.assertEqual(
            inline_formula_errors(["scripts/ci/check_x.py"], lambda p: text, ok={}),
            [])

    def test_an_occurrence_inside_a_comment_is_reported_too(self):
        # Decided: the gate is a substring gate and does not parse comments.
        errors = inline_formula_errors(
            ["scripts/ci/gen_x.py"],
            lambda p: '# return "sha256:" + hashlib.sha256(b).hexdigest()\n', ok={})
        self.assertEqual(len(errors), 1, errors)

    def test_the_owner_is_allowed_by_the_table(self):
        fixture = {
            "scripts/ci/manifest_pins.py":
                'MANIFEST = "signoff/block-manifest.json"\n'
                'return "sha256:" + hashlib.sha256(data).hexdigest()\n',
            "scripts/ci/test_checkers.py":
                'return "sha256:" + hashlib.sha256((root / rel).read_bytes()).hexdigest()\n',
        }
        errors = inline_formula_errors(sorted(fixture), fixture.get)
        self.assertEqual(errors, [])

    def test_an_exemption_still_needs_a_reason(self):
        errors = inline_formula_errors(
            ["scripts/ci/gen_x.py"],
            lambda p: 'return "sha256:" + hashlib.sha256(b).hexdigest()\n',
            ok={"scripts/ci/gen_x.py:sha256-formula": "  "})
        self.assertTrue(any("needs a reason" in e for e in errors), errors)

    def test_a_stale_exemption_is_reported(self):
        errors = inline_formula_errors(
            ["scripts/ci/gen_x.py"], lambda p: "import hashlib\n",
            ok={"scripts/ci/gen_x.py:sha256-formula": "gone now"})
        self.assertTrue(any("site that is gone" in e for e in errors), errors)

    def test_an_exemption_for_an_untracked_path_is_reported(self):
        errors = inline_formula_errors([], lambda p: "", ok={
            "scripts/ci/gone.py:sha256-formula": "r"})
        self.assertTrue(any("no longer tracked" in e for e in errors), errors)

    def test_an_exemption_outside_the_guard_scope_says_so(self):
        errors = inline_formula_errors(
            ["scripts/ci/gen_x.py", "sim/gen_x.py"], lambda p: "", ok={
                "sim/gen_x.py:sha256-formula": "tracked, but not beside manifest_pins"})
        self.assertTrue(any("outside this guard's scope" in e for e in errors), errors)

    def test_a_table_entry_for_an_unknown_pattern_is_reported(self):
        errors = inline_formula_errors(
            ["scripts/ci/gen_x.py"], lambda p: "",
            ok={"scripts/ci/gen_x.py:sha256 formula": "typo"})
        self.assertTrue(any("pattern this guard does not check" in e for e in errors),
                        errors)


class NoPrivateCopyOfAPinHelperTests(unittest.TestCase):
    """#283: the manifest-pin consolidation must not quietly lapse either."""

    @classmethod
    def setUpClass(cls):
        cls.tracked = git(REPO, "ls-files").splitlines()

    def read(self, path):
        return (REPO / path).read_text()

    def test_no_tracked_checker_shadows_a_manifest_pins_helper(self):
        errors = private_pin_helper_errors(self.tracked, self.read)
        self.assertEqual(errors, [], "\n" + "\n".join(errors))

    def test_no_tracked_ci_generator_shadows_a_manifest_pins_helper(self):
        errors = private_gen_pin_helper_errors(self.tracked, self.read)
        self.assertEqual(errors, [], "\n" + "\n".join(errors))

    def test_manifest_pins_actually_defines_every_name_this_test_guards(self):
        # Otherwise the guard would pass by guarding nothing.
        text = (REPO / MANIFEST_PINS).read_text()
        for name in SHARED_PIN_HELPERS:
            self.assertIn(f"def {name}(", text)

    def test_manifest_pins_actually_defines_every_name_the_gen_guard_guards(self):
        # Same for the generator guard's narrower name list.
        text = (REPO / MANIFEST_PINS).read_text()
        for name in GEN_PIN_HELPERS:
            self.assertIn(f"def {name}(", text)

    # -- the detector, against a fixture --------------------------------------

    def test_an_unlisted_private_copy_is_reported(self):
        errors = private_pin_helper_errors(
            ["scripts/ci/check_x.py"], lambda p: "def sha(data):\n    return 1\n")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("scripts/ci/check_x.py:sha", errors[0])

    def test_an_unlisted_ci_generator_private_copy_is_reported(self):
        # The gap #292 closes: before the gen guard this fixture was clean
        # under every pin guard in this file.
        errors = private_gen_pin_helper_errors(
            ["scripts/ci/gen_x.py"], lambda p: "def sha(data):\n    return 1\n", ok={})
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("scripts/ci/gen_x.py:sha", errors[0])

    def test_a_checker_that_only_imports_the_shared_helper_is_clean(self):
        self.assertEqual(
            private_pin_helper_errors(["scripts/ci/check_x.py"],
                                      lambda p: "from manifest_pins import sha\nsha(b'x')\n"),
            [])

    def test_a_ci_generator_that_only_imports_the_shared_helper_is_clean(self):
        self.assertEqual(
            private_gen_pin_helper_errors(["scripts/ci/gen_x.py"],
                                          lambda p: "from manifest_pins import sha\nsha(b'x')\n",
                                          ok={}),
            [])

    def test_the_pin_guards_stay_out_of_the_unrelated_families(self):
        # The check-family guard does not reach generators, and the generator
        # pin guard does not reach check_*.py, run_*.py, or a gen_*.py outside
        # scripts/ci (those import nothing from this directory).
        sha_def = "def sha(d):\n    return 1\n"
        self.assertEqual(
            private_pin_helper_errors(["scripts/ci/gen_x.py"], lambda p: sha_def),
            [])
        self.assertEqual(
            private_gen_pin_helper_errors(
                ["scripts/ci/check_x.py", "scripts/ci/run_x.py", "sim/gen_common.py"],
                lambda p: sha_def),
            [])

    def test_manifest_pins_itself_is_not_its_own_private_copy(self):
        self.assertEqual(
            private_gen_pin_helper_errors(
                [MANIFEST_PINS], lambda p: "def sha(d):\n    return 1\n", ok={}),
            [])

    def test_a_stale_exemption_is_reported(self):
        errors = private_pin_helper_errors(["scripts/ci/check_x.py"], lambda p: "",
                                           ok={"scripts/ci/check_x.py:sha": "gone now"})
        self.assertTrue(any("definition that is gone" in e for e in errors), errors)

    def test_a_stale_gen_exemption_is_reported(self):
        errors = private_gen_pin_helper_errors(["scripts/ci/gen_x.py"], lambda p: "",
                                               ok={"scripts/ci/gen_x.py:sha": "gone now"})
        self.assertTrue(any("definition that is gone" in e for e in errors), errors)

    def test_a_gen_exemption_outside_the_guard_scope_says_so(self):
        # The gen guard scans only scripts/ci, so a GEN_PIN_HELPERS_OK entry
        # naming a genuinely tracked path elsewhere must not be reported as
        # "no longer tracked" -- the file exists, it is just out of scope.
        errors = private_gen_pin_helper_errors(
            ["scripts/ci/gen_x.py", "sim/gen_common.py"], lambda p: "",
            ok={"sim/gen_common.py:sha": "tracked, but not beside manifest_pins"})
        self.assertTrue(any("outside this guard's scope" in e for e in errors), errors)
        self.assertFalse(any("no longer tracked" in e for e in errors), errors)

    def test_a_full_tracked_set_caller_keeps_the_untracked_message(self):
        # The check-family guard passes the whole tracked set, so a path that
        # is not in it is genuinely untracked and keeps the original message.
        errors = private_pin_helper_errors([], lambda p: "",
                                           ok={"sim/gone/gen_gone.py:sha": "r"})
        self.assertTrue(any("no longer tracked" in e for e in errors), errors)
        self.assertFalse(any("outside this guard's scope" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
