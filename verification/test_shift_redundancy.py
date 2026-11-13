"""Exhaustive single-fault sweep of the 20 + 2 shift-redundancy remap (T-05, RTL row).

DR-0016 layout: wires 0..19 carry bits 0..19, wires 20/21 are the two spares, and a
fault at `pos` moves bits pos..19 up two wires. Cases: 2 channel directions (ab, ba)
x 20 fault positions = 40, plus the no-fault case = 41 tests. For each, every data bit
must reach the same far-end output through TX remap -> wires (faulty wire forced to X,
stuck-0 and stuck-1 in turn) -> RX remap, and the TX bit-to-wire map must be a
bijection that avoids the faulty wire `pos` and the wire `pos + 1`. Mux function only
(test configuration).
"""

import cocotb
from cocotb.triggers import Timer

PATTERNS = [0x00000, 0xFFFFF, 0xAAAAA, 0x55555] + [1 << i for i in range(20)] + [0xFFFFF ^ (1 << i) for i in range(20)]
FAULT_MODES = (0, 1, 2)  # X, stuck-0, stuck-1


def _drive(dut, link, en, pos, mask, d):
    getattr(dut, f"en_{link}").value = en
    getattr(dut, f"pos_{link}").value = pos
    getattr(dut, f"fmask_{link}").value = mask
    getattr(dut, f"d_{link}").value = d


def _expected_wire(k, en, pos):
    return k + 2 if (en and k >= pos) else k


async def _check_map(dut, link, en, pos):
    """Bit-to-wire map read from the TX wires (one-hot probes), not the round trip."""
    dut.fmode.value = 1
    seen = {}
    for k in range(20):
        _drive(dut, link, en, pos, 0, 1 << k)
        await Timer(1, "ns")
        w = getattr(dut, f"w_{link}").value
        assert w.is_resolvable, f"{link} pos={pos} bit={k}: unresolved TX wires {w}"
        wv = int(w)
        assert wv != 0 and wv & (wv - 1) == 0, f"{link} pos={pos} bit={k}: drives {wv:022b}, not exactly one wire"
        seen[k] = wv.bit_length() - 1
    wires = list(seen.values())
    assert len(set(wires)) == 20, f"{link} pos={pos}: bit-to-wire map is not injective: {seen}"
    assert all(0 <= x <= 21 for x in wires), f"{link} pos={pos}: wire outside 0..21: {seen}"
    if en:
        assert pos not in wires and pos + 1 not in wires, (
            f"{link} pos={pos}: a bit lands on the faulty wire {pos} or the vacated wire {pos + 1}: {seen}"
        )
    for k, x in seen.items():
        assert x == _expected_wire(k, en, pos), f"{link} pos={pos}: bit {k} on wire {x}, expected {_expected_wire(k, en, pos)}"


async def _check(dut, link, en, pos, mask):
    other = "ba" if link == "ab" else "ab"
    _drive(dut, other, 0, 0, 0, 0)
    await _check_map(dut, link, en, pos)
    for mode in FAULT_MODES:
        dut.fmode.value = mode
        for d in PATTERNS:
            _drive(dut, link, en, pos, mask, d)
            await Timer(1, "ns")
            q = getattr(dut, f"q_{link}").value
            assert q.is_resolvable, f"{link} pos={pos} mode={mode}: unresolved bits in {q}"
            assert int(q) == d, f"{link} pos={pos} mode={mode}: sent {d:05x} got {int(q):05x}"


@cocotb.test()
async def no_fault(dut):
    # Every data wire (0..19) is healthy: spares carry nothing and no mask is applied.
    for link in ("ab", "ba"):
        await _check(dut, link, 0, 0, 0)
        _drive(dut, link, 0, 0, 0, 0xFFFFF)
        await Timer(1, "ns")
        assert (int(getattr(dut, f"w_{link}").value) >> 20) == 0, f"{link}: spare wires driven with no fault"


@cocotb.parametrize(link=("ab", "ba"), pos=tuple(range(20)))
async def single_fault(dut, link, pos):
    # The faulty wire is `pos`, the wire that carries data bit `pos` when there is no fault.
    await _check(dut, link, 1, pos, 1 << pos)


single_fault = cocotb.test()(single_fault)
