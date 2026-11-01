"""Exhaustive single-fault sweep of the 20 + 2 shift-redundancy remap (T-05, RTL row).

Cases (DR-0016): 2 channel directions (ab, ba) x 20 fault positions = 40, plus
the no-fault case = 41 tests. For each, every data bit must reach the same
far-end output through TX remap -> wires (both vacated wires, `pos` and `pos + 1`,
forced to X, stuck-0 and stuck-1 in turn) -> RX remap. Mux function only (test
configuration).
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


async def _check(dut, link, en, pos, mask):
    other = "ba" if link == "ab" else "ab"
    _drive(dut, other, 0, 0, 0, 0)
    for mode in FAULT_MODES:
        dut.fmode.value = mode
        for d in PATTERNS:
            _drive(dut, link, en, pos, mask, d)
            await Timer(1, "ns")
            q = getattr(dut, f"q_{link}").value
            assert q.is_resolvable, f"{link} pos={pos} mode={mode}: unresolved bits in {q}"
            assert int(q) == d, (
                f"{link} pos={pos} mode={mode}: sent {d:05x} got {int(q):05x}"
            )


@cocotb.test()
async def no_fault(dut):
    # Every data wire (0..19) is healthy: spares carry nothing and no mask is applied.
    for link in ("ab", "ba"):
        await _check(dut, link, 0, 0, 0)


@cocotb.parametrize(link=("ab", "ba"), pos=tuple(range(20)))
async def single_fault(dut, link, pos):
    # The faulty wire is the one that carries data bit `pos` when there is no fault;
    # the repair vacates it and the next wire, and both are corrupted.
    await _check(dut, link, 1, pos, (1 << pos) | (1 << (pos + 1)))


single_fault = cocotb.test()(single_fault)
