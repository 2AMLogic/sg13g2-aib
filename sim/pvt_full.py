#!/usr/bin/env python3
"""PVT-FULL, the corner set every recorded analog result carries, defined once.

Stdlib only; no PDK and no simulator. `spec/target-spec.md` ("PVT-FULL: the
corner set every recorded analog result carries") defines the grid; this module
is its one encoding in the repo. Every `klt sim` request generator under `sim/`
builds its `corners` block from here instead of restating the table, and
`scripts/ci/check_corner_bundles.py` checks every committed request against the
same table, so the copies cannot drift apart again.

The bundling rule (`sim/README.md`, `sim/dc-static/README.md`): a process corner
is a bundle of the matching MOS, poly-resistor and diode sections -- the
resistor and diode sections follow the MOS corner. `mos_sf` and `mos_fs` are
mixed MOS corners with no matching resistor or diode section, so they take the
typical ones.

Two request shapes are in use, and both come out of this one table:

  "inline"    corner name `mos_ss`, MOS section a bare string (its library is
              the request's `models.lib`) -- channel-eye, clock-path.
  "explicit"  corner name `ss`, MOS section an explicit {lib, section} pair --
              mc (with `mismatch=True`, i.e. `mos_ss_mismatch`, so per-instance
              mismatch is live), dc-static.

Changing a value here changes the *next* run of every family. It does not touch
a committed record under `sim/*/records/`: those are append-only evidence and
keep the request they were run with.
"""
MODELS = "libs.tech/ngspice/models/"
LIB_MOS = MODELS + "cornerMOSlv.lib"
LIB_RES = MODELS + "cornerRES.lib"
LIB_DIO = MODELS + "cornerDIO.lib"

# MOS corner -> (poly-resistor section, diode section) of the PDK corner libraries
PROCESS = {"tt": ("res_typ", "dio_tt"), "ss": ("res_wcs", "dio_ss"),
           "ff": ("res_bcs", "dio_ff"), "sf": ("res_typ", "dio_tt"),
           "fs": ("res_typ", "dio_tt")}
SUPPLY_V = [1.08, 1.2, 1.32]        # VDDIO, nominal 1.2 V +-10 %
TEMPERATURE_C = [-40, 27, 125]
OSDI = ["psp103", "psp103_nqs", "r3_cmc", "mosvar"]
OSDI_DIR = "$PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/osdi"
N_UNITS = len(PROCESS) * len(SUPPLY_V) * len(TEMPERATURE_C)   # 45


def osdi_preload(osdi_dir=OSDI_DIR):
    """The four OSDI models every bench preloads (PSP103 + r3_cmc + mosvar)."""
    return [f"{osdi_dir}/{m}.osdi" for m in OSDI]


def mos_section(corner, mismatch=False):
    """PDK `cornerMOSlv.lib` section name for a MOS corner key ('ss' -> 'mos_ss')."""
    return f"mos_{corner}" + ("_mismatch" if mismatch else "")


def process(style="inline", mismatch=False, only=None):
    """The `corners.process` list: one bundle per MOS corner.

    style:    "inline" or "explicit" (see the module docstring).
    mismatch: use the PDK's `mos_<c>_mismatch` sections (Monte Carlo benches).
    only:     restrict to these MOS corner keys, in table order (default: all).
    """
    if style not in ("inline", "explicit"):
        raise ValueError(f"unknown style {style!r}")
    out = []
    for c, (res, dio) in PROCESS.items():
        if only is not None and c not in only:
            continue
        sec = mos_section(c, mismatch)
        out.append({"name": sec if style == "inline" else c,
                    "sections": [sec if style == "inline" else {"lib": LIB_MOS, "section": sec},
                                 {"lib": LIB_RES, "section": res},
                                 {"lib": LIB_DIO, "section": dio}]})
    return out


def corners(supplies, style="inline", mismatch=False, only=None,
            supply_v=None, temperature_c=None):
    """The whole `corners` object: process bundles x supplies x temperatures.

    supplies: the supply source names that sweep together (each gets the same
              list, so a grid of N process corners x 3 V x 3 C is 9N units).
    supply_v / temperature_c: override the PVT-FULL lists (single-corner probes
              and bench controls; never used to shrink a graded grid).
    """
    v = SUPPLY_V if supply_v is None else supply_v
    return {"process": process(style, mismatch, only),
            "supply_v": {s: list(v) for s in supplies},
            "temperature_c": list(TEMPERATURE_C if temperature_c is None else temperature_c)}


# --- checking a committed request against the table -------------------------

def _section_of(sections, lib):
    for s in sections:
        if isinstance(s, dict) and s.get("lib", "").endswith(lib.rsplit("/", 1)[-1]):
            return s.get("section")
    return None


def _mos_corner_of(sections):
    """The MOS corner key named by a bundle's sections, or None."""
    sec = _section_of(sections, LIB_MOS)
    if sec is None:
        for s in sections:
            if isinstance(s, str):
                sec = s
                break
    if not isinstance(sec, str) or not sec.startswith("mos_"):
        return None
    return sec[len("mos_"):].removesuffix("_mismatch")


def check_corners(block, where=""):
    """Problems in one request's `corners` block; empty list means it conforms.

    Checks the invariant that drifted (#184): every process entry bundles the
    MOS, poly-resistor and diode sections that this table pairs, and the supply
    and temperature values are drawn from the PVT-FULL lists. A reduced grid (a
    single-corner probe, a bench control) is accepted -- a *wrong* pairing or an
    off-grid value is not.
    """
    bad = []
    p = f"{where}: " if where else ""
    if not isinstance(block, dict):
        return [f"{p}corners is not an object"]
    for entry in block.get("process") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("sections"), list):
            bad.append(f"{p}process entry is not a bundle: {entry!r}")
            continue
        secs = entry["sections"]
        c = _mos_corner_of(secs)
        if c is None:
            bad.append(f"{p}process {entry.get('name')!r} names no MOS section")
            continue
        if c not in PROCESS:
            bad.append(f"{p}process {entry.get('name')!r}: unknown MOS corner {c!r}")
            continue
        want_res, want_dio = PROCESS[c]
        for lib, want, what in ((LIB_RES, want_res, "resistor"), (LIB_DIO, want_dio, "diode")):
            got = _section_of(secs, lib)
            if got is None:
                bad.append(f"{p}process {entry.get('name')!r}: no {what} section "
                           f"(mos_{c} must bundle {want})")
            elif got != want:
                bad.append(f"{p}process {entry.get('name')!r}: {what} section {got!r}, "
                           f"expected {want!r} for mos_{c} (sim/pvt_full.py)")
    for name, vals in (block.get("supply_v") or {}).items():
        off = [v for v in vals if v not in SUPPLY_V]
        if off:
            bad.append(f"{p}supply_v[{name}] has off-grid values {off} (PVT-FULL: {SUPPLY_V})")
    off = [t for t in block.get("temperature_c") or [] if t not in TEMPERATURE_C]
    if off:
        bad.append(f"{p}temperature_c has off-grid values {off} (PVT-FULL: {TEMPERATURE_C})")
    return bad
