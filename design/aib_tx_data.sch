v {xschem version=3.4.7 file_version=1.3
* aib_tx_data -- unterminated full-swing tristate data driver (T-06, T-07, T-08, T-28).
* PAD = DIN when OE=1; both output devices off when OE=0.
* Gating: GP = NAND(DIN,OE), GN = NOR(DIN,!OE); output stage Mp/Mn.
* Weak pulls: PUN=0 enables the pull-up (Mpu+Rpu), PD=1 the pull-down
* (Mpd+Rpd); about 10-20 kohm each (T-28). PUN=1 and PD=0 select none.
* Output stage sized so Ron lands in 40-80 ohm by hand estimate (T-08);
* all sizes are first-cut and UNSIMULATED. No row is claimed met here.
* PAD is the driver output; the pad_esd cell is not instantiated here.
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/sg13_lv_pmos.sym} 200 200 0 0 {name=Mi1p model=sg13_lv_pmos w=2u l=0.13u ng=1 m=1}
C {lab_pin.sym} 220 230 0 0 {name=l1 lab=OEB}
C {lab_pin.sym} 180 200 0 0 {name=l2 lab=OE}
C {lab_pin.sym} 220 170 0 0 {name=l3 lab=VDDIO}
C {lab_pin.sym} 220 200 0 0 {name=l4 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 420 200 0 0 {name=Mi1n model=sg13_lv_nmos w=1u l=0.13u ng=1 m=1}
C {lab_pin.sym} 440 170 0 0 {name=l5 lab=OEB}
C {lab_pin.sym} 400 200 0 0 {name=l6 lab=OE}
C {lab_pin.sym} 440 230 0 0 {name=l7 lab=VSS}
C {lab_pin.sym} 440 200 0 0 {name=l8 lab=VSS}
C {sg13g2_pr/sg13_lv_pmos.sym} 640 200 0 0 {name=Mnd1p model=sg13_lv_pmos w=4u l=0.13u ng=2 m=1}
C {lab_pin.sym} 660 230 0 0 {name=l9 lab=GP}
C {lab_pin.sym} 620 200 0 0 {name=l10 lab=DIN}
C {lab_pin.sym} 660 170 0 0 {name=l11 lab=VDDIO}
C {lab_pin.sym} 660 200 0 0 {name=l12 lab=VDDIO}
C {sg13g2_pr/sg13_lv_pmos.sym} 860 200 0 0 {name=Mnd2p model=sg13_lv_pmos w=4u l=0.13u ng=2 m=1}
C {lab_pin.sym} 880 230 0 0 {name=l13 lab=GP}
C {lab_pin.sym} 840 200 0 0 {name=l14 lab=OE}
C {lab_pin.sym} 880 170 0 0 {name=l15 lab=VDDIO}
C {lab_pin.sym} 880 200 0 0 {name=l16 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 1080 200 0 0 {name=Mnd1n model=sg13_lv_nmos w=4u l=0.13u ng=2 m=1}
C {lab_pin.sym} 1100 170 0 0 {name=l17 lab=GP}
C {lab_pin.sym} 1060 200 0 0 {name=l18 lab=DIN}
C {lab_pin.sym} 1100 230 0 0 {name=l19 lab=NA}
C {lab_pin.sym} 1100 200 0 0 {name=l20 lab=VSS}
C {sg13g2_pr/sg13_lv_nmos.sym} 1300 200 0 0 {name=Mnd2n model=sg13_lv_nmos w=4u l=0.13u ng=2 m=1}
C {lab_pin.sym} 1320 170 0 0 {name=l21 lab=NA}
C {lab_pin.sym} 1280 200 0 0 {name=l22 lab=OE}
C {lab_pin.sym} 1320 230 0 0 {name=l23 lab=VSS}
C {lab_pin.sym} 1320 200 0 0 {name=l24 lab=VSS}
C {sg13g2_pr/sg13_lv_pmos.sym} 200 400 0 0 {name=Mnr1p model=sg13_lv_pmos w=4u l=0.13u ng=2 m=1}
C {lab_pin.sym} 220 430 0 0 {name=l25 lab=NB}
C {lab_pin.sym} 180 400 0 0 {name=l26 lab=DIN}
C {lab_pin.sym} 220 370 0 0 {name=l27 lab=VDDIO}
C {lab_pin.sym} 220 400 0 0 {name=l28 lab=VDDIO}
C {sg13g2_pr/sg13_lv_pmos.sym} 420 400 0 0 {name=Mnr2p model=sg13_lv_pmos w=4u l=0.13u ng=2 m=1}
C {lab_pin.sym} 440 430 0 0 {name=l29 lab=GN}
C {lab_pin.sym} 400 400 0 0 {name=l30 lab=OEB}
C {lab_pin.sym} 440 370 0 0 {name=l31 lab=NB}
C {lab_pin.sym} 440 400 0 0 {name=l32 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 640 400 0 0 {name=Mnr1n model=sg13_lv_nmos w=2u l=0.13u ng=2 m=1}
C {lab_pin.sym} 660 370 0 0 {name=l33 lab=GN}
C {lab_pin.sym} 620 400 0 0 {name=l34 lab=DIN}
C {lab_pin.sym} 660 430 0 0 {name=l35 lab=VSS}
C {lab_pin.sym} 660 400 0 0 {name=l36 lab=VSS}
C {sg13g2_pr/sg13_lv_nmos.sym} 860 400 0 0 {name=Mnr2n model=sg13_lv_nmos w=2u l=0.13u ng=2 m=1}
C {lab_pin.sym} 880 370 0 0 {name=l37 lab=GN}
C {lab_pin.sym} 840 400 0 0 {name=l38 lab=OEB}
C {lab_pin.sym} 880 430 0 0 {name=l39 lab=VSS}
C {lab_pin.sym} 880 400 0 0 {name=l40 lab=VSS}
C {sg13g2_pr/sg13_lv_pmos.sym} 1080 400 0 0 {name=Mp model=sg13_lv_pmos w=28u l=0.13u ng=28 m=1}
C {lab_pin.sym} 1100 430 0 0 {name=l41 lab=PAD}
C {lab_pin.sym} 1060 400 0 0 {name=l42 lab=GP}
C {lab_pin.sym} 1100 370 0 0 {name=l43 lab=VDDIO}
C {lab_pin.sym} 1100 400 0 0 {name=l44 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 1300 400 0 0 {name=Mn model=sg13_lv_nmos w=14u l=0.13u ng=14 m=1}
C {lab_pin.sym} 1320 370 0 0 {name=l45 lab=PAD}
C {lab_pin.sym} 1280 400 0 0 {name=l46 lab=GN}
C {lab_pin.sym} 1320 430 0 0 {name=l47 lab=VSS}
C {lab_pin.sym} 1320 400 0 0 {name=l48 lab=VSS}
C {sg13g2_pr/sg13_lv_pmos.sym} 200 600 0 0 {name=Mpu model=sg13_lv_pmos w=2u l=0.13u ng=1 m=1}
C {lab_pin.sym} 220 630 0 0 {name=l49 lab=PUX}
C {lab_pin.sym} 180 600 0 0 {name=l50 lab=PUN}
C {lab_pin.sym} 220 570 0 0 {name=l51 lab=VDDIO}
C {lab_pin.sym} 220 600 0 0 {name=l52 lab=VDDIO}
C {sg13g2_pr/rppd.sym} 420 600 0 0 {name=Rpu model=rppd w=0.5u l=24u b=0 m=1 body=VSS spiceprefix=X}
C {lab_pin.sym} 420 570 0 0 {name=l53 lab=PUX}
C {lab_pin.sym} 420 630 0 0 {name=l54 lab=PAD}
C {sg13g2_pr/sg13_lv_nmos.sym} 640 600 0 0 {name=Mpd model=sg13_lv_nmos w=1u l=0.13u ng=1 m=1}
C {lab_pin.sym} 660 570 0 0 {name=l55 lab=PDX}
C {lab_pin.sym} 620 600 0 0 {name=l56 lab=PD}
C {lab_pin.sym} 660 630 0 0 {name=l57 lab=VSS}
C {lab_pin.sym} 660 600 0 0 {name=l58 lab=VSS}
C {sg13g2_pr/rppd.sym} 860 600 0 0 {name=Rpd model=rppd w=0.5u l=24u b=0 m=1 body=VSS spiceprefix=X}
C {lab_pin.sym} 860 570 0 0 {name=l59 lab=PAD}
C {lab_pin.sym} 860 630 0 0 {name=l60 lab=PDX}
C {ipin.sym} -100 100 0 0 {name=p1 lab=DIN}
C {ipin.sym} -100 160 0 0 {name=p2 lab=OE}
C {ipin.sym} -100 220 0 0 {name=p3 lab=PUN}
C {ipin.sym} -100 280 0 0 {name=p4 lab=PD}
C {iopin.sym} -100 340 0 0 {name=p5 lab=PAD}
C {iopin.sym} -100 400 0 0 {name=p6 lab=VDDIO}
C {iopin.sym} -100 460 0 0 {name=p7 lab=VSS}
