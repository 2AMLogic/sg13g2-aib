* edge_lane.inc -- one TX -> pad ESD -> declared channel -> pad ESD -> RX lane for the single-edge
* skew benches (tb_t15*.cir, tb_t16*.cir). The including netlist defines the cells, the channel
* model (spec/channel/channel_rc.cir, CH-3MM-RC, nominal) and `.subckt link txp rxp gnd` first.
* Same lane as sim/channel-eye/tb_body.inc (DOUT carries the declared 5 fF load); the stimulus
* is one edge instead of PRBS-7. Mismatch is per instance (mos_*_mismatch sections).
* OE tied high (driving), weak pull-up gate PUN high (off), pull-down gate PD low (off).
.subckt lane din dout rxp vtx vrx
Xtx   din vtx vtx 0 txi vtx 0 aib_tx_data
Xesdt txp txi vtx 0 aib_pad_esd
Xlnk  txp rxp 0 link
Xesdr rxp rxi vrx 0 aib_pad_esd
Xrx   rxi dout vrx 0 aib_rx_data
Cdout dout 0 5f
.ends lane
