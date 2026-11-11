#!/usr/bin/env python3
"""Generate the single-corner `klt sim` requests of the T-16 attribution (issue #161).

Stdlib only; imports gen_channel_eye for the stimulus, edge pairing and corner tables.
  python3 -I sim/channel-eye/gen_t16attr.py OUTDIR
writes OUTDIR/request_t16attr_<link>_<corner>.json for link in {ch, id} (CH-3MM-RC, ideal
connection) and corner in {ss (mos_ss, 1.08 V, 125 C, the binding corner), tt (mos_tt,
1.20 V, 27 C)}. Each request is one unit (local backend). Measurements: the eight bench
t16_* cards unchanged (self-check against the CH record) plus, for each of the eight edge
pairs, the absolute 50 % crossing time of every probe stage (t16attr_probes.inc).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_channel_eye as g  # noqa: E402

UI = g.UI_PS * 1e-12
LANES = ("a", "p", "n")  # data A, clock pin rxc (clk), clock pin rxcb (clkb)
CORNERS = {"ss": ("mos_ss", 1.08, 125), "tt": ("mos_tt", 1.2, 27)}
LINKS = {"ch": "tb_t16attr_ch.cir", "id": "tb_t16attr_id.cir"}


def edges():
    """{bench name: dict(pol, i, cpol)}: data edge i of polarity pol, clock edge at (i + 0.5) UI."""
    b = g.stream()
    trs = [t for t in g.transitions(b) if t[1] and t[0] >= 1]
    out = {}
    _, cards = g.skew_pairs()
    for nm, card in cards:
        m = re.search(r"v\(dsa\) VAL=0 (RISE|FALL)=(\d+) TARG v\(csig\) VAL=0 (RISE|FALL)=(\d+)", card)
        pol, n, cpol = m.group(1), int(m.group(2)), m.group(3)
        seq = [t[0] for t in trs if t[1] == pol.lower()]
        # the n-th transition of this polarity counted from the stream start (rises_before / falls_before)
        i = seq[n - 1]
        assert cpol == ("RISE" if i % 2 == 0 else "FALL"), nm
        out[nm] = {"pol": pol, "i": i, "cpol": cpol}
    return out


def stage_cards(nm, e):
    """Absolute crossing-time .meas cards for the edge pair `nm`; names `att_<nm>__<lane><stage>`."""
    flip = lambda p: "FALL" if p == "RISE" else "RISE"
    i = e["i"]
    td_d, td_c = i * UI - 150e-12, (i + 0.5) * UI - 150e-12
    cards = []
    for lane in LANES:
        pol = e["pol"] if lane == "a" else (e["cpol"] if lane == "p" else flip(e["cpol"]))
        td = td_d if lane == "a" else td_c
        for s in range(4):
            cards.append((f"att_{nm}__{lane}{s}",
                          f".meas tran att_{nm}__{lane}{s} WHEN v(q{lane}{s})=0 {pol}=1 TD={td:.6g}"))
    cards.append((f"att_{nm}__csig", f".meas tran att_{nm}__csig WHEN v(csig)=0 {e['cpol']}=1 TD={td_c:.6g}"))
    cards.append((f"att_{nm}__dsa", f".meas tran att_{nm}__dsa WHEN v(dsa)=0 {e['pol']}=1 TD={td_d:.6g}"))
    return cards


def request(link, corner):
    proc, vdd, temp = CORNERS[corner]
    r = g.request("ch")
    r["netlist"] = LINKS[link]
    r["backend"] = "local"
    r.pop("batch", None)
    r["corners"] = {"process": [c for c in r["corners"]["process"] if c["name"] == proc],
                    "supply_v": {s: [vdd] for s in g.SUPPLIES}, "temperature_c": [temp]}
    m = [x for x in g.measurements("ch") if x["name"].startswith("t16_")]
    for x in m:
        x.pop("limits", None)
    ed = edges()
    for nm, e in ed.items():
        for name, card in stage_cards(nm, e):
            m.append({"name": name, "unit": "s", "spice": card})
    r["measurements"] = m
    r["options"]["timeout_s"] = 900
    return r


def main(argv):
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    for link in LINKS:
        for corner in CORNERS:
            (out / f"request_t16attr_{link}_{corner}.json").write_text(json.dumps(request(link, corner), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
