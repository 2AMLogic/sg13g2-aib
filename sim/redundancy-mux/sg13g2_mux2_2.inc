* sg13g2_mux2_2 -- the drive-2 member of the same 2:1 mux family as sg13g2_mux2_1,
* measured as the first of the two sized remap stages of spec/decisions/0024-*.md.
* Identical to sg13g2_mux2_1 except for the output inverter: XP5 2.24u/ng=2 and
* XN5 1.48u/ng=2 against 1.12u/ng=1 and 740n/ng=1, i.e. the same select stack and the
* same A0/A1 input load driving twice the output drive.
* Copied VERBATIM (lines 710-723 of libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice)
* from the PDK pinned in sim/pdk.json (IHP-GmbH/IHP-Open-PDK v0.3.0, Apache-2.0,
* Copyright 2023 IHP PDK Authors). Vendored as one subcircuit so the batch fleet needs
* no PDK stdcell path; the subcircuit is unmodified.
*
* Pins: X A0 A1 S VDD VSS -- X = S ? A1 : A0 (non-inverting; A0/A1 drive an internal
* select stack whose node net6 is inverted onto X).
.subckt sg13g2_mux2_2 X A0 A1 S VDD VSS
XP1 net4 S VDD VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XP5 X net6 VDD VDD sg13_lv_pmos w=2.24u l=130.00n ng=2 ad=4.256e-13 as=7.616e-13 pd=3e-06 ps=5.84e-06 m=1
XP4 net6 A1 net5 VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XP0 Sb S VDD VDD sg13_lv_pmos w=840.00n l=130.00n ng=1 ad=2.856e-13 as=2.856e-13 pd=2.36e-06 ps=2.36e-06 m=1
XP3 net5 Sb VDD VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XP2 net6 A0 net4 VDD sg13_lv_pmos w=1.000u l=130.00n ng=1 ad=3.4e-13 as=3.4e-13 pd=2.68e-06 ps=2.68e-06 m=1
XN4 net3 S VSS VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN2 net1 Sb VSS VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN5 X net6 VSS VSS sg13_lv_nmos w=1.48u l=130.00n ng=2 ad=2.812e-13 as=5.032e-13 pd=2.24e-06 ps=4.32e-06 m=1
XN0 Sb S VSS VSS sg13_lv_nmos w=550.00n l=130.00n ng=1 ad=1.87e-13 as=1.87e-13 pd=1.78e-06 ps=1.78e-06 m=1
XN3 net6 A1 net3 VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
XN1 net6 A0 net1 VSS sg13_lv_nmos w=740.00n l=130.00n ng=1 ad=2.516e-13 as=2.516e-13 pd=2.16e-06 ps=2.16e-06 m=1
.ends
