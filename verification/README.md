# verification

cocotb + Icarus benches. Needs `iverilog` and `cocotb` (2.x); no PDK, no klt.

Each bench is defined **once**, by its `klt functional-verification` request under
`klt/` — the same file the item 5 digital envelopes cite. `run_tb.py` takes one
request path and reads the sources, top, test module, parameters, defines,
timescale and seed from it, so there is no second copy to drift. With no
argument it runs `klt/shift_redundancy.json`.

    python3 verification/run_tb.py                                       # expect exit 0, 41/41
    python3 verification/run_tb.py verification/klt/neg_shift_edge.json  # expect exit 1

Run it with plain `python3`, not `-I` (isolated mode hides a user-site cocotb).

Exit codes (same contract as the gf180-polysynth runner, DR-0015):
0 all passed, 1 the suite ran and a test failed, 2 the suite did not run.
A negative control must require exactly 1.

    python3 verification/run_tb.py verification/klt/datapath_n20.json     # also _n8; expect exit 0, 8/8
    python3 verification/run_tb.py verification/klt/neg_extra_stage.json  # expect exit 1

`post_route.json` and `neg_post_route_timing.json` are the exception: they
annotate an SDF and name `@PDK_ROOT@`, so they need the PDK and the pinned klt.
`run_tb.py` refuses them with exit 2 (the suite did not run) rather than running
a half-configured bench; use `klt/run_evidence.py` for those.

Every other way a request can fail to load exits 2 as well: a missing file,
malformed JSON, and a request that parses but is the wrong shape (a missing or
wrong-typed field). That last one is why the loader validates rather than
indexing: a shape mistake in `neg_shift_edge.json` or `neg_extra_stage.json`
that exited 1 would satisfy the negative control with the bench never built.
`timescale` and `random_seed` are required for the same reason the flags are
gone -- a fallback literal in the runner would be a second copy of a value the
request is meant to be the only home for.

`test_run_tb.py` is the self-test for that contract (the whole wrong-shape
class; no cocotb needed for the loader cases), and
`testdata/wrong_shape_request.json` is the mis-authored negative control
`scripts/ci/check_local.sh` asserts exit 2 on end to end.

    python3 -I verification/test_run_tb.py

- `test_shift_redundancy.py`: T-05 `RTL` row, all 40 single-fault cases (20 positions x 2 channel directions) plus no-fault, with a TX bit-to-wire bijection check per position.
- `tb_top.v`: bench top with fault injection (X, stuck-0, stuck-1) on the wires.
- `test_datapath.py`: T-02, T-27, T-29 `RTL` rows. PRBS-7 round trips in DDR, SDR and L1
  (L1 with a decoy on `rx_wire`), mode switch, and the TX/RX cycle-accounting tests.
- `tb_datapath.v`: bench top; zero-delay wire, `rx_clk` = `clk` delayed a quarter cycle.

## `klt functional-verification` requests (`klt/`)

The same benches through the pinned `klt` (T1 item 5, digital): `shift_redundancy.json`
(T-05, 41 tests), `datapath_n20.json` and `datapath_n8.json` (T-02, T-03, T-27, T-29),
and the negative controls `neg_shift_edge.json` and `neg_extra_stage.json`, which must
exit 3. `klt/run_evidence.py` runs all of them plus the STA and writes the envelopes
to `signoff/attest/item5-digital/` (see `signoff/README.md`). The klt verdict comes
from `results.xml`; `run_tb.py` stays the quick local runner over the same request
files, and the CI `rtl` job runs all five through it. Running klt directly
needs the extra: `uvx --from "klayout-tools[functional-verification]==$(cat signoff/KLT_VERSION)" klt functional-verification verification/klt/<name>.json -o <dir>`.
