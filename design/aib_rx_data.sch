v {xschem version=3.4.7 file_version=1.3
* aib_rx_data -- single-ended supply-referenced data receiver (T-10, T-11).
* Adopted in #398 from the #386 sizing study (sim/rx-threshold-study,
* cand_cells.inc subckt rx__vref, verbatim device sizes). NMOS pair: the
* input PAD against vrn, a matched rppd VDDIO/2 divider (Rdiv1/Rdiv2,
* 0.5u x 48u each); PMOS mirror load (Mlp diode-connected, Mln); ~100 uA
* tail (Mtail, gate VDDIO); restore inverter Mi2 at half the committed
* width. Comparing the pad against a divider that tracks the same supply
* turns the PVT N/P strength skew -- the mechanism that moves an inverter
* trip point and put 13 of 45 corners outside +/-60 mV on the committed
* cell -- into a near common-mode current change: the study's confirmed
* record reads klt yield pass at +/-60 mV / 3 sigma, 0 of 5400 draws and
* 0 of 45 corners outside the limits. The asymmetric output stage (d1
* charges through the mirror but discharges through the input pair) is why
* the clock legs keep the committed aib_rx_inv receiver: this cell
* multiplies clock-path duty distortion ~8x at the binding corner. The
* divider + tail standing current (~57-94 uA over the grid, ~0.7 mW per
* data lane at 1.2 V) is the architecture's cost; the design note in
* design/README.md carries the measured numbers. Divider resistors are
* corner-section rppd: the committed T-10 Monte Carlo varies MOS mismatch
* only, no independent resistor-pair mismatch (documented in the adoption
* record).
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/rppd.sym} 200 200 0 0 {name=Rdiv1 model=rppd w=0.5u l=48u b=0 m=1 body=VSS spiceprefix=X}
C {lab_pin.sym} 200 170 0 0 {name=l1 lab=VDDIO}
C {lab_pin.sym} 200 230 0 0 {name=l2 lab=vrn}
C {sg13g2_pr/rppd.sym} 420 200 0 0 {name=Rdiv2 model=rppd w=0.5u l=48u b=0 m=1 body=VSS spiceprefix=X}
C {lab_pin.sym} 420 170 0 0 {name=l3 lab=vrn}
C {lab_pin.sym} 420 230 0 0 {name=l4 lab=VSS}
C {sg13g2_pr/sg13_lv_nmos.sym} 640 200 0 0 {name=Mtail model=sg13_lv_nmos w=2u l=0.5u ng=2 m=1}
C {lab_pin.sym} 660 170 0 0 {name=l5 lab=s1}
C {lab_pin.sym} 620 200 0 0 {name=l6 lab=VDDIO}
C {lab_pin.sym} 660 230 0 0 {name=l7 lab=VSS}
C {lab_pin.sym} 660 200 0 0 {name=l8 lab=VSS}
C {sg13g2_pr/sg13_lv_nmos.sym} 860 200 0 0 {name=Mnp model=sg13_lv_nmos w=1u l=0.5u ng=2 m=1}
C {lab_pin.sym} 880 170 0 0 {name=l9 lab=d1}
C {lab_pin.sym} 840 200 0 0 {name=l10 lab=PAD}
C {lab_pin.sym} 880 230 0 0 {name=l11 lab=s1}
C {lab_pin.sym} 880 200 0 0 {name=l12 lab=VSS}
C {sg13g2_pr/sg13_lv_nmos.sym} 1080 200 0 0 {name=Mnn model=sg13_lv_nmos w=1u l=0.5u ng=2 m=1}
C {lab_pin.sym} 1100 170 0 0 {name=l13 lab=d2}
C {lab_pin.sym} 1060 200 0 0 {name=l14 lab=vrn}
C {lab_pin.sym} 1100 230 0 0 {name=l15 lab=s1}
C {lab_pin.sym} 1100 200 0 0 {name=l16 lab=VSS}
C {sg13g2_pr/sg13_lv_pmos.sym} 200 450 0 0 {name=Mlp model=sg13_lv_pmos w=4u l=0.25u ng=4 m=1}
C {lab_pin.sym} 220 480 0 0 {name=l17 lab=d2}
C {lab_pin.sym} 180 450 0 0 {name=l18 lab=d2}
C {lab_pin.sym} 220 420 0 0 {name=l19 lab=VDDIO}
C {lab_pin.sym} 220 450 0 0 {name=l20 lab=VDDIO}
C {sg13g2_pr/sg13_lv_pmos.sym} 420 450 0 0 {name=Mln model=sg13_lv_pmos w=4u l=0.25u ng=4 m=1}
C {lab_pin.sym} 440 480 0 0 {name=l21 lab=d1}
C {lab_pin.sym} 400 450 0 0 {name=l22 lab=d2}
C {lab_pin.sym} 440 420 0 0 {name=l23 lab=VDDIO}
C {lab_pin.sym} 440 450 0 0 {name=l24 lab=VDDIO}
C {sg13g2_pr/sg13_lv_pmos.sym} 640 450 0 0 {name=Mi2p model=sg13_lv_pmos w=2u l=0.13u ng=1 m=1}
C {lab_pin.sym} 660 480 0 0 {name=l25 lab=DOUT}
C {lab_pin.sym} 620 450 0 0 {name=l26 lab=d1}
C {lab_pin.sym} 660 420 0 0 {name=l27 lab=VDDIO}
C {lab_pin.sym} 660 450 0 0 {name=l28 lab=VDDIO}
C {sg13g2_pr/sg13_lv_nmos.sym} 860 450 0 0 {name=Mi2n model=sg13_lv_nmos w=1u l=0.13u ng=1 m=1}
C {lab_pin.sym} 880 420 0 0 {name=l29 lab=DOUT}
C {lab_pin.sym} 840 450 0 0 {name=l30 lab=d1}
C {lab_pin.sym} 880 480 0 0 {name=l31 lab=VSS}
C {lab_pin.sym} 880 450 0 0 {name=l32 lab=VSS}
C {ipin.sym} -100 100 0 0 {name=p1 lab=PAD}
C {opin.sym} -100 160 0 0 {name=p2 lab=DOUT}
C {iopin.sym} -100 220 0 0 {name=p3 lab=VDDIO}
C {iopin.sym} -100 280 0 0 {name=p4 lab=VSS}
