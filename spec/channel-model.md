# Channel model

The channel this block is designed for, as a model every channel simulation
includes. **It is declared, not measured.** No die-to-die assembly exists in any
test this repo can run (CLAUDE.md), so every claim tagged CH in
[`target-spec.md`](target-spec.md) rests on this file. If a parameter below is
wrong, those claims move with it.

AIB 1.2 gives no trace model: its electrical table has a *Trace* column of eye
width only (§4.1 Table 17), and the interposer is outside its scope. The model
is therefore this repo's own, chosen in [DR-0005](decisions/0005-channel-model.md).

## The model: `CH-3MM-RC`

Source: [`channel/channel_rc.cir`](channel/channel_rc.cir), subcircuit
`chan_rlc tx rx gnd`, ten uniform RLC pi-sections. A different tool must
reproduce the parameters below, not the netlist's topology.

| Parameter | Value (target model) | Fallback model `CH-1MM` | Stretch model `CH-5MM` | Provenance |
|---|---|---|---|---|
| Length | 3 mm | 1 mm | 5 mm | README "few mm"; AIB 1.2 does not fix a length |
| R per mm | 5.5 Ω/mm | 5.5 | 5.5 | **Anchored in the PDK**: TopMetal2 sheet resistance RSTM2 typ 11 mΩ/sq (min 7.5, max 14.5), PDK-proc §2.13, over a 2 µm wide line = 500 squares/mm |
| C per mm (to ground, includes neighbor coupling) | 0.20 pF/mm | 0.20 | 0.20 | **Declared.** An order-of-magnitude value for a few-µm wide line over a ground plane; not read from AIB 1.2 or any interposer vendor. The PDK gives only an *area* term for the on-die analogue: TopMetal2–TopMetal1 CATOPMET2 typ 13 aF/µm² (PDK-proc §2.17), i.e. about 26 fF/mm for a 2 µm line, before fringing and coupling. The declared 0.20 pF/mm is deliberately larger than that on-die area term |
| L per mm | 0.5 nH/mm | 0.5 | 0.5 | **Declared**, same status as C |
| Far-end load at the RX pin (everything the channel sees besides the line) | 0.1 pF | 0.1 | 0.1 | **Declared**: the T-24 target of 100 fF for the receiver input, pad and ESD together |
| Spread corners | R and C each ×0.8 and ×1.2 | same | same | **Declared**; R tracks the PDK RSTM2 min/max (−32 %/+32 %) in spirit only |
| Crosstalk | not modeled in this version | | | DR-0005; the C per mm is meant to include neighbor coupling to a quiet neighbor |

Everything marked *Declared* is an assumption this repo chose and labels as such.
A measured or vendor value supersedes it only through a new decision record.

## Derived quantities (arithmetic from the table, for review)

| Quantity | Value at 3 mm | Formula |
|---|---|---|
| Total R, C, L | 16.5 Ω, 0.60 pF, 1.5 nH | length × per-mm value |
| Characteristic impedance Z0 | 50 Ω | √(L/C) |
| Flight time | 10 ps/mm, 30 ps total | √(LC) × length |
| Total load on the driver | 0.70 pF | line C + far-end load |
| Source-match target (T-08) | 40–80 Ω | Z0 ± 40 % |

At a 100–300 ps edge the flight time (30 ps) is a small fraction of the edge, so
the channel behaves as an RC line with an inductance that matters mainly for
overshoot at the unterminated far end (T-09). That is why L is kept in the model
and not dropped.

A first check that the file parses and behaves: with a 60 Ω source, a 100 ps
edge and the `CH-3MM-RC` defaults, one `ngspice` run of the subcircuit gave a
50 %-point delay of about 8 ps across the line and no overshoot beyond the supply.
That run is a parse and sanity check, not recorded evidence, and sets no spec
value.

## What a result on this model does and does not claim

- A CH row measured on `CH-3MM-RC` holds for *that model*. It is not a statement
  about an interposer, a silicon bridge, or any real routing.
- The three models give a length sensitivity, and the ±20 % R and C corners a
  parameter sensitivity. A row that passes at 3 mm but fails at 5 mm is reported
  as such; the 5 mm stretch is not a requirement.
- Test-configuration results use [`test-configuration.md`](test-configuration.md)'s
  loads, not this model, and are labelled TC.
