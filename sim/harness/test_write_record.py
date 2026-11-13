#!/usr/bin/env python3
"""Self-tests for the shared batch record harness (no PDK, no ngspice, no fleet).

Run: python3 -I sim/harness/test_write_record.py

The record-writing step is replayed over every committed record of every family:
sim/harness/write_record.py is handed the committed report.json.gz / rows.json /
request.json and must reproduce the committed record.json, field for field, apart
from the job-id and runner-version fields that this harness exists to fix. Nothing
under sim/**/records/ is written: records are append-only evidence.

The family fields (claim_scope, energy_label, t04_bound, t05_bound, ...) are read back out of
each committed record rather than restated here, so this test cannot drift away
from what the runners actually emit.
"""
import gzip
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
sys.path.insert(0, str(HERE))
import write_record  # noqa: E402

# fields write_record.py produces itself; everything else in a committed record is a
# family field the entry point passes in.
PRODUCED = {"record", "utc_stamp", "kind", "pdk", "klt_exit_code", "corners", "rows",
            "report_only_ranges", "batch_job_ids", "runner_klt_version"}
# the two fields the channel-eye copy got wrong (it recorded only environment.remote.job_id,
# which a sharded run never sets, so every committed channel-eye record has nulls).
JOB_FIELDS = {"batch_job_id", "batch_job_ids", "runner_klt_version"}


# the families sim/harness/batch_record.sh drives; the other sim/ record families
# (mc, pdk-smoke, rtl-synth, the local t16attr probes) follow a different procedure.
FAMILIES = ("channel-eye", "clock-path", "redundancy-mux")


def committed_records():
    for family in FAMILIES:
        for p in sorted((SIM / family).glob("records/*/record.json")):
            if (p.parent / "report.json.gz").is_file() and (p.parent / "rows.json").is_file():
                yield p.parent


def split_family_fields(committed):
    """Family fields of a committed record, split into the head and tail slots."""
    keys = list(committed)
    pivot = keys.index("pdk")
    head = {k: committed[k] for k in keys[:pivot] if k not in PRODUCED}
    tail = {k: committed[k] for k in keys[pivot:] if k not in PRODUCED and k not in JOB_FIELDS}
    return head, tail


class ReplayTests(unittest.TestCase):
    def test_at_least_one_record_of_each_family_is_replayed(self):
        families = {d.parent.parent.name for d in committed_records()}
        self.assertIn("channel-eye", families)
        self.assertIn("clock-path", families)

    def test_every_committed_record_replays(self):
        seen = 0
        for rec in committed_records():
            committed = json.loads((rec / "record.json").read_text())
            head, tail = split_family_fields(committed)
            with self.subTest(record=str(rec.relative_to(SIM))):
                built = write_record.build(
                    rec, committed["record"], committed["utc_stamp"],
                    committed["pdk"]["release_tag"], committed["klt_exit_code"],
                    head, tail, with_ranges="report_only_ranges" in committed)
                for k in set(built) | set(committed):
                    if k in JOB_FIELDS:
                        continue
                    self.assertEqual(built.get(k), committed.get(k), f"{rec.name}: field {k!r}")
            seen += 1
        self.assertGreater(seen, 0)

    def test_the_clock_path_record_reproduces_byte_for_byte(self):
        """The clock-path copy was the correct one; the shared harness must not change it."""
        rec = next(d for d in committed_records() if d.parent.parent.name == "clock-path")
        committed = json.loads((rec / "record.json").read_text())
        head, tail = split_family_fields(committed)
        built = write_record.build(rec, committed["record"], committed["utc_stamp"],
                                   committed["pdk"]["release_tag"], committed["klt_exit_code"],
                                   head, tail, with_ranges=True)
        self.assertEqual(json.dumps(built, indent=2) + "\n", (rec / "record.json").read_text())

    def test_a_decompressed_report_copy_matches_its_gz(self):
        """`report.json` is excluded from the bench-file set, so check it is what it claims.

        sim/README.md section "The decompressed `report.json` copies": each copy is a
        `gzip -dc` of the committed `.gz` beside it, written because the pinned grader
        (0.9.0) cannot read a `.json.gz` citation (2AMLogic/klayout-tools#5452) - no re-run,
        byte-identical. The exclusion above would otherwise let an unrelated `report.json`
        land in a record unseen.

        No minimum count is asserted: the copies go away when that grader bug is fixed, and a
        record with no `report.json` excludes nothing, so there is nothing to check there.
        """
        for rec in committed_records():
            copy = rec / "report.json"
            if not copy.is_file():
                continue
            with self.subTest(record=str(rec.relative_to(SIM))):
                self.assertEqual(gzip.open(rec / "report.json.gz", "rb").read(),
                                 copy.read_bytes(),
                                 f"{rec.name}: report.json is not the decompressed "
                                 f"report.json.gz beside it")

    def test_a_sharded_channel_eye_run_now_records_its_job_ids(self):
        """The fix: every committed channel-eye record has null ids; the replay recovers them."""
        checked = 0
        for rec in committed_records():
            if rec.parent.parent.name != "channel-eye":
                continue
            committed = json.loads((rec / "record.json").read_text())
            report = json.load(gzip.open(rec / "report.json.gz", "rt"))
            shards = (report.get("environment", {}).get("remote") or {}).get("fleet") or []
            if not shards:  # a single-job run; the old field was already right
                continue
            self.assertIsNone(committed["batch_job_id"], f"{rec.name}: expected the old null")
            job_ids, runner_vs = write_record.job_identity(report)
            self.assertEqual(len(job_ids), len(shards), f"{rec.name}: one id per shard")
            self.assertTrue(all(job_ids), f"{rec.name}: no empty id")
            self.assertTrue(runner_vs, f"{rec.name}: runner version recovered")
            checked += 1
        self.assertGreater(checked, 0, "no sharded channel-eye record found to check")


class JobIdentityTests(unittest.TestCase):
    def test_single_job_run(self):
        rep = {"environment": {"remote": {"job_id": "klt-sim-1", "runner_klt_version": "0.9.0"}}}
        self.assertEqual(write_record.job_identity(rep), (["klt-sim-1"], ["0.9.0"]))

    def test_sharded_run(self):
        rep = {"environment": {"remote": {"fleet": [
            {"job_id": "klt-sim-a", "runner_klt_version": "0.9.0"},
            {"job_id": "klt-sim-b", "runner_klt_version": "0.9.0"}]}}}
        self.assertEqual(write_record.job_identity(rep), (["klt-sim-a", "klt-sim-b"], ["0.9.0"]))

    def test_no_remote_block_at_all(self):
        self.assertEqual(write_record.job_identity({}), ([], []))


class NoDriftTests(unittest.TestCase):
    """The duplication this harness replaced must not grow back."""

    ENTRY_POINTS = (SIM / "channel-eye/run_channel_eye.sh", SIM / "clock-path/run_clock_path.sh",
                    SIM / "redundancy-mux/run_redundancy_mux.sh")

    def test_only_the_shared_script_submits_to_the_fleet(self):
        for p in self.ENTRY_POINTS:
            self.assertNotIn("--backend batch", p.read_text(),
                             f"{p.name} submits its own request; the shared procedure should")
        self.assertIn("--backend batch", (HERE / "batch_record.sh").read_text())

    def test_the_never_launched_match_is_the_summary_sentence_only(self):
        """A --resume prints 'never launched' per shard it RECOVERS (see the comment there)."""
        shared = (HERE / "batch_record.sh").read_text()
        self.assertIn("grep -q 'were submitted but never launched'", shared)
        self.assertNotIn("grep -q 'never launched'", shared)


class EntryPointTests(unittest.TestCase):
    """What each thin entry point hands the shared procedure (`--dry-run`, no PDK, no fleet)."""

    def dry_run(self, *argv):
        out = subprocess.run([str(a) for a in argv] + ["--dry-run"], check=True,
                             capture_output=True, text=True).stdout
        return json.loads(out)

    def committed(self, in_dir, **match):
        """The NEWEST committed record of a family that matches, not the oldest.

        Record directories are UTC stamps and committed_records() yields them in sorted
        order, so the last match is the most recent run of that family. The entry point
        under test describes the bench **as it is now**, and assert_matches_committed
        compares its --copy list with the record's bench files: pinning that comparison to
        the first record ever written would fail the moment a family gains a bench file
        (adding sg13g2_mux2_2.inc and sg13g2_buf_4.inc to redundancy-mux did exactly that,
        #232). Records are append-only evidence, so the fix is to compare against the run
        the entry point would reproduce today -- never to edit an older record into line.
        """
        newest = None
        for rec in committed_records():
            if rec.parent.parent.name != in_dir:
                continue
            data = json.loads((rec / "record.json").read_text())
            if all(data.get(k) == v for k, v in match.items()):
                newest = (rec, data)       # sorted order: keep overwriting, end with the newest
        if newest is None:
            self.fail(f"no committed {in_dir} record matching {match}")
        return newest

    def assert_matches_committed(self, cfg, rec, data):
        """The entry point's family fields and copy list must reproduce a committed record."""
        for k, v in list(cfg["fields_head"].items()) + list(cfg["fields_tail"].items()):
            self.assertEqual(v, data.get(k), f"{rec.name}: field {k!r}")
        request = json.loads((rec / "request.json").read_text())
        bench = set(cfg["copy"]) | {request["netlist"]}
        committed_bench = {p.name for p in rec.iterdir()
                           if p.name not in ("record.json", "rows.json", "request.json",
                                             "report.json.gz", "report.json", "klt.stderr",
                                             "README.md")}
        self.assertEqual(bench, committed_bench,
                         f"{rec.name}: the copied bench files drifted from the record")

    def test_channel_eye_ch(self):
        cfg = self.dry_run(SIM / "channel-eye/run_channel_eye.sh", "ch")
        self.assertEqual(cfg["record"], "channel-eye")
        self.assertEqual(cfg["record_suffix"], "-ch")
        self.assertEqual(cfg["max_units_per_job"], "1")  # timeout_s 2400 => 1 unit per job
        self.assertEqual(cfg["env_prefix"], "CHANNEL_EYE")
        self.assertFalse(cfg["report_only_ranges"])
        self.assert_matches_committed(cfg, *self.committed("channel-eye", family="ch"))

    def test_channel_eye_tc(self):
        cfg = self.dry_run(SIM / "channel-eye/run_channel_eye.sh", "tc")
        self.assertEqual(cfg["record_suffix"], "-tc")
        self.assert_matches_committed(cfg, *self.committed("channel-eye", family="tc"))

    def test_channel_eye_control_is_not_design_evidence(self):
        cfg = self.dry_run(SIM / "channel-eye/run_channel_eye.sh", "control")
        self.assertEqual(cfg["record_suffix"], "-control")
        self.assertTrue(cfg["fields_head"]["claim_scope"].startswith("none:"),
                        "the bench positive control must claim nothing")

    def test_clock_path(self):
        cfg = self.dry_run(SIM / "clock-path/run_clock_path.sh")
        self.assertEqual(cfg["record"], "clock-path")
        self.assertEqual(cfg["record_suffix"], "")
        self.assertEqual(cfg["max_units_per_job"], "3")
        self.assertEqual(cfg["env_prefix"], "CLOCK_PATH")
        self.assertTrue(cfg["report_only_ranges"])
        self.assert_matches_committed(cfg, *self.committed("clock-path"))

    def test_redundancy_mux(self):
        cfg = self.dry_run(SIM / "redundancy-mux/run_redundancy_mux.sh")
        self.assertEqual(cfg["record"], "redundancy-mux")
        self.assertEqual(cfg["record_suffix"], "")
        self.assertEqual(cfg["max_units_per_job"], "3")
        self.assertEqual(cfg["env_prefix"], "REDUNDANCY_MUX")
        self.assertTrue(cfg["report_only_ranges"])
        # T-05's SIM leg has no bound of its own (DR-0023); the record must say so itself.
        self.assertTrue(cfg["fields_tail"]["t05_bound"].startswith("none:"))
        self.assert_matches_committed(cfg, *self.committed("redundancy-mux"))

    def test_committed_selects_the_newest_record_not_the_first(self):
        """The bench comparison tracks the newest run of a family, not the first (#232).

        With two or more committed records of a family this is what keeps
        assert_matches_committed honest: an entry point that gains a --copy is compared
        with the record that run produced, and the earlier records stay untouched.
        """
        for family in FAMILIES:
            stamps = sorted(r.name for r in committed_records()
                            if r.parent.parent.name == family)
            if len(stamps) < 2:
                continue
            with self.subTest(family=family):
                rec, _ = self.committed(family)
                self.assertEqual(rec.name, stamps[-1])

    def test_an_unknown_kind_is_refused(self):
        r = subprocess.run([str(SIM / "channel-eye/run_channel_eye.sh"), "nope", "--dry-run"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
