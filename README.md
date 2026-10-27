# sg13g2-aib

A die-to-die parallel I/O channel in the class of the open Advanced
Interface Bus (AIB) Gen1 specification, published through CHIPS Alliance —
many short, unterminated, low-swing wires with a forwarded clock — on
[IHP SG13G2](https://github.com/IHP-GmbH/IHP-Open-PDK), a 130 nm SiGe
BiCMOS open PDK, designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools), xschem + ngspice
on the analog side and Yosys/OpenROAD on the digital side.

**Status: specification ratified; verification harness and RTL smoke in place.**
The spec ([`spec/target-spec.md`](spec/target-spec.md), ratified by #2) is the
reference. The data-path RTL and its cocotb benches exist; no analog I/O cell,
layout or channel simulation exists yet, and the T1 signoff record
([`signoff/`](signoff/README.md)) reads `unmet` for every item not yet cited.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using SG13G2, not just this repo.

## Why this block, on this node

Die-to-die links are the opposite of a SerDes. Instead of one fast lane over
a lossy channel, they use many slow wires over a channel of a few
millimetres: no termination, no equalization, no clock recovery — a
forwarded clock, simple CMOS drivers and receivers at reduced swing, and
tight skew between wires. The difficulty moves from the signal to the
array: per-wire area and capacitance, ESD at a level suited to an assembly
that never leaves the package, clock-to-data skew across a whole column of
I/O cells, and redundancy for wires that fail.

The open AIB specification gives the class a public definition to design
against. This repo pairs with `sg13g2-serdes` on the same PDK — die-to-die
and long-reach as the two ends of chip I/O — and it uses SG13G2's CMOS only;
no HBTs are needed for a channel this short.

## Scope

- **In scope**: the I/O cell (driver, receiver, ESD, pad) at a pitch the
  spec ratifies; a channel of N data wires plus forwarded clock; TX/RX
  data path and DDR capture; per-wire redundancy muxing; loopback and test
  modes; the column/array layout.
- **From a sibling**: forwarded-clock alignment and duty-cycle correction
  (a DLL). This repo has no `consumes:` edge yet; it specifies the DLL
  interface and does not design one. The SG13G2 DLL canary opened alongside
  this repo is the candidate.
- **Not in scope**: the AIB adapter layer and any protocol above the
  physical wires; the interposer or package.
- **Not claimed**: conformance with the AIB specification. "AIB Gen1-class"
  names the architecture this block follows.

## Target specification (ratified: [`spec/target-spec.md`](spec/target-spec.md), #2)

Headline rows only; the spec has the full set (T-01 to T-30), each with its
verification code, PVT scope and the AIB section it was read from. Results hold
for the modeled channel (CH) or for the test configuration (TC), never blurred:
see [`spec/test-configuration.md`](spec/test-configuration.md).

| Parameter (row) | Target | Fallback | Stretch |
|---|---|---|---|
| Rate per wire, DDR (T-01) | 1 Gb/s (500 MHz forwarded clock) | 500 Mb/s | 2 Gb/s |
| Data wires per direction (T-03) | 20 TX + 20 RX + forwarded clock | 8 + 8 | 40 + 40 |
| Spare wires (T-05) | 2 per channel, shift redundancy | none | — |
| Signalling (T-06) | unterminated, full-rail CMOS at VDDIO (1.2 V) | — | reduced swing |
| Channel model (T-12) | CH-3MM-RC, 3 mm RLC line ([`spec/channel-model.md`](spec/channel-model.md)) | CH-1MM | CH-5MM |
| Data-to-data skew at TX (T-13) | ≤ 0.04 UI | ≤ 0.08 UI | ≤ 0.04 UI |
| Data-to-clock skew at TX (T-14) | ≤ 0.02 UI | ≤ 0.04 UI | ≤ 0.02 UI |
| I/O cell pitch (T-22) | 55 µm | 80 µm | 40 µm |
| Energy per bit, TX + RX (T-26, simulated) | ≤ 1 pJ/bit | ≤ 2 pJ/bit | ≤ 0.5 pJ/bit |
| Signoff (T-30) | DRC + LVS clean, I/O column included | — | — |

Maturity ladder: spec ratified → I/O cell simulated across PVT → channel
simulated end to end over the channel model → I/O column DRC-clean →
assembled and LVS-clean → post-layout re-verification → shuttle seat →
measured silicon. **Current position: spec ratified; digital data-path
verification and PDK/synthesis smoke only.**

## Reproducing results

Every committed result comes from a command below, run from the repo root.
CI (`.github/workflows/ci.yml`) runs the PDK-free ones; the rest need the PDK,
ngspice or Yosys and run on a worker.

```bash
# RTL: cocotb + Icarus (pip install "cocotb>=2.0,<3"; iverilog on PATH)
python3 verification/run_tb.py                                   # shift redundancy, 81/81
python3 verification/run_tb.py --bench datapath --param N=20     # 8/8
python3 verification/run_tb.py --bench datapath --param N=8      # 8/8

# Evidence format and harness self-tests (no tools needed)
python3 -I scripts/ci/test_checkers.py
python3 -I scripts/ci/check_evidence_format.py

# Signoff record: pinned grader, byte-for-byte reproduction
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt signoff \
  --manifest signoff/block-manifest.json --format json | cmp - signoff/block-manifest.signoff.json
```

PDK fetch, OSDI models, the ngspice smoke and the Yosys synthesis smoke are in
[`sim/README.md`](sim/README.md); how the signoff record and the item 9 and 10
attestations are made and checked is in [`signoff/README.md`](signoff/README.md).
Simulated numbers (including energy per bit) are labelled as simulated.

## Repo layout

```
spec/          ratified spec + decision records
rtl/           channel data path, redundancy muxing, test modes
verification/  cocotb testbenches
design/        analog schematics (driver, receiver, ESD)
sim/           testbenches + PVT corner results (ngspice), channel studies
layout/        GDS + DRC/LVS reports, including the I/O column
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
