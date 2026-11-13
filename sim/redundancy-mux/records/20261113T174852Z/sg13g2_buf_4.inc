* sg13g2_buf_4 -- the buffer of the second sized remap stage of spec/decisions/0024-*.md:
* a minimum-strength sg13g2_mux2_1 remap followed by this buffer, so the ~30 fF DIN load
* is driven by a drive-4 output stage instead of by the mux's own drive-1 inverter.
*
* Why buf_4 of sg13g2_buf_1/2/4/8/16: its output devices (XN1 2.96u/ng=4, XP1 4.48u/ng=4)
* are about four times the mux2_1 output inverter's (740n, 1.12u), while its own input
* load (XN0 740n, XP0 1.68u) stays light enough for the drive-1 mux ahead of it. buf_8
* and buf_16 add more input load for the mux to charge and more self-loading than the
* ~30 fF they would drive repays; buf_1 and buf_2 leave most of the load-driving delay
* in place. The deck measures one choice, and this is it -- it is not a claim that buf_4
* is optimal.
* Copied VERBATIM (lines 227-232 of libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice)
* from the PDK pinned in sim/pdk.json (IHP-GmbH/IHP-Open-PDK v0.3.0, Apache-2.0,
* Copyright 2023 IHP PDK Authors). Vendored as one subcircuit so the batch fleet needs
* no PDK stdcell path; the subcircuit is unmodified.
*
* Pins: X A VDD VSS -- X = A (non-inverting; two inverters in series).
.subckt sg13g2_buf_4 X A VDD VSS
XN0 net1 A VSS VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN1 X net1 VSS VSS sg13_lv_nmos w=2.96u l=130.00n ng=4 ad=5.624e-13 as=7.844e-13 pd=4.48e-06 ps=6.56e-06 m=1
XP1 X net1 VDD VDD sg13_lv_pmos w=4.48u l=130.00n ng=4 ad=8.512e-13 as=1.187e-12 pd=6e-06 ps=8.84e-06 m=1
XP0 net1 A VDD VDD sg13_lv_pmos w=1.68u l=130.00n ng=2 ad=3.192e-13 as=5.712e-13 pd=2.44e-06 ps=4.72e-06 m=1
.ends
