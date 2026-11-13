// Shift-redundancy remap for one 20 + 2 channel direction (T-05, DR-0016).
//
// Physical wires 0..21: wires 0..19 carry data bits 0..19 in the no-fault
// case; wires 20 and 21 are the two spares, both at the same end (DR-0016).
// A fault on wire `pos` is repaired with one two-signal shift: bits pos..19
// move up two wires (wire k + 2). Bits below `pos` stay on wire k. The faulty
// wire (pos) and the one after it (pos + 1) are left undriven by the TX side
// and ignored by the RX side. `en` = 0 is the no-fault setting (wires 0..19,
// spares idle). TX and RX take the same {en, pos} selection, so each chiplet
// applies the same control to its own end of the channel. There is no
// direction input: the shift only ever goes toward the spares.
//
// Function only: this is the mux, not repair on a real channel. See rtl/README.md.

`timescale 1ns/1ps

module tx_remap (
    input  wire [19:0] d,
    input  wire        en,
    input  wire [4:0]  pos,
    output reg  [21:0] w
);
    integer k;
    always @* begin
        w = 22'b0;
        for (k = 0; k < 20; k = k + 1) begin
            if (en && k >= pos
`ifdef INJECT_BUG_SHIFT_EDGE
                && pos != 5'd19
`endif
                )
                w[k + 2] = d[k];
            else
                w[k] = d[k];
        end
    end
endmodule

module rx_remap (
    input  wire [21:0] w,
    input  wire        en,
    input  wire [4:0]  pos,
    output reg  [19:0] q
);
    integer k;
    always @* begin
        q = 20'b0;
        for (k = 0; k < 20; k = k + 1) begin
            if (en && k >= pos)
                q[k] = w[k + 2];
            else
                q[k] = w[k];
        end
    end
endmodule
