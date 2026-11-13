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

    def test_l1_request_is_the_on_die_loopback_and_grades_t01_and_t09(self):
        l1 = json.loads((HERE / "request_l1_1g.json").read_text())
        self.assertEqual(l1["netlist"], "tb_l1.cir")
        rows = {m["spec_row"] for m in l1["measurements"]}
        # test-configuration.md: L1 cannot observe an eye (T-18) or RX-input skew (T-15/T-16)
        self.assertFalse({"T-15", "T-16", "T-18"} & rows)
        # the matrix marks T-01 and T-09 `yes` for L1; T-26 is "not measured" there, so report-only
        self.assertEqual({m["spec_row"] for m in l1["measurements"] if "limits" in m}, {"T-01", "T-09"})
        self.assertIn("T-26", rows)

    def test_l1_sweeps_the_route_rc_band_as_separate_corners(self):
        l1 = json.loads((HERE / "request_l1_1g.json").read_text())
        c = l1["corners"]
        # +-20 % of CH-3MM-RC R and C, zipped so R and C move together: 3 points, not 9
        self.assertEqual(c["params"], {"kr_l1": [0.8, 1.0, 1.2], "kc_l1": [0.8, 1.0, 1.2]})
        self.assertEqual(len(c["process"]) * len(next(iter(c["supply_v"].values())))
                         * len(c["temperature_c"]) * len(c["params"]["kr_l1"]), 135)
        # the sweep is inert unless the netlist declares the targets at the top level
        tb = (HERE / "tb_l1.cir").read_text()
        for name in c["params"]:
            self.assertRegex(tb, rf"(?m)^\.param .*\b{name}=")
        self.assertNotIn("l_mm=0.5n", tb)       # DR-0009 Limits: L1 does not reproduce the model's L
        self.assertIn("l_mm=0", tb)

    def test_l1_includes_the_cells_and_never_copies_them(self):
        tb = (HERE / "tb_l1.cir").read_text()
        for cell in ("aib_tx_data", "aib_rx_data", "aib_pad_esd"):
            self.assertIn(f".include ../../design/{cell}.spice", tb)
        self.assertNotIn(".subckt aib_", tb)     # no cell body is pasted into the bench
        self.assertIn(".include tb_body.inc", tb)

    def test_the_three_claims_are_three_separate_requests(self):
        nets = [json.loads((HERE / f"request_{k}_1g.json").read_text())["netlist"] for k in ("ch", "tc", "l1")]
        self.assertEqual(len(set(nets)), 3)

    def test_45_corner_grid_and_no_2gbps(self):
        ch = json.loads((HERE / "request_ch_1g.json").read_text())
        c = ch["corners"]
        self.assertEqual(len(c["process"]) * len(next(iter(c["supply_v"].values()))) * len(c["temperature_c"]), 45)
        self.assertEqual(gen.UI_PS, 1000)

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

    def test_param_axis_corner_keeps_its_temperature(self):
        """The L1 R/C sweep adds a 4th corner_id segment; the temperature must survive it."""
        cid = ("mos_ss/vdd_arx=1.080_vdd_atx=1.080_vdd_brx=1.080_vdd_btx=1.080"
               "_vdd_crx=1.080_vdd_ctx=1.080V/125C/params:kc_l1=0.8,kr_l1=0.8")
        # "mixed" rather than "1.080" is a separate pre-existing quirk of the supply
        # label (the last rail carries a trailing "V", so the value set never collapses);
        # every committed ch/tc record reads "mixed" too. Filed, not fixed here.
        short = post.short_corner(cid)
        self.assertEqual(short, "mos_ss/mixed/125C/params:kc_l1=0.8,kr_l1=0.8")
        self.assertIn("125C", short)
        # the 3-segment form the ch/tc records use is unchanged
        self.assertEqual(post.short_corner("mos_tt/vdd_atx=1.200_vdd_arx=1.200V/-40C"),
                         "mos_tt/mixed/-40C")

    def test_ungraded_row_is_reported_not_passed(self):
        r = report((("1.200", 27), [meas("a", "T-01", "pass", 64.0, None)]))
        self.assertEqual(post.summarise(r)["T-01"]["verdict"], "reported")


if __name__ == "__main__":
    unittest.main()
