v {xschem version=3.4.7 file_version=1.3
* aib_pad_esd -- pad protection structure for one AIB-class I/O pin.
* Topology only: primary diode pair + rail clamp at PAD, series resistor
* to the core node PADI, small secondary diode pair at PADI (Dp2 to VDDIO; Mn2 to VSS, a
* grounded-gate NMOS used as its drain-junction diode, see sim/README.md). Thin-oxide
* devices only (T-06). Sizes are first-cut placeholders; no ESD level
* (T-25) and no capacitance (T-24) is claimed by this source.
* Rail clamp is a gate-grounded NMOS VDDIO->VSS. PAD is wirebond/bump side.
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/dpantenna.sym} 200 200 0 0 {name=Dp1 model=dpantenna l=10u w=10u spiceprefix=X}
C {lab_pin.sym} 200 230 0 0 {name=l1 lab=PAD}
C {lab_pin.sym} 200 170 0 0 {name=l2 lab=VDDIO}
C {sg13g2_pr/dantenna.sym} 420 200 0 0 {name=Dn1 model=dantenna l=10u w=10u spiceprefix=X}
C {lab_pin.sym} 420 230 0 0 {name=l3 lab=VSS}
C {lab_pin.sym} 420 170 0 0 {name=l4 lab=PAD}
C {sg13g2_pr/sg13_lv_nmos.sym} 640 200 0 0 {name=Mclamp model=sg13_lv_nmos w=40u l=0.35u ng=20 m=1}
C {lab_pin.sym} 660 170 0 0 {name=l5 lab=VDDIO}
C {lab_pin.sym} 620 200 0 0 {name=l6 lab=VSS}
C {lab_pin.sym} 660 230 0 0 {name=l7 lab=VSS}
C {lab_pin.sym} 660 200 0 0 {name=l8 lab=VSS}
C {sg13g2_pr/rppd.sym} 860 200 0 0 {name=Resd model=rppd w=2u l=2u b=0 m=1 body=VSS spiceprefix=X}
C {lab_pin.sym} 860 170 0 0 {name=l9 lab=PAD}
C {lab_pin.sym} 860 230 0 0 {name=l10 lab=PADI}
C {sg13g2_pr/dpantenna.sym} 1080 200 0 0 {name=Dp2 model=dpantenna l=2u w=2u spiceprefix=X}
C {lab_pin.sym} 1080 230 0 0 {name=l11 lab=PADI}
C {lab_pin.sym} 1080 170 0 0 {name=l12 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 1300 200 0 0 {name=Mn2 model=sg13_lv_nmos w=1u l=0.13u ng=1 m=1}
C {lab_pin.sym} 1320 170 0 0 {name=l13 lab=PADI}
C {lab_pin.sym} 1280 200 0 0 {name=l14 lab=VSS}
C {lab_pin.sym} 1320 230 0 0 {name=l15 lab=VSS}
C {lab_pin.sym} 1320 200 0 0 {name=l16 lab=VSS}
C {iopin.sym} -100 100 0 0 {name=p1 lab=PAD}
C {iopin.sym} -100 160 0 0 {name=p2 lab=PADI}
C {iopin.sym} -100 220 0 0 {name=p3 lab=VDDIO}
C {iopin.sym} -100 280 0 0 {name=p4 lab=VSS}
