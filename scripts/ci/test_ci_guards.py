#!/usr/bin/env python3
"""Self-tests of the repo-wide CI hygiene and meta-guards: every generator parses
its flags strictly and is fresh, the one check list is complete, the test
aggregator loads exactly the suites that list runs, and no private copy of a
shared builder, pin helper or digest formula has regrown.

Stdlib only; PDK-free. Run alone: python3 -I scripts/ci/test_ci_guards.py
python3 -I drops this directory from sys.path, hence the insert below (the check_record_not_ignored.py idiom).
"""
import fnmatch
import importlib.util
import posixpath
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _checker_test_helpers import REPO, git, run  # noqa: E402

# layout/attest_item2.py is not a generator: it writes no generated file, it builds a
# `klt signoff --attest 2` command line. Its write targets are the two committed signoff
# envelopes, which is why its own mistyped-flag fall-through was worse than a stale bench
# file (#265) -- and why it gets an assertion of its own below.
ATTEST_ITEM2 = "layout/attest_item2.py"
ATTEST_ENVELOPES = ("signoff/attest/item2-analog.json", "signoff/attest/item2-digital.json")


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
        # Since #387 the generator has a --check entry point that runs before
        # klayout is imported, so its strictness is asserted like every other
        # subject -- the old witness for "EXEMPT and not a strict subject" is
        # gone and must not come back.
        self.assertIn("layout/gen_io_column.py", STRICT_FLAG_SUBJECTS)


class GeneratorFreshnessTests(unittest.TestCase):
    """#266: every generator with a --check flag reports fresh, and every exemption from that is real and reasoned."""

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
        "scripts/ci/test_ci_guards.py",
        "--check runs in test_every_check_capable_generator_is_fresh",
    ),
    "sim/channel-eye/gen_t16sizing.py": (
        "scripts/ci/test_ci_guards.py",
        "--check runs in test_every_check_capable_generator_is_fresh",
    ),
    "sim/clock-path/gen_clock_path.py": (
        "scripts/ci/test_ci_guards.py",
        "--check runs in test_every_check_capable_generator_is_fresh",
    ),
    "sim/io-cell-study/gen_io_cell.py": (
        "scripts/ci/test_ci_guards.py",
        "--check runs in test_every_check_capable_generator_is_fresh",
    ),
    "sim/redundancy-mux/gen_redundancy_mux.py": (
        "scripts/ci/test_ci_guards.py",
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
        "cocotb bench module, imported by the klt functional-verification requests; not a standalone suite",
    "verification/test_shift_redundancy.py":
        "cocotb bench module, imported by the klt functional-verification requests; not a standalone suite",
    "layout/check_io_column.py":
        "needs the pinned klt environment (imports klayout.db); CI-only, like the klt signoff steps",
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
    "scripts/ci/test_checkers.py":
        "aggregator entry point: signoff/attest/item10.inventory.json and `npm test` run it by name, "
        "and it only loads the sibling suites; AggregatorSuitesMatchCheckListTests (#406) asserts "
        "that it loads and that its SUITES names exactly the suites check_local.sh runs",
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
                      "scripts/ci/test_ci_guards.py -- add a run line, or a table entry with a reason")
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

    def test_the_netlist_closure_check_is_listed(self):
        # #405: the checker inventory entry for the cited-record closure check.
        # Listed outright, so it must carry no COVERED/EXEMPT entry to keep in step.
        listed = "scripts/ci/check_netlist_closure.py" in strip_sh_comments(self.text)
        self.assertTrue(listed, f"{CHECK_LIST} does not run scripts/ci/check_netlist_closure.py")
        self.assertNotIn("scripts/ci/check_netlist_closure.py", COVERED)
        self.assertNotIn("scripts/ci/check_netlist_closure.py", EXEMPT)

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
# The aggregator loads exactly the suites the check list runs (#406)
#
# Since #401 CI runs each scripts/ci suite through its own check_local.sh line,
# so no CI job imports scripts/ci/test_checkers.py: only `npm test` and the
# item 10 audit do. A SUITES entry and a run line could therefore drift apart,
# or the aggregator itself could stop loading, with CI green and the failure
# surfacing only at signoff.
# ---------------------------------------------------------------------------

AGGREGATOR = "scripts/ci/test_checkers.py"
LISTED_SUITE = re.compile(r"python3 -I scripts/ci/(test_\w+)\.py")


def load_suites(path):
    """Execute the aggregator at `path` as the module `test_checkers`; return its SUITES.

    The module-level run `python3 -I scripts/ci/test_checkers.py` performs before
    unittest.main: it defines SUITES and load_tests and runs no test -- which is
    why this guard may load the aggregator even while running under it.
    """
    spec = importlib.util.spec_from_file_location("test_checkers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SUITES


def suite_list_errors(check_list_text, suites):
    """Return a sorted list of ways SUITES and the check list's suite run lines disagree.

    Pure: both inputs are passed in, so each drift direction can be tested
    against a fixture without touching the real tree. The check list is read for
    its `python3 -I scripts/ci/test_*.py` run lines, comments dropped.
    """
    listed = LISTED_SUITE.findall(strip_sh_comments(check_list_text))
    errors = []
    if "test_checkers" in listed:
        errors.append(f"{AGGREGATOR} is run by {CHECK_LIST}: that runs every suite it loads "
                      "twice (#401); drop the run line, and never add the aggregator to its own SUITES")
    for name in sorted(set(listed) - set(suites) - {"test_checkers"}):
        errors.append(f"{name}: run by {CHECK_LIST} but absent from SUITES, so `npm test` "
                      "and the item 10 audit run fewer tests than CI")
    for name in sorted(set(suites) - set(listed)):
        errors.append(f"{name}: in SUITES but not run by {CHECK_LIST}, so no CI job runs it")
    return sorted(errors)


class AggregatorSuitesMatchCheckListTests(unittest.TestCase):
    """#406: `npm test`, the item 10 audit and CI run the same suites."""

    def suites(self, path):
        try:
            return load_suites(path)
        except Exception as e:
            self.fail(f"{AGGREGATOR} does not load ({e!r}); no CI job runs it, so only "
                      "`npm test` and the item 10 audit would notice")

    # -- the real tree -------------------------------------------------------

    def test_the_aggregator_loads_exactly_the_suites_the_check_list_runs(self):
        errors = suite_list_errors((REPO / CHECK_LIST).read_text(), self.suites(REPO / AGGREGATOR))
        self.assertEqual(errors, [], "\n" + "\n".join(errors))

    # -- the failure modes, against a fixture pair ---------------------------
    #
    # The pair is patched rather than the real tree edited, so a failing
    # assertion here can never leave the working tree dirty.

    FIX_LIST = ('# not CI: python3 -I scripts/ci/test_checkers.py would run every suite twice\n'
                'run "a" python3 -I scripts/ci/test_a.py\n'
                'run "b" python3 -I scripts/ci/test_b.py\n')
    FIX_SUITES = ("test_a", "test_b")

    def fixture(self, text=None, suites=None):
        return suite_list_errors(text if text is not None else self.FIX_LIST,
                                 suites if suites is not None else self.FIX_SUITES)

    def test_an_aggregator_that_does_not_load_fails_the_guard(self):
        with tempfile.TemporaryDirectory() as t:
            broken = Path(t) / "test_checkers.py"
            for text in ('SUITES = ("test_a", "test_b"\n',
                         'SUITES = ("test_a",)\nimport no_such_suite\n',
                         'pass\n'):
                with self.subTest(text=text):
                    broken.write_text(text)
                    with self.assertRaises(self.failureException):
                        self.suites(broken)
            with self.subTest(text="missing file"):
                with self.assertRaises(self.failureException):
                    self.suites(Path(t) / "gone.py")

    def test_a_suite_the_check_list_runs_but_the_aggregator_omits_fails(self):
        self.assertEqual(self.fixture(suites=("test_a",)), [
            "test_b: run by scripts/ci/check_local.sh but absent from SUITES, so `npm test` "
            "and the item 10 audit run fewer tests than CI"])

    def test_a_suite_the_aggregator_loads_but_the_check_list_omits_fails(self):
        self.assertEqual(self.fixture(suites=("test_a", "test_b", "test_c")), [
            "test_c: in SUITES but not run by scripts/ci/check_local.sh, so no CI job runs it"])

    def test_the_aggregator_run_by_the_check_list_fails(self):
        text = self.FIX_LIST + 'run "all" python3 -I scripts/ci/test_checkers.py\n'
        errors = self.fixture(text=text)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("runs every suite it loads twice", errors[0])

    def test_a_clean_pair_reports_nothing(self):
        self.assertEqual(self.fixture(), [])


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
# used throughout test_signoff_pins.py. It is a substring gate, so an
# occurrence inside a comment or docstring is reported like any other -- a
# commented-out copy of the formula should not survive either.
# ---------------------------------------------------------------------------

FORMULA_PATTERNS = {
    "sha256-formula": re.compile(re.escape('"sha256:" + hashlib.sha256('), re.M),
    "manifest-constant": re.compile(r"^MANIFEST\s*=", re.M),
}

# "<path>:<pattern>" -> why this site is the formula's legitimate home.
INLINE_FORMULA_OK = {
    "scripts/ci/manifest_pins.py:sha256-formula":
        "the canonical owner: manifest_pins.sha() spells the digest formula once",
    "scripts/ci/test_ci_guards.py:sha256-formula":
        "the pattern's own source and the NoInlineFormulaDuplicationTests fixtures that feed it, "
        "not a second definition",
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
            "scripts/ci/test_ci_guards.py":
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
