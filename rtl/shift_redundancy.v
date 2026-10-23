// Shift-redundancy remap for one 20 + 2 channel direction (T-05, DR-0003).
//
// Physical wires 0..21: wire 0 is spare A, wires 1..20 carry data bits 0..19
// in the no-fault case, wire 21 is spare B. A fault on the wire that carries
// data bit `pos` is repaired by shifting the bits on one side of it by one
// wire toward a spare:
//   dir = 0  toward spare A: bits 0..pos move down one wire (wire k)
//   dir = 1  toward spare B: bits pos..19 move up one wire (wire k + 2)
// The faulty wire (pos + 1) is left undriven by the TX side and ignored by
// the RX side. `en` = 0 is the no-fault setting (wires 1..20, spares idle).
// TX and RX take the same {en, dir, pos} selection, so each chiplet applies
// the same control to its own end of the channel.
//
// Function only: this is the mux, not repair on a real channel. See rtl/README.md.

`timescale 1ns/1ps

module tx_remap (
    input  wire [19:0] d,
    input  wire        en,
    input  wire        dir,
    input  wire [4:0]  pos,
    output reg  [21:0] w
);
    integer k;
    always @* begin
        w = 22'b0;
        for (k = 0; k < 20; k = k + 1) begin
            if (en && !dir && k <= pos)
                w[k] = d[k];
            else if (en && dir && k >= pos
`ifdef INJECT_BUG_SHIFT_EDGE
                     && pos != 5'd19
`endif
                     )
                w[k + 2] = d[k];
            else
                w[k + 1] = d[k];
        end
    end
endmodule

module rx_remap (
    input  wire [21:0] w,
    input  wire        en,
    input  wire        dir,
    input  wire [4:0]  pos,
    output reg  [19:0] q
);
    integer k;
    always @* begin
        q = 20'b0;
        for (k = 0; k < 20; k = k + 1) begin
            if (en && !dir && k <= pos)
                q[k] = w[k];
            else if (en && dir && k >= pos)
                q[k] = w[k + 2];
            else
                q[k] = w[k + 1];
        end
    end
endmodule
