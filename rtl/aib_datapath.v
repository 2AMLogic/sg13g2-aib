// N-wire TX serializer + RX deserializer with the L1 on-die loopback select.
// N = 20 is the default channel direction, N = 8 the fallback (target-spec T-03).
// `l1` makes each RX slice sample its own TX wire instead of rx_wire (the
// digital select only; the TopMetal2 route is layout work). `sdr` is the
// single-data-rate test mode and applies to the TX side.
`timescale 1ns/1ps

module aib_datapath #(
    parameter N = 20
) (
    input  wire         clk,
    input  wire         rx_clk,
    input  wire         rst_n,
    input  wire         sdr,
    input  wire         l1,
    input  wire [N-1:0] tx_d0,
    input  wire [N-1:0] tx_d1,
    output wire [N-1:0] tx_wire,
    input  wire [N-1:0] rx_wire,
    output wire [N-1:0] rx_q0,
    output wire [N-1:0] rx_q1
);
    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : g_wire
            aib_tx_slice u_tx (.clk(clk), .rst_n(rst_n), .sdr(sdr),
                               .d0(tx_d0[i]), .d1(tx_d1[i]), .wire_o(tx_wire[i]));
            aib_rx_slice u_rx (.rx_clk(rx_clk), .rst_n(rst_n),
                               .wire_i(l1 ? tx_wire[i] : rx_wire[i]),
                               .q0(rx_q0[i]), .q1(rx_q1[i]));
        end
    endgenerate
endmodule
