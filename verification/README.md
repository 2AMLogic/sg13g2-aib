# verification

cocotb + Icarus benches. Needs `iverilog` and `cocotb` (2.x); no PDK, no klt.

    python3 verification/run_tb.py                                  # expect exit 0, 81/81
    python3 verification/run_tb.py --define INJECT_BUG_SHIFT_EDGE=1 # expect exit 1

Run it with plain `python3`, not `-I` (isolated mode hides a user-site cocotb).

Exit codes (same contract as the gf180-polysynth runner, DR-0015):
0 all passed, 1 the suite ran and a test failed, 2 the suite did not run.
A negative control must require exactly 1.

    python3 verification/run_tb.py --bench datapath --param N=20    # also N=8; expect exit 0, 8/8
    python3 verification/run_tb.py --bench datapath --define INJECT_EXTRA_STAGE=1   # expect exit 1

- `test_shift_redundancy.py`: T-05 `RTL` row, all 80 single-fault cases plus no-fault.
- `tb_top.v`: bench top with fault injection (X, stuck-0, stuck-1) on the wires.
- `test_datapath.py`: T-02, T-27, T-29 `RTL` rows. PRBS-7 round trips in DDR, SDR and L1
  (L1 with a decoy on `rx_wire`), mode switch, and the TX/RX cycle-accounting tests.
- `tb_datapath.v`: bench top; zero-delay wire, `rx_clk` = `clk` delayed a quarter cycle.

## `klt functional-verification` requests (`klt/`)

The same benches through the pinned `klt` (T1 item 5, digital): `shift_redundancy.json`
(T-05, 81 tests), `datapath_n20.json` and `datapath_n8.json` (T-02, T-03, T-27, T-29),
and the negative controls `neg_shift_edge.json` and `neg_extra_stage.json`, which must
exit 3. `klt/run_evidence.py` runs all of them plus the STA and writes the envelopes
to `signoff/attest/item5-digital/` (see `signoff/README.md`). The klt verdict comes
from `results.xml`; `run_tb.py` stays the quick local runner. Running klt directly
needs the extra: `uvx --from "klayout-tools[functional-verification]==$(cat signoff/KLT_VERSION)" klt functional-verification verification/klt/<name>.json -o <dir>`.
