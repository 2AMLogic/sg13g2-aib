# sg13g2-aib

A die-to-die parallel I/O channel in the class of the open Advanced
Interface Bus (AIB) Gen1 specification, published through CHIPS Alliance —
many short, unterminated, low-swing wires with a forwarded clock — on
[IHP SG13G2](https://github.com/IHP-GmbH/IHP-Open-PDK), a 130 nm SiGe
BiCMOS open PDK, designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools), xschem + ngspice
on the analog side and Yosys/OpenROAD on the digital side.

**Status: just opened, specification phase.** Nothing is designed yet.

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

## Target specification (DRAFT — engineering to ratify, see issue #1)

| Parameter | Target | Fallback | Stretch |
|---|---|---|---|
| Rate per wire | 1 Gb/s (DDR) | 500 Mb/s | 2 Gb/s |
| Channel width | 20 data + forwarded clock | 8 data + clock | 40 data |
| Signalling | unterminated, core-supply CMOS | — | reduced-swing below core supply |
| Channel model | a ratified short-reach RC/RLC model (few mm) | — | — |
| Skew | clock-to-data skew budget across the channel, ratified | — | — |
| Energy | ≤ 1 pJ/bit TX + RX (target, simulated) | ≤ 2 pJ/bit | ≤ 0.5 pJ/bit |
| Redundancy | spare wire per channel with muxing | none | — |
| Signoff | DRC + LVS clean, I/O column included | — | — |

Maturity ladder: spec ratified → I/O cell simulated across PVT → channel
simulated end to end over the channel model → I/O column DRC-clean →
assembled and LVS-clean → post-layout re-verification → shuttle seat →
measured silicon. **Current position: pre-spec.**

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
