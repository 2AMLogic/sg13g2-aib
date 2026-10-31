* tb_body.inc -- four-lane channel testbench body (circuit body for `klt sim`).
*
* Lanes (each: aib_tx_data -> aib_pad_esd -> link -> aib_pad_esd -> aib_rx_data):
*   A   data lane, PRBS-7                 pin rxa
*   B   data lane, complement of A        pin rxb   (T-15: opposite-polarity edges launch together)
*   C   forwarded clock, clk              pin rxc   (clk and clkb are the quasi-differential pair, T-04)
*   CB  forwarded clock, clkb             pin rxcb
* The including netlist defines `.subckt link txp rxp gnd` first: the declared channel
* CH-3MM-RC (tb_ch.cir) or the declared L2 wire-bond loopback (tb_tc.cir).
*
* Cells are .include'd by the including netlist, never copied. design/aib_{tx,rx}_clk.spice
* embed copies of aib_tx_data / aib_rx_data, so the clock cells are not included next to the
* data cells: the clock lane is two aib_tx_data / aib_rx_data instances, which is what those
* cells are.
.include ../prbs7_stim.inc

* One lane. OE tied high (driving), weak pull-up gate PUN high (off), pull-down gate PD low (off).
* DOUT carries a declared 5 fF load (an RTL flop input; no PDK or layout value behind it).
.subckt lane din dout rxp vtx vrx
Xtx   din vtx vtx 0 txi vtx 0 aib_tx_data
Xesdt txp txi vtx 0 aib_pad_esd
Xlnk  txp rxp 0 link
Xesdr rxp rxi vrx 0 aib_pad_esd
Xrx   rxi dout vrx 0 aib_rx_data
Cdout dout 0 5f
.ends lane

* Supplies: one source per block so the energy of each is separable; corners.supply_v sweeps
* them together. Nominal value only here, `klt sim` alters it per corner.
Vdd_atx vdd_atx 0 DC 1.2
Vdd_arx vdd_arx 0 DC 1.2
Vdd_btx vdd_btx 0 DC 1.2
Vdd_brx vdd_brx 0 DC 1.2
Vdd_ctx vdd_ctx 0 DC 1.2
Vdd_crx vdd_crx 0 DC 1.2

* Ideal full-rail drivers scaled by the TX supply (stimulus; their current is not counted).
Bda  da  0 V = v(pa)*v(vdd_atx)

Xa  da  douta  rxa  vdd_atx vdd_arx lane

* Zero-crossing probes (no loading): data minus RX mid-rail, clock quasi-differential.
Bdsa dsa  0 V = v(rxa) - 0.5*v(vdd_arx)
