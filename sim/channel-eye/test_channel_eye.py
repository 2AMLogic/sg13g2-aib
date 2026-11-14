#!/usr/bin/env python3
"""Self-tests for the channel-eye generator and post-processor (no PDK, no fleet).

Run: python3 -I sim/channel-eye/test_channel_eye.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import channel_eye_post as post  # noqa: E402
import gen_channel_eye as gen  # noqa: E402


def meas(name, row, status, value=None, margin=None):
    return {"name": name, "spec_row": row, "status": status, "value": value, "margin": margin}


def report(*corner_meas):
    return {"corners": [{"corner_id": f"mos_tt/vdd_atx={v}_vdd_arx={v}/{t}C", "measurements": ms}
                        for (v, t), ms in corner_meas]}


def spread_report(per_corner):
    """A report shaped like a `corners.params` run: the same PVT corner at each (kr, kc).

    per_corner maps a (kr, kc) pair to the measurement list recorded there, so a test can
    seed a defect at exactly one spread corner and check it is reported against that one.
    """
    return {"corners": [
        {"corner_id": f"mos_tt/vdd_atx=1.200_vdd_arx=1.200V/27C/params:ch_kc={kc},ch_kr={kr}",
         "measurements": ms}
        for (kr, kc), ms in per_corner.items()]}


class GeneratorTests(unittest.TestCase):
    def test_prbs7_is_maximal_and_balanced(self):
        p = gen.prbs7()
        self.assertEqual(len(p), 127)
        self.assertEqual(sum(p), 64)

    def test_stream_is_cyclic_so_the_waveform_is_periodic(self):
        s = gen.stream()
        self.assertEqual(len(s), gen.NBITS)
        self.assertEqual(s[gen.WARM:], gen.prbs7())
        self.assertEqual(s[:gen.WARM], gen.prbs7()[-gen.WARM:])

    def test_generated_files_are_fresh(self):
        for name, text in gen.outputs().items():
            self.assertEqual((HERE / name).read_text(), text, f"{name} is stale: run gen_channel_eye.py")

    def test_ch_and_tc_claims_are_separate_requests(self):
        ch, tc = json.loads((HERE / "request_ch_1g.json").read_text()), json.loads((HERE / "request_tc_1g.json").read_text())
        self.assertEqual((ch["netlist"], tc["netlist"]), ("tb_ch.cir", "tb_tc.cir"))
        rows = lambda r: {m["spec_row"] for m in r["measurements"]}
        self.assertTrue({"T-18", "T-15", "T-16"} <= rows(ch))
        self.assertFalse({"T-18", "T-15", "T-16"} & rows(tc))  # test-configuration.md: not observable in L2
        # TC only grades T-09 (expected to fail, recorded); T-01 and T-26 are report-only there
        graded = {m["spec_row"] for m in tc["measurements"] if "limits" in m}
        self.assertEqual(graded, {"T-09"})

    def test_45_corner_grid_and_no_2gbps(self):
        ch = json.loads((HERE / "request_ch_1g.json").read_text())
        c = ch["corners"]
        self.assertEqual(len(c["process"]) * len(next(iter(c["supply_v"].values()))) * len(c["temperature_c"]), 45)
        self.assertEqual(gen.UI_PS, 1000)

    def test_spread_request_is_180_units_of_the_four_kr_kc_corners(self):
        """T-12: PVT-FULL once per (kr, kc) pair, zipped by index, not crossed."""
        r = json.loads((HERE / "request_ch_spread_1g.json").read_text())
        c = r["corners"]
        pvt = len(c["process"]) * len(next(iter(c["supply_v"].values()))) * len(c["temperature_c"])
        self.assertEqual(pvt, 45)
        kr, kc = c["params"]["ch_kr"], c["params"]["ch_kc"]
        self.assertEqual(len(kr), len(kc))
        self.assertEqual(pvt * len(kr), 180)
        # zipped by index: the pairs are the four +-20 % combinations, each exactly once
        self.assertEqual(sorted(zip(kr, kc)), [(0.8, 0.8), (0.8, 1.2), (1.2, 0.8), (1.2, 1.2)])

    def test_spread_request_differs_from_nominal_only_in_netlist_params_and_timeout(self):
        """The sensitivity run must not also move a measurement, a limit or the stimulus.

        Three differences are intended: the parameterised netlist, the `corners.params`
        axis, and the shorter per-unit timeout that lets the fleet pack a job. Stripping
        exactly those three must leave the nominal request.
        """
        ch = json.loads((HERE / "request_ch_1g.json").read_text())
        sp = json.loads((HERE / "request_ch_spread_1g.json").read_text())
        self.assertEqual((ch["netlist"], sp["netlist"]), ("tb_ch.cir", "tb_ch_spread.cir"))
        self.assertEqual(sp["measurements"], ch["measurements"])
        stripped = dict(sp, netlist=ch["netlist"],
                        corners={k: v for k, v in sp["corners"].items() if k != "params"},
                        options=dict(sp["options"], timeout_s=ch["options"]["timeout_s"]))
        self.assertEqual(stripped, ch)

    def test_the_packed_job_stays_under_the_fleet_ceiling(self):
        """units x timeout_s must stay below the per-job ceiling, or the fleet refuses the
        submit outright (batch_max_units_per_job_invalid). The two numbers are chosen
        together, so pin them together."""
        sp = json.loads((HERE / "request_ch_spread_1g.json").read_text())
        self.assertEqual(sp["options"]["timeout_s"], gen.SPREAD_TIMEOUT_S)
        # the fleet's own rule, quoted in its refusal message:
        # max_units_per_job = floor((max_job_seconds - 120) / options.timeout_s)
        self.assertLessEqual(
            gen.SPREAD_UNITS_PER_JOB,
            (gen.FLEET_JOB_CEILING_S - gen.FLEET_JOB_OVERHEAD_S) // gen.SPREAD_TIMEOUT_S)
        self.assertGreater(gen.SPREAD_UNITS_PER_JOB, 1, "the point is to pack more than one")
        # and the timeout must still leave real margin over the measured per-corner cost
        self.assertGreater(gen.SPREAD_TIMEOUT_S, 10 * 22)

    def test_the_spread_bench_only_lifts_kr_kc_to_top_level(self):
        """`corners.params` can target a top-level `.param` only, so the bench needs that
        form; everything else must be the nominal bench, which the records cite."""
        ch = [l for l in (HERE / "tb_ch.cir").read_text().splitlines() if not l.startswith("*")]
        sp = [l for l in (HERE / "tb_ch_spread.cir").read_text().splitlines() if not l.startswith("*")]
        self.assertIn(".param ch_kr=1 ch_kc=1", sp)
        self.assertIn("Xch txp rxp gnd chan_rlc len_mm=3 kr={ch_kr} kc={ch_kc}", sp)
        # same cards otherwise: the .param line added, the Xch line parameterised
        self.assertEqual([l for l in sp if l != ".param ch_kr=1 ch_kc=1"
                          and not l.startswith("Xch ")],
                         [l for l in ch if not l.startswith("Xch ")])

    def test_skew_edges_pair_the_expected_polarity(self):
        t15, t16 = gen.skew_pairs()
        self.assertEqual(len(t15), 4)
        self.assertEqual(len(t16), 8)
        self.assertTrue(all("TRIG v(dsa)" in c for _, c in t15 + t16))


class PostTests(unittest.TestCase):
    def test_all_pass_is_pass(self):
        r = report((("1.200", 27), [meas("a", "T-09", "pass", 0.1, 0.15)]),
                   (("1.080", 125), [meas("a", "T-09", "pass", 0.2, 0.05)]))
        row = post.summarise(r)["T-09"]
        self.assertEqual(row["verdict"], "pass")
        self.assertEqual(row["binding"]["corner"], "mos_tt/1.080/125C")

    def test_seeded_bad_bound_fails_on_a_named_corner(self):
        r = report((("1.200", 27), [meas("a", "T-18", "pass", 0.2, 0.11)]),
                   (("1.320", -40), [meas("a", "T-18", "fail", 0.05, -0.04)]))
        row = post.summarise(r)["T-18"]
        self.assertEqual(row["verdict"], "fail")
        self.assertEqual(row["binding"]["corner"], "mos_tt/1.320/-40C")

    def test_error_corner_is_never_a_pass(self):
        r = report((("1.200", 27), [meas("a", "T-26", "error")]))
        self.assertEqual(post.summarise(r)["T-26"]["verdict"], "fail")

    def test_ungraded_row_is_reported_not_passed(self):
        r = report((("1.200", 27), [meas("a", "T-01", "pass", 64.0, None)]))
        self.assertEqual(post.summarise(r)["T-01"]["verdict"], "reported")


class ParamCornerTests(unittest.TestCase):
    """The `corners.params` half: T-12's +-20 % channel R/C spread corners."""

    SPREAD = ((0.8, 0.8), (0.8, 1.2), (1.2, 0.8), (1.2, 1.2))

    # the supply label is "mixed" because klt suffixes only the LAST supply with "V",
    # so the value set has two members -- a separate defect, tracked in #185 and
    # deliberately not fixed here. These tests pin the temperature and the params
    # segment, which is what this issue changes.
    PVT = "mos_ss/vdd_arx=1.080_vdd_atx=1.080_vdd_crx=1.080V/-40C"

    def test_short_corner_keeps_the_temperature_and_names_the_spread_corner(self):
        short = post.short_corner(f"{self.PVT}/params:ch_kc=1.2,ch_kr=0.8")
        self.assertIn("-40C", short, "the temperature must survive the params segment")
        self.assertIn("ch_kc=1.2,ch_kr=0.8", short)
        self.assertEqual(short, "mos_ss/mixed/-40C/ch_kc=1.2,ch_kr=0.8")

    def test_short_corner_is_unchanged_without_a_params_segment(self):
        self.assertEqual(post.short_corner(self.PVT), "mos_ss/mixed/-40C")

    def test_no_param_groups_without_the_axis(self):
        r = report((("1.200", 27), [meas("a", "T-18", "pass", 0.2, 0.11)]))
        self.assertEqual(post.param_groups(r), {})

    def test_a_failure_is_reported_against_its_own_spread_corner_only(self):
        """The result T-12 asks for: pass at three spread corners, fail at the fourth."""
        ok = [meas("t18_eye_height_ok_v", "T-18", "pass", 0.20, 0.11)]
        bad = [meas("t18_eye_height_ok_v", "T-18", "fail", 0.05, -0.04)]
        r = spread_report({p: (bad if p == (1.2, 1.2) else ok) for p in self.SPREAD})
        groups = post.param_groups(r)
        self.assertEqual(len(groups), 4)
        for kr, kc in self.SPREAD:
            key = f"ch_kc={kc},ch_kr={kr}"
            row = groups[key]["rows"]["T-18"]
            self.assertEqual(groups[key]["corners"], 1)
            if (kr, kc) == (1.2, 1.2):
                self.assertEqual(row["verdict"], "fail", key)
                self.assertEqual(row["fail"], 1)
                self.assertIn(key, row["binding"]["corner"])
            else:
                self.assertEqual(row["verdict"], "pass", key)
                self.assertEqual(row["fail"], 0)
        # the pooled summary still fails, and names the failing spread corner
        pooled = post.summarise(r)["T-18"]
        self.assertEqual(pooled["verdict"], "fail")
        self.assertIn("ch_kc=1.2,ch_kr=1.2", pooled["binding"]["corner"])

    def test_an_unmeasurable_spread_corner_is_error_never_a_pass(self):
        ok = [meas("t26_energy_per_bit_simulated_j", "T-26", "pass", 6e-13, 4e-13)]
        err = [meas("t26_energy_per_bit_simulated_j", "T-26", "error")]
        r = spread_report({p: (err if p == (0.8, 1.2) else ok) for p in self.SPREAD})
        groups = post.param_groups(r)
        bad = groups["ch_kc=1.2,ch_kr=0.8"]["rows"]["T-26"]
        self.assertEqual(bad["verdict"], "fail")
        self.assertEqual((bad["error"], bad["pass"]), (1, 0))
        self.assertEqual(bad["binding"]["why"], "error")
        self.assertEqual(groups["ch_kc=0.8,ch_kr=0.8"]["rows"]["T-26"]["verdict"], "pass")

    def test_the_grid_splits_evenly_across_the_spread_corners(self):
        """45 PVT corners at each pair: every group must hold its own 45, not 180."""
        ms = [meas("t01_dout_edges_a", "T-01", "pass", 64.0, 0.5)]
        r = {"corners": [
            {"corner_id": f"mos_{p}/vdd_atx={v}V/{tc}C/params:ch_kc={kc},ch_kr={kr}",
             "measurements": ms}
            for p in ("tt", "ss", "ff", "sf", "fs")
            for v in ("1.080", "1.200", "1.320")
            for tc in (-40, 27, 125)
            for kr, kc in self.SPREAD]}
        self.assertEqual(len(r["corners"]), 180)
        groups = post.param_groups(r)
        self.assertEqual(sorted(groups), ["ch_kc=0.8,ch_kr=0.8", "ch_kc=0.8,ch_kr=1.2",
                                          "ch_kc=1.2,ch_kr=0.8", "ch_kc=1.2,ch_kr=1.2"])
        self.assertEqual([g["corners"] for g in groups.values()], [45, 45, 45, 45])


if __name__ == "__main__":
    unittest.main()
