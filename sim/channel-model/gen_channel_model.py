#!/usr/bin/env python3
"""Generate the T-12 channel-model conformance bench and its `klt sim` request.

Stdlib only.  `python3 -I sim/channel-model/gen_channel_model.py [--check]` writes
(or checks) tb_channel_model.cir and request_channel_model.json.

What this family measures (T-12, spec/target-spec.md): that the committed netlist
spec/channel/channel_rc.cir -- the input T-01, T-09, T-15, T-16, T-18 and T-26 all
take -- implements the declared table spec/channel-model.md at the three declared
lengths (CH-3MM-RC 3 mm target, CH-1MM 1 mm fallback, CH-5MM 5 mm stretch) and at
nominal plus the four declared +-20 % (kr, kc) combinations, over the 45-corner
PVT-FULL grid (passive network: the PVT corners cost nothing and the record then
matches the row's grid column, "PVT-FULL, plus channel R/C +-20 %", as written).
Three graded ratios (plus their _default twins), all `spec_row: T-12`, limit +-1 % (a property of the check,
not a spec bound; README "Tolerance"):

  t12_r_ratio   end-to-end series resistance, from a DC operating point with the
                far end shorted and a 1 A drive: DUT v/I over reference v/I. The
                reference ladder's series R arms sum to kr * r_mm * len_mm, so the
                ratio is the netlist's resistance against the declared product.
  t12_c_ratio   total shunt capacitance including the far-end load, from the
                1 MHz open-end impedance (both sides driven 1 A). The open-end
                reactance is -1/(omega C), so the capacitance ratio DUT/reference
                is the REFERENCE reactance over the DUT's. The reference's shunt C
                sums to kc * c_mm * len_mm + cfar.
  t12_l_ratio   total series inductance. The far-end-shorted Im Z at 10 MHz is
                omega * (total L - b), where b is the ladder's own R-C bias (below).
                The bias is additive and scales as R^2 * C, so a bare DUT/reference
                division of Im Z would also pass an R/C error as an L error (and
                the other way round). The graded expression therefore ADDS BACK the
                bias before dividing by the declared total: the reference's bias is
                read off the bench (a bare inductor of the declared total L gives
                omega * L_declared; its difference from the reference ladder's Im Z
                is omega * b_ref) and is rescaled to the DUT's measured R and C
                (Re Z ratio, squared, times the open-end C ratio). What remains is
                the DUT's total series L over the declared one, with a cross term
                only in the second order of the (separately graded) R and C errors.

Each ratio is also graded on a second pair of DUT instances that omit len_mm, kr
and kc (suffix _default) against a fixed nominal reference, so the subcircuit's own
defaults -- what consumers such as sim/channel-eye instantiate -- are exercised
and not overridden by the sweep.

Why the bench is differential (a generated reference ladder, not a materialised
constant): the reference's ideal R/L/C values come from the same table parse, so
the netlist is graded against the declaration, never against itself -- but the
probe-frequency observables are NOT the lumped constants. The shorted-far-end read
(R + jwL) carries a frequency-INDEPENDENT inductance bias (each interior shunt cap
feeds current through the series resistance behind it: C_seg * R^2 * sum of
squares, about 3 % of L at 3 mm, 12 % at 5 mm / kr 1.2). A plain DUT/reference
division leaves that bias in the ratio and dilutes then amplifies the L error by
1/(1 - b/L) (an L +0.9 % edit read 1.0109 at 5 mm), so the L expression adds the
bias back, rescaled to the DUT's own R and C (t12_l_ratio above).
test_channel_model.py's nodal solver of the netlist text runs the same
expression at every parameter corner, offline, pins both tolerance boundaries
for L, R and C varied independently, and seeds each defect class as an edit of
that text to show the ratio leaves the band.

The expected values are read from spec/channel-model.md here, never restated by
hand: the generator parses the declared table, writes the constants into the
generated bench as `.param`s, and builds the ten-section reference ladders from
them (channel-model.md declares "ten uniform RLC pi-sections"). ch_len/ch_kr/ch_kc
are top-level `.param`s so `corners.params` can sweep the 15 (length, kr, kc) rows
zipped by index.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pvt_full  # noqa: E402  (the one PVT-FULL corner-bundle definition)
import gen_common  # noqa: E402  (write_or_check)

from math import pi as PI  # noqa: E402

SPEC_MD = HERE.parent.parent / "spec" / "channel-model.md"
TB_NAME = "tb_channel_model.cir"
REQUEST_NAME = "request_channel_model.json"

TOL = 0.01                 # the +-1 % numerical-agreement band (README "Tolerance")
PROBE_HZ_LO = 1e6          # the C probe
PROBE_HZ_HI = 1e7          # the L probe; both << the ~1.7 GHz section resonance
F_LO_ARG, F_HI_ARG = "1meg", "10meg"   # as ngspice .ac args
SECTIONS = 10              # channel-model.md: "ten uniform RLC pi-sections"
# Fleet job shape: the per-job cap is floor((ceiling - overhead) / timeout_s) with
# this fleet's own 3600 s ceiling and 120 s overhead (gen_channel_eye.py pins both,
# from 2AMLogic/klayout-tools#4675). A passive ladder runs in well under a second,
# so 60 s per unit packs 58 units per job and the 675-unit grid is 12 jobs.
TIMEOUT_S = 60
FLEET_JOB_CEILING_S = 3600
FLEET_JOB_OVERHEAD_S = 120
UNITS_PER_JOB = (FLEET_JOB_CEILING_S - FLEET_JOB_OVERHEAD_S) // TIMEOUT_S

# --- parsing the declared table (spec/channel-model.md) ------------------------

# first-cell prefix -> key in TABLE. The target cell carries the value with its
# unit ("5.5 Ω/mm", "0.20 pF/mm", "0.1 pF"); the fallback and stretch columns
# repeat the number bare, in the same unit. The bench supports one value per
# quantity, so table() parses all three columns and rejects a row where they differ.
ROW_OF = (("Length", "lengths"),
          ("R per mm", "r_mm"),
          ("C per mm", "c_mm"),
          ("L per mm", "l_mm"),
          ("Far-end load at the RX pin", "cfar"),
          ("Spread corners", "spread"))

SI = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6}


def _cell(row, i):
    return row.split("|")[i].strip()


_NUM_RE = r"[0-9]+(?:\.[0-9]+)?"

# The whole declaration of each cell is parsed, not a numeric prefix: a cell with a
# unit or syntax the bench does not model ("1 cm", "0.20 nF/mm", "R and C each
# ×0.6 and ×1.4") is rejected rather than read as its leading digits. Target-column
# unit pattern per row; the fallback and stretch columns repeat the number bare or
# with that same unit.
_VALUE_UNIT = {"r_mm": r"Ω/mm", "c_mm": r"([fpn])F/mm", "l_mm": r"([pnu])H/mm",
               "cfar": r"([fpn])F"}
_SPREAD_RE = re.compile(r"R and C each ×(%s) and ×(%s)" % (_NUM_RE, _NUM_RE))


def _length(cell, what):
    m = re.fullmatch(r"(%s) mm" % _NUM_RE, cell)
    if not m:
        raise SystemExit(f"gen_channel_model: {what} cell {cell!r} is not "
                         "'<number> mm'; the bench models lengths in mm only")
    return float(m.group(1))


def _value(key, row):
    """(SI value, ngspice literal) of a per-mm/far-end row; all three columns checked."""
    unit_re = _VALUE_UNIT[key]
    m = re.fullmatch(r"(%s) ?(%s)" % (_NUM_RE, unit_re), _cell(row, 2))
    if not m:
        raise SystemExit(f"gen_channel_model: {key} target cell {_cell(row, 2)!r} is not "
                         f"'<number> <unit>' with unit {unit_re!r}; unsupported unit or "
                         "syntax -- extend the generator before declaring it")
    num = m.group(1)
    suf = (m.group(3) if len(m.groups()) >= 3 else None) or ""
    unit_txt = _cell(row, 2)[len(num):].strip()
    value = float(num) * SI.get(suf, 1.0)
    for col, name in ((3, "fallback"), (4, "stretch")):
        cell = _cell(row, col)
        mc = re.fullmatch(r"(%s)(?: ?%s)?" % (_NUM_RE, re.escape(unit_txt)), cell)
        if not mc:
            raise SystemExit(f"gen_channel_model: {key} {name} cell {cell!r} is not the "
                             f"bare number or the number with the target unit {unit_txt!r}")
        other = float(mc.group(1)) * SI.get(suf, 1.0)
        if abs(other - value) > 1e-9 * abs(value):
            raise SystemExit(
                f"gen_channel_model: {key} differs in the {name} column "
                f"({cell!r} vs the target {_cell(row, 2)!r}); the bench supports one "
                "value per quantity -- extend the generator before declaring "
                "per-model values")
    return value, num + suf


def table():
    """The declared channel-model table: values, lengths and spread multipliers.

    Values come back in SI base units; `*_lit` keeps the table's own digits for
    the bench netlist, so the generated file shows 0.20p exactly as declared.
    """
    rows = {}
    for line in SPEC_MD.read_text().splitlines():
        if not line.startswith("|"):
            continue
        first = _cell(line, 1)
        for prefix, key in ROW_OF:
            if not first.startswith(prefix):
                continue
            if key == "lengths":
                rows[key] = [_length(_cell(line, i), name) for i, name in
                             ((2, "target length"), (3, "fallback length"),
                              (4, "stretch length"))]
            elif key == "spread":
                m = _SPREAD_RE.fullmatch(_cell(line, 2))
                if not m:
                    raise SystemExit(
                        f"gen_channel_model: spread target cell {_cell(line, 2)!r} is not "
                        "'R and C each ×<a> and ×<b>'")
                for col, name in ((3, "fallback"), (4, "stretch")):
                    if _cell(line, col) != "same":
                        raise SystemExit(
                            f"gen_channel_model: spread {name} cell {_cell(line, col)!r} "
                            "is not 'same'; the bench supports one spread pair")
                rows[key] = [float(m.group(1)), float(m.group(2))]
            else:
                rows[key], rows[key + "_lit"] = _value(key, line)
    missing = [k for _, k in ROW_OF if k not in rows]
    if missing:
        raise SystemExit(f"gen_channel_model: {SPEC_MD} is missing rows {missing}")
    return rows


TABLE = table()

# (kr, kc): nominal first, then the four declared +-20 % combinations, spelled out
# because `corners.params` is zipped by index, not crossed (gen_channel_eye.py).
SPREAD_POINTS = [(1.0, 1.0)] + [(kr, kc) for kr in TABLE["spread"]
                                for kc in TABLE["spread"]]
PARAM_ROWS = [(length, kr, kc) for length in TABLE["lengths"]
              for kr, kc in SPREAD_POINTS]


# --- the generated bench -------------------------------------------------------

def _ref_ladder(prefix, shorted, len_x="ch_len", kr_x="ch_kr*", kc_x="ch_kc*"):
    """One reference ladder, built from the declared table values only.

    Mirrors chan_rlc's structure exactly as channel-model.md declares it (ten
    uniform RLC pi-sections, half-section caps at the ends, the far-end load at
    the far node) so the DUT/reference ratios cancel the probe-frequency
    corrections. The shorted copy ties the far node to ground, which shorts its
    half-section cap and the far-end load, as shorting chan_rlc's rx pin does to
    C10 and Cfar; the open copy keeps both, plus the same Rleak at the drive node
    the DUT's open copy carries (its DC-path helper moves the 1 MHz read by
    ~2e-7 relative).
    """
    seg_r = "{%stb_r_mm*%s/%d}" % (kr_x, len_x, SECTIONS)
    seg_l = "{tb_l_mm*%s/%d}" % (len_x, SECTIONS)
    seg_c = "{%stb_c_mm*%s/%d}" % (kc_x, len_x, SECTIONS)
    seg_c_half = "{%stb_c_mm*%s/%d/2}" % (kc_x, len_x, SECTIONS)
    lines = [f"C{prefix}0 {prefix}0 0 {seg_c_half}"]
    for k in range(1, SECTIONS + 1):
        cap = seg_c_half if k == SECTIONS else seg_c
        lines += [f"R{prefix}{k} {prefix}{k-1} q{prefix}{k} {seg_r}",
                  f"L{prefix}{k} q{prefix}{k} {prefix}{k} {seg_l}",
                  f"C{prefix}{k} {prefix}{k} 0 {cap}"]
    if shorted:
        lines.append(f"V{prefix}sh {prefix}{SECTIONS} 0 0")
    else:
        lines += [f"C{prefix}far {prefix}{SECTIONS} 0 {{tb_cfar}}",
                  f"R{prefix}leak {prefix}0 0 1e12"]
    return "\n".join(lines)


def bench_netlist():
    t = TABLE
    len_def = int(TABLE["lengths"][0])
    ref_short = _ref_ladder("ya", shorted=True)
    ref_open = _ref_ladder("yb", shorted=False)
    nom = dict(len_x="tb_len0", kr_x="", kc_x="")
    nom_short = _ref_ladder("yc", shorted=True, **nom)
    nom_open = _ref_ladder("yd", shorted=False, **nom)
    l_total = "{tb_l_mm*ch_len}"
    l_total_nom = "{tb_l_mm*tb_len0}"
    return f"""* {TB_NAME} -- GENERATED by gen_channel_model.py; do not edit.
* T-12 conformance bench: spec/channel/channel_rc.cir (the DUT, two bare chan_rlc
* instances) against reference ladders built from the declared table values
* (spec/channel-model.md, parsed by the generator), through identical probes. The
* request grades DUT/reference ratios at +-1 %: a property of the check, not a
* spec bound. Differential on purpose: the probe-frequency observables differ from
* the lumped constants by corrections of the declared ladder itself (README
* "Why differential"), which cancel between the two sides.
* ch_len/ch_kr/ch_kc are top-level .param so corners.params can sweep them:
* {t['lengths'][0]:g}/{t['lengths'][1]:g}/{t['lengths'][2]:g} mm at (kr, kc) = (1,1) and the four
* declared +-20 % combinations of ({t['spread'][0]:g}, {t['spread'][1]:g}).
.include ../../spec/channel/channel_rc.cir
.param ch_len={len_def} ch_kr=1 ch_kc=1
* the declared per-mm values and far-end load, as parsed from spec/channel-model.md
.param tb_r_mm={t['r_mm_lit']} tb_c_mm={t['c_mm_lit']} tb_l_mm={t['l_mm_lit']} tb_cfar={t['cfar_lit']}
.param tb_len0={len_def}
* DUT, far end shorted: at DC the caps are open, so v(txa) at 1 A is the series R
Xs txa rxa 0 chan_rlc len_mm={{ch_len}} kr={{ch_kr}} kc={{ch_kc}}
Vsh rxa 0 0
Iza 0 txa dc 1 ac 1
* DUT, far end open (Rleak only gives the DC operating point a path)
Xo txb rxb 0 chan_rlc len_mm={{ch_len}} kr={{ch_kr}} kc={{ch_kc}}
Rleak txb 0 1e12
Izb 0 txb dc 0 ac 1
* DUT with the subcircuit's own defaults (no len_mm/kr/kc): what consumers such as
* sim/channel-eye instantiate, so a changed default cannot hide behind the sweep
Xsd txc rxc 0 chan_rlc
Vshd rxc 0 0
Izc 0 txc dc 1 ac 1
Xod txd rxd 0 chan_rlc
Rleakd txd 0 1e12
Izd 0 txd dc 0 ac 1
* reference, far end shorted
{ref_short}
Irya 0 ya0 dc 1 ac 1
* reference, far end open
{ref_open}
Iryb 0 yb0 dc 0 ac 1
* fixed nominal references (declared length {len_def} mm, kr = kc = 1) for the default instances
{nom_short}
Iryc 0 yc0 dc 1 ac 1
{nom_open}
Iryd 0 yd0 dc 0 ac 1
* bare inductors of the declared total L, driven like the ladders: Im Z at the L probe
* is omega * L_declared, the quantity the ladder's bias is measured against
Lyl yl0 0 {l_total}
Iryl 0 yl0 dc 0 ac 1
Lyn yn0 0 {l_total_nom}
Iryn 0 yn0 dc 0 ac 1
* the PVT-FULL supply axis rides this dummy rail: the ladder is linear and
* supply-free, so the source exists only that corners.supply_v has a name to alter
Vpvt vpvt 0 dc 1.2
"""


# --- the request ---------------------------------------------------------------

def graded(name, expr):
    return {"name": name, "spec_row": "T-12", "unit": "ratio", "expr": expr,
            "limits": {"min": 1 - TOL, "max": 1 + TOL}}


def l_ratio_expr(dut_short, dut_open, ref_short, ref_open, ref_l):
    """Total-L ratio with the ladder's R-C bias added back (docstring, t12_l_ratio).

    X(n) = vecmax(imag(v(n))), Rr = Re Z_dut / Re Z_ref (shorted end), Cr = reference
    over DUT open-end reactance (the C ratio). With XL = omega * L_declared:
        (X(dut) + (XL - X(ref)) * Rr^2 * Cr) / XL
    """
    def x(n):
        return f"vecmax(imag(v({n})))"

    def re(n):
        return f"vecmax(real(v({n})))"

    rr = f"({re(dut_short)}/{re(ref_short)})"
    cr = f"(vecmax(imag(-v({ref_open})))/vecmax(imag(-v({dut_open}))))"
    return (f"({x(dut_short)}+({x(ref_l)}-{x(ref_short)})*{rr}*{rr}*{cr})"
            f"/{x(ref_l)}")


def steps():
    return [
        {"name": "r_dc", "analysis": {"kind": "op", "args": ""}, "alter": {},
         "measurements": [graded("t12_r_ratio", "v(txa)/v(ya0)"),
                          graded("t12_r_ratio_default", "v(txc)/v(yc0)")]},
        # open-end reactance is -1/(omega C): the C ratio DUT/reference is the
        # REFERENCE reactance over the DUT's
        {"name": "c_lo",
         "analysis": {"kind": "ac", "args": f"lin 1 {F_LO_ARG} {F_LO_ARG}"},
         "alter": {},
         "measurements": [
             graded("t12_c_ratio",
                    "vecmax(imag(-v(yb0)))/vecmax(imag(-v(txb)))"),
             graded("t12_c_ratio_default",
                    "vecmax(imag(-v(yd0)))/vecmax(imag(-v(txd)))")]},
        # the shorted-end Im Z is omega * (total L - the ladder's own R-C bias b); the
        # expression adds b back (see l_ratio_expr) so only total L is graded
        {"name": "l_hi",
         "analysis": {"kind": "ac", "args": f"lin 1 {F_HI_ARG} {F_HI_ARG}"},
         "alter": {},
         "measurements": [
             graded("t12_l_ratio", l_ratio_expr("txa", "txb", "ya0", "yb0", "yl0")),
             graded("t12_l_ratio_default",
                    l_ratio_expr("txc", "txd", "yc0", "yd0", "yn0"))]},
    ]


def request():
    return {
        "engine": "ngspice",
        "netlist": TB_NAME,
        "models": {"pdk": "ihp-sg13g2", "lib": pvt_full.LIB_MOS},
        "backend": "batch",
        "corners": dict(pvt_full.corners(("vpvt",)),
                        params={"ch_len": [p[0] for p in PARAM_ROWS],
                                "ch_kr": [p[1] for p in PARAM_ROWS],
                                "ch_kc": [p[2] for p in PARAM_ROWS]}),
        "analysis_steps": steps(),
        "measurements": [],
        "options": {"osdi_preload": pvt_full.osdi_preload(),
                    "timeout_s": TIMEOUT_S},
        "batch": {"capacity_wait_s": 600},
    }


def outputs():
    return {TB_NAME: bench_netlist(),
            REQUEST_NAME: json.dumps(request(), indent=2) + "\n"}


def main(argv):
    return gen_common.write_or_check(outputs(), argv, base=HERE,
                                     description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
