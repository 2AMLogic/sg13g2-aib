v {xschem version=3.4.7 file_version=1.3
* aib_rx_clk -- quasi-differential forwarded-clock receiver (T-04).
* Two aib_rx_data receivers, one per leg. The clk/clkb crossing at the
* receiver is what T-04 verifies in simulation; nothing is claimed here.
}
G {}
K {}
V {}
S {}
E {}
C {aib_rx_data.sym} 200 200 0 0 {name=Xclk}
C {lab_pin.sym} 140 170 0 0 {name=l1 lab=CLK_PAD}
C {lab_pin.sym} 260 170 0 0 {name=l2 lab=CLK_O}
C {lab_pin.sym} 200 140 0 0 {name=l3 lab=VDDIO}
C {lab_pin.sym} 200 260 0 0 {name=l4 lab=VSS}
C {aib_rx_data.sym} 500 200 0 0 {name=Xclkb}
C {lab_pin.sym} 440 170 0 0 {name=l5 lab=CLKB_PAD}
C {lab_pin.sym} 560 170 0 0 {name=l6 lab=CLKB_O}
C {lab_pin.sym} 500 140 0 0 {name=l7 lab=VDDIO}
C {lab_pin.sym} 500 260 0 0 {name=l8 lab=VSS}
C {ipin.sym} -100 100 0 0 {name=p1 lab=CLK_PAD}
C {ipin.sym} -100 160 0 0 {name=p2 lab=CLKB_PAD}
C {opin.sym} -100 220 0 0 {name=p3 lab=CLK_O}
C {opin.sym} -100 280 0 0 {name=p4 lab=CLKB_O}
C {iopin.sym} -100 340 0 0 {name=p5 lab=VDDIO}
C {iopin.sym} -100 400 0 0 {name=p6 lab=VSS}
