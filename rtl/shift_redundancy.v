// Shift-redundancy remap for one 20 + 2 channel direction (T-05, DR-0003, DR-0016).
//
// Physical wires 0..21: wires 0..19 carry data bits 0..19 in the no-fault case;
// wires 20 and 21 are the two spares, both at the high end. A fault on the wire
// that carries data bit `pos` is repaired by moving bits pos..19 up two wires
// (bit k on wire k + 2), toward the spares. Wires `pos` and `pos + 1` are then
// vacated: the TX side drives them 0 and the RX side ignores them. There is no
// direction input; the shift always runs toward the spares (DR-0016).
// `en` = 0 is the no-fault setting (wires 0..19, spares idle).
// TX and RX take the same {en, pos} selection, so each chiplet applies the same
// control to its own end of the channel.
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
            if (!en || k < pos
`ifdef INJECT_BUG_SHIFT_EDGE
                || pos == 5'd19
`endif
                )
                w[k] = d[k];
            else
                w[k + 2] = d[k];
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
