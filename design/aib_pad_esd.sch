v {xschem version=3.4.7 file_version=1.3
* aib_pad_esd -- pad protection structure for one AIB-class I/O pin.
* Primary pair + rail clamp at PAD: Dp1 to VDDIO is the PDK pad diode diodevdd_2kv
* (sg13g2_esd.lib), adopted from the dpantenna antenna-diode by DR-0029 (issue #196,
* operator ruling 2026-11-18: T-24 is held at its fallback column so the 0.5 A T-25
* discharge has a device that can carry it); Mn1 to VSS is a grounded-gate NMOS used
* as its drain-junction diode, see sim/README.md. Series resistor
* to the core node PADI, small secondary diode pair at PADI (Dp2 to VDDIO; Mn2 to VSS, a
* grounded-gate NMOS used as its drain-junction diode, see sim/README.md). Thin-oxide
* devices only (T-06). T-24 is held at its fallback column (108.9 fF against the 100 fF
* target, DR-0018/DR-0029); the T-25 0.5 A transient is sim/esd-transient/.
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/diodevdd_2kv.sym} 200 200 0 0 {name=Dp1 model=diodevdd_2kv m=1 spiceprefix=X}
C {lab_pin.sym} 200 230 0 0 {name=l1 lab=PAD}
C {lab_pin.sym} 200 170 0 0 {name=l2 lab=VDDIO}
C {lab_pin.sym} 170 200 0 0 {name=l19 lab=VSS}
C {sg13g2_pr/sg13_lv_nmos.sym} 420 200 0 0 {name=Mn1 model=sg13_lv_nmos w=20u l=0.13u ng=10 m=1}
C {lab_pin.sym} 440 170 0 0 {name=l3 lab=PAD}
C {lab_pin.sym} 400 200 0 0 {name=l4 lab=VSS}
C {lab_pin.sym} 440 230 0 0 {name=l17 lab=VSS}
C {lab_pin.sym} 440 200 0 0 {name=l18 lab=VSS}
C {sg13g2_pr/sg13_lv_nmos.sym} 640 200 0 0 {name=Mclamp model=sg13_lv_nmos w=40u l=0.35u ng=20 m=1}
C {lab_pin.sym} 660 170 0 0 {name=l5 lab=VDDIO}
C {lab_pin.sym} 620 200 0 0 {name=l6 lab=VSS}
C {lab_pin.sym} 660 230 0 0 {name=l7 lab=VSS}
C {lab_pin.sym} 660 200 0 0 {name=l8 lab=VSS}
C {sg13g2_pr/rppd.sym} 860 200 0 0 {name=Resd model=rppd w=2u l=1u b=0 m=1 body=VSS spiceprefix=X}
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
