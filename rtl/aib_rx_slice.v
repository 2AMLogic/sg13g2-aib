// One RX wire slice: one wire -> two parallel bits per forwarded-clock cycle.
// rx_clk is the forwarded clock already centred in the data eye (the DLL's
// job, not this module's), so the first bit of a word is sampled on its
// posedge and the second on its negedge. Counted on rx_clk edges:
//   r0   posedge  E0   first bit sampled
//   r1   negedge  E1   second bit sampled
//   q0/q1 posedge E2   RX output register: 2 UI after the first sample
// In SDR the wire is constant over the cycle, so q1 repeats q0 and carries no data.
// INJECT_EXTRA_STAGE adds a posedge stage after the output register.
`timescale 1ns/1ps

module aib_rx_slice (
    input  wire rx_clk,
    input  wire rst_n,
    input  wire wire_i,
    output wire q0,
    output wire q1
);
    reg r0, r1, p0, p1;
    always @(posedge rx_clk or negedge rst_n)
        if (!rst_n) r0 <= 1'b0;
        else        r0 <= wire_i;

    always @(negedge rx_clk or negedge rst_n)
        if (!rst_n) r1 <= 1'b0;
        else        r1 <= wire_i;

    always @(posedge rx_clk or negedge rst_n)
        if (!rst_n) begin p0 <= 1'b0; p1 <= 1'b0; end
        else        begin p0 <= r0;   p1 <= r1;   end

`ifdef INJECT_EXTRA_STAGE
    reg e0, e1;
    always @(posedge rx_clk or negedge rst_n)
        if (!rst_n) begin e0 <= 1'b0; e1 <= 1'b0; end
        else        begin e0 <= p0;   e1 <= p1;   end
    assign q0 = e0;
    assign q1 = e1;
`else
    assign q0 = p0;
    assign q1 = p1;
`endif
endmodule
