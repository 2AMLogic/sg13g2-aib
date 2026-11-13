#!/usr/bin/env python3
"""Self-tests for the T-19 bench generator and aperture post-processing (no PDK, no fleet).

Run: python3 -I sim/mc/capture_window/test_t19.py
"""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import gen_mc  # noqa: E402
import gen_t19 as g  # noqa: E402


def pwl_points(netlist: str, src: str) -> list:
    line = next(l for l in netlist.splitlines() if l.startswith(src + " "))
    nums = re.search(r"pwl\((.*)\)", line).group(1).split()
    vals = [float(n.rstrip("n")) if n.endswith("n") else float(n) for n in nums]
    return list(zip(vals[0::2], vals[1::2]))


class AperturePostProcessing(unittest.TestCase):
    def test_known_samples(self):
        # first failing setup offset -120 ps, first capturing hold offset -90 ps, delays 65/60 ps
        setup, hold, ap = g.setup_hold_ps(-0.120, -0.090, 65e-12, 60e-12)
        self.assertAlmostEqual(setup, 60.0)   # x* = -125, D crossing at -125+65 = -60 ps
        self.assertAlmostEqual(hold, -35.0)   # y* = -95, D crossing at -95+60 = -35 ps
        self.assertAlmostEqual(ap, 25.0)

    def test_window_wider_than_the_limit_is_measured_not_clipped(self):
        # an aperture of 300 ps still lies inside the sweep window (-400..+100 ps at the pad)
        _, _, ap = g.setup_hold_ps(-0.390, 0.100, 0.0, 0.0)
        self.assertAlmostEqual(ap, 490.0)

    def test_request_expressions_match_the_python_reference(self):
        row = {m["name"]: m["expr"] for m in gen_mc.ROWS["t19"]["top"]}
        xs, ys, dr, df = -0.130, -0.070, 7.0e-11, 5.5e-11
        env = {"cw": type("M", (), {"xs": xs, "ys": ys, "dr": dr, "df": df})}
        got = [eval(row[k], {}, env) for k in ("t19_setup_ps", "t19_hold_ps", "t19_aperture_ps")]
        for a, b in zip(got, g.setup_hold_ps(xs, ys, dr, df)):
            self.assertAlmostEqual(a, b)


class Bench(unittest.TestCase):
    def test_sweep_covers_the_nominal_windows_with_margin(self):
        self.assertEqual(g.K, 51)
        self.assertLessEqual(g.XLO_PS, -300)
        self.assertGreaterEqual(g.XHI_PS, 50)

    def test_pwl_times_are_strictly_increasing(self):
        for ctl in (False, True):
            nl = g.netlist(ctl)
            for src in ("Vpn", "Vcn", "Vxr", "Vyr"):
                t = [p[0] for p in pwl_points(nl, src)]
                self.assertTrue(all(b > a for a, b in zip(t, t[1:])), f"{src} ctl={ctl}")

    def test_staircase_holds_between_cycle_starts(self):
        pts = pwl_points(g.netlist(False), "Vxr")
        # the level at the middle of cycle k is x_k
        for k in (0, 7, g.K - 2):
            t_mid = (k * g.PERIOD_PS + g.CLK_PS) / 1000
            lvl = next(v0 for (t0, v0), (t1, v1) in zip(pts, pts[1:]) if t0 <= t_mid <= t1 and v0 == v1)
            self.assertAlmostEqual(lvl, (g.XLO_PS + k * g.DELTA_PS) / 1000)

    def test_control_differs_only_in_the_clock_edge(self):
        a, b = g.netlist(False), g.netlist(True)
        self.assertNotEqual(a, b)
        self.assertEqual(pwl_points(a, "Vpn"), pwl_points(b, "Vpn"))
        self.assertNotEqual(pwl_points(a, "Vcn"), pwl_points(b, "Vcn"))

    def test_generated_files_are_fresh(self):
        for name, text in g.outputs().items():
            self.assertEqual((HERE / name).read_text(), text, f"{name} is stale: run gen_t19.py")


if __name__ == "__main__":
    unittest.main()
