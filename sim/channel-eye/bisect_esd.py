#!/usr/bin/env python3
"""bisect_esd.py -- single-corner debug probe for the pad-ESD transient abort (issue #60).

NOT a recorded result: one corner (mos_tt, 1.20 V, 27 C), no PVT grid, no limits. It writes
one single-lane TX -> [ESD] -> CH-3MM-RC -> [ESD] -> RX netlist per variant into OUTDIR,
which a person runs one at a time with `ngspice -b` (a single run each is within host
rules; never loop them in parallel). Variants:

  b00 / b10 / b01 / b11   ESD cell absent / TX side only / RX side only / both
  x_<elem>                b10 with one element of aib_pad_esd removed (XDp1 XDn1 XMclamp
                          XResd XDp2 XDn2)
  sub_<k>                 b10 with XDn2 replaced by a 1e15 ohm resistor ("res") or a 1 fF
                          capacitor ("cap"): control for "the element is electrical"
  v_<k>                   b10 with XDn2 replaced by a candidate (VARIANTS below): smaller
                          dantenna, series resistor ahead of it, gate-grounded NMOS drain
                          junction. Only the XDn2 line changes. vb_<k> is the same with the
                          cell on both pads (TX and RX side).

Usage: bisect_esd.py OUTDIR [PDK_ROOT]
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
PDK = Path(sys.argv[2] if len(sys.argv) > 2 else "~/share/pdk").expanduser() / "ihp-sg13g2/libs.tech/ngspice"
ESD = (REPO / "design/aib_pad_esd.spice").read_text()
VARIANTS = {
    "l1": "XDn2 VSS PADI dantenna l=1u w=1u",
    "min": "XDn2 VSS PADI dantenna l=0.78u w=0.78u",
    "r100": "XRs2 PADI PADX VSS rppd w=0.5u l=2u m=1 b=0\nXDn2 VSS PADX dantenna l=2u w=2u",
    "r1k": "XRs2 PADI PADX VSS rppd w=0.5u l=19u m=1 b=0\nXDn2 VSS PADX dantenna l=2u w=2u",
    "nmos": "XMn2 PADI VSS VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1",
}
ELEMS = ["XDp1", "XDn1", "XMclamp", "XResd", "XDp2", "XDn2"]


def netlist(name, esd_t, esd_r, esd_file):
    t = "Xesdt txp txi vtx 0 aib_pad_esd" if esd_t else "Rt txp txi 1m"
    r = "Xesdr rxp rxi vrx 0 aib_pad_esd" if esd_r else "Rr rxp rxi 1m"
    return f"""* {name}: issue #60 debug probe, mos_tt 1.20 V 27 C, not a recorded result
.include {REPO}/spec/channel/channel_rc.cir
.include {REPO}/design/aib_tx_data.spice
.include {REPO}/design/aib_rx_data.spice
.include {esd_file}
.subckt link txp rxp gnd
Xch txp rxp gnd chan_rlc len_mm=3
.ends link
Vtx vtx 0 1.2
Vrx vrx 0 1.2
Vin da 0 pwl(0 0 0.5n 0 0.6n 1.2 1.5n 1.2 1.6n 0 2.5n 0 2.6n 1.2)
Xtx da vtx vtx 0 txi vtx 0 aib_tx_data
{t}
Xlnk txp rxp 0 link
{r}
Xrx rxi dout vrx 0 aib_rx_data
Cdout dout 0 5f
.control
pre_osdi {PDK}/osdi/psp103.osdi
pre_osdi {PDK}/osdi/psp103_nqs.osdi
pre_osdi {PDK}/osdi/r3_cmc.osdi
pre_osdi {PDK}/osdi/mosvar.osdi
tran 2p 3n 0 5p
meas tran vmax max v(rxp)
.endc
.lib {PDK}/models/cornerMOSlv.lib mos_tt
.lib {PDK}/models/cornerRES.lib res_typ
.lib {PDK}/models/cornerDIO.lib dio_tt
.end
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = REPO / "design/aib_pad_esd.spice"
    for name, t, r in [("b00", 0, 0), ("b10", 1, 0), ("b01", 0, 1), ("b11", 1, 1)]:
        (OUT / f"{name}.cir").write_text(netlist(name, t, r, base))
    for e in ELEMS:
        f = OUT / f"esd_x_{e}.spice"
        f.write_text("\n".join(l for l in ESD.splitlines() if not l.startswith(e + " ")) + "\n")
        (OUT / f"x_{e}.cir").write_text(netlist(f"x_{e}", 1, 0, f))
    for k, rep in {"res": "Rdn2 VSS PADI 1e15", "cap": "Cdn2 VSS PADI 1f"}.items():
        f = OUT / f"esd_sub_{k}.spice"
        f.write_text("\n".join(rep if l.startswith("XDn2 ") else l for l in ESD.splitlines()) + "\n")
        (OUT / f"sub_{k}.cir").write_text(netlist(f"sub_{k}", 1, 0, f))
    for k, rep in VARIANTS.items():
        f = OUT / f"esd_v_{k}.spice"
        f.write_text("\n".join(rep if l.startswith("XDn2 ") else l for l in ESD.splitlines()) + "\n")
        (OUT / f"v_{k}.cir").write_text(netlist(f"v_{k}", 1, 0, f))
        (OUT / f"vb_{k}.cir").write_text(netlist(f"vb_{k}", 1, 1, f))
    print(f"bisect_esd.py: wrote {len(list(OUT.glob('*.cir')))} netlists to {OUT}")


main()
