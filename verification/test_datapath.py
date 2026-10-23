"""DDR/SDR serializer, deserializer and L1 loopback (T-02, T-27, T-29, RTL rows).

PRBS-7 round trips in DDR, SDR and L1 are bit-exact, and are deliberately
latency-agnostic (the lag is searched, not asserted) so that only the cycle
accounting tests fail when a pipeline stage is added. The latency tests count
clock edges: 1 UI = one edge = half a forwarded-clock cycle, and T-27's
1.5 cycles each way is 3 UI. TX is counted from the edge that loads the TX
input register to the UI where the bit starts on the wire; RX from the edge
that samples a word's first bit to the edge that loads the RX output register.
The channel is a zero-delay wire and rx_clk is clk delayed a quarter cycle
(tb_datapath.v), so this is the test configuration, not the modeled channel.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

PERIOD_NS = 10
BUDGET_UI = 3  # T-27: 1.5 cycles each way
PRBS_LEN = 127
CYCLES = 3 * PRBS_LEN
MAX_LAG = 6


def prbs7(seed=0x7F):
    """x^7 + x^6 + 1, period 127."""
    s = seed
    while True:
        bit = ((s >> 6) ^ (s >> 5)) & 1
        s = ((s << 1) | bit) & 0x7F
        yield bit


def wire_streams(n):
    """Per wire a PRBS-7 stream at its own phase, so no two wires carry the same bits."""
    streams = []
    for i in range(n):
        g = prbs7()
        for _ in range((i * 13) % PRBS_LEN):
            next(g)
        streams.append(g)
    return streams


def pack(bits):
    return sum(b << i for i, b in enumerate(bits))


_clock = None


async def start(dut, sdr=0, l1=0, decoy=0):
    global _clock
    if _clock is not None:
        _clock.cancel()
    _clock = cocotb.start_soon(Clock(dut.clk, PERIOD_NS, unit="ns").start())
    dut.sdr.value = sdr
    dut.l1.value = l1
    dut.decoy.value = decoy
    dut.ext_en.value = 0
    dut.ext_wire.value = 0
    dut.tx_d0.value = 0
    dut.tx_d1.value = 0
    dut.rst_n.value = 0
    await Timer(3 * PERIOD_NS, "ns")
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def round_trip(dut, n, sdr, l1):
    """Send CYCLES PRBS-7 words, collect the RX output each cycle, return the matched lag."""
    streams = wire_streams(n)
    sent, got = [], []
    for _ in range(CYCLES + MAX_LAG):
        d0 = [next(s) for s in streams]
        d1 = [0 if sdr else next(s) for s in streams]
        sent.append((pack(d0), pack(d1)))
        dut.tx_d0.value = sent[-1][0]
        dut.tx_d1.value = sent[-1][1]
        await RisingEdge(dut.rx_clk)
        await Timer(1, "ns")
        assert dut.rx_q0.value.is_resolvable and dut.rx_q1.value.is_resolvable, "unresolved RX output"
        got.append((int(dut.rx_q0.value), int(dut.rx_q1.value)))

    def matches(lag):
        words = [(s, g) for s, g in zip(sent, got[lag:])][PRBS_LEN:CYCLES]
        return all(s[0] == g[0] and (sdr or s[1] == g[1]) for s, g in words)

    lags = [lag for lag in range(MAX_LAG + 1) if matches(lag)]
    assert len(lags) == 1, f"round trip is not bit-exact at a single lag (matching lags {lags})"
    return lags[0]


async def check_mode(dut, sdr, l1):
    n = len(dut.tx_d0)
    # L1 must ignore rx_wire: it carries the inverse of the TX wire.
    await start(dut, sdr=sdr, l1=l1, decoy=l1)
    lag = await round_trip(dut, n, sdr, l1)
    dut._log.info(f"N={n} sdr={sdr} l1={l1}: PRBS-7 x {CYCLES} words bit-exact, lag {lag} cycles")


@cocotb.test()
async def ddr_round_trip(dut):
    await check_mode(dut, sdr=0, l1=0)


@cocotb.test()
async def sdr_round_trip(dut):
    await check_mode(dut, sdr=1, l1=0)


@cocotb.test()
async def l1_round_trip_ddr(dut):
    await check_mode(dut, sdr=0, l1=1)


@cocotb.test()
async def l1_round_trip_sdr(dut):
    await check_mode(dut, sdr=1, l1=1)


@cocotb.test()
async def l1_ignores_rx_wire(dut):
    # With l1 = 0 the same decoy wire corrupts the round trip, so the l1 tests above
    # prove the select and not a decoy that happens to be harmless.
    n = len(dut.tx_d0)
    await start(dut, sdr=0, l1=0, decoy=1)
    try:
        await round_trip(dut, n, 0, 0)
    except AssertionError:
        return
    assert False, "decoy rx_wire did not corrupt the round trip with l1 = 0"


@cocotb.test()
async def mode_switch(dut):
    # DDR then SDR then DDR on the same instance, reset between runs.
    n = len(dut.tx_d0)
    for sdr in (0, 1, 0):
        await start(dut, sdr=sdr)
        await round_trip(dut, n, sdr, 0)


async def tx_latency_ui(dut, slot, sdr):
    """UI from the edge that loads the TX input register (E0) to the marker on every wire."""
    full = (1 << len(dut.tx_d0)) - 1
    await start(dut, sdr=sdr)
    await FallingEdge(dut.clk)
    dut.tx_d0.value = 0 if slot else full
    dut.tx_d1.value = full if slot else 0
    await RisingEdge(dut.clk)  # E0
    dut.tx_d0.value = 0
    dut.tx_d1.value = 0
    for ui in range(9):
        if ui:
            await dut.clk.value_change
            await Timer(1, "ns")
        if int(dut.tx_wire.value) == full:
            return ui
    assert False, "marker never appeared on the wire"


async def rx_latency_ui(dut, slot):
    """UI from the rx_clk edge sampling the word's first bit (E0) to the RX output register."""
    full = (1 << len(dut.tx_d0)) - 1
    await start(dut)
    dut.ext_en.value = 1
    await FallingEdge(dut.rx_clk)
    dut.ext_wire.value = 0 if slot else full  # first bit, stable through E0
    await RisingEdge(dut.rx_clk)  # E0
    await Timer(1, "ns")
    dut.ext_wire.value = full if slot else 0  # second bit, stable through E1
    for ui in range(9):
        if ui:
            await dut.rx_clk.value_change
            await Timer(1, "ns")
            dut.ext_wire.value = 0
        if int(dut.rx_q0.value) | int(dut.rx_q1.value):
            assert int(dut.rx_q1.value if slot else dut.rx_q0.value) == full, "marker landed in the wrong slot"
            return ui
    assert False, "marker never reached the RX output register"


@cocotb.test()
async def latency_ddr(dut):
    tx = max([await tx_latency_ui(dut, slot, 0) for slot in (0, 1)])
    rx = max([await rx_latency_ui(dut, slot) for slot in (0, 1)])
    print(f"LATENCY mode=ddr n={len(dut.tx_d0)} tx_ui={tx} rx_ui={rx} budget_ui={BUDGET_UI}")
    assert tx <= BUDGET_UI, f"TX sequential latency {tx} UI exceeds {BUDGET_UI} UI (T-27)"
    assert rx <= BUDGET_UI, f"RX sequential latency {rx} UI exceeds {BUDGET_UI} UI (T-27)"


@cocotb.test()
async def latency_sdr(dut):
    tx = await tx_latency_ui(dut, 0, 1)
    print(f"LATENCY mode=sdr n={len(dut.tx_d0)} tx_ui={tx} budget_ui={BUDGET_UI}")
    assert tx <= BUDGET_UI, f"TX sequential latency {tx} UI exceeds {BUDGET_UI} UI (T-27)"
