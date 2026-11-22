#!/usr/bin/env python3
"""Self-tests of the evidence and record-integrity checkers: each must accept a
good input and reject a seeded-bad one.

Stdlib only; PDK-free. Run alone: python3 -I scripts/ci/test_evidence_checkers.py
python3 -I drops this directory from sys.path, hence the insert below (the
check_record_not_ignored.py idiom).
"""
import contextlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _checker_test_helpers import GOOD, HERE, REPO, git, make_tree, run  # noqa: E402

FMT = HERE / "check_evidence_format.py"
APP = HERE / "check_sim_append_only.py"
IGN = HERE / "check_record_not_ignored.py"
README_STATUS = HERE / "check_readme_status.py"


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
