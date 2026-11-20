#!/usr/bin/env python3
"""Self-tests for the channel-model conformance bench (no PDK, no ngspice, no fleet).

Run: python3 -I sim/channel-model/test_channel_model.py

Three layers:

  table      the generator's parse of spec/channel-model.md yields the declared
             values (per-mm R/C/L, far-end load, three lengths, +-20 % spread);
  request    the generated bench and request carry the three graded `spec_row: T-12`
             ratios with +-1 % limits, the 15 parameter rows (3 lengths x nominal
             plus the four spread corners) on the 45-corner PVT-FULL grid, and the
             probe frequencies the extraction expressions name;
  bench      an exact ideal-ladder solver (the same ideal R, L, C elements ngspice
             solves, folded by hand) runs the SAME extraction the request runs, on
             the defaults parsed out of spec/channel/channel_rc.cir itself, at all
             15 parameter corners: every ratio must sit inside +-1 % for the
             committed netlist and outside it for each seeded defect class (a wrong
             per-mm default, a dropped kr scaling, a dropped far-end load, a wrong
             inductance).

The solver is the offline half of the conformance claim: it ties the committed
netlist to the declared table without ngspice, so the recorded run is the second,
independent half rather than the only witness. Its known boundary is asserted too:
a section-count change that keeps the totals identical moves the probe-frequency
reads by ~1e-5 relative, far inside the tolerance -- the bench is a check on the
declared VALUES, their scaling and the far-end load, not on the section count,
whose low-frequency signature vanishes by design (channel_rc.cir: the ladder is
"valid far above the signal bandwidth").
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_channel_model as gen  # noqa: E402

SPEC_CIR = gen.HERE.parent.parent / "spec" / "channel" / "channel_rc.cir"
POST = gen.HERE.parent / "channel-eye" / "channel_eye_post.py"


# --- parsing the netlist under test -------------------------------------------

def netlist_defaults(text=SPEC_CIR.read_text()):
    """The declared defaults of `chan_rlc`, parsed out of channel_rc.cir itself.

    Returns (r_mm, c_mm, l_mm, cfar, sections): SI base units and the number of
    pi-sections, counted off the R devices of the ladder. The bench's expectations
    come from spec/channel-model.md; these come from the netlist -- the two must
    agree, which is exactly what T-12's conformance record asserts electrically
    and this file asserts arithmetically.
    """
    sub = re.search(r"^\.subckt\s+chan_rlc\b.*?params:\s*(.+)$", text, re.M | re.I)
    if not sub:
        raise AssertionError("no .subckt chan_rlc params line in channel_rc.cir")
    params = dict(p.split("=") for p in sub.group(1).split())
    eng = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3,
           "meg": 1e6}

    def value(token):
        m = re.fullmatch(r"([0-9.]+)\s*(meg|[fpnumk]?)", token.strip())
        if not m:
            raise AssertionError(f"unparsable default {token!r} in channel_rc.cir")
        return float(m.group(1)) * eng.get(m.group(2), 1.0)

    sections = len(re.findall(r"^R\d+\s+\S+\s+\S+\s+\{seg_r\}", text, re.M))
    if not sections:
        raise AssertionError("no ladder R devices found in channel_rc.cir")
    return (value(params["r_mm"]), value(params["c_mm"]), value(params["l_mm"]),
            value(params["cfar"]), sections)


# --- the exact ideal-ladder solver ---------------------------------------------

def zin_ladder(open_end, r_mm, c_mm, l_mm, cfar, sections, len_mm, kr, kc, omega,
               drop_kr=False):
    """Exact input impedance of the uniform pi-section ladder at radian frequency omega.

    Ideal elements, folded from the far end: the same linear system ngspice solves
    on the batch fleet, evaluated analytically. open_end=False short-circuits the
    far end (the DC series-R read); open_end=True leaves it open (the C and L
    reads) and carries the bench's Rleak (1e12 ohm giving the DC operating point a
    path), exactly as tb_channel_model.cir instantiates it. drop_kr is the seeded
    negative control: it multiplies the section resistance by 1 instead of kr,
    the "broken kr scaling" defect class.
    """
    jw = complex(0.0, omega)
    seg_r = (1.0 if drop_kr else kr) * r_mm * len_mm / sections
    seg_l = l_mm * len_mm / sections
    seg_c = kc * c_mm * len_mm / sections

    def par(a, b):
        return a * b / (a + b)

    # far-end node n_sections: its half-section cap, plus cfar, both to ground
    z = 0.0 if not open_end else 1.0 / (jw * (seg_c / 2 + cfar))
    for k in range(sections, 0, -1):     # section k's series arm lands on node k-1
        z = seg_r + jw * seg_l + z
        c = seg_c / 2 if k == 1 else seg_c   # C_{k-1}: C0 is a half-section cap
        z = par(1.0 / (jw * c), z)
    if open_end:
        z = par(1e12, z)                # Rleak txb 0 1e12
    return z


def extract(ladder, drop_kr=False):
    """The three DUT/reference ratios the request grades, from the ideal solver.

    `ladder` is the DUT's (r_mm, c_mm, l_mm, cfar, sections); the reference is
    always the declared one (gen.TABLE, ten sections). Mirrors the request:
    R from the shorted far end at DC, C from the 1 MHz open-end impedance, L from
    the omega^2 coefficient of W = -omega * Im Z_open over the two probes, as a
    DUT-over-reference ratio (the R-coupled corrections cancel between the sides;
    see the generator docstring for why no lumped constant can be used directly).
    drop_kr is the seeded control's hook: the DUT's section R loses its kr.
    """
    ref = (gen.TABLE["r_mm"], gen.TABLE["c_mm"], gen.TABLE["l_mm"],
           gen.TABLE["cfar"], gen.SECTIONS)
    w_lo, w_hi = 2 * gen.PI * gen.PROBE_HZ_LO, 2 * gen.PI * gen.PROBE_HZ_HI

    # the seeded defect belongs to the DUT only; the reference is always the
    # declared ladder, so a dropped kr cannot cancel in the ratio
    def r_dc(args, len_mm, kr, kc, drop=False):
        return zin_ladder(False, *args, len_mm, kr, kc, 2 * gen.PI * 1e-6,
                          drop_kr=drop).real

    def z_open(args, len_mm, kr, kc, w, drop=False):
        return zin_ladder(True, *args, len_mm, kr, kc, w, drop_kr=drop)

    def w_of(z, w):
        return -w * z.imag

    ratios = {}
    for len_mm, kr, kc in gen.PARAM_ROWS:
        dut_o_lo = z_open(ladder, len_mm, kr, kc, w_lo, drop_kr)
        dut_o_hi = z_open(ladder, len_mm, kr, kc, w_hi, drop_kr)
        ref_o_lo = zin_ladder(True, *ref, len_mm, kr, kc, w_lo)
        ref_o_hi = zin_ladder(True, *ref, len_mm, kr, kc, w_hi)
        ratios[(len_mm, kr, kc)] = (
            r_dc(ladder, len_mm, kr, kc, drop_kr) / r_dc(ref, len_mm, kr, kc),
            dut_o_lo.imag / ref_o_lo.imag,
            (w_of(dut_o_lo, w_lo) - w_of(dut_o_hi, w_hi))
            / (w_of(ref_o_lo, w_lo) - w_of(ref_o_hi, w_hi)),
        )
    return ratios


def dut_totals(ladder):
    """The DUT's closed-form totals, for the two quantities that have exact ones.

    R is exact at DC (the caps open, the short carries the current); C from the
    1 MHz open-end read sits within omega^2*L*C ~ 4e-8 of the true total. L has
    NO closed form at the probe frequencies (the corrections are of the ladder
    itself), which is why the bench grades it differentially.
    """
    w_lo = 2 * gen.PI * gen.PROBE_HZ_LO
    out = {}
    for len_mm, kr, kc in gen.PARAM_ROWS:
        r, c, l, cfar, sections = ladder
        z_dc = zin_ladder(False, *ladder, len_mm, kr, kc, 2 * gen.PI * 1e-6)
        z_lo = zin_ladder(True, *ladder, len_mm, kr, kc, w_lo)
        out[(len_mm, kr, kc)] = (
            z_dc.real / (kr * r * len_mm),
            (-1.0 / (w_lo * z_lo.imag)) / (kc * c * len_mm + cfar),
        )
    return out


LO, HI = 1 - gen.TOL, 1 + gen.TOL


class TableTests(unittest.TestCase):
    def test_the_declared_table_parses(self):
        t = gen.TABLE
        self.assertEqual((t["r_mm"], t["c_mm"], t["l_mm"], t["cfar"]),
                         (5.5, 0.20e-12, 0.5e-9, 0.1e-12))
        self.assertEqual(t["lengths"], [3, 1, 5])
        self.assertEqual(t["spread"], [0.8, 1.2])

    def test_the_parameter_rows_are_three_lengths_times_five_corners(self):
        self.assertEqual(len(gen.PARAM_ROWS), 15)
        self.assertEqual(gen.PARAM_ROWS[0], (3, 1, 1))       # nominal first
        self.assertEqual(sorted(set(gen.PARAM_ROWS)), sorted(
            (ln, kr, kc) for ln in (3, 1, 5)
            for kr, kc in ((1, 1), (0.8, 0.8), (0.8, 1.2), (1.2, 0.8), (1.2, 1.2))))


class RequestTests(unittest.TestCase):
    def test_generated_files_are_fresh(self):
        for name, text in gen.outputs().items():
            self.assertEqual((HERE / name).read_text(), text,
                             f"{name} is stale: run gen_channel_model.py")

    def test_every_step_of_the_request_grades_t12_within_one_percent(self):
        req = json.loads((HERE / gen.REQUEST_NAME).read_text())
        steps = {s["name"]: s for s in req["analysis_steps"]}
        self.assertEqual(set(steps), {"r_dc", "c_lo", "l_hi"})
        graded = [m for s in req["analysis_steps"] for m in s["measurements"]
                  if "limits" in m] + req["measurements"]
        self.assertEqual({m["name"] for m in graded},
                         {"t12_r_ratio", "t12_c_ratio", "t12_l_ratio"})
        for m in graded:
            self.assertEqual(m.get("spec_row"), "T-12", m["name"])
            self.assertEqual(m["limits"], {"min": LO, "max": HI}, m["name"])
        # the L combination references the W intermediates of both sides by
        # step-qualified name
        self.assertIn("c_lo.w_open_lo", req["measurements"][0]["expr"])
        self.assertIn("l_hi.w_open_hi", req["measurements"][0]["expr"])
        self.assertIn("c_lo.w_open_ref_lo", req["measurements"][0]["expr"])
        self.assertIn("l_hi.w_open_ref_hi", req["measurements"][0]["expr"])

    def test_the_grid_is_pvt_full_times_fifteen_parameter_rows(self):
        req = json.loads((HERE / gen.REQUEST_NAME).read_text())
        c = req["corners"]
        n_pvt = len(c["process"]) * len(next(iter(c["supply_v"].values()))) \
            * len(c["temperature_c"])
        self.assertEqual(n_pvt, 45)                       # the PVT-FULL grid
        for name in ("ch_len", "ch_kr", "ch_kc"):
            self.assertEqual(len(c["params"][name]), 15, name)
        self.assertEqual(list(zip(c["params"]["ch_len"], c["params"]["ch_kr"],
                                  c["params"]["ch_kc"])), gen.PARAM_ROWS)

    def test_the_probe_frequencies_in_args_and_expressions_agree(self):
        req = json.loads((HERE / gen.REQUEST_NAME).read_text())
        steps = {s["name"]: s for s in req["analysis_steps"]}
        self.assertEqual(steps["c_lo"]["analysis"]["args"], "lin 1 1meg 1meg")
        self.assertEqual(steps["l_hi"]["analysis"]["args"], "lin 1 10meg 10meg")
        for m in steps["c_lo"]["measurements"][1:]:
            self.assertIn("2*pi*1e6", m["expr"])
        for m in steps["l_hi"]["measurements"]:
            self.assertIn("2*pi*1e7", m["expr"])

    def test_the_bench_instantiates_the_dut_twice_and_builds_two_references(self):
        tb = (HERE / gen.TB_NAME).read_text()
        self.assertIn(".include ../../spec/channel/channel_rc.cir", tb)
        self.assertEqual(len(re.findall(r"^X[so]\s+\S+\s+\S+\s+0\s+chan_rlc", tb, re.M)), 2)
        # the declared constants the generator parsed are in the bench, not restated
        self.assertIn("tb_r_mm=5.5", tb)
        self.assertIn("tb_c_mm=0.20p", tb)
        self.assertIn("tb_l_mm=0.5n", tb)
        self.assertIn("tb_cfar=0.1p", tb)
        # the reference ladders carry the same scaling the DUT instance does:
        # ten full R/L/C section expressions per ladder, per side
        self.assertEqual(len(re.findall(r"\{ch_kr\*tb_r_mm\*ch_len/10\}", tb)), 20)
        self.assertEqual(len(re.findall(r"\{ch_kc\*tb_c_mm\*ch_len/10\}", tb)), 18)
        self.assertEqual(len(re.findall(r"\{tb_l_mm\*ch_len/10\}", tb)), 20)
        self.assertEqual(len(re.findall(r"\{ch_kc\*tb_c_mm\*ch_len/10/2\}", tb)), 4)


class BenchConformanceTests(unittest.TestCase):
    """The committed netlist against the declared table, at all 15 corners."""

    def test_the_committed_netlist_matches_the_table_at_every_corner(self):
        ladder = netlist_defaults()
        r, c, l, cfar, sections = ladder
        t = gen.TABLE
        self.assertEqual((r, c, l, cfar),
                         (t["r_mm"], t["c_mm"], t["l_mm"], t["cfar"]),
                         "channel_rc.cir defaults differ from spec/channel-model.md")
        worst = 0.0
        for (ln, kr, kc), (rr, cr, lr) in extract(ladder).items():
            for name, ratio in (("R", rr), ("C", cr), ("L", lr)):
                worst = max(worst, abs(ratio - 1))
                self.assertGreaterEqual(ratio, LO, f"{name} at len={ln} kr={kr} kc={kc}")
                self.assertLessEqual(ratio, HI, f"{name} at len={ln} kr={kr} kc={kc}")
        # the whole extraction asymmetry sits far inside the tolerance the request
        # grades at (both sides are ideal ladders folded in exact arithmetic)
        self.assertLess(worst, 2e-3, "method error ate the tolerance margin")

    def test_the_quantities_with_closed_forms_match_the_table_products(self):
        """R against kr*r_mm*len and C against kc*c_mm*len + cfar, arithmetically.

        The two products the issue's row names directly: exact at DC for R, and
        the 1 MHz open-end read for C (contaminated only by omega^2*L*C, ~4e-8).
        This is the offline statement of what the differential ratios mean -- the
        reference ladder's arms sum to exactly these products.
        """
        ladder = netlist_defaults()
        worst = 0.0
        for (ln, kr, kc), (rr, cr) in dut_totals(ladder).items():
            for name, ratio in (("R", rr), ("C", cr)):
                worst = max(worst, abs(ratio - 1))
                self.assertLess(abs(ratio - 1), 1e-5,
                                f"{name} at len={ln} kr={kr} kc={kc}")
        self.assertLess(worst, 1e-5)

    def test_seeded_defects_leave_the_band(self):
        """The negative control the record's README describes, run offline.

        Each seed is a class of edit that would move every dependent row silently:
        a wrong per-mm default, a dropped spread multiplier, a dropped far-end
        load, a wrong inductance. The bench must fail each one at the corner where
        it binds.
        """
        r, c, l, cfar, sections = netlist_defaults()
        seeds = [
            ("r_mm default 5.5 -> 6.5 ohm/mm",
             (6.5 * r, c, l, cfar, sections), 0, None, False),
            ("kr dropped from seg_r (binds where kr != 1)",
             (r, c, l, cfar, sections), 0, "spread", True),
            ("cfar dropped from the far end",
             (r, c, l, 0.0, sections), 1, None, False),
            ("l_mm default 0.5n -> 0.6n per mm",
             (r, c, 1.2 * l, cfar, sections), 2, None, False),
        ]
        for label, ladder, which, where, drop_kr in seeds:
            with self.subTest(defect=label):
                table = extract(ladder, drop_kr=drop_kr)
                corners = ([p for p in table if p[1] != 1 or p[2] != 1]
                           if where == "spread" else list(table))
                left = any(not (LO <= table[p][which] <= HI) for p in corners)
                self.assertTrue(left, f"{label} still inside +-{gen.TOL:.0%}")

    def test_a_same_total_section_count_change_is_below_the_band(self):
        """The bench's stated boundary: 10 -> 9 sections, totals identical.

        The uniform ladder's probe-frequency signature is its totals; the section
        count only shows up near the section resonance (~1.7 GHz at 3 mm), two
        orders above the 10 MHz probe. This asserts the honest limit of the check
        rather than letting it be discovered: a section-count-only edit is NOT a
        defect this bench can see, and the record's README says so.
        """
        r, c, l, cfar, _ = netlist_defaults()
        for p, (rr, cr, lr) in extract((r, c, l, cfar, 9)).items():
            for name, ratio in (("R", rr), ("C", cr), ("L", lr)):
                self.assertGreaterEqual(ratio, LO, f"{name} at {p}")
                self.assertLessEqual(ratio, HI, f"{name} at {p}")


class PostWiringTests(unittest.TestCase):
    """The shared post-processor resolves this family's step-named T-12 ratios."""

    def test_row_map_and_request_together_reach_every_graded_name(self):
        report = {"corners": [
            {"corner_id": "mos_tt/vpvt=1.200V/27C/params:ch_kc=0.8,ch_kr=0.8,ch_len=3",
             "measurements": [
                 {"name": "r_dc.t12_r_ratio", "spec_row": None, "status": "pass",
                  "value": 1.0, "margin": 0.01},
                 {"name": "c_lo.t12_c_ratio", "spec_row": None, "status": "pass",
                  "value": 1.0, "margin": 0.01},
                 {"name": "t12_l_ratio", "spec_row": None, "status": "pass",
                  "value": 1.0, "margin": 0.01},
                 {"name": "l_hi.w_open_hi", "spec_row": None, "status": "pass",
                  "value": 1.4e12, "margin": None},
             ]}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(report, fh)
            path = fh.name
        out = subprocess.run(
            [sys.executable, "-I", str(POST), path,
             "--request", str(HERE / gen.REQUEST_NAME),
             "--row-map", '{"t12_": "T-12"}'],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        summary = json.loads(out.stdout)
        row = summary["rows"]["T-12"]
        self.assertEqual(row["verdict"], "pass")
        self.assertEqual(row["pass"], 3)      # the W intermediate grades nothing
        self.assertIn("ch_kc=0.8,ch_kr=0.8,ch_len=3", summary["param_groups"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
