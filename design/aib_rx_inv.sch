v {xschem version=3.4.7 file_version=1.3
* aib_rx_inv -- single-ended full-swing inverter receiver, no hysteresis.
* Two inverters in series; the first (Mi1) is sized for a switching
* threshold near VDDIO/2, the second (Mi2) restores the edge. No feedback,
* so no hysteresis by construction. This is the committed receiver that
* design/aib_rx_clk.spice instantiated (as two embedded aib_rx_data copies)
* until the #398 split; the clock legs keep it because the supply-referenced
* stage adopted for the data lanes multiplies clock-path duty distortion
* ~8x at the binding corner (sim/rx-threshold-study, clock-path leg). Its
* inverter threshold moves with the sf/fs corners and with mismatch, so it
* does not close T-10 (+/-60 mV, 3 sigma) on its own (sim/mc/records/;
* 13 of 45 corners hold out-of-limit draws); the clock path reads that
* offset common-mode, which the quasi-differential pair rejects. Sizes are
* unchanged from the cell as first committed (#35): Mi1 2.5u/1u, Mi2
* 4u/2u, all l=0.13u ng=2.
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/sg13_lv_pmos.sym} 200 200 0 0 {name=Mi1p model=sg13_lv_pmos w=2.5u l=0.13u ng=2 m=1}
C {lab_pin.sym} 220 230 0 0 {name=l1 lab=M1}
C {lab_pin.sym} 180 200 0 0 {name=l2 lab=PAD}
C {lab_pin.sym} 220 170 0 0 {name=l3 lab=VDDIO}
C {lab_pin.sym} 220 200 0 0 {name=l4 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 420 200 0 0 {name=Mi1n model=sg13_lv_nmos w=1u l=0.13u ng=2 m=1}
C {lab_pin.sym} 440 170 0 0 {name=l5 lab=M1}
C {lab_pin.sym} 400 200 0 0 {name=l6 lab=PAD}
C {lab_pin.sym} 440 230 0 0 {name=l7 lab=VSS}
C {lab_pin.sym} 440 200 0 0 {name=l8 lab=VSS}
C {sg13g2_pr/sg13_lv_pmos.sym} 640 200 0 0 {name=Mi2p model=sg13_lv_pmos w=4u l=0.13u ng=2 m=1}
C {lab_pin.sym} 660 230 0 0 {name=l9 lab=DOUT}
C {lab_pin.sym} 620 200 0 0 {name=l10 lab=M1}
C {lab_pin.sym} 660 170 0 0 {name=l11 lab=VDDIO}
C {lab_pin.sym} 660 200 0 0 {name=l12 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 860 200 0 0 {name=Mi2n model=sg13_lv_nmos w=2u l=0.13u ng=2 m=1}
C {lab_pin.sym} 880 170 0 0 {name=l13 lab=DOUT}
C {lab_pin.sym} 840 200 0 0 {name=l14 lab=M1}
C {lab_pin.sym} 880 230 0 0 {name=l15 lab=VSS}
C {lab_pin.sym} 880 200 0 0 {name=l16 lab=VSS}
C {ipin.sym} -100 100 0 0 {name=p1 lab=PAD}
C {opin.sym} -100 160 0 0 {name=p2 lab=DOUT}
C {iopin.sym} -100 220 0 0 {name=p3 lab=VDDIO}
C {iopin.sym} -100 280 0 0 {name=p4 lab=VSS}
