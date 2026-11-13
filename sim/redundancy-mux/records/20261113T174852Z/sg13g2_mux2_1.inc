* sg13g2_mux2_1 -- the 2:1 mux the synthesis maps the TX serializer's clock-selected
* mux to (22 instances in design/synth/.klt/synthesize/run-2080*/aib_datapath_synth.v),
* and the stand-in for the T-05 redundancy remap stage (spec/decisions/0023-*.md).
* Copied VERBATIM (lines 691-704 of libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice)
* from the PDK pinned in sim/pdk.json (IHP-GmbH/IHP-Open-PDK v0.3.0, Apache-2.0,
* Copyright 2023 IHP PDK Authors). Vendored as one subcircuit so the batch fleet needs
* no PDK stdcell path; the subcircuit is unmodified.
*
* Pins: X A0 A1 S VDD VSS -- X = S ? A1 : A0 (non-inverting; A0/A1 drive an internal
* select stack whose node net6 is inverted onto X).
.subckt sg13g2_mux2_1 X A0 A1 S VDD VSS
XP1 net4 S VDD VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XP5 X net6 VDD VDD sg13_lv_pmos w=1.12u l=130.00n ng=1 ad=3.808e-13 as=3.808e-13 pd=2.92e-06 ps=2.92e-06 m=1
XP4 net6 A1 net5 VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XP0 Sb S VDD VDD sg13_lv_pmos w=840.00n l=130.00n ng=1 ad=2.856e-13 as=2.856e-13 pd=2.36e-06 ps=2.36e-06 m=1
XP3 net5 Sb VDD VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XP2 net6 A0 net4 VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XN4 net3 S VSS VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN2 net1 Sb VSS VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN5 X net6 VSS VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN0 Sb S VSS VSS sg13_lv_nmos w=550.00n l=130.00n ng=1 ad=1.87e-13 as=1.87e-13 pd=1.78e-06 ps=1.78e-06 m=1
XN3 net6 A1 net3 VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN1 net6 A0 net1 VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
.ends
