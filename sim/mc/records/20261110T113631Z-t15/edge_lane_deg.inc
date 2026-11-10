* edge_lane_deg.inc -- NEGATIVE-CONTROL lanes (not design evidence): edge_lane.inc plus `lane_deg`,
* the same lane with a seeded degradation, an extra 500 fF of load at the receiver input node
* (about 2.5x the channel's own 0.6 pF -> a delay shift well above the limit). `lane` is healthy.
.subckt lane din dout rxp vtx vrx
Xtx   din vtx vtx 0 txi vtx 0 aib_tx_data
Xesdt txp txi vtx 0 aib_pad_esd
Xlnk  txp rxp 0 link
Xesdr rxp rxi vrx 0 aib_pad_esd
Xrx   rxi dout vrx 0 aib_rx_data
Cdout dout 0 5f
.ends lane
.subckt lane_deg din dout rxp vtx vrx
Xtx   din vtx vtx 0 txi vtx 0 aib_tx_data
Xesdt txp txi vtx 0 aib_pad_esd
Xlnk  txp rxp 0 link
Xesdr rxp rxi vrx 0 aib_pad_esd
Xrx   rxi dout vrx 0 aib_rx_data
Cdeg  rxi 0 500f
Cdout dout 0 5f
.ends lane_deg
