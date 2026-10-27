module aib_datapath (clk,
    l1,
    rst_n,
    rx_clk,
    sdr,
    rx_q0,
    rx_q1,
    rx_wire,
    tx_d0,
    tx_d1,
    tx_wire);
 input clk;
 input l1;
 input rst_n;
 input rx_clk;
 input sdr;
 output [19:0] rx_q0;
 output [19:0] rx_q1;
 input [19:0] rx_wire;
 input [19:0] tx_d0;
 input [19:0] tx_d1;
 output [19:0] tx_wire;

 wire _00_;
 wire _01_;
 wire _02_;
 wire _03_;
 wire _04_;
 wire _05_;
 wire _06_;
 wire _07_;
 wire _08_;
 wire _09_;
 wire _10_;
 wire _11_;
 wire _12_;
 wire _13_;
 wire _14_;
 wire _15_;
 wire _16_;
 wire _17_;
 wire _18_;
 wire _19_;
 wire _20_;
 wire _21_;
 wire \g_wire[0].u_rx/_0_ ;
 wire \g_wire[0].u_rx/r0 ;
 wire \g_wire[0].u_rx/r1 ;
 wire \g_wire[0].u_tx/_0_ ;
 wire \g_wire[0].u_tx/_1_ ;
 wire \g_wire[0].u_tx/a0 ;
 wire \g_wire[0].u_tx/a1 ;
 wire \g_wire[0].u_tx/o_n ;
 wire \g_wire[0].u_tx/o_p ;
 wire \g_wire[10].u_rx/_0_ ;
 wire \g_wire[10].u_rx/r0 ;
 wire \g_wire[10].u_rx/r1 ;
 wire \g_wire[10].u_tx/_0_ ;
 wire \g_wire[10].u_tx/_1_ ;
 wire \g_wire[10].u_tx/a0 ;
 wire \g_wire[10].u_tx/a1 ;
 wire \g_wire[10].u_tx/o_n ;
 wire \g_wire[10].u_tx/o_p ;
 wire \g_wire[11].u_rx/_0_ ;
 wire \g_wire[11].u_rx/r0 ;
 wire \g_wire[11].u_rx/r1 ;
 wire \g_wire[11].u_tx/_0_ ;
 wire \g_wire[11].u_tx/_1_ ;
 wire \g_wire[11].u_tx/a0 ;
 wire \g_wire[11].u_tx/a1 ;
 wire \g_wire[11].u_tx/o_n ;
 wire \g_wire[11].u_tx/o_p ;
 wire \g_wire[12].u_rx/_0_ ;
 wire \g_wire[12].u_rx/r0 ;
 wire \g_wire[12].u_rx/r1 ;
 wire \g_wire[12].u_tx/_0_ ;
 wire \g_wire[12].u_tx/_1_ ;
 wire \g_wire[12].u_tx/a0 ;
 wire \g_wire[12].u_tx/a1 ;
 wire \g_wire[12].u_tx/o_n ;
 wire \g_wire[12].u_tx/o_p ;
 wire \g_wire[13].u_rx/_0_ ;
 wire \g_wire[13].u_rx/r0 ;
 wire \g_wire[13].u_rx/r1 ;
 wire \g_wire[13].u_tx/_0_ ;
 wire \g_wire[13].u_tx/_1_ ;
 wire \g_wire[13].u_tx/a0 ;
 wire \g_wire[13].u_tx/a1 ;
 wire \g_wire[13].u_tx/o_n ;
 wire \g_wire[13].u_tx/o_p ;
 wire \g_wire[14].u_rx/_0_ ;
 wire \g_wire[14].u_rx/r0 ;
 wire \g_wire[14].u_rx/r1 ;
 wire \g_wire[14].u_tx/_0_ ;
 wire \g_wire[14].u_tx/_1_ ;
 wire \g_wire[14].u_tx/a0 ;
 wire \g_wire[14].u_tx/a1 ;
 wire \g_wire[14].u_tx/o_n ;
 wire \g_wire[14].u_tx/o_p ;
 wire \g_wire[15].u_rx/_0_ ;
 wire \g_wire[15].u_rx/r0 ;
 wire \g_wire[15].u_rx/r1 ;
 wire \g_wire[15].u_tx/_0_ ;
 wire \g_wire[15].u_tx/_1_ ;
 wire \g_wire[15].u_tx/a0 ;
 wire \g_wire[15].u_tx/a1 ;
 wire \g_wire[15].u_tx/o_n ;
 wire \g_wire[15].u_tx/o_p ;
 wire \g_wire[16].u_rx/_0_ ;
 wire \g_wire[16].u_rx/r0 ;
 wire \g_wire[16].u_rx/r1 ;
 wire \g_wire[16].u_tx/_0_ ;
 wire \g_wire[16].u_tx/_1_ ;
 wire \g_wire[16].u_tx/a0 ;
 wire \g_wire[16].u_tx/a1 ;
 wire \g_wire[16].u_tx/o_n ;
 wire \g_wire[16].u_tx/o_p ;
 wire \g_wire[17].u_rx/_0_ ;
 wire \g_wire[17].u_rx/r0 ;
 wire \g_wire[17].u_rx/r1 ;
 wire \g_wire[17].u_tx/_0_ ;
 wire \g_wire[17].u_tx/_1_ ;
 wire \g_wire[17].u_tx/a0 ;
 wire \g_wire[17].u_tx/a1 ;
 wire \g_wire[17].u_tx/o_n ;
 wire \g_wire[17].u_tx/o_p ;
 wire \g_wire[18].u_rx/_0_ ;
 wire \g_wire[18].u_rx/r0 ;
 wire \g_wire[18].u_rx/r1 ;
 wire \g_wire[18].u_tx/_0_ ;
 wire \g_wire[18].u_tx/_1_ ;
 wire \g_wire[18].u_tx/a0 ;
 wire \g_wire[18].u_tx/a1 ;
 wire \g_wire[18].u_tx/o_n ;
 wire \g_wire[18].u_tx/o_p ;
 wire \g_wire[19].u_rx/_0_ ;
 wire \g_wire[19].u_rx/r0 ;
 wire \g_wire[19].u_rx/r1 ;
 wire \g_wire[19].u_tx/_0_ ;
 wire \g_wire[19].u_tx/_1_ ;
 wire \g_wire[19].u_tx/a0 ;
 wire \g_wire[19].u_tx/a1 ;
 wire \g_wire[19].u_tx/o_n ;
 wire \g_wire[19].u_tx/o_p ;
 wire \g_wire[1].u_rx/_0_ ;
 wire \g_wire[1].u_rx/r0 ;
 wire \g_wire[1].u_rx/r1 ;
 wire \g_wire[1].u_tx/_0_ ;
 wire \g_wire[1].u_tx/_1_ ;
 wire \g_wire[1].u_tx/a0 ;
 wire \g_wire[1].u_tx/a1 ;
 wire \g_wire[1].u_tx/o_n ;
 wire \g_wire[1].u_tx/o_p ;
 wire \g_wire[2].u_rx/_0_ ;
 wire \g_wire[2].u_rx/r0 ;
 wire \g_wire[2].u_rx/r1 ;
 wire \g_wire[2].u_tx/_0_ ;
 wire \g_wire[2].u_tx/_1_ ;
 wire \g_wire[2].u_tx/a0 ;
 wire \g_wire[2].u_tx/a1 ;
 wire \g_wire[2].u_tx/o_n ;
 wire \g_wire[2].u_tx/o_p ;
 wire \g_wire[3].u_rx/_0_ ;
 wire \g_wire[3].u_rx/r0 ;
 wire \g_wire[3].u_rx/r1 ;
 wire \g_wire[3].u_tx/_0_ ;
 wire \g_wire[3].u_tx/_1_ ;
 wire \g_wire[3].u_tx/a0 ;
 wire \g_wire[3].u_tx/a1 ;
 wire \g_wire[3].u_tx/o_n ;
 wire \g_wire[3].u_tx/o_p ;
 wire \g_wire[4].u_rx/_0_ ;
 wire \g_wire[4].u_rx/r0 ;
 wire \g_wire[4].u_rx/r1 ;
 wire \g_wire[4].u_tx/_0_ ;
 wire \g_wire[4].u_tx/_1_ ;
 wire \g_wire[4].u_tx/a0 ;
 wire \g_wire[4].u_tx/a1 ;
 wire \g_wire[4].u_tx/o_n ;
 wire \g_wire[4].u_tx/o_p ;
 wire \g_wire[5].u_rx/_0_ ;
 wire \g_wire[5].u_rx/r0 ;
 wire \g_wire[5].u_rx/r1 ;
 wire \g_wire[5].u_tx/_0_ ;
 wire \g_wire[5].u_tx/_1_ ;
 wire \g_wire[5].u_tx/a0 ;
 wire \g_wire[5].u_tx/a1 ;
 wire \g_wire[5].u_tx/o_n ;
 wire \g_wire[5].u_tx/o_p ;
 wire \g_wire[6].u_rx/_0_ ;
 wire \g_wire[6].u_rx/r0 ;
 wire \g_wire[6].u_rx/r1 ;
 wire \g_wire[6].u_tx/_0_ ;
 wire \g_wire[6].u_tx/_1_ ;
 wire \g_wire[6].u_tx/a0 ;
 wire \g_wire[6].u_tx/a1 ;
 wire \g_wire[6].u_tx/o_n ;
 wire \g_wire[6].u_tx/o_p ;
 wire \g_wire[7].u_rx/_0_ ;
 wire \g_wire[7].u_rx/r0 ;
 wire \g_wire[7].u_rx/r1 ;
 wire \g_wire[7].u_tx/_0_ ;
 wire \g_wire[7].u_tx/_1_ ;
 wire \g_wire[7].u_tx/a0 ;
 wire \g_wire[7].u_tx/a1 ;
 wire \g_wire[7].u_tx/o_n ;
 wire \g_wire[7].u_tx/o_p ;
 wire \g_wire[8].u_rx/_0_ ;
 wire \g_wire[8].u_rx/r0 ;
 wire \g_wire[8].u_rx/r1 ;
 wire \g_wire[8].u_tx/_0_ ;
 wire \g_wire[8].u_tx/_1_ ;
 wire \g_wire[8].u_tx/a0 ;
 wire \g_wire[8].u_tx/a1 ;
 wire \g_wire[8].u_tx/o_n ;
 wire \g_wire[8].u_tx/o_p ;
 wire \g_wire[9].u_rx/_0_ ;
 wire \g_wire[9].u_rx/r0 ;
 wire \g_wire[9].u_rx/r1 ;
 wire \g_wire[9].u_tx/_0_ ;
 wire \g_wire[9].u_tx/_1_ ;
 wire \g_wire[9].u_tx/a0 ;
 wire \g_wire[9].u_tx/a1 ;
 wire \g_wire[9].u_tx/o_n ;
 wire \g_wire[9].u_tx/o_p ;
 wire net1;
 wire net2;
 wire clk_regs;
 wire clknet_leaf_0_clk;
 wire clknet_leaf_1_clk;
 wire clknet_leaf_2_clk;
 wire clknet_leaf_3_clk;
 wire clknet_leaf_4_clk;
 wire clknet_0_clk;
 wire clknet_1_0__leaf_clk;
 wire clknet_1_1__leaf_clk;
 wire clknet_0_clk_regs;
 wire clknet_4_0_0_clk_regs;
 wire clknet_4_1_0_clk_regs;
 wire clknet_4_2_0_clk_regs;
 wire clknet_4_3_0_clk_regs;
 wire clknet_4_4_0_clk_regs;
 wire clknet_4_5_0_clk_regs;
 wire clknet_4_6_0_clk_regs;
 wire clknet_4_7_0_clk_regs;
 wire clknet_4_8_0_clk_regs;
 wire clknet_4_9_0_clk_regs;
 wire clknet_4_10_0_clk_regs;
 wire clknet_4_11_0_clk_regs;
 wire clknet_4_12_0_clk_regs;
 wire clknet_4_13_0_clk_regs;
 wire clknet_4_14_0_clk_regs;
 wire clknet_4_15_0_clk_regs;
 wire clknet_0__09_;
 wire clknet_1_0__leaf__09_;
 wire clknet_1_1__leaf__09_;
 wire clknet_0__08_;
 wire clknet_1_0__leaf__08_;
 wire clknet_1_1__leaf__08_;
 wire clknet_0__07_;
 wire clknet_1_0__leaf__07_;
 wire clknet_1_1__leaf__07_;
 wire clknet_0__06_;
 wire clknet_1_0__leaf__06_;
 wire clknet_1_1__leaf__06_;
 wire clknet_0__05_;
 wire clknet_1_0__leaf__05_;
 wire clknet_1_1__leaf__05_;
 wire clknet_0__04_;
 wire clknet_1_0__leaf__04_;
 wire clknet_1_1__leaf__04_;
 wire clknet_0__03_;
 wire clknet_1_0__leaf__03_;
 wire clknet_1_1__leaf__03_;
 wire clknet_0__02_;
 wire clknet_1_0__leaf__02_;
 wire clknet_1_1__leaf__02_;
 wire clknet_0__01_;
 wire clknet_1_0__leaf__01_;
 wire clknet_1_1__leaf__01_;
 wire clknet_0__19_;
 wire clknet_1_0__leaf__19_;
 wire clknet_1_1__leaf__19_;
 wire clknet_0__18_;
 wire clknet_1_0__leaf__18_;
 wire clknet_1_1__leaf__18_;
 wire clknet_0__17_;
 wire clknet_1_0__leaf__17_;
 wire clknet_1_1__leaf__17_;
 wire clknet_0__16_;
 wire clknet_1_0__leaf__16_;
 wire clknet_1_1__leaf__16_;
 wire clknet_0__15_;
 wire clknet_1_0__leaf__15_;
 wire clknet_1_1__leaf__15_;
 wire clknet_0__14_;
 wire clknet_1_0__leaf__14_;
 wire clknet_1_1__leaf__14_;
 wire clknet_0__13_;
 wire clknet_1_0__leaf__13_;
 wire clknet_1_1__leaf__13_;
 wire clknet_0__12_;
 wire clknet_1_0__leaf__12_;
 wire clknet_1_1__leaf__12_;
 wire clknet_0__11_;
 wire clknet_1_0__leaf__11_;
 wire clknet_1_1__leaf__11_;
 wire clknet_0__10_;
 wire clknet_1_0__leaf__10_;
 wire clknet_1_1__leaf__10_;
 wire clknet_0__00_;
 wire clknet_1_0__leaf__00_;
 wire clknet_1_1__leaf__00_;
 wire delaynet_0_clk;
 wire delaynet_1_clk;
 wire delaynet_2_clk;
 wire delaynet_3_clk;

 sg13g2_antennanp ANTENNA_1 (.A(tx_d0[1]));
 sg13g2_buf_8 _22_ (.A(l1),
    .X(_20_));
 sg13g2_mux2_1 _23_ (.A0(rx_wire[19]),
    .A1(tx_wire[19]),
    .S(net2),
    .X(_19_));
 sg13g2_mux2_1 _24_ (.A0(rx_wire[18]),
    .A1(tx_wire[18]),
    .S(net2),
    .X(_18_));
 sg13g2_mux2_1 _25_ (.A0(rx_wire[17]),
    .A1(tx_wire[17]),
    .S(net2),
    .X(_17_));
 sg13g2_mux2_1 _26_ (.A0(rx_wire[16]),
    .A1(tx_wire[16]),
    .S(net2),
    .X(_16_));
 sg13g2_mux2_1 _27_ (.A0(rx_wire[15]),
    .A1(tx_wire[15]),
    .S(net2),
    .X(_15_));
 sg13g2_mux2_1 _28_ (.A0(rx_wire[14]),
    .A1(tx_wire[14]),
    .S(net2),
    .X(_14_));
 sg13g2_mux2_1 _29_ (.A0(rx_wire[13]),
    .A1(tx_wire[13]),
    .S(net2),
    .X(_13_));
 sg13g2_mux2_1 _30_ (.A0(rx_wire[12]),
    .A1(tx_wire[12]),
    .S(_20_),
    .X(_12_));
 sg13g2_mux2_1 _31_ (.A0(rx_wire[11]),
    .A1(tx_wire[11]),
    .S(_20_),
    .X(_11_));
 sg13g2_mux2_1 _32_ (.A0(rx_wire[10]),
    .A1(tx_wire[10]),
    .S(net2),
    .X(_10_));
 sg13g2_buf_8 _33_ (.A(l1),
    .X(_21_));
 sg13g2_mux2_1 _34_ (.A0(rx_wire[9]),
    .A1(tx_wire[9]),
    .S(net1),
    .X(_09_));
 sg13g2_mux2_1 _35_ (.A0(rx_wire[8]),
    .A1(tx_wire[8]),
    .S(net1),
    .X(_08_));
 sg13g2_mux2_1 _36_ (.A0(rx_wire[7]),
    .A1(tx_wire[7]),
    .S(net1),
    .X(_07_));
 sg13g2_mux2_1 _37_ (.A0(rx_wire[6]),
    .A1(tx_wire[6]),
    .S(net1),
    .X(_06_));
 sg13g2_mux2_1 _38_ (.A0(rx_wire[5]),
    .A1(tx_wire[5]),
    .S(net1),
    .X(_05_));
 sg13g2_mux2_1 _39_ (.A0(rx_wire[4]),
    .A1(tx_wire[4]),
    .S(_21_),
    .X(_04_));
 sg13g2_mux2_1 _40_ (.A0(rx_wire[3]),
    .A1(tx_wire[3]),
    .S(net1),
    .X(_03_));
 sg13g2_mux2_1 _41_ (.A0(rx_wire[2]),
    .A1(tx_wire[2]),
    .S(net1),
    .X(_02_));
 sg13g2_mux2_1 _42_ (.A0(rx_wire[1]),
    .A1(tx_wire[1]),
    .S(net1),
    .X(_01_));
 sg13g2_mux2_1 _43_ (.A0(rx_wire[0]),
    .A1(rx_wire[0]),
    .S(_21_),
    .X(_00_));
 sg13g2_buf_16 clkbuf_0__00_ (.X(clknet_0__00_),
    .A(_00_));
 sg13g2_buf_16 clkbuf_0__01_ (.X(clknet_0__01_),
    .A(_01_));
 sg13g2_buf_16 clkbuf_0__02_ (.X(clknet_0__02_),
    .A(_02_));
 sg13g2_buf_16 clkbuf_0__03_ (.X(clknet_0__03_),
    .A(_03_));
 sg13g2_buf_16 clkbuf_0__04_ (.X(clknet_0__04_),
    .A(_04_));
 sg13g2_buf_16 clkbuf_0__05_ (.X(clknet_0__05_),
    .A(_05_));
 sg13g2_buf_16 clkbuf_0__06_ (.X(clknet_0__06_),
    .A(_06_));
 sg13g2_buf_16 clkbuf_0__07_ (.X(clknet_0__07_),
    .A(_07_));
 sg13g2_buf_16 clkbuf_0__08_ (.X(clknet_0__08_),
    .A(_08_));
 sg13g2_buf_16 clkbuf_0__09_ (.X(clknet_0__09_),
    .A(_09_));
 sg13g2_buf_16 clkbuf_0__10_ (.X(clknet_0__10_),
    .A(_10_));
 sg13g2_buf_16 clkbuf_0__11_ (.X(clknet_0__11_),
    .A(_11_));
 sg13g2_buf_16 clkbuf_0__12_ (.X(clknet_0__12_),
    .A(_12_));
 sg13g2_buf_16 clkbuf_0__13_ (.X(clknet_0__13_),
    .A(_13_));
 sg13g2_buf_16 clkbuf_0__14_ (.X(clknet_0__14_),
    .A(_14_));
 sg13g2_buf_16 clkbuf_0__15_ (.X(clknet_0__15_),
    .A(_15_));
 sg13g2_buf_16 clkbuf_0__16_ (.X(clknet_0__16_),
    .A(_16_));
 sg13g2_buf_16 clkbuf_0__17_ (.X(clknet_0__17_),
    .A(_17_));
 sg13g2_buf_16 clkbuf_0__18_ (.X(clknet_0__18_),
    .A(_18_));
 sg13g2_buf_16 clkbuf_0__19_ (.X(clknet_0__19_),
    .A(_19_));
 sg13g2_buf_16 clkbuf_0_clk (.X(clknet_0_clk),
    .A(delaynet_3_clk));
 sg13g2_buf_16 clkbuf_0_clk_regs (.X(clknet_0_clk_regs),
    .A(clk_regs));
 sg13g2_buf_16 clkbuf_1_0__f__00_ (.X(clknet_1_0__leaf__00_),
    .A(clknet_0__00_));
 sg13g2_buf_16 clkbuf_1_0__f__01_ (.X(clknet_1_0__leaf__01_),
    .A(clknet_0__01_));
 sg13g2_buf_16 clkbuf_1_0__f__02_ (.X(clknet_1_0__leaf__02_),
    .A(clknet_0__02_));
 sg13g2_buf_16 clkbuf_1_0__f__03_ (.X(clknet_1_0__leaf__03_),
    .A(clknet_0__03_));
 sg13g2_buf_16 clkbuf_1_0__f__04_ (.X(clknet_1_0__leaf__04_),
    .A(clknet_0__04_));
 sg13g2_buf_16 clkbuf_1_0__f__05_ (.X(clknet_1_0__leaf__05_),
    .A(clknet_0__05_));
 sg13g2_buf_16 clkbuf_1_0__f__06_ (.X(clknet_1_0__leaf__06_),
    .A(clknet_0__06_));
 sg13g2_buf_16 clkbuf_1_0__f__07_ (.X(clknet_1_0__leaf__07_),
    .A(clknet_0__07_));
 sg13g2_buf_16 clkbuf_1_0__f__08_ (.X(clknet_1_0__leaf__08_),
    .A(clknet_0__08_));
 sg13g2_buf_16 clkbuf_1_0__f__09_ (.X(clknet_1_0__leaf__09_),
    .A(clknet_0__09_));
 sg13g2_buf_16 clkbuf_1_0__f__10_ (.X(clknet_1_0__leaf__10_),
    .A(clknet_0__10_));
 sg13g2_buf_16 clkbuf_1_0__f__11_ (.X(clknet_1_0__leaf__11_),
    .A(clknet_0__11_));
 sg13g2_buf_16 clkbuf_1_0__f__12_ (.X(clknet_1_0__leaf__12_),
    .A(clknet_0__12_));
 sg13g2_buf_16 clkbuf_1_0__f__13_ (.X(clknet_1_0__leaf__13_),
    .A(clknet_0__13_));
 sg13g2_buf_16 clkbuf_1_0__f__14_ (.X(clknet_1_0__leaf__14_),
    .A(clknet_0__14_));
 sg13g2_buf_16 clkbuf_1_0__f__15_ (.X(clknet_1_0__leaf__15_),
    .A(clknet_0__15_));
 sg13g2_buf_16 clkbuf_1_0__f__16_ (.X(clknet_1_0__leaf__16_),
    .A(clknet_0__16_));
 sg13g2_buf_16 clkbuf_1_0__f__17_ (.X(clknet_1_0__leaf__17_),
    .A(clknet_0__17_));
 sg13g2_buf_16 clkbuf_1_0__f__18_ (.X(clknet_1_0__leaf__18_),
    .A(clknet_0__18_));
 sg13g2_buf_16 clkbuf_1_0__f__19_ (.X(clknet_1_0__leaf__19_),
    .A(clknet_0__19_));
 sg13g2_buf_16 clkbuf_1_0__f_clk (.X(clknet_1_0__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_1_1__f__00_ (.X(clknet_1_1__leaf__00_),
    .A(clknet_0__00_));
 sg13g2_buf_16 clkbuf_1_1__f__01_ (.X(clknet_1_1__leaf__01_),
    .A(clknet_0__01_));
 sg13g2_buf_16 clkbuf_1_1__f__02_ (.X(clknet_1_1__leaf__02_),
    .A(clknet_0__02_));
 sg13g2_buf_16 clkbuf_1_1__f__03_ (.X(clknet_1_1__leaf__03_),
    .A(clknet_0__03_));
 sg13g2_buf_16 clkbuf_1_1__f__04_ (.X(clknet_1_1__leaf__04_),
    .A(clknet_0__04_));
 sg13g2_buf_16 clkbuf_1_1__f__05_ (.X(clknet_1_1__leaf__05_),
    .A(clknet_0__05_));
 sg13g2_buf_16 clkbuf_1_1__f__06_ (.X(clknet_1_1__leaf__06_),
    .A(clknet_0__06_));
 sg13g2_buf_16 clkbuf_1_1__f__07_ (.X(clknet_1_1__leaf__07_),
    .A(clknet_0__07_));
 sg13g2_buf_16 clkbuf_1_1__f__08_ (.X(clknet_1_1__leaf__08_),
    .A(clknet_0__08_));
 sg13g2_buf_16 clkbuf_1_1__f__09_ (.X(clknet_1_1__leaf__09_),
    .A(clknet_0__09_));
 sg13g2_buf_16 clkbuf_1_1__f__10_ (.X(clknet_1_1__leaf__10_),
    .A(clknet_0__10_));
 sg13g2_buf_16 clkbuf_1_1__f__11_ (.X(clknet_1_1__leaf__11_),
    .A(clknet_0__11_));
 sg13g2_buf_16 clkbuf_1_1__f__12_ (.X(clknet_1_1__leaf__12_),
    .A(clknet_0__12_));
 sg13g2_buf_16 clkbuf_1_1__f__13_ (.X(clknet_1_1__leaf__13_),
    .A(clknet_0__13_));
 sg13g2_buf_16 clkbuf_1_1__f__14_ (.X(clknet_1_1__leaf__14_),
    .A(clknet_0__14_));
 sg13g2_buf_16 clkbuf_1_1__f__15_ (.X(clknet_1_1__leaf__15_),
    .A(clknet_0__15_));
 sg13g2_buf_16 clkbuf_1_1__f__16_ (.X(clknet_1_1__leaf__16_),
    .A(clknet_0__16_));
 sg13g2_buf_16 clkbuf_1_1__f__17_ (.X(clknet_1_1__leaf__17_),
    .A(clknet_0__17_));
 sg13g2_buf_16 clkbuf_1_1__f__18_ (.X(clknet_1_1__leaf__18_),
    .A(clknet_0__18_));
 sg13g2_buf_16 clkbuf_1_1__f__19_ (.X(clknet_1_1__leaf__19_),
    .A(clknet_0__19_));
 sg13g2_buf_16 clkbuf_1_1__f_clk (.X(clknet_1_1__leaf_clk),
    .A(clknet_0_clk));
 sg13g2_buf_16 clkbuf_4_0_0_clk_regs (.X(clknet_4_0_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_10_0_clk_regs (.X(clknet_4_10_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_11_0_clk_regs (.X(clknet_4_11_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_12_0_clk_regs (.X(clknet_4_12_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_13_0_clk_regs (.X(clknet_4_13_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_14_0_clk_regs (.X(clknet_4_14_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_15_0_clk_regs (.X(clknet_4_15_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_1_0_clk_regs (.X(clknet_4_1_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_2_0_clk_regs (.X(clknet_4_2_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_3_0_clk_regs (.X(clknet_4_3_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_4_0_clk_regs (.X(clknet_4_4_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_5_0_clk_regs (.X(clknet_4_5_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_6_0_clk_regs (.X(clknet_4_6_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_7_0_clk_regs (.X(clknet_4_7_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_8_0_clk_regs (.X(clknet_4_8_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_4_9_0_clk_regs (.X(clknet_4_9_0_clk_regs),
    .A(clknet_0_clk_regs));
 sg13g2_buf_16 clkbuf_leaf_0_clk (.X(clknet_leaf_0_clk),
    .A(clknet_1_1__leaf_clk));
 sg13g2_buf_16 clkbuf_leaf_1_clk (.X(clknet_leaf_1_clk),
    .A(clknet_1_1__leaf_clk));
 sg13g2_buf_16 clkbuf_leaf_2_clk (.X(clknet_leaf_2_clk),
    .A(clknet_1_0__leaf_clk));
 sg13g2_buf_16 clkbuf_leaf_3_clk (.X(clknet_leaf_3_clk),
    .A(clknet_1_0__leaf_clk));
 sg13g2_buf_16 clkbuf_leaf_4_clk (.X(clknet_leaf_4_clk),
    .A(clknet_1_0__leaf_clk));
 sg13g2_buf_16 clkbuf_regs_0_clk (.X(clk_regs),
    .A(clk));
 sg13g2_buf_16 clkload0 (.A(clknet_1_1__leaf_clk));
 sg13g2_inv_1 clkload1 (.A(clknet_4_0_0_clk_regs));
 sg13g2_inv_1 clkload10 (.A(clknet_4_10_0_clk_regs));
 sg13g2_inv_1 clkload11 (.A(clknet_4_11_0_clk_regs));
 sg13g2_inv_1 clkload12 (.A(clknet_4_12_0_clk_regs));
 sg13g2_inv_1 clkload13 (.A(clknet_4_14_0_clk_regs));
 sg13g2_inv_1 clkload14 (.A(clknet_4_15_0_clk_regs));
 sg13g2_inv_1 clkload2 (.A(clknet_4_1_0_clk_regs));
 sg13g2_inv_1 clkload3 (.A(clknet_4_2_0_clk_regs));
 sg13g2_inv_1 clkload4 (.A(clknet_4_3_0_clk_regs));
 sg13g2_inv_1 clkload5 (.A(clknet_4_4_0_clk_regs));
 sg13g2_inv_1 clkload6 (.A(clknet_4_5_0_clk_regs));
 sg13g2_inv_1 clkload7 (.A(clknet_4_6_0_clk_regs));
 sg13g2_inv_1 clkload8 (.A(clknet_4_8_0_clk_regs));
 sg13g2_inv_1 clkload9 (.A(clknet_4_9_0_clk_regs));
 sg13g2_buf_16 delaybuf_0_clk (.X(delaynet_0_clk),
    .A(clk));
 sg13g2_buf_16 delaybuf_1_clk (.X(delaynet_1_clk),
    .A(delaynet_0_clk));
 sg13g2_buf_16 delaybuf_2_clk (.X(delaynet_2_clk),
    .A(delaynet_1_clk));
 sg13g2_buf_16 delaybuf_3_clk (.X(delaynet_3_clk),
    .A(delaynet_2_clk));
 sg13g2_buf_1 fanout1 (.A(_21_),
    .X(net1));
 sg13g2_buf_1 fanout2 (.A(_20_),
    .X(net2));
 sg13g2_inv_2 \g_wire[0].u_rx/_1_  (.Y(\g_wire[0].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[0].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[0].u_rx/r0 ),
    .Q(rx_q0[0]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[0].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[0].u_rx/r1 ),
    .Q(rx_q1[0]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[0].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__00_),
    .Q(\g_wire[0].u_rx/r1 ),
    .CLK(\g_wire[0].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[0].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__00_),
    .Q(\g_wire[0].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[0].u_tx/_2_  (.A0(\g_wire[0].u_tx/a1 ),
    .A1(\g_wire[0].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[0].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[0].u_tx/_3_  (.A0(\g_wire[0].u_tx/o_p ),
    .A1(\g_wire[0].u_tx/o_n ),
    .S(clknet_leaf_2_clk),
    .X(tx_wire[0]));
 sg13g2_inv_1 \g_wire[0].u_tx/_4_  (.Y(\g_wire[0].u_tx/_1_ ),
    .A(clknet_4_5_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[0].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[0].u_tx/_0_ ),
    .Q(\g_wire[0].u_tx/o_p ),
    .CLK(clknet_4_5_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[0].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[0].u_tx/a0 ),
    .Q(\g_wire[0].u_tx/o_n ),
    .CLK(\g_wire[0].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[0].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[0]),
    .Q(\g_wire[0].u_tx/a0 ),
    .CLK(clknet_4_4_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[0].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[0]),
    .Q(\g_wire[0].u_tx/a1 ),
    .CLK(clknet_4_4_0_clk_regs));
 sg13g2_inv_2 \g_wire[10].u_rx/_1_  (.Y(\g_wire[10].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[10].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[10].u_rx/r0 ),
    .Q(rx_q0[10]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[10].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[10].u_rx/r1 ),
    .Q(rx_q1[10]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[10].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__10_),
    .Q(\g_wire[10].u_rx/r1 ),
    .CLK(\g_wire[10].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[10].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__10_),
    .Q(\g_wire[10].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[10].u_tx/_2_  (.A0(\g_wire[10].u_tx/a1 ),
    .A1(\g_wire[10].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[10].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[10].u_tx/_3_  (.A0(\g_wire[10].u_tx/o_p ),
    .A1(\g_wire[10].u_tx/o_n ),
    .S(clknet_leaf_0_clk),
    .X(tx_wire[10]));
 sg13g2_inv_1 \g_wire[10].u_tx/_4_  (.Y(\g_wire[10].u_tx/_1_ ),
    .A(clknet_4_12_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[10].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[10].u_tx/_0_ ),
    .Q(\g_wire[10].u_tx/o_p ),
    .CLK(clknet_4_14_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[10].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[10].u_tx/a0 ),
    .Q(\g_wire[10].u_tx/o_n ),
    .CLK(\g_wire[10].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[10].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[10]),
    .Q(\g_wire[10].u_tx/a0 ),
    .CLK(clknet_4_11_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[10].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[10]),
    .Q(\g_wire[10].u_tx/a1 ),
    .CLK(clknet_4_11_0_clk_regs));
 sg13g2_inv_2 \g_wire[11].u_rx/_1_  (.Y(\g_wire[11].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[11].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[11].u_rx/r0 ),
    .Q(rx_q0[11]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[11].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[11].u_rx/r1 ),
    .Q(rx_q1[11]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[11].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__11_),
    .Q(\g_wire[11].u_rx/r1 ),
    .CLK(\g_wire[11].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[11].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__11_),
    .Q(\g_wire[11].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[11].u_tx/_2_  (.A0(\g_wire[11].u_tx/a1 ),
    .A1(\g_wire[11].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[11].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[11].u_tx/_3_  (.A0(\g_wire[11].u_tx/o_p ),
    .A1(\g_wire[11].u_tx/o_n ),
    .S(clknet_leaf_2_clk),
    .X(tx_wire[11]));
 sg13g2_inv_1 \g_wire[11].u_tx/_4_  (.Y(\g_wire[11].u_tx/_1_ ),
    .A(clknet_4_7_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[11].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[11].u_tx/_0_ ),
    .Q(\g_wire[11].u_tx/o_p ),
    .CLK(clknet_4_5_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[11].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[11].u_tx/a0 ),
    .Q(\g_wire[11].u_tx/o_n ),
    .CLK(\g_wire[11].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[11].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[11]),
    .Q(\g_wire[11].u_tx/a0 ),
    .CLK(clknet_4_6_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[11].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[11]),
    .Q(\g_wire[11].u_tx/a1 ),
    .CLK(clknet_4_6_0_clk_regs));
 sg13g2_inv_2 \g_wire[12].u_rx/_1_  (.Y(\g_wire[12].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[12].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[12].u_rx/r0 ),
    .Q(rx_q0[12]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[12].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[12].u_rx/r1 ),
    .Q(rx_q1[12]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[12].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__12_),
    .Q(\g_wire[12].u_rx/r1 ),
    .CLK(\g_wire[12].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[12].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__12_),
    .Q(\g_wire[12].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[12].u_tx/_2_  (.A0(\g_wire[12].u_tx/a1 ),
    .A1(\g_wire[12].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[12].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[12].u_tx/_3_  (.A0(\g_wire[12].u_tx/o_p ),
    .A1(\g_wire[12].u_tx/o_n ),
    .S(clknet_leaf_0_clk),
    .X(tx_wire[12]));
 sg13g2_inv_1 \g_wire[12].u_tx/_4_  (.Y(\g_wire[12].u_tx/_1_ ),
    .A(clknet_4_11_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[12].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[12].u_tx/_0_ ),
    .Q(\g_wire[12].u_tx/o_p ),
    .CLK(clknet_4_14_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[12].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[12].u_tx/a0 ),
    .Q(\g_wire[12].u_tx/o_n ),
    .CLK(\g_wire[12].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[12].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[12]),
    .Q(\g_wire[12].u_tx/a0 ),
    .CLK(clknet_4_10_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[12].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[12]),
    .Q(\g_wire[12].u_tx/a1 ),
    .CLK(clknet_4_10_0_clk_regs));
 sg13g2_inv_2 \g_wire[13].u_rx/_1_  (.Y(\g_wire[13].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[13].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[13].u_rx/r0 ),
    .Q(rx_q0[13]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[13].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[13].u_rx/r1 ),
    .Q(rx_q1[13]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[13].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__13_),
    .Q(\g_wire[13].u_rx/r1 ),
    .CLK(\g_wire[13].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[13].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__13_),
    .Q(\g_wire[13].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[13].u_tx/_2_  (.A0(\g_wire[13].u_tx/a1 ),
    .A1(\g_wire[13].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[13].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[13].u_tx/_3_  (.A0(\g_wire[13].u_tx/o_p ),
    .A1(\g_wire[13].u_tx/o_n ),
    .S(clknet_leaf_3_clk),
    .X(tx_wire[13]));
 sg13g2_inv_1 \g_wire[13].u_tx/_4_  (.Y(\g_wire[13].u_tx/_1_ ),
    .A(clknet_4_0_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[13].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[13].u_tx/_0_ ),
    .Q(\g_wire[13].u_tx/o_p ),
    .CLK(clknet_4_0_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[13].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[13].u_tx/a0 ),
    .Q(\g_wire[13].u_tx/o_n ),
    .CLK(\g_wire[13].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[13].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[13]),
    .Q(\g_wire[13].u_tx/a0 ),
    .CLK(clknet_4_2_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[13].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[13]),
    .Q(\g_wire[13].u_tx/a1 ),
    .CLK(clknet_4_12_0_clk_regs));
 sg13g2_inv_2 \g_wire[14].u_rx/_1_  (.Y(\g_wire[14].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[14].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[14].u_rx/r0 ),
    .Q(rx_q0[14]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[14].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[14].u_rx/r1 ),
    .Q(rx_q1[14]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[14].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__14_),
    .Q(\g_wire[14].u_rx/r1 ),
    .CLK(\g_wire[14].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[14].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__14_),
    .Q(\g_wire[14].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[14].u_tx/_2_  (.A0(\g_wire[14].u_tx/a1 ),
    .A1(\g_wire[14].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[14].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[14].u_tx/_3_  (.A0(\g_wire[14].u_tx/o_p ),
    .A1(\g_wire[14].u_tx/o_n ),
    .S(clknet_leaf_1_clk),
    .X(tx_wire[14]));
 sg13g2_inv_1 \g_wire[14].u_tx/_4_  (.Y(\g_wire[14].u_tx/_1_ ),
    .A(clknet_4_13_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[14].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[14].u_tx/_0_ ),
    .Q(\g_wire[14].u_tx/o_p ),
    .CLK(clknet_4_15_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[14].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[14].u_tx/a0 ),
    .Q(\g_wire[14].u_tx/o_n ),
    .CLK(\g_wire[14].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[14].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[14]),
    .Q(\g_wire[14].u_tx/a0 ),
    .CLK(clknet_4_14_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[14].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[14]),
    .Q(\g_wire[14].u_tx/a1 ),
    .CLK(clknet_4_15_0_clk_regs));
 sg13g2_inv_2 \g_wire[15].u_rx/_1_  (.Y(\g_wire[15].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[15].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[15].u_rx/r0 ),
    .Q(rx_q0[15]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[15].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[15].u_rx/r1 ),
    .Q(rx_q1[15]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[15].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__15_),
    .Q(\g_wire[15].u_rx/r1 ),
    .CLK(\g_wire[15].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[15].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__15_),
    .Q(\g_wire[15].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[15].u_tx/_2_  (.A0(\g_wire[15].u_tx/a1 ),
    .A1(\g_wire[15].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[15].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[15].u_tx/_3_  (.A0(\g_wire[15].u_tx/o_p ),
    .A1(\g_wire[15].u_tx/o_n ),
    .S(clknet_leaf_4_clk),
    .X(tx_wire[15]));
 sg13g2_inv_1 \g_wire[15].u_tx/_4_  (.Y(\g_wire[15].u_tx/_1_ ),
    .A(clknet_4_9_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[15].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[15].u_tx/_0_ ),
    .Q(\g_wire[15].u_tx/o_p ),
    .CLK(clknet_4_8_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[15].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[15].u_tx/a0 ),
    .Q(\g_wire[15].u_tx/o_n ),
    .CLK(\g_wire[15].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[15].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[15]),
    .Q(\g_wire[15].u_tx/a0 ),
    .CLK(clknet_4_9_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[15].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[15]),
    .Q(\g_wire[15].u_tx/a1 ),
    .CLK(clknet_4_8_0_clk_regs));
 sg13g2_inv_2 \g_wire[16].u_rx/_1_  (.Y(\g_wire[16].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[16].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[16].u_rx/r0 ),
    .Q(rx_q0[16]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[16].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[16].u_rx/r1 ),
    .Q(rx_q1[16]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[16].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__16_),
    .Q(\g_wire[16].u_rx/r1 ),
    .CLK(\g_wire[16].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[16].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__16_),
    .Q(\g_wire[16].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[16].u_tx/_2_  (.A0(\g_wire[16].u_tx/a1 ),
    .A1(\g_wire[16].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[16].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[16].u_tx/_3_  (.A0(\g_wire[16].u_tx/o_p ),
    .A1(\g_wire[16].u_tx/o_n ),
    .S(clknet_leaf_3_clk),
    .X(tx_wire[16]));
 sg13g2_inv_1 \g_wire[16].u_tx/_4_  (.Y(\g_wire[16].u_tx/_1_ ),
    .A(clknet_4_1_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[16].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[16].u_tx/_0_ ),
    .Q(\g_wire[16].u_tx/o_p ),
    .CLK(clknet_4_1_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[16].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[16].u_tx/a0 ),
    .Q(\g_wire[16].u_tx/o_n ),
    .CLK(\g_wire[16].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[16].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[16]),
    .Q(\g_wire[16].u_tx/a0 ),
    .CLK(clknet_4_0_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[16].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[16]),
    .Q(\g_wire[16].u_tx/a1 ),
    .CLK(clknet_4_3_0_clk_regs));
 sg13g2_inv_2 \g_wire[17].u_rx/_1_  (.Y(\g_wire[17].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[17].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[17].u_rx/r0 ),
    .Q(rx_q0[17]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[17].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[17].u_rx/r1 ),
    .Q(rx_q1[17]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[17].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__17_),
    .Q(\g_wire[17].u_rx/r1 ),
    .CLK(\g_wire[17].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[17].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__17_),
    .Q(\g_wire[17].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[17].u_tx/_2_  (.A0(\g_wire[17].u_tx/a1 ),
    .A1(\g_wire[17].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[17].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[17].u_tx/_3_  (.A0(\g_wire[17].u_tx/o_p ),
    .A1(\g_wire[17].u_tx/o_n ),
    .S(clknet_leaf_3_clk),
    .X(tx_wire[17]));
 sg13g2_inv_1 \g_wire[17].u_tx/_4_  (.Y(\g_wire[17].u_tx/_1_ ),
    .A(clknet_4_5_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[17].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[17].u_tx/_0_ ),
    .Q(\g_wire[17].u_tx/o_p ),
    .CLK(clknet_4_5_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[17].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[17].u_tx/a0 ),
    .Q(\g_wire[17].u_tx/o_n ),
    .CLK(\g_wire[17].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[17].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[17]),
    .Q(\g_wire[17].u_tx/a0 ),
    .CLK(clknet_4_1_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[17].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[17]),
    .Q(\g_wire[17].u_tx/a1 ),
    .CLK(clknet_4_1_0_clk_regs));
 sg13g2_inv_2 \g_wire[18].u_rx/_1_  (.Y(\g_wire[18].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[18].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[18].u_rx/r0 ),
    .Q(rx_q0[18]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[18].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[18].u_rx/r1 ),
    .Q(rx_q1[18]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[18].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__18_),
    .Q(\g_wire[18].u_rx/r1 ),
    .CLK(\g_wire[18].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[18].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__18_),
    .Q(\g_wire[18].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[18].u_tx/_2_  (.A0(\g_wire[18].u_tx/a1 ),
    .A1(\g_wire[18].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[18].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[18].u_tx/_3_  (.A0(\g_wire[18].u_tx/o_p ),
    .A1(\g_wire[18].u_tx/o_n ),
    .S(clknet_leaf_1_clk),
    .X(tx_wire[18]));
 sg13g2_inv_1 \g_wire[18].u_tx/_4_  (.Y(\g_wire[18].u_tx/_1_ ),
    .A(clknet_4_13_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[18].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[18].u_tx/_0_ ),
    .Q(\g_wire[18].u_tx/o_p ),
    .CLK(clknet_4_13_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[18].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[18].u_tx/a0 ),
    .Q(\g_wire[18].u_tx/o_n ),
    .CLK(\g_wire[18].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[18].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[18]),
    .Q(\g_wire[18].u_tx/a0 ),
    .CLK(clknet_4_12_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[18].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[18]),
    .Q(\g_wire[18].u_tx/a1 ),
    .CLK(clknet_4_0_0_clk_regs));
 sg13g2_inv_2 \g_wire[19].u_rx/_1_  (.Y(\g_wire[19].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[19].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[19].u_rx/r0 ),
    .Q(rx_q0[19]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[19].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[19].u_rx/r1 ),
    .Q(rx_q1[19]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[19].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__19_),
    .Q(\g_wire[19].u_rx/r1 ),
    .CLK(\g_wire[19].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[19].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__19_),
    .Q(\g_wire[19].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[19].u_tx/_2_  (.A0(\g_wire[19].u_tx/a1 ),
    .A1(\g_wire[19].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[19].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[19].u_tx/_3_  (.A0(\g_wire[19].u_tx/o_p ),
    .A1(\g_wire[19].u_tx/o_n ),
    .S(clknet_leaf_0_clk),
    .X(tx_wire[19]));
 sg13g2_inv_1 \g_wire[19].u_tx/_4_  (.Y(\g_wire[19].u_tx/_1_ ),
    .A(clknet_4_10_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[19].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[19].u_tx/_0_ ),
    .Q(\g_wire[19].u_tx/o_p ),
    .CLK(clknet_4_10_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[19].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[19].u_tx/a0 ),
    .Q(\g_wire[19].u_tx/o_n ),
    .CLK(\g_wire[19].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[19].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[19]),
    .Q(\g_wire[19].u_tx/a0 ),
    .CLK(clknet_4_9_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[19].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[19]),
    .Q(\g_wire[19].u_tx/a1 ),
    .CLK(clknet_4_8_0_clk_regs));
 sg13g2_inv_2 \g_wire[1].u_rx/_1_  (.Y(\g_wire[1].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[1].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[1].u_rx/r0 ),
    .Q(rx_q0[1]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[1].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[1].u_rx/r1 ),
    .Q(rx_q1[1]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[1].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__01_),
    .Q(\g_wire[1].u_rx/r1 ),
    .CLK(\g_wire[1].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[1].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__01_),
    .Q(\g_wire[1].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[1].u_tx/_2_  (.A0(\g_wire[1].u_tx/a1 ),
    .A1(\g_wire[1].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[1].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[1].u_tx/_3_  (.A0(\g_wire[1].u_tx/o_p ),
    .A1(\g_wire[1].u_tx/o_n ),
    .S(clknet_leaf_0_clk),
    .X(tx_wire[1]));
 sg13g2_inv_1 \g_wire[1].u_tx/_4_  (.Y(\g_wire[1].u_tx/_1_ ),
    .A(clknet_4_11_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[1].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[1].u_tx/_0_ ),
    .Q(\g_wire[1].u_tx/o_p ),
    .CLK(clknet_4_14_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[1].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[1].u_tx/a0 ),
    .Q(\g_wire[1].u_tx/o_n ),
    .CLK(\g_wire[1].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[1].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[1]),
    .Q(\g_wire[1].u_tx/a0 ),
    .CLK(clknet_4_11_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[1].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[1]),
    .Q(\g_wire[1].u_tx/a1 ),
    .CLK(clknet_4_9_0_clk_regs));
 sg13g2_inv_2 \g_wire[2].u_rx/_1_  (.Y(\g_wire[2].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[2].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[2].u_rx/r0 ),
    .Q(rx_q0[2]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[2].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[2].u_rx/r1 ),
    .Q(rx_q1[2]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[2].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__02_),
    .Q(\g_wire[2].u_rx/r1 ),
    .CLK(\g_wire[2].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[2].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__02_),
    .Q(\g_wire[2].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[2].u_tx/_2_  (.A0(\g_wire[2].u_tx/a1 ),
    .A1(\g_wire[2].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[2].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[2].u_tx/_3_  (.A0(\g_wire[2].u_tx/o_p ),
    .A1(\g_wire[2].u_tx/o_n ),
    .S(clknet_leaf_4_clk),
    .X(tx_wire[2]));
 sg13g2_inv_1 \g_wire[2].u_tx/_4_  (.Y(\g_wire[2].u_tx/_1_ ),
    .A(clknet_4_2_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[2].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[2].u_tx/_0_ ),
    .Q(\g_wire[2].u_tx/o_p ),
    .CLK(clknet_4_2_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[2].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[2].u_tx/a0 ),
    .Q(\g_wire[2].u_tx/o_n ),
    .CLK(\g_wire[2].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[2].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[2]),
    .Q(\g_wire[2].u_tx/a0 ),
    .CLK(clknet_4_2_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[2].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[2]),
    .Q(\g_wire[2].u_tx/a1 ),
    .CLK(clknet_4_2_0_clk_regs));
 sg13g2_inv_2 \g_wire[3].u_rx/_1_  (.Y(\g_wire[3].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[3].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[3].u_rx/r0 ),
    .Q(rx_q0[3]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[3].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[3].u_rx/r1 ),
    .Q(rx_q1[3]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[3].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__03_),
    .Q(\g_wire[3].u_rx/r1 ),
    .CLK(\g_wire[3].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[3].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__03_),
    .Q(\g_wire[3].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[3].u_tx/_2_  (.A0(\g_wire[3].u_tx/a1 ),
    .A1(\g_wire[3].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[3].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[3].u_tx/_3_  (.A0(\g_wire[3].u_tx/o_p ),
    .A1(\g_wire[3].u_tx/o_n ),
    .S(clknet_leaf_2_clk),
    .X(tx_wire[3]));
 sg13g2_inv_1 \g_wire[3].u_tx/_4_  (.Y(\g_wire[3].u_tx/_1_ ),
    .A(clknet_4_7_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[3].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[3].u_tx/_0_ ),
    .Q(\g_wire[3].u_tx/o_p ),
    .CLK(clknet_4_7_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[3].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[3].u_tx/a0 ),
    .Q(\g_wire[3].u_tx/o_n ),
    .CLK(\g_wire[3].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[3].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[3]),
    .Q(\g_wire[3].u_tx/a0 ),
    .CLK(clknet_4_6_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[3].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[3]),
    .Q(\g_wire[3].u_tx/a1 ),
    .CLK(clknet_4_6_0_clk_regs));
 sg13g2_inv_2 \g_wire[4].u_rx/_1_  (.Y(\g_wire[4].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[4].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[4].u_rx/r0 ),
    .Q(rx_q0[4]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[4].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[4].u_rx/r1 ),
    .Q(rx_q1[4]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[4].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__04_),
    .Q(\g_wire[4].u_rx/r1 ),
    .CLK(\g_wire[4].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[4].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__04_),
    .Q(\g_wire[4].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[4].u_tx/_2_  (.A0(\g_wire[4].u_tx/a1 ),
    .A1(\g_wire[4].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[4].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[4].u_tx/_3_  (.A0(\g_wire[4].u_tx/o_p ),
    .A1(\g_wire[4].u_tx/o_n ),
    .S(clknet_leaf_2_clk),
    .X(tx_wire[4]));
 sg13g2_inv_1 \g_wire[4].u_tx/_4_  (.Y(\g_wire[4].u_tx/_1_ ),
    .A(clknet_4_7_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[4].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[4].u_tx/_0_ ),
    .Q(\g_wire[4].u_tx/o_p ),
    .CLK(clknet_4_7_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[4].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[4].u_tx/a0 ),
    .Q(\g_wire[4].u_tx/o_n ),
    .CLK(\g_wire[4].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[4].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[4]),
    .Q(\g_wire[4].u_tx/a0 ),
    .CLK(clknet_4_6_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[4].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[4]),
    .Q(\g_wire[4].u_tx/a1 ),
    .CLK(clknet_4_4_0_clk_regs));
 sg13g2_inv_2 \g_wire[5].u_rx/_1_  (.Y(\g_wire[5].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[5].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[5].u_rx/r0 ),
    .Q(rx_q0[5]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[5].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[5].u_rx/r1 ),
    .Q(rx_q1[5]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[5].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__05_),
    .Q(\g_wire[5].u_rx/r1 ),
    .CLK(\g_wire[5].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[5].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__05_),
    .Q(\g_wire[5].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[5].u_tx/_2_  (.A0(\g_wire[5].u_tx/a1 ),
    .A1(\g_wire[5].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[5].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[5].u_tx/_3_  (.A0(\g_wire[5].u_tx/o_p ),
    .A1(\g_wire[5].u_tx/o_n ),
    .S(clknet_leaf_4_clk),
    .X(tx_wire[5]));
 sg13g2_inv_1 \g_wire[5].u_tx/_4_  (.Y(\g_wire[5].u_tx/_1_ ),
    .A(clknet_4_10_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[5].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[5].u_tx/_0_ ),
    .Q(\g_wire[5].u_tx/o_p ),
    .CLK(clknet_4_9_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[5].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[5].u_tx/a0 ),
    .Q(\g_wire[5].u_tx/o_n ),
    .CLK(\g_wire[5].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[5].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[5]),
    .Q(\g_wire[5].u_tx/a0 ),
    .CLK(clknet_4_8_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[5].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[5]),
    .Q(\g_wire[5].u_tx/a1 ),
    .CLK(clknet_4_8_0_clk_regs));
 sg13g2_inv_2 \g_wire[6].u_rx/_1_  (.Y(\g_wire[6].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[6].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[6].u_rx/r0 ),
    .Q(rx_q0[6]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[6].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[6].u_rx/r1 ),
    .Q(rx_q1[6]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[6].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__06_),
    .Q(\g_wire[6].u_rx/r1 ),
    .CLK(\g_wire[6].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[6].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__06_),
    .Q(\g_wire[6].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[6].u_tx/_2_  (.A0(\g_wire[6].u_tx/a1 ),
    .A1(\g_wire[6].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[6].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[6].u_tx/_3_  (.A0(\g_wire[6].u_tx/o_p ),
    .A1(\g_wire[6].u_tx/o_n ),
    .S(clknet_leaf_3_clk),
    .X(tx_wire[6]));
 sg13g2_inv_1 \g_wire[6].u_tx/_4_  (.Y(\g_wire[6].u_tx/_1_ ),
    .A(clknet_4_4_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[6].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[6].u_tx/_0_ ),
    .Q(\g_wire[6].u_tx/o_p ),
    .CLK(clknet_4_4_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[6].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[6].u_tx/a0 ),
    .Q(\g_wire[6].u_tx/o_n ),
    .CLK(\g_wire[6].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[6].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[6]),
    .Q(\g_wire[6].u_tx/a0 ),
    .CLK(clknet_4_1_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[6].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[6]),
    .Q(\g_wire[6].u_tx/a1 ),
    .CLK(clknet_4_0_0_clk_regs));
 sg13g2_inv_2 \g_wire[7].u_rx/_1_  (.Y(\g_wire[7].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[7].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[7].u_rx/r0 ),
    .Q(rx_q0[7]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[7].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[7].u_rx/r1 ),
    .Q(rx_q1[7]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[7].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__07_),
    .Q(\g_wire[7].u_rx/r1 ),
    .CLK(\g_wire[7].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[7].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__07_),
    .Q(\g_wire[7].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[7].u_tx/_2_  (.A0(\g_wire[7].u_tx/a1 ),
    .A1(\g_wire[7].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[7].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[7].u_tx/_3_  (.A0(\g_wire[7].u_tx/o_p ),
    .A1(\g_wire[7].u_tx/o_n ),
    .S(clknet_leaf_4_clk),
    .X(tx_wire[7]));
 sg13g2_inv_1 \g_wire[7].u_tx/_4_  (.Y(\g_wire[7].u_tx/_1_ ),
    .A(clknet_4_3_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[7].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[7].u_tx/_0_ ),
    .Q(\g_wire[7].u_tx/o_p ),
    .CLK(clknet_4_3_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[7].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[7].u_tx/a0 ),
    .Q(\g_wire[7].u_tx/o_n ),
    .CLK(\g_wire[7].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[7].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[7]),
    .Q(\g_wire[7].u_tx/a0 ),
    .CLK(clknet_4_3_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[7].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[7]),
    .Q(\g_wire[7].u_tx/a1 ),
    .CLK(clknet_4_3_0_clk_regs));
 sg13g2_inv_2 \g_wire[8].u_rx/_1_  (.Y(\g_wire[8].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[8].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[8].u_rx/r0 ),
    .Q(rx_q0[8]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[8].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[8].u_rx/r1 ),
    .Q(rx_q1[8]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[8].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__08_),
    .Q(\g_wire[8].u_rx/r1 ),
    .CLK(\g_wire[8].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[8].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__08_),
    .Q(\g_wire[8].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[8].u_tx/_2_  (.A0(\g_wire[8].u_tx/a1 ),
    .A1(\g_wire[8].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[8].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[8].u_tx/_3_  (.A0(\g_wire[8].u_tx/o_p ),
    .A1(\g_wire[8].u_tx/o_n ),
    .S(clknet_leaf_1_clk),
    .X(tx_wire[8]));
 sg13g2_inv_1 \g_wire[8].u_tx/_4_  (.Y(\g_wire[8].u_tx/_1_ ),
    .A(clknet_4_13_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[8].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[8].u_tx/_0_ ),
    .Q(\g_wire[8].u_tx/o_p ),
    .CLK(clknet_4_13_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[8].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[8].u_tx/a0 ),
    .Q(\g_wire[8].u_tx/o_n ),
    .CLK(\g_wire[8].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[8].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[8]),
    .Q(\g_wire[8].u_tx/a0 ),
    .CLK(clknet_4_12_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[8].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[8]),
    .Q(\g_wire[8].u_tx/a1 ),
    .CLK(clknet_4_12_0_clk_regs));
 sg13g2_inv_2 \g_wire[9].u_rx/_1_  (.Y(\g_wire[9].u_rx/_0_ ),
    .A(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[9].u_rx/_2_  (.RESET_B(rst_n),
    .D(\g_wire[9].u_rx/r0 ),
    .Q(rx_q0[9]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[9].u_rx/_3_  (.RESET_B(rst_n),
    .D(\g_wire[9].u_rx/r1 ),
    .Q(rx_q1[9]),
    .CLK(rx_clk));
 sg13g2_dfrbpq_1 \g_wire[9].u_rx/_4_  (.RESET_B(rst_n),
    .D(clknet_1_0__leaf__09_),
    .Q(\g_wire[9].u_rx/r1 ),
    .CLK(\g_wire[9].u_rx/_0_ ));
 sg13g2_dfrbpq_1 \g_wire[9].u_rx/_5_  (.RESET_B(rst_n),
    .D(clknet_1_1__leaf__09_),
    .Q(\g_wire[9].u_rx/r0 ),
    .CLK(rx_clk));
 sg13g2_mux2_1 \g_wire[9].u_tx/_2_  (.A0(\g_wire[9].u_tx/a1 ),
    .A1(\g_wire[9].u_tx/a0 ),
    .S(sdr),
    .X(\g_wire[9].u_tx/_0_ ));
 sg13g2_mux2_1 \g_wire[9].u_tx/_3_  (.A0(\g_wire[9].u_tx/o_p ),
    .A1(\g_wire[9].u_tx/o_n ),
    .S(clknet_leaf_1_clk),
    .X(tx_wire[9]));
 sg13g2_inv_1 \g_wire[9].u_tx/_4_  (.Y(\g_wire[9].u_tx/_1_ ),
    .A(clknet_4_15_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[9].u_tx/_5_  (.RESET_B(rst_n),
    .D(\g_wire[9].u_tx/_0_ ),
    .Q(\g_wire[9].u_tx/o_p ),
    .CLK(clknet_4_15_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[9].u_tx/_6_  (.RESET_B(rst_n),
    .D(\g_wire[9].u_tx/a0 ),
    .Q(\g_wire[9].u_tx/o_n ),
    .CLK(\g_wire[9].u_tx/_1_ ));
 sg13g2_dfrbpq_1 \g_wire[9].u_tx/_7_  (.RESET_B(rst_n),
    .D(tx_d0[9]),
    .Q(\g_wire[9].u_tx/a0 ),
    .CLK(clknet_4_14_0_clk_regs));
 sg13g2_dfrbpq_1 \g_wire[9].u_tx/_8_  (.RESET_B(rst_n),
    .D(tx_d1[9]),
    .Q(\g_wire[9].u_tx/a1 ),
    .CLK(clknet_4_15_0_clk_regs));
endmodule
