#!/usr/bin/env python3
"""Generate the T-16 pad-loading sizing-study requests (issue #251).

Stdlib only. `python3 -I sim/channel-eye/gen_t16sizing.py [--check]`.

The study sweeps three levers of the pad ESD cell, lifted to top-level `.param` in
`esd_sz_dpa.inc` / `esd_sz_2kv.inc` (defaults = the committed cell, so candidate S00 is the
committed design):
  sz_dp  XDp1 side (dpantenna l = w), metres      -- dpa family only
  sz_ng  XMn1 finger count, w = 2 um x ng          -- both
  sz_rl  XResd length at w = 2 um                  -- both
Requests (all `request("ch")` measurements, limits and stimulus, so they cannot drift):
  request_t16sz_dpa.json / request_t16sz_2kv.json   screen: kr = kc = 1.2, mos_ss + mos_fs,
        1.08 V, -40/125 C, every candidate of the family (the binding region of
        records 20261111T231422Z-t16attr and 20261113T223804Z-ch-spread).
  request_t16sz_fin_<id>.json  written on demand by `gen_t16sizing.py --finalist ID` (the
        finalist's PVT-FULL x 4 spread run; see run_t16sizing.sh), which regenerates
        it before every run, so it is disposable output, not committed.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import gen_channel_eye as ce  # noqa: E402
import gen_common  # noqa: E402
import pvt_full  # noqa: E402




def um(x):
    return round(x * 1e-6, 12)
# id -> (sz_dp [m], sz_ng, sz_rl [m]); S00 is the committed cell.
DPA = {
    "S00": (um(4.5), 10, um(2.0)),
    "S01": (um(4.0), 10, um(2.0)),
    "S02": (um(3.5), 10, um(2.0)),
    "S03": (um(3.0), 10, um(2.0)),
    "S04": (um(2.5), 10, um(2.0)),
    "S05": (um(4.5), 5, um(2.0)),
    "S06": (um(4.5), 2, um(2.0)),
    "S07": (um(4.5), 10, um(1.0)),
    "S08": (um(4.5), 10, um(0.5)),
    "S09": (um(3.5), 5, um(2.0)),
    "S10": (um(3.0), 5, um(1.0)),
    "S11": (um(3.5), 5, um(1.0)),
}
KV2 = {
    "K00": (um(4.5), 10, um(2.0)),
    "K01": (um(4.5), 5, um(2.0)),
    "K02": (um(4.5), 10, um(1.0)),
    "K03": (um(4.5), 5, um(1.0)),
}
FAMILY = {"dpa": DPA, "2kv": KV2}
SCREEN_PROCESS = ("ss", "fs")


def screen(fam, cands=None):
    cands = FAMILY[fam] if cands is None else {k: FAMILY[fam][k] for k in cands}
    r = ce.request("ch")
    r["netlist"] = f"tb_t16sz_{fam}.cir"
    r["corners"] = pvt_full.corners(ce.SUPPLIES, only=SCREEN_PROCESS, supply_v=[1.08],
                                    temperature_c=[-40, 125])
    ids = list(cands)
    r["corners"]["params"] = {
        "ch_kr": [1.2] * len(ids), "ch_kc": [1.2] * len(ids),
        "sz_dp": [cands[i][0] for i in ids], "sz_ng": [cands[i][1] for i in ids],
        "sz_rl": [cands[i][2] for i in ids]}
    r["options"] = dict(r["options"], timeout_s=ce.SPREAD_TIMEOUT_S)
    return r


def finalist(fam, cid):
    """PVT-FULL x the four (kr, kc) spread pairs for ONE candidate (and nominal as a fifth)."""
    c = FAMILY[fam][cid]
    pairs = ce.CH_SPREAD
    r = ce.spread_request()
    r["netlist"] = f"tb_t16sz_{fam}.cir"
    r["corners"] = dict(r["corners"], params={
        "ch_kr": [p[0] for p in pairs], "ch_kc": [p[1] for p in pairs],
        "sz_dp": [c[0]] * len(pairs), "sz_ng": [c[1]] * len(pairs), "sz_rl": [c[2]] * len(pairs)})
    return r


def dc(fam):
    """T-06/T-07/T-08/T-11/T-24/T-28 (the item-5 dc-static set, unchanged steps and limits) for
    every candidate of the family at PVT-FULL: 45 corners x candidates, params zipped."""
    sys.path.insert(0, str(HERE.parent / "dc-static"))
    import gen_dc_static as dcs
    r = dcs.request(f"tb_dc_static_sz_{fam}.cir", dcs.DC_STEPS, dcs.DC_TOP)
    ids = list(FAMILY[fam])
    r["corners"]["params"] = {"sz_dp": [FAMILY[fam][i][0] for i in ids],
                              "sz_ng": [FAMILY[fam][i][1] for i in ids],
                              "sz_rl": [FAMILY[fam][i][2] for i in ids]}
    return r


def outputs():
    o = {f"request_t16sz_{f}.json": json.dumps(screen(f), indent=2) + "\n" for f in FAMILY}
    for f in FAMILY:
        o[str(HERE.parent / "dc-static" / f"request_t16sz_{f}.json")] = json.dumps(dc(f), indent=2) + "\n"
    return o


def main(argv):
    if argv[:1] == ["--finalist"]:
        fam, cid = ("dpa" if argv[1].startswith("S") else "2kv"), argv[1]
        out = HERE / f"request_t16sz_fin_{cid}.json"
        out.write_text(json.dumps(finalist(fam, cid), indent=2) + "\n")
        print(out)
        return 0
    return gen_common.write_or_check(outputs(), argv, base=HERE,
                                     description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
