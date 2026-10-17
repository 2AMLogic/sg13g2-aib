# spec

The specification for the `sg13g2-aib` canary: a die-to-die parallel I/O
channel in the class of the open AIB Gen1 specification, on IHP SG13G2.

**Status: ratified by the merge of the pull request that closes issue #2.**
Until that merge the tables below are a proposal. After it, a row changes only
through a new decision record that names the row and the evidence; an agent
does not relax a row to make a result pass (see `CLAUDE.md`).

**No conformance claim is made anywhere in this repo.** "AIB Gen1-class" names
the architecture the block follows. The public specification is used as a
reference: every parameter it defines is cited by section, none of its text or
figures is copied, and a value taken from it is a number with a section
reference, not a quotation.

## Index

| File | Holds |
|---|---|
| [`target-spec.md`](target-spec.md) | The ratified table: every parameter with target / fallback / stretch, verification method, PVT corners, AIB citation, scope tag |
| [`channel-model.md`](channel-model.md) | The declared die-to-die channel model, its parameters and provenance |
| [`channel/channel_rc.cir`](channel/channel_rc.cir) | The model as an ngspice subcircuit, the form the simulations include |
| [`test-configuration.md`](test-configuration.md) | What the shuttle part can exercise, and which rows each loopback covers |
| [`dll-interface.md`](dll-interface.md) | The forwarded-clock alignment requirement, compared against `2AMLogic/sg13g2-dll` |
| [`decisions/`](decisions/) | One decision record per choice, with the alternatives rejected |

## References (read for this spec)

| Short name | What | Pin |
|---|---|---|
| **AIB 1.2** | *Advanced Interface Bus (AIB) Specification*, Revision 1.2 (the Gen1 revision), `AIB_Specification 1_2.pdf` in `chipsalliance/AIB-specification` | commit `096a97006a1e46dbab51b4e16ca99e6193dd16cb` |
| **PDK** | IHP-Open-PDK `v0.3.0`, the pin in [`sim/pdk.json`](../sim/pdk.json) | `.fetched-version` of the install read: `0.3.0` |
| **PDK-proc** | `libs.doc/doc/SG13G2_os_process_spec.pdf`, Rev. 1.2 | in PDK `v0.3.0` |
| **PDK-lay** | `libs.doc/doc/SG13G2_os_layout_rules.pdf`, Rev. 0.4 (2024-12-19) | in PDK `v0.3.0` |
| **PDK-io** | `libs.ref/sg13g2_io/` (README, LEF, liberty corner files, SPICE) | in PDK `v0.3.0` |
| **PDK-esd** | `libs.tech/ngspice/models/sg13g2_esd.lib`, `sg13g2_bondpad.lib` | in PDK `v0.3.0` |
| **DLL canary** | `2AMLogic/sg13g2-dll` | `da166a6` (main HEAD on 2026-10-17) |

A section citation of the form "AIB 1.2 §4.1 Table 17" means that section of
that revision. The AIB specification has later revisions (2.0, AIB-O, 3D); this
spec follows 1.2 because "Gen1" is the target class. A later revision is not
read here.

## Conventions used by the tables

**Scope tag** (CLAUDE.md: keep the modeled channel and the test configuration
apart):

- **CH** holds for the *modeled die-to-die channel* ([`channel-model.md`](channel-model.md)).
  There is no assembly to measure it on; it is a simulation claim only.
- **TC** holds for the *test configuration* (on-die loopback, wire-bond
  loopback; [`test-configuration.md`](test-configuration.md)). It is what silicon
  could show.
- **BOTH** holds, with the same value, for both, and each is verified in its own
  setup.

A row tagged CH is never quoted as measured, and a row tagged TC is never quoted
as a channel claim.

**Verification method** codes:

| Code | Meaning |
|---|---|
| `SIM` | ngspice transient or DC/AC through `klt sim`, a multi-corner request |
| `SIM-MC` | as `SIM` with a `monte_carlo` request; the row is **statistical** and is reported as a mean, sigma and the tail used |
| `PEX` | `klt pex` re-simulation of the extracted layout |
| `LAYOUT` | `klt drc`, `klt lvs`, `klt extract`, or a geometric measurement of the layout |
| `RTL` | cocotb + Icarus functional verification |
| `ANALYSIS` | a derivation recorded in a decision record, no simulation |
| `MEAS` | silicon measurement; none exists before tape-out |

**PVT corners**: the set named *PVT-FULL* in [`target-spec.md`](target-spec.md).
