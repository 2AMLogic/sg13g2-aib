# verification

cocotb + Icarus benches. Needs `iverilog` and `cocotb` (2.x); no PDK, no klt.

    python3 verification/run_tb.py                                  # expect exit 0, 81/81
    python3 verification/run_tb.py --define INJECT_BUG_SHIFT_EDGE=1 # expect exit 1

Run it with plain `python3`, not `-I` (isolated mode hides a user-site cocotb).

Exit codes (same contract as the gf180-polysynth runner, DR-0015):
0 all passed, 1 the suite ran and a test failed, 2 the suite did not run.
A negative control must require exactly 1.

- `test_shift_redundancy.py`: T-05 `RTL` row, all 80 single-fault cases plus no-fault.
- `tb_top.v`: bench top with fault injection (X, stuck-0, stuck-1) on the wires.
