# verification

cocotb + Icarus benches. Needs `iverilog` and the pinned `klt` with the
functional-verification extra (which brings cocotb 2.x); no PDK.

Each bench is defined **once**, by its `klt functional-verification` request under
`klt/` -- the same file the item 5 digital envelopes cite -- and is run by the same
pinned klt (`signoff/KLT_VERSION`) that graded that evidence. There is no second
reader of the request schema.

    K="uvx --from klayout-tools[functional-verification]==$(cat signoff/KLT_VERSION) klt"
    env -u PDK_ROOT $K functional-verification verification/klt/shift_redundancy.json -o <dir>   # exit 0
    env -u PDK_ROOT $K functional-verification verification/klt/datapath_n20.json -o <dir>       # also _n8; exit 0
    env -u PDK_ROOT $K functional-verification verification/klt/neg_shift_edge.json -o <dir>     # exit 3
    env -u PDK_ROOT $K functional-verification verification/klt/neg_extra_stage.json -o <dir>    # exit 3

Exit codes: 0 all tests passed, 3 the suite ran and a test failed, 1 the bench did
not build. A negative control must require exactly 3: a request that does not
build exits 1, so it can never satisfy a control without the bench running.
`scripts/ci/check_local.sh rtl` runs all five this way (`KLT=klt` to use a klt on
PATH instead of fetching the pin); the CI `rtl` job installs the pinned klt with the extra.

- `test_shift_redundancy.py`: T-05 `RTL` row, all 40 single-fault cases (20 positions x 2 channel directions) plus no-fault, with a TX bit-to-wire bijection check per position.
- `tb_top.v`: bench top with fault injection (X, stuck-0, stuck-1) on the wires.
- `test_datapath.py`: T-02, T-27, T-29 `RTL` rows. PRBS-7 round trips in DDR, SDR and with
  the datapath's `l1` loopback select on (with a decoy on `rx_wire`), mode switch, and the
  TX/RX cycle-accounting tests. The `l1` path is the **digital** select only and is not the
  L1 electrical path of `spec/test-configuration.md` (DR-0019). The electrical benches
  in `sim/channel-eye/` hold TX enables high. Per-group checks remain open (#446).
- `tb_datapath.v`: bench top; zero-delay wire, `rx_clk` = `clk` delayed a quarter cycle.

## `klt functional-verification` requests (`klt/`)

The same benches through the pinned `klt` (T1 item 5, digital): `shift_redundancy.json`
(T-05, 41 tests), `datapath_n20.json` and `datapath_n8.json` (T-02, T-03, T-27, T-29),
and the negative controls `neg_shift_edge.json` and `neg_extra_stage.json`, which must
exit 3. `klt/run_evidence.py` runs all of them plus the STA and writes the envelopes
to `signoff/attest/item5-digital/` (see `signoff/README.md`). The klt verdict comes
from `results.xml`, and the CI `rtl` job runs all five through the same klt.
