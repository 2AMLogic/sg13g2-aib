# Test configuration

What the shuttle part can actually exercise, and which rows of
[`target-spec.md`](target-spec.md) each setup covers. The modeled channel
([`channel-model.md`](channel-model.md)) does not exist in any test this repo can
run: a shuttle die is packaged by wire bond. Two loopbacks stand in for it, and
neither is the channel. Decision: [DR-0009](decisions/0009-test-configuration-and-loopbacks.md).

## The two loopbacks

### L1: on-die loopback

A TX pin drives an RX pin of the *same die* through an on-die route. The route
is a TopMetal2 line sized to emulate `CH-3MM-RC`: R within ±20 % of the model
(the PDK anchor, RSTM2, is what the model's R is built on) and total C brought
within ±20 % of the model by extracted-capacitance check (`klt extract` or
`klt pex`) and, if the route alone is short of it, an added explicit
capacitor. The cells at both ends are the real I/O cells, with their real pad
(if any) and ESD structures, so the capacitance at the pin is the one T-24
specifies.

- Stimulus and observation are on-die: a PRBS generator and an error counter
  (RTL, #3), plus a controllable sampling-clock phase. The analog eye is *not*
  observable; the observable is an error count versus phase, supply and
  temperature (a shmoo), which gives the capture window T-20 directly.
- Nothing on this path leaves the die, so L1 carries no package ESD exposure
  and no bond-wire inductance.
- **L1 is the better test of the I/O cell** (driver, receiver, ESD load, array
  skew), and is the setup the spec relies on for TC claims about the cell.

### L2: wire-bond loopback

A TX bond pad goes through a bond wire, package trace and a second bond wire
to an RX bond pad. This is what is available when the loopback must leave the die
(for example to be driven or probed from the board).

The PDK has no bond-pad model: `sg13g2_bondpad` is a placeholder subcircuit with
no electrical content in PDK `v0.3.0`, and no package data is in this repo. So the
L2 model is declared. These inputs are **assumptions, to be replaced by package
data when the packaging for the shuttle is known**:

| Quantity | Declared value | Note |
|---|---|---|
| Bond wire | 2 nH per wire (about 2 mm of wire) | two wires in the loop: 4 nH |
| Pad + package + board stub C per pin | 0.5 pF | five times the T-24 target |
| Resulting loop | series L 4 nH, C of 0.25 pF in series (two 0.5 pF ends) | resonates near 5 GHz: 1/(2π√(4 nH × 0.25 pF)) ≈ 5.0 GHz |
| Damping with a 40–80 Ω driver | Q of about 2 | a second-order estimate, `ANALYSIS`; `SIM` replaces it |

A second-order response with Q ≈ 2 overshoots by tens of percent, well above
the 0.25 × VOS limit of T-09. **L2 is expected to violate T-09 and to load the
driver and the receiver far more than the channel does.** That is a property of
the configuration, recorded here, and not a reason to relax T-09 or to change
the cell to pass L2.

## Which rows each setup covers

`yes` = the row is verified in that setup and holds for it; `report` = measured
and reported, but it is **not** a claim about the channel and is never quoted
as one; `no` = the setup cannot exercise it.

| Row | Parameter | CH (model) | L1 | L2 |
|---|---|---|---|---|
| T-01 | Rate per wire | yes (`SIM`) | yes (error-free at the rate) | report (loaded channel) |
| T-02 | DDR format | yes | yes | yes |
| T-03 | Wire count | yes | the subset the seat holds | the pads the package allows |
| T-04 | Quasi-differential clock | yes | yes | report |
| T-05 | Spare wires, redundancy | repair claim in simulation | **mux function only** (no real open or short exists) | mux function only; a deliberately opened or shorted wire is not part of this repo's test |
| T-06, T-07, T-08 | Levels, termination, driver impedance | yes | yes | report |
| T-09 | Overshoot | yes | yes | **expected to fail; reported** |
| T-10, T-11 | Receiver threshold, hysteresis | yes (`SIM-MC`) | yes (statistically, across the array) | yes |
| T-12 | Channel model | CH only | no: L1 emulates it, it is not it | no |
| T-13, T-14 | TX skew | yes | **yes: the on-die array skew, observed through the shmoo** | report |
| T-15, T-16 | RX-input skew | CH only (the channel adds it) | no direct observation | no |
| T-17 | Clock duty cycle | yes | indirect (shmoo asymmetry) | report |
| T-18 | Far-end eye | CH only | no (error count, not eye) | no |
| T-19, T-20 | Capture aperture, sampling margin | yes | **yes: measured as the shmoo window** | report |
| T-21 | Clock alignment | interface contract | whatever alignment hardware is on the seat; the DLL is a sibling | no |
| T-22, T-23 | Pitch, area | yes (layout) | yes | yes |
| T-24 | Pad + ESD capacitance | yes | yes | report (bond pad dominates) |
| T-25 | ESD protection level | n/a | none planned | none planned (no tester access in scope) |
| T-26 | Energy per bit | simulated | not measured by this repo's plan | not measured |
| T-27, T-28 | Latency, tristate/pulls | yes | yes | yes |
| T-29 | Test modes | n/a | defined here | defined here |

## What no test in this repo can show

- Behavior over a real interposer or bridge: its true R, C, L, crosstalk, and the
  skew of unequal route lengths.
- That the redundancy scheme repairs a real open or short.
- The ESD level (T-25): no measurement is planned.
- Any energy figure from silicon: T-26 is simulated only.

## Maturity

A row's maturity is the weakest evidence it has. A CH row has at most simulation
evidence on a declared model; a TC row can reach silicon, and then it is labeled
with the loopback that produced it (L1 or L2).
