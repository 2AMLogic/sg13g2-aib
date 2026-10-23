// Bench top: two channel directions, each TX remap -> fault-injected wires ->
// RX remap. `fmask` selects wires to corrupt; `fmode` 0 = X, 1 = stuck-0, 2 = stuck-1.
`timescale 1ns/1ps

module tb_top (
    input  wire [19:0] d_ab, input wire [19:0] d_ba,
    input  wire        en_ab, input wire dir_ab, input wire [4:0] pos_ab,
    input  wire        en_ba, input wire dir_ba, input wire [4:0] pos_ba,
    input  wire [21:0] fmask_ab, input wire [21:0] fmask_ba,
    input  wire [1:0]  fmode,
    output wire [19:0] q_ab, output wire [19:0] q_ba
);
    wire [21:0] tx_ab, tx_ba, rx_ab, rx_ba;
    tx_remap u_tx_ab (.d(d_ab), .en(en_ab), .dir(dir_ab), .pos(pos_ab), .w(tx_ab));
    tx_remap u_tx_ba (.d(d_ba), .en(en_ba), .dir(dir_ba), .pos(pos_ba), .w(tx_ba));

    genvar i;
    generate
        for (i = 0; i < 22; i = i + 1) begin : g_fault
            assign rx_ab[i] = !fmask_ab[i] ? tx_ab[i]
                            : (fmode == 2'd0) ? 1'bx : (fmode == 2'd1) ? 1'b0 : 1'b1;
            assign rx_ba[i] = !fmask_ba[i] ? tx_ba[i]
                            : (fmode == 2'd0) ? 1'bx : (fmode == 2'd1) ? 1'b0 : 1'b1;
        end
    endgenerate

    rx_remap u_rx_ab (.w(rx_ab), .en(en_ab), .dir(dir_ab), .pos(pos_ab), .q(q_ab));
    rx_remap u_rx_ba (.w(rx_ba), .en(en_ba), .dir(dir_ba), .pos(pos_ba), .q(q_ba));
endmodule
