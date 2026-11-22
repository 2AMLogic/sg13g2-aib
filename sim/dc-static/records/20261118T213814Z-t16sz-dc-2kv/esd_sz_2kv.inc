* esd_sz_2kv.inc -- as esd_sz_dpa.inc but XDp1 is diodevdd_2kv (design/aib_pad_esd_2kv.spice, DR-0018); sz_dp is unused.
* Same topology, devices and defaults as design/aib_pad_esd.spice (the defaults below ARE its
* values, so the baseline candidate reproduces the committed cell); only XDp1's side, XMn1's
* finger count (w = 2 um x ng, as committed: w=20u ng=10) and XResd's length are parametric.
* `corners.params` can only target a top-level .param, hence the globals.
.param sz_dp=4.5u sz_ng=10 sz_rl=2u
.subckt aib_pad_esd PAD PADI VDDIO VSS
XDp1 VDDIO PAD VSS diodevdd_2kv
XMn1 PAD VSS VSS VSS sg13_lv_nmos w={2u*sz_ng} l=0.13u ng={sz_ng} m=1
XMclamp VDDIO VSS VSS VSS sg13_lv_nmos w=40u l=0.35u ng=20 m=1
XResd PAD PADI VSS rppd w=2u l={sz_rl} m=1 b=0
XDp2 PADI VDDIO dpantenna l=2u w=2u
XMn2 PADI VSS VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1
.ends
