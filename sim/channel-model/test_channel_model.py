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
  bench      a nodal solver reads spec/channel/channel_rc.cir ITSELF (defaults,
             .params, every R/L/C), runs the SAME extraction the request runs at all
             15 parameter corners and on the default-parameter instance, and the
             ratios must sit inside +-1 % for the committed netlist and outside it
             for each seeded edit of the netlist text (wrong defaults, dropped kr
             or kc, removed Cfar, one inductor +20 %, a changed instance default).
             The ideal-ladder fold is the reference side only.

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


# --- a nodal solver for the netlist text itself --------------------------------

_ENG = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6}
_NUM = re.compile(r"(?<![A-Za-z_0-9.])([0-9]+(?:\.[0-9]+)?(?:e[-+]?[0-9]+)?)(meg|[fpnumk])?(?![A-Za-z_0-9.])")


def _expr(text, env):
    """Evaluate a .param/element expression: engineering suffixes, + - * /, names."""
    py = _NUM.sub(lambda m: repr(float(m.group(1)) * _ENG.get(m.group(2) or "", 1.0)),
                  text.strip().strip("{}"))
    return eval(py, {"__builtins__": {}}, dict(env))


def netlist_z(text, shorted, omega, overrides=None):
    """Input impedance at `tx` of chan_rlc as WRITTEN in `text`, at radian frequency omega.

    Parses the subcircuit's parameter defaults, its .param lines and every R/L/C
    element, applies `overrides` the way an instance line does, merges the
    zero-volt V sources, optionally shorts `rx` to ground (open: adds the bench's
    1e12 Rleak at `tx`), injects 1 A and solves the nodal equations. Mutating
    `text` therefore changes what is measured: the seeded defects are edits of the
    netlist, not arguments of a separate model.
    """
    sub = re.search(r"^\.subckt\s+chan_rlc\s+(.*?)\s+params:\s*(.+)$", text, re.M | re.I)
    pins = sub.group(1).split()
    env = {k: _expr(v, {}) for k, v in (p.split("=") for p in sub.group(2).split())}
    env.update(overrides or {})
    body = text[sub.end():text.index(".ends", sub.end())]
    parent = {}

    def find(n):
        n = "0" if n.lower() in ("0", "gnd") else n
        while parent.get(n, n) != n:
            n = parent[n]
        return n

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            if b == "0":
                parent[a] = b
            else:
                parent[b] = a

    elems = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        tok = line.split()
        if tok[0].lower() == ".param":
            for assign in re.findall(r"(\w+)=(\{[^}]*\}|\S+)", line):
                env[assign[0]] = _expr(assign[1], env)
        elif tok[0][0] in "Vv":
            union(tok[1], tok[2])
        elif tok[0][0] in "RLCrlc":
            elems.append((tok[0][0].upper(), tok[1], tok[2], _expr(tok[3], env)))
    if shorted:
        union(pins[1], "0")
    elems_y = []
    for kind, a, b, v in elems:
        y = {"R": 1.0 / v, "L": 1.0 / (1j * omega * v), "C": 1j * omega * v}[kind]
        elems_y.append((find(a), find(b), y))
    if not shorted:
        elems_y.append((find(pins[0]), "0", 1e-12))      # the bench's 1e12 Rleak
    nodes = sorted({n for a, b, _ in elems_y for n in (a, b)} - {"0"})
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    mat = [[0j] * (n + 1) for _ in range(n)]
    for a, b, y in elems_y:
        for p, q in ((a, b), (b, a)):
            if p != "0":
                mat[idx[p]][idx[p]] += y
                if q != "0":
                    mat[idx[p]][idx[q]] -= y
    mat[idx[find(pins[0])]][n] = 1.0                       # 1 A into tx
    for col in range(n):                                   # Gaussian elimination
        piv = max(range(col, n), key=lambda r: abs(mat[r][col]))
        mat[col], mat[piv] = mat[piv], mat[col]
        for r in range(n):
            if r != col and mat[r][col] != 0:
                f = mat[r][col] / mat[col][col]
                mat[r] = [x - f * y for x, y in zip(mat[r], mat[col])]
    return mat[idx[find(pins[0])]][n] / mat[idx[find(pins[0])]][idx[find(pins[0])]]


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


W_LO, W_HI = 2 * gen.PI * gen.PROBE_HZ_LO, 2 * gen.PI * gen.PROBE_HZ_HI
W_DC = 2 * gen.PI * 1e-6
REF = (gen.TABLE["r_mm"], gen.TABLE["c_mm"], gen.TABLE["l_mm"], gen.TABLE["cfar"],
       gen.SECTIONS)


def ideal_dut(ladder):
    """DUT provider backed by the ideal-ladder folding (the section-count control)."""
    return lambda shorted, w, len_mm, kr, kc: zin_ladder(
        not shorted, *ladder, len_mm, kr, kc, w)


def netlist_dut(text=SPEC_CIR.read_text(), defaults=False):
    """DUT provider that solves the netlist text; `defaults` omits len/kr/kc as the
    bench's default instances do."""
    def z(shorted, w, len_mm, kr, kc):
        ov = {} if defaults else {"len_mm": len_mm, "kr": kr, "kc": kc}
        return netlist_z(text, shorted, w, ov)
    return z


def extract(dut, defaults=False):
    """The three DUT/reference ratios the request grades, per parameter row.

    Mirrors the request's expressions: R from the shorted far end at DC, C as the
    REFERENCE open-end reactance over the DUT's at 1 MHz (reactance is -1/(wC)),
    L from Im Z of the shorted far end at 10 MHz, DUT over reference. `dut(shorted,
    omega, len_mm, kr, kc)` gives the DUT impedance; the reference is always the
    declared ladder (gen.TABLE, ten sections). With `defaults`, the DUT ignores the
    row and is graded against the fixed nominal reference, as the bench's
    default-instance pair is.
    """
    ratios = {}
    for len_mm, kr, kc in ([(gen.TABLE["lengths"][0], 1, 1)] if defaults
                           else gen.PARAM_ROWS):
        ref = lambda open_end, w: zin_ladder(open_end, *REF, len_mm, kr, kc, w)
        ratios[(len_mm, kr, kc)] = (
            dut(True, W_DC, len_mm, kr, kc).real / ref(False, W_DC).real,
            ref(True, W_LO).imag / dut(False, W_LO, len_mm, kr, kc).imag,
            dut(True, W_HI, len_mm, kr, kc).imag / ref(False, W_HI).imag,
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
        graded = [m for s in req["analysis_steps"] for m in s["measurements"]]
        self.assertEqual(req["measurements"], [])
        self.assertEqual({m["name"] for m in graded},
                         {"t12_r_ratio", "t12_c_ratio", "t12_l_ratio",
                          "t12_r_ratio_default", "t12_c_ratio_default",
                          "t12_l_ratio_default"})
        for m in graded:
            self.assertEqual(m.get("spec_row"), "T-12", m["name"])
            self.assertEqual(m["limits"], {"min": LO, "max": HI}, m["name"])

    def test_the_extraction_expressions_are_the_ones_the_solver_mirrors(self):
        """The C ratio is reference reactance over DUT reactance (C ~ 1/|Im Z|)."""
        req = json.loads((HERE / gen.REQUEST_NAME).read_text())
        by = {m["name"]: m["expr"] for s in req["analysis_steps"]
              for m in s["measurements"]}
        self.assertEqual(by["t12_c_ratio"],
                         "vecmax(imag(-v(yb0)))/vecmax(imag(-v(txb)))")
        self.assertEqual(by["t12_c_ratio_default"],
                         "vecmax(imag(-v(yd0)))/vecmax(imag(-v(txd)))")
        self.assertEqual(by["t12_l_ratio"],
                         "vecmax(imag(v(txa)))/vecmax(imag(v(ya0)))")
        self.assertEqual(by["t12_r_ratio_default"], "v(txc)/v(yc0)")

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

    def test_the_probe_frequencies_in_args_agree(self):
        req = json.loads((HERE / gen.REQUEST_NAME).read_text())
        steps = {s["name"]: s for s in req["analysis_steps"]}
        self.assertEqual(steps["c_lo"]["analysis"]["args"], "lin 1 1meg 1meg")
        self.assertEqual(steps["l_hi"]["analysis"]["args"], "lin 1 10meg 10meg")

    def test_the_bench_has_override_and_default_instances_and_four_references(self):
        tb = (HERE / gen.TB_NAME).read_text()
        self.assertIn(".include ../../spec/channel/channel_rc.cir", tb)
        inst = re.findall(r"^(X\w+)\s+\S+\s+\S+\s+0\s+chan_rlc(.*)$", tb, re.M)
        self.assertEqual(sorted(n for n, _ in inst), ["Xo", "Xod", "Xs", "Xsd"])
        for name, rest in inst:
            if name.endswith("d"):    # default instances omit every parameter
                self.assertEqual(rest.strip(), "", name)
            else:
                for p in ("len_mm", "kr", "kc"):
                    self.assertIn(p + "=", rest, name)
        # the declared constants the generator parsed are in the bench, not restated
        self.assertIn("tb_r_mm=5.5", tb)
        self.assertIn("tb_c_mm=0.20p", tb)
        self.assertIn("tb_l_mm=0.5n", tb)
        self.assertIn("tb_cfar=0.1p", tb)
        self.assertIn("tb_len0=3", tb)
        # swept references carry the DUT's scaling; nominal ones are fixed
        self.assertEqual(len(re.findall(r"\{ch_kr\*tb_r_mm\*ch_len/10\}", tb)), 20)
        self.assertEqual(len(re.findall(r"\{ch_kc\*tb_c_mm\*ch_len/10\}", tb)), 18)
        self.assertEqual(len(re.findall(r"\{tb_l_mm\*ch_len/10\}", tb)), 20)
        self.assertEqual(len(re.findall(r"\{ch_kc\*tb_c_mm\*ch_len/10/2\}", tb)), 4)
        self.assertEqual(len(re.findall(r"\{tb_r_mm\*tb_len0/10\}", tb)), 20)
        self.assertEqual(len(re.findall(r"\{tb_c_mm\*tb_len0/10\}", tb)), 18)
        self.assertEqual(len(re.findall(r"\{tb_l_mm\*tb_len0/10\}", tb)), 20)
        self.assertEqual(len(re.findall(r"\{tb_c_mm\*tb_len0/10/2\}", tb)), 4)


class BenchConformanceTests(unittest.TestCase):
    """The committed netlist against the declared table, at all 15 corners."""

    def check_in_band(self, table, label=""):
        for (ln, kr, kc), ratios in table.items():
            for name, ratio in zip("RCL", ratios):
                self.assertGreaterEqual(ratio, LO, f"{label}{name} at len={ln} kr={kr} kc={kc}")
                self.assertLessEqual(ratio, HI, f"{label}{name} at len={ln} kr={kr} kc={kc}")

    def test_the_committed_netlist_matches_the_table_at_every_corner(self):
        r, c, l, cfar, sections = netlist_defaults()
        t = gen.TABLE
        self.assertEqual((r, c, l, cfar),
                         (t["r_mm"], t["c_mm"], t["l_mm"], t["cfar"]),
                         "channel_rc.cir defaults differ from spec/channel-model.md")
        swept = extract(netlist_dut())
        self.assertEqual(len(swept), 15)
        self.check_in_band(swept)
        self.check_in_band(extract(netlist_dut(defaults=True), defaults=True),
                           "default instance: ")
        # both sides are the same ideal ladder solved exactly: any residual is
        # numerical (the 1e-12 S Rleak branch makes the open-end solve ~1e-6
        # conditioned), far inside the band the request grades at
        worst = max(abs(x - 1) for v in swept.values() for x in v)
        self.assertLess(worst, 1e-5, "method error ate the tolerance margin")

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

    def band_left(self, text, defaults=False, only_spread=False):
        """True when some ratio of the mutated NETLIST leaves the band."""
        table = extract(netlist_dut(text, defaults=defaults), defaults=defaults)
        rows = [p for p in table if not only_spread or p[1] != 1 or p[2] != 1]
        return any(not (LO <= x <= HI) for p in rows for x in table[p])

    def test_each_seeded_netlist_defect_leaves_the_band(self):
        """Negative controls run through the SAME extraction on edited netlist text.

        Every seed edits channel_rc.cir's text and re-solves it, so the controls
        exercise the changed netlist and not a separate model. The single-section
        inductance edit and the dropped Cfar were both accepted by earlier
        measurement choices; the default-kr edit hides behind the swept instances
        and only the default pair can see it.
        """
        text = SPEC_CIR.read_text()
        seeds = [
            # (label, find, replace, default instance?, spread corners only?)
            ("r_mm default 5.5 -> 6.5", "r_mm=5.5", "r_mm=6.5", False, False),
            ("c_mm default 0.20p -> 0.24p", "c_mm=0.20p", "c_mm=0.24p", False, False),
            ("l_mm default 0.5n -> 0.6n", "l_mm=0.5n", "l_mm=0.6n", False, False),
            ("cfar default 0.1p -> 0.2p", "cfar=0.1p", "cfar=0.2p", False, False),
            ("kr dropped from seg_r", "{kr*r_mm*len_mm/10}", "{r_mm*len_mm/10}",
             False, True),
            ("kc dropped from seg_c", "{kc*c_mm*len_mm/10}", "{c_mm*len_mm/10}",
             False, True),
            ("Cfar device removed", "Cfar n10 gnd {cfar}\n", "", False, False),
            ("one series inductor +20 % (L10)", "L10 m10 n10 {seg_l}",
             "L10 m10 n10 {1.2*seg_l}", False, False),
            ("one series inductor +20 % (L1)", "L1  m1  n1  {seg_l}",
             "L1  m1  n1  {1.2*seg_l}", False, False),
            ("DUT default kr 1 -> 1.2", "kr=1 kc=1", "kr=1.2 kc=1", True, False),
            ("DUT default len_mm 3 -> 4", "len_mm=3 ", "len_mm=4 ", True, False),
        ]
        for label, find, repl, default, spread in seeds:
            with self.subTest(defect=label):
                self.assertEqual(text.count(find), 1, f"seed anchor {find!r} not unique")
                self.assertTrue(
                    self.band_left(text.replace(find, repl), default, spread),
                    f"{label} still inside +-{gen.TOL:.0%}")
        # the swept instances cannot see a changed default of kr: the default pair can
        mutated = text.replace("kr=1 kc=1", "kr=1.2 kc=1")
        self.assertFalse(self.band_left(mutated, defaults=False))

    def test_c_and_r_tolerance_boundaries_in_both_directions(self):
        """+-1 % total C (both capacitances) and R, DUT over declared, fail outside.

        The C ratio is DUT capacitance over the declared value: scaling c_mm and
        cfar together by 1.0099 stays in, by 1.0101 or 1/1.0101 does not -- in both
        directions (an inverted ratio passes one side and fails the other).
        """
        text = SPEC_CIR.read_text()
        for factor, inside in ((1.0099, True), (0.9901, True),
                               (1.0101, False), (0.9899, False)):
            mut = text.replace("c_mm=0.20p", f"c_mm={0.20 * factor:.8f}p") \
                      .replace("cfar=0.1p", f"cfar={0.1 * factor:.8f}p")
            table = extract(netlist_dut(mut))
            ratios_c = [v[1] for v in table.values()]
            self.assertEqual(all(LO <= x <= HI for x in ratios_c), inside,
                             f"C x{factor}")
            # direction: more capacitance reads as a ratio above one
            self.assertEqual(all(x > 1 for x in ratios_c), factor > 1, f"C x{factor}")

    def test_a_same_total_section_count_change_is_below_the_band(self):
        """The bench's stated boundary: 10 -> 9 sections, totals identical.

        The uniform ladder's probe-frequency signature is its totals; the section
        count only shows up near the section resonance (~1.7 GHz at 3 mm), two
        orders above the 10 MHz probe. This asserts the honest limit of the check
        rather than letting it be discovered: a section-count-only edit is NOT a
        defect this bench can see, and the record's README says so. (Ideal-ladder
        DUT: the netlist text is fixed at ten explicit sections.)
        """
        r, c, l, cfar, _ = netlist_defaults()
        self.check_in_band(extract(ideal_dut((r, c, l, cfar, 9))), "9 sections: ")


class FallbackColumnTests(unittest.TestCase):
    """The generator reads all three model columns and rejects a divergent one."""

    def run_table(self, edit):
        spec = gen.SPEC_MD.read_text()
        with tempfile.TemporaryDirectory() as d:
            alt = Path(d) / "channel-model.md"
            alt.write_text(edit(spec))
            old = gen.SPEC_MD
            gen.SPEC_MD = alt
            try:
                return gen.table()
            finally:
                gen.SPEC_MD = old

    def test_unmodified_columns_parse(self):
        self.assertEqual(self.run_table(lambda t: t)["r_mm"], 5.5)

    def test_a_divergent_fallback_or_stretch_value_is_rejected(self):
        row = "| R per mm | 5.5 Ω/mm | 5.5 | 5.5 |"
        self.assertIn(row, gen.SPEC_MD.read_text())
        for alt in ("| R per mm | 5.5 Ω/mm | 6.5 | 5.5 |",
                    "| R per mm | 5.5 Ω/mm | 5.5 | 4.5 |"):
            with self.subTest(alt=alt), self.assertRaises(SystemExit):
                self.run_table(lambda t, alt=alt: t.replace(row, alt))
        crow = "| 0.20 | 0.20 |"
        self.assertIn(crow, gen.SPEC_MD.read_text())
        with self.assertRaises(SystemExit):
            self.run_table(lambda t: t.replace(crow, "| 0.20 | 0.30 |"))


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
                 {"name": "l_hi.t12_l_ratio", "spec_row": None, "status": "pass",
                  "value": 1.0, "margin": 0.01},
                 {"name": "l_hi.t12_l_ratio_default", "spec_row": None,
                  "status": "pass", "value": 1.0, "margin": 0.01},
                 {"name": "r_dc.t12_r_ratio_default", "spec_row": None,
                  "status": "pass", "value": 1.0, "margin": 0.01},
                 {"name": "c_lo.t12_c_ratio_default", "spec_row": None,
                  "status": "pass", "value": 1.0, "margin": 0.01},
                 {"name": "c_lo.w_probe", "spec_row": None, "status": "pass",
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
        self.assertEqual(row["pass"], 6)      # an ungraded intermediate counts nothing
        self.assertIn("ch_kc=0.8,ch_kr=0.8,ch_len=3", summary["param_groups"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
