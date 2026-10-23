"""Exhaustive single-fault sweep of the 20 + 2 shift-redundancy remap (T-05, RTL row).

Cases: 2 channel directions (ab, ba) x 2 shift directions x 20 fault positions
= 80, plus the no-fault case = 81 tests. For each, every data bit must reach
the same far-end output through TX remap -> wires (faulty wire forced to X,
stuck-0 and stuck-1 in turn) -> RX remap. Mux function only (test configuration).
"""

import cocotb
from cocotb.triggers import Timer

PATTERNS = [0x00000, 0xFFFFF, 0xAAAAA, 0x55555] + [1 << i for i in range(20)] + [0xFFFFF ^ (1 << i) for i in range(20)]
FAULT_MODES = (0, 1, 2)  # X, stuck-0, stuck-1


def _drive(dut, link, en, direction, pos, mask, d):
    getattr(dut, f"en_{link}").value = en
    getattr(dut, f"dir_{link}").value = direction
    getattr(dut, f"pos_{link}").value = pos
    getattr(dut, f"fmask_{link}").value = mask
    getattr(dut, f"d_{link}").value = d


async def _check(dut, link, en, direction, pos, mask):
    other = "ba" if link == "ab" else "ab"
    _drive(dut, other, 0, 0, 0, 0, 0)
    for mode in FAULT_MODES:
        dut.fmode.value = mode
        for d in PATTERNS:
            _drive(dut, link, en, direction, pos, mask, d)
            await Timer(1, "ns")
            q = getattr(dut, f"q_{link}").value
            assert q.is_resolvable, f"{link} dir={direction} pos={pos} mode={mode}: unresolved bits in {q}"
            assert int(q) == d, (
                f"{link} dir={direction} pos={pos} mode={mode}: sent {d:05x} got {int(q):05x}"
            )


@cocotb.test()
async def no_fault(dut):
    # Every data wire (1..20) is healthy: spares carry nothing and no mask is applied.
    for link in ("ab", "ba"):
        await _check(dut, link, 0, 0, 0, 0)


@cocotb.parametrize(link=("ab", "ba"), direction=(0, 1), pos=tuple(range(20)))
async def single_fault(dut, link, direction, pos):
    # The faulty wire is the one that carries data bit `pos` when there is no fault.
    await _check(dut, link, 1, direction, pos, 1 << (pos + 1))


single_fault = cocotb.test()(single_fault)
