read_db /home/ubuntu/GitHub/sg13g2-aib/.loom/worktrees/issue-38/layout/pnr/.klt/place-and-route/aib_datapath_place.odb
read_liberty /home/ubuntu/share/pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib
set_dont_use {sg13g2_lgcp_1}
set_dont_use {sg13g2_sighold}
set_dont_use {sg13g2_slgcp_1}
set_dont_use {sg13g2_sdfbbp_1}
set_dont_use {sg13g2_dfrbp_2}
set_cmd_units -time ns -capacitance pF
create_clock -name clk -period 2.0 [get_ports clk]
set_wire_rc -layer Metal2
estimate_parasitics -placement
set _klt_cts_seq_sinks [llength [all_registers -clock [get_clocks {clk}]]]
if {$_klt_cts_seq_sinks > 0} {
clock_tree_synthesis -root_buf sg13g2_buf_16 -buf_list sg13g2_buf_16 -sink_clustering_enable -obstruction_aware
estimate_parasitics -placement
repair_timing -hold
} else {
puts "klt place-and-route: clock clk has no sequential (registered) fanout -- skipping clock_tree_synthesis (see issue #1506)"
}
detailed_placement
write_def /home/ubuntu/GitHub/sg13g2-aib/.loom/worktrees/issue-38/layout/pnr/.klt/place-and-route/aib_datapath.cts.def
report_worst_slack_metric -setup
report_tns_metric -setup
report_worst_slack_metric -hold
report_design_area_metrics
report_fmax_metric
report_power_metric
report_clock_skew_metric -setup
puts "===KLT_SETUP_VIOLATIONS_BEGIN==="
report_check_types -max_delay -recovery -clock_gating_setup -violators -format end
puts "===KLT_SETUP_VIOLATIONS_END==="
puts "===KLT_HOLD_VIOLATIONS_BEGIN==="
report_check_types -min_delay -removal -clock_gating_hold -violators -format end
puts "===KLT_HOLD_VIOLATIONS_END==="
write_db /home/ubuntu/GitHub/sg13g2-aib/.loom/worktrees/issue-38/layout/pnr/.klt/place-and-route/aib_datapath_cts.odb
