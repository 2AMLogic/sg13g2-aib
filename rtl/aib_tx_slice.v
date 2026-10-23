// One TX wire slice: two parallel bits per forwarded-clock cycle -> one wire.
// DDR: d0 then d1, one per clock edge. SDR (test mode): d0 held for the cycle.
// Register path, counted on clock edges (E0 = posedge that loads a0/a1):
//   a0/a1  posedge  E0   TX input register
//   o_n    negedge  E1   (carries d0)
//   o_p    posedge  E2   (carries d1, or d0 in SDR)
//   wire   = clk ? o_n : o_p   d0 starts at E2 (2 UI), d1 at E3 (3 UI)
// INJECT_EXTRA_STAGE adds a posedge stage behind the input register: the
// negative control for the latency test.
`timescale 1ns/1ps

module aib_tx_slice (
    input  wire clk,
    input  wire rst_n,
    input  wire sdr,
    input  wire d0,
    input  wire d1,
    output wire wire_o
);
    reg a0, a1, o_n, o_p;
`ifdef INJECT_EXTRA_STAGE
    reg b0, b1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a0 <= 1'b0; a1 <= 1'b0; b0 <= 1'b0; b1 <= 1'b0; end
        else        begin a0 <= d0;   a1 <= d1;   b0 <= a0;   b1 <= a1;   end
    wire s0 = b0, s1 = b1;
`else
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a0 <= 1'b0; a1 <= 1'b0; end
        else        begin a0 <= d0;   a1 <= d1;   end
    wire s0 = a0, s1 = a1;
`endif

    always @(negedge clk or negedge rst_n)
        if (!rst_n) o_n <= 1'b0;
        else        o_n <= s0;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) o_p <= 1'b0;
        else        o_p <= sdr ? s0 : s1;

    assign wire_o = clk ? o_n : o_p;
endmodule
