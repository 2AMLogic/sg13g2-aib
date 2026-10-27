v {xschem version=3.4.7 file_version=1.3
* aib_tx_clk -- quasi-differential forwarded-clock driver (T-04).
* Two aib_tx_data drivers: CLK_D -> CLK_PAD and CLKB_D -> CLKB_PAD. The
* datapath supplies CLKB_D as the complement of CLK_D; this cell does not
* generate it. Same unterminated full-swing output stage as the data pin,
* so clk and data see matched drivers. Duty-cycle correction is out of
* scope for this repo (see CLAUDE.md); T-17 is a simulation row.
}
G {}
K {}
V {}
S {}
E {}
C {aib_tx_data.sym} 200 200 0 0 {name=Xclk}
C {lab_pin.sym} 140 110 0 0 {name=l1 lab=CLK_D}
C {lab_pin.sym} 140 130 0 0 {name=l2 lab=OE}
C {lab_pin.sym} 140 150 0 0 {name=l3 lab=PUN}
C {lab_pin.sym} 140 170 0 0 {name=l4 lab=PD}
C {lab_pin.sym} 260 110 0 0 {name=l5 lab=CLK_PAD}
C {lab_pin.sym} 200 80 0 0 {name=l6 lab=VDDIO}
C {lab_pin.sym} 200 320 0 0 {name=l7 lab=VSS}
C {aib_tx_data.sym} 500 200 0 0 {name=Xclkb}
C {lab_pin.sym} 440 110 0 0 {name=l8 lab=CLKB_D}
C {lab_pin.sym} 440 130 0 0 {name=l9 lab=OE}
C {lab_pin.sym} 440 150 0 0 {name=l10 lab=PUN}
C {lab_pin.sym} 440 170 0 0 {name=l11 lab=PD}
C {lab_pin.sym} 560 110 0 0 {name=l12 lab=CLKB_PAD}
C {lab_pin.sym} 500 80 0 0 {name=l13 lab=VDDIO}
C {lab_pin.sym} 500 320 0 0 {name=l14 lab=VSS}
C {ipin.sym} -100 100 0 0 {name=p1 lab=CLK_D}
C {ipin.sym} -100 160 0 0 {name=p2 lab=CLKB_D}
C {ipin.sym} -100 220 0 0 {name=p3 lab=OE}
C {ipin.sym} -100 280 0 0 {name=p4 lab=PUN}
C {ipin.sym} -100 340 0 0 {name=p5 lab=PD}
C {iopin.sym} -100 400 0 0 {name=p6 lab=CLK_PAD}
C {iopin.sym} -100 460 0 0 {name=p7 lab=CLKB_PAD}
C {iopin.sym} -100 520 0 0 {name=p8 lab=VDDIO}
C {iopin.sym} -100 580 0 0 {name=p9 lab=VSS}
