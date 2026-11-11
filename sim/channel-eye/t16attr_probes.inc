* t16attr_probes.inc -- zero-crossing probes for the T-16 attribution (issue #161).
* Included LAST by tb_t16attr_*.cir. Each probe is node minus half its own supply, so every
* stage is timed at the same 50 % level the bench's `dsa` and `csig` use. Probes load nothing.
* Stages per lane: 0 stimulus (ideal driver), 1 TX cell output (txi), 2 TX pad (txp, after the
* TX ESD resistor), 3 RX-side pin after the link (rxa / rxc / rxcb).
Bqa0 qa0 0 V = v(da)       - 0.5*v(vdd_atx)
Bqa1 qa1 0 V = v(xa.txi)   - 0.5*v(vdd_atx)
Bqa2 qa2 0 V = v(xa.txp)   - 0.5*v(vdd_atx)
Bqa3 qa3 0 V = v(rxa)      - 0.5*v(vdd_arx)
Bqp0 qp0 0 V = v(dcp)      - 0.5*v(vdd_ctx)
Bqp1 qp1 0 V = v(xcp.txi)  - 0.5*v(vdd_ctx)
Bqp2 qp2 0 V = v(xcp.txp)  - 0.5*v(vdd_ctx)
Bqp3 qp3 0 V = v(rxc)      - 0.5*v(vdd_crx)
Bqn0 qn0 0 V = v(dcn)      - 0.5*v(vdd_ctx)
Bqn1 qn1 0 V = v(xcn.txi)  - 0.5*v(vdd_ctx)
Bqn2 qn2 0 V = v(xcn.txp)  - 0.5*v(vdd_ctx)
Bqn3 qn3 0 V = v(rxcb)     - 0.5*v(vdd_crx)
