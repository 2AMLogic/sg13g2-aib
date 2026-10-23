// Bench top for aib_datapath. The channel is a zero-delay wire; rx_clk is clk
// delayed by a quarter cycle, an ideal stand-in for the DLL's eye-centring
// (not a model of the DLL). `decoy` drives rx_wire with the inverse of
// tx_wire, so a loopback that is not selected is visible. `ext_en` lets the
// bench drive rx_wire directly for the RX latency measurement.
`timescale 1ns/1ps

module tb_datapath #(
    parameter N = 20
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         sdr,
    input  wire         l1,
    input  wire         decoy,
    input  wire         ext_en,
    input  wire [N-1:0] ext_wire,
    input  wire [N-1:0] tx_d0,
    input  wire [N-1:0] tx_d1,
    output wire [N-1:0] tx_wire,
    output wire         rx_clk,
    output wire [N-1:0] rx_q0,
    output wire [N-1:0] rx_q1
);
    assign #2.5 rx_clk = clk;
    wire [N-1:0] rx_wire = ext_en ? ext_wire : (decoy ? ~tx_wire : tx_wire);

    aib_datapath #(.N(N)) dut (.clk(clk), .rx_clk(rx_clk), .rst_n(rst_n), .sdr(sdr), .l1(l1),
                               .tx_d0(tx_d0), .tx_d1(tx_d1), .tx_wire(tx_wire),
                               .rx_wire(rx_wire), .rx_q0(rx_q0), .rx_q1(rx_q1));
endmodule
