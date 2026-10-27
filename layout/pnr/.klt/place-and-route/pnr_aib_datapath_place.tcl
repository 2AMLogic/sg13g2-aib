read_db /home/ubuntu/GitHub/sg13g2-aib/.loom/worktrees/issue-38/layout/pnr/.klt/place-and-route/aib_datapath_floorplan.odb
read_liberty /home/ubuntu/share/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib
set_dont_use {sg13g2_lgcp_1}
set_dont_use {sg13g2_sighold}
set_dont_use {sg13g2_slgcp_1}
set_dont_use {sg13g2_sdfbbp_1}
set_dont_use {sg13g2_dfrbp_2}
set_cmd_units -time ns -capacitance pF
create_clock -name clk -period 2.0 [get_ports clk]
place_pins -hor_layers Metal3 -ver_layers Metal2
set_wire_rc -layer Metal2
global_placement -density 0.6 -routability_driven -timing_driven -random_seed 1
estimate_parasitics -placement
repair_design
repair_timing
detailed_placement
report_worst_slack_metric -setup
report_tns_metric -setup
report_worst_slack_metric -hold
report_design_area_metrics
report_fmax_metric
report_power_metric
puts "===KLT_SETUP_VIOLATIONS_BEGIN==="
report_check_types -max_delay -recovery -clock_gating_setup -violators -format end
puts "===KLT_SETUP_VIOLATIONS_END==="
puts "===KLT_HOLD_VIOLATIONS_BEGIN==="
report_check_types -min_delay -removal -clock_gating_hold -violators -format end
puts "===KLT_HOLD_VIOLATIONS_END==="
write_def /home/ubuntu/GitHub/sg13g2-aib/.loom/worktrees/issue-38/layout/pnr/.klt/place-and-route/aib_datapath.place.def
write_db /home/ubuntu/GitHub/sg13g2-aib/.loom/worktrees/issue-38/layout/pnr/.klt/place-and-route/aib_datapath_place.odb
