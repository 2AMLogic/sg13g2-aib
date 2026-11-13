// Post-route variant of tb_datapath.v for the item 7 / digital run. Identical
// stimulus and wiring; the only differences are that N is fixed at 20 (the routed
// netlist has no N parameter, and klt rejects request.parameters with options.sdf)
// and that the module has no parameter list (klt's SDF wrapper needs a plain
// `module <top>(` declaration).
// Bench top for aib_datapath. The channel is a zero-delay wire; rx_clk is clk
// delayed by a quarter cycle, an ideal stand-in for the DLL's eye-centring
// (not a model of the DLL). `decoy` drives rx_wire with the inverse of
// tx_wire, so a loopback that is not selected is visible. `ext_en` lets the
// bench drive rx_wire directly for the RX latency measurement.
`timescale 1ns/1ps

module tb_datapath_postroute (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         sdr,
    input  wire         l1,
    input  wire         decoy,
    input  wire         ext_en,
    input  wire [19:0] ext_wire,
    input  wire [19:0] tx_d0,
    input  wire [19:0] tx_d1,
    output wire [19:0] tx_wire,
    output wire         rx_clk,
    output wire [19:0] rx_q0,
    output wire [19:0] rx_q1
);
    assign #2.5 rx_clk = clk;
    wire [19:0] rx_wire = ext_en ? ext_wire : (decoy ? ~tx_wire : tx_wire);

    // The suite changes tx_d0/tx_d1 on the clock edge. The routed clock tree delays
    // the edge at the registers, so an input that moves with the edge would race it
    // (a hold violation at the input). The bench holds the data inputs for 1 ns past
    // the edge, a declared input-hold assumption that sits above the clock insertion
    // delay; the suite itself is unchanged.
    wire [19:0] tx_d0_h, tx_d1_h;
    assign #1 tx_d0_h = tx_d0;
    assign #1 tx_d1_h = tx_d1;

    aib_datapath dut (.clk(clk), .rx_clk(rx_clk), .rst_n(rst_n), .sdr(sdr), .l1(l1),
                               .tx_d0(tx_d0_h), .tx_d1(tx_d1_h), .tx_wire(tx_wire),
                               .rx_wire(rx_wire), .rx_q0(rx_q0), .rx_q1(rx_q1));
endmodule
