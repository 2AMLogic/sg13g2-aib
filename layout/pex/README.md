# layout/pex: `klt pex` for T1 item 7 (post-layout verification, analog)

Item 7's analog leg asks for the spec suite re-run against the netlist **extracted from the
layout**, reported as a per-corner, per-spec-row schematic-vs-extracted delta. `klt signoff`
accepts only one evidence kind for it — a `klt pex` JSON report — and rejects a passing
citation of any other kind, because a clean DRC or a pre-layout schematic sim says nothing
about post-layout behaviour.

## Status: `7.analog` is `unmet`. The extracted netlist cannot be simulated.

**Extraction works. The measurement does not.** `klt pex` extracts all four drawn I/O cells
cleanly, and the schematic leg of both benches here runs and reproduces item 5's committed
numbers. The **extracted** leg has never produced a single `delta[]` row: every corner of
every leg dies in ngspice before any analysis starts, because the extracted netlist writes the
pad/ESD antenna diode as a card the SG13G2 PDK has no model for. That is a defect in the tool,
not in this design or these benches, and there is no caller-side way around it (defect 2
below). Both defects are reproduced by a committed record and filed upstream.

**The deferred measurement is owned, not dropped.** Issue #81 closes with `7.analog` `unmet`;
submitting the committed 45-corner requests and recording `delta[]` once the tool is fixed is
tracked by **#226** (blocked by
[2AMLogic/klayout-tools#5491](https://github.com/2AMLogic/klayout-tools/issues/5491) and
[#5493](https://github.com/2AMLogic/klayout-tools/issues/5493)), which also owns the two
acceptance criteria #81 leaves unmet: the per-corner schematic/extracted/delta rows and T-24's
`PEX` leg. The upstream issues track the tool defects; #226 tracks this repo's re-run.

So this directory delivers the extraction evidence that does exist, the benches and requests
the campaign needs, and the reproduction of what blocks it. **No claim is made here about any
spec row's post-layout value.** Nothing in `spec/` is relaxed and no cell is changed.

| Row | Leg | Post-layout value | Why |
|---|---|---|---|
| T-06, T-07, T-08, T-11, T-24, T-28 | `dc-static`, both tops | **not measured** | defect 2 |
| T-01, T-09, T-15, T-16, T-18, T-26 | `channel-eye` | **not measured** | defect 2, and no bench yet (see "One extracted top per run") |
| T-17 | `clock-path` | **not measured** | same |

Item 5's own declared gaps (`T-02`, `T-04`, `T-05`, `T-12`, `T-20`, `T-21`, `T-25`, `T-29`)
are carried forward unchanged, with the same trackers: #216, #192, #193, #194, #195, #196,
#176. Nothing here measures them and nothing here closes them.

## The two defects

Both are reproduced by `records/20261113T130846Z/` (`run_pex.sh probe`), which runs each leg
twice for exactly this purpose. Both are present in the pinned grader `0.9.0`
(`signoff/KLT_VERSION`) **and** in the newest build on this host, `0.9.2.dev915+g513f88f6836d`,
so neither is fixed by a pin bump today.

### Defect 1 — `options.osdi_preload` is dropped when the backend is not named

*Filed as [2AMLogic/klayout-tools#5492](https://github.com/2AMLogic/klayout-tools/issues/5492).
Does not block this item: every committed
request here states its own `backend`, so the campaign never takes this path.*

When neither `--backend` is given nor the testbench request carries a `backend` field,
`klt pex` resolves the backend from `$KLT_SIM_BACKEND` (which this fleet exports as `batch`),
strips every `options.osdi_preload` entry as "the runner will resolve it" — and then runs the
deck on the **local** ngspice anyway (`environment.engine_host: "local"`). The generated
corner deck carries no `pre_osdi` line, so every PSP103 device is unknown and both legs die:

```
Warning: Model issue on line 232 :
  .model xtx_h.xesd.xmn1:sg13g2_lv_nmos_psp psp103va type=+1 level=103.60  ...
Unknown model type psp103va - ignored
...
Error on line 265 or its substitute:
  n.xtx_h.xesd.xmn1.nsg13_lv_nmos pad_h 0 0 0 xtx_h.xesd.xmn1:sg13g2_lv_nmos_psp w= ...
Unable to find definition of model xtx_h.xesd.xmn1:sg13g2_lv_nmos_psp
```

(`records/20261113T130846Z/aib_io_tx.envbackend.schematic.ngspice.log`.) Adding `--backend
local` to the same command emits the four `pre_osdi` lines and the leg passes — so the option
is understood, just discarded on one resolution path. `klt sim` run directly on the same
request always emits them, whatever the backend resolution.

### Defect 2 — the `sg13g2` deck writes `dantenna`/`dpantenna` as a `D` card the PDK cannot resolve

*Filed as [2AMLogic/klayout-tools#5491](https://github.com/2AMLogic/klayout-tools/issues/5491).
**This is what blocks item 7 for this block.***

The extracted netlist is otherwise fully simulatable: MOS devices come out as `X` calls to the
PDK subcircuits (`X$1 … sg13_lv_nmos L=0.35U W=2U AS=… PS=…`) and so do the poly resistors
(`X$134 … rppd l=2U w=2U`). The antenna diodes do not — they come out as bare `D` cards naming
a `.model`:

```
D$133 PAD__t0 VDDIO__t3 dpantenna A=20.25P P=18U
```

The SG13G2 ngspice PDK defines `dpantenna` (and `dantenna`) **only as a `.subckt`** —
`libs.tech/ngspice/models/diodes.lib`, a three-diode composite parameterised by `l`/`w`:

```
.subckt dpantenna 1 2
.params l=780n w=780n DEV_A=(l*w)/1p DEV_P=(l+w)/0.5u DEV_C=4
D1 1 2 dparea area=DEV_A
D2 1 2 dpperim area=DEV_P
D3 1 2 dpcorner area=DEV_C
.ends
```

There is no `.model dpantenna` anywhere in the PDK, so ngspice stops at netlist load:

```
Error on line 413 or its substitute:
  d.xtx_h.d$132 xtx_h.\$3__t1 xtx_h.vddio__t6 dpantenna a=4p p=8u
could not find a valid modelname
    Simulation interrupted due to error!
```

(`records/20261113T130846Z/aib_io_tx.named.extracted.ngspice.log`; the RX leg fails the same
way at its own line.) **Every** I/O cell this block draws contains `aib_pad_esd`, which is two
antenna diodes, so no top short of a diode-free cell avoids it — and there is no diode-free
cell, nor should there be.

`--device-model CLASS=SUBCKT` is the flag shaped for exactly this, and it refuses the class:

```
$ klt pex … --device-model dpantenna=dpantenna --extract-only
extraction failed: --device-model class 'dpantenna' is not a bipolar class of
deck 'sg13g2' (bindable classes: none)
```

#### What was considered and rejected

- **A `.model dpantenna d …` shim in the bench body.** ngspice would resolve the `D` card, and
  the schematic side would keep using the PDK `.subckt`, so both legs would run. Rejected: no
  single `.model` reproduces a three-diode area/perimeter/corner composite, so the two legs
  would model the ESD diode differently and every `delta[]` row — T-24 above all, which *is*
  the diode's capacitance — would report a hand-fitted model error as a parasitic effect. That
  is a worse outcome than no number.
- **`--measure-command` with a netlist rewritten from `D … A=,P=` back to `X … l=,w=`.** The
  inverse is exact (`A = w·l`, `P = 2(w+l)` ⇒ `w = l = 4.5 µm` and `2 µm`, matching
  `design/aib_pad_esd.spice`), so this would work and would produce rows. Rejected: it moves
  the measurement outside `klt pex`'s own testbench contract *and* silently simulates something
  other than the netlist the report pins by `extraction.netlist_sha256`. A citation whose
  provenance chain says "the extracted netlist" while the numbers came from a repo-side rewrite
  of it is not evidence this project should file.
- **Waiting for a pin bump.** The newest build has the same defect.

## Extraction model and what the numbers would and would not include

Quoted from the reports' own `extraction.model` field (`records/*/.*extract.report.json`), not
restated: the lumped-RC model is

- **capacitance** — net-to-ground for every net's own (non-coupled) area/perimeter, plus
  net-to-net for vertical-overlap coupling;
- **coupling** — vertical overlap (crossover) unconditionally; lateral (same-layer, sidewall)
  coupling **only** for a net pair naming a declared `--critical-net`, and these runs declare
  none (`extraction.critical_nets: []`), so no lateral coupling is modelled at all. Fringe
  shielding is not modelled;
- **resistance** — a single lumped series resistance per net, distributed as a star across that
  net's device terminals, not a per-segment RC ladder (`extraction.distributed_rc: false`);
- **frequency** — quasi-static: one frequency-independent R and C per net, no skin effect, no
  distributed transmission-line behaviour;
- **substrate** — tied to ground through 1e12 Ω, i.e. capacitively floating in transient
  analysis, DC reference only.

Any result this directory ever produces is therefore a **layout-extracted estimate, not
silicon**, and specifically one with no lateral coupling and no distributed RC. For the I/O
column that matters most where two pad nets run alongside each other over a 55 µm pitch — the
array-skew risk this canary names — so a future campaign should declare `--critical-net` on the
pad nets before any skew claim is made from it.

### `body_bias`: `biased`, checked, on all four cells

Every report here carries `body_bias.status: "biased"` with `unbiased_device_count: 0` and
empty `unbiased_nets` / `unbiased_pmos_body_nets`. That is the tool positively stating it
checked and found every device body on a DC bias path — distinct from a record that never
reported the field. No `--tie-net` is needed, and the "`klt signoff` renders `met` on an
unbiased netlist without grading it" hazard does not apply to these runs.

## One extracted top per run, and no cell holds both ends of a link

`klt pex` extracts **one** `--top` per run. The drawn cell tree is

```
aib_io_column > aib_io_column_tx / aib_io_column_rx
                  > aib_io_tx, aib_io_tx_clk (2 x aib_io_tx)
                  / aib_io_rx, aib_io_rx_clk (2 x aib_io_rx)
```

so no cell below the 48-unit column top contains both a TX and an RX. The `channel-eye` and
`clock-path` benches are **link** benches: they instantiate a transmitter, the declared channel
and a receiver in one netlist. Putting one behind a single extracted `--top` therefore means
extracting **one end at a time** — TX extracted against a schematic RX, then the reverse — and
a both-ends-extracted leg is not available from one `klt pex` run at all. Extracting the whole
column to get both ends in one top is 4320 devices over 45 corners of a 141 ns transient for no
new row coverage, and is not done.

That limitation is filed upstream as a generic gap,
[2AMLogic/klayout-tools#5493](https://github.com/2AMLogic/klayout-tools/issues/5493). It is the
second reason the two link families carry no bench here yet: with defect 2 blocking every
extracted leg, there is nothing to validate a link bench against, and committing an unexercised
one would be scaffolding presented as work. They stay declared gaps.

## Row split: the item 5 pin is not a pin this layout draws

`sim/dc-static/tb_pin.cir` models **one bidirectional pin** — pad/ESD, driver and receiver all
on the same node. No drawn cell is that. The column draws 24 TX pads (`aib_io_tx`: pad/ESD +
driver) and 24 RX pads (`aib_io_rx`: pad/ESD + receiver), each unidirectional, as an AIB-class
channel is. Post-layout the pin rows are therefore measured on the two pins that exist:

| Leg (`--top`) | Rows | Steps |
|---|---|---|
| `aib_io_tx` | T-06, T-08 (drive levels, output resistance), T-07 (pin leakage), T-28 (weak pulls), T-24 (pad capacitance at the TX pin) | `drv_nl`, `drv_ld`, `lk_{0,5,10}`, `pu_on`, `pd_on`, `cap_{0,5,10}` |
| `aib_io_rx` | T-07 (pin leakage), T-11 (receiver hysteresis), T-24 (pad capacitance at the RX pin) | `lk_{0,5,10}`, `cap_{0,5,10}`, `rx_up`, `rx_dn` |

`spec/target-spec.md` binds T-24 "at the receiver pin", so the `aib_io_rx` leg is its binding
one. T-28 is TX-only: the receiver cell has no weak pulls, so the two pull steps are dropped
from that leg rather than reported from a default state under a T-28 name
(`gen_pex_benches.py`, `MEASUREMENT_NEEDS`). This is a change of **measurement point**, never
of limit: every limit is imported unchanged from `sim/dc-static/gen_dc_static.py`, so the spec
bound stays the only threshold and no delta tolerance is invented.

### What the split already shows pre-layout (schematic leg, verified)

The schematic leg of both generated benches runs. At `tt / 1.200 V / 27 C` it reproduces item
5's committed record (`sim/dc-static/records/20261112T001207Z/report.json`) **exactly** for
every row whose circuit the merge does not change — T-06 (`8.559169e-08` V droop,
`1.446819e-07` V VOL), T-08 (`56.26209` / `52.69882` Ω), T-28 (`13340.54` / `13047.72` Ω) — which
is the check that the assembled DUTs are the same circuit item 5 measured.

Where it differs, it differs for a stated reason:

| Measurement | Item 5 (combined pin) | TX pad | RX pad |
|---|---|---|---|
| `t24_cpin_ff` (`cap_0` / `cap_5` / `cap_10`) | 81.7 / 91.1 / 87.2 fF | 76.9 / 78.4 / 83.2 fF | 33.5 / 41.0 / 33.4 fF |
| `t07_t28_ipin_a` (`lk_0`) | 2.63e-9 A | 2.59e-9 A | 4.80e-11 A |
| `t11_hyst_mv` | 0.00096 mV | — | 0.00084 mV |

Item 5's combined pin carries **one** ESD structure shared by a driver and a receiver; the two
drawn pads carry one each, which is why TX + RX exceeds the combined figure. **This is not a
post-layout result and is not cited as evidence** — it is the pre-layout value of the same
circuit at the pins the layout actually draws, and it says that T-24's pre-layout margin at the
real pins (76.9 fF and 33.5 fF against ≤ 100 fF) is wider than the 96.4 fF worst case item 5
records for the combined pin. Whether layout parasitics consume that margin is exactly the
question defect 2 prevents answering.

## Files

| File | What |
|---|---|
| `gen_pex_benches.py` | writes everything in `benches/`; `--check` fails on a stale file |
| `benches/<top>.dut.spice` | the simulatable assembly of one drawn cell: a `.subckt` with the pin list and order of `layout/lvs/<top>.ref.spice`, calling the item 1 cells, whose text is inlined verbatim from `design/`. One self-contained file, so the bench has exactly one `.include` |
| `benches/tb_dc_static_<top>.cir` | the bench body: that single `.include`, the supply, and this leg's stimulus |
| `benches/request_dc_static_<top>.json` | the `klt sim` request; corner grid, steps, measurement names and limits imported from `sim/dc-static/gen_dc_static.py`, never restated |
| `benches/extraction.json` | layout, deck, PDK, `--label-layer` roles and the per-top `--pins` list, in one machine-readable place both the script and the record read |
| `run_pex.sh` | `extract` / `probe` / `delta`; writes one append-only record per run |
| `records/<UTC>/` | append-only reports, `record.json`, and the ngspice log that names each failure |
| `test_pex_benches.py` | offline self-test of the invariants `klt pex` needs (one `.include`, DUT pins == LVS pins, node counts, row split, 45 corners, capacity wait) |

`layout/lvs/<top>.ref.spice` is the LVS **comparison** form — plain `M …/X …/D …` element cards
against device-class names (`nfet`, `rppd`, `dpantenna`). It is not simulatable, which is why
the schematic DUTs here are generated separately rather than reusing it.

## Records

| Record | Mode | What it establishes |
|---|---|---|
| `20261113T130842Z` | `extract` | extraction of all four drawn cells: device/net counts, `extraction.model`, `body_bias: biased`. Input hash is the **pre-#248** stream, superseded by `20261114T025329Z` below — history, not the cited evidence |
| `20261113T130846Z` | `probe` | the reproduction of both defects: `*.envbackend.*` (defect 1) and `*.named.*` (defect 2, with the schematic side passing) |
| `20261114T025329Z` | `extract` | the same extraction re-run after #248 regenerated `layout/aib_io_column.gds` for the DR-0016 spare placement: input hash = the committed stream. This is what `signoff/block-manifest.json` cites under 7.analog |

`20261114T025329Z` re-binds the extraction to the stream the repo ships, and in doing so
measures the claim #248 made in passing — that renaming 24 `TM1lbl` strings inside
`aib_io_column_tx`/`aib_io_column_rx` cannot move an extraction of the **unit** cells. It
cannot: each new `*.extract.report.json` differs from its `20261113T130842Z` predecessor in
exactly one field, `provenance.input.content_hash`. All four `extraction.netlist_sha256` are
unchanged, so is `extraction.pdk.version` (`fetched:0.3.0`), so are the device counts
(42/84/138/276) and net counts (6/10/17/29), and `benches/extraction.json` is byte-identical.
The `20261113T130846Z` probe record still binds the pre-#248 hash and is deliberately left
alone: it is never cited as 7.analog evidence, and what it establishes — an ngspice
netlist-**load** failure — is independent of the stream.

All three records are append-only. `20261113T130846Z`, the only one with a measurement leg and
so the only one that ran a request, keeps the request it ran with, which is **not** today's
committed request: #210 (merged after this branch was cut) paired the diode section with the
MOS corner in `sim/pvt_full.py` (#184), so regenerating `benches/request_dc_static_<top>.json`
moved `ss` to `dio_ss` and `ff` to `dio_ff`. The `tt` bundle — `mos_tt` / `res_typ` / `dio_tt` —
is byte-identical before and after that change, and `20261113T130846Z` narrowed the grid to the
single corner `tt / 1.200 V / 27 C` (`record.json` → `request_modifications`), so the schematic-leg
reproduction above was taken on the same corner bundle the table defines today. The record's
45-corner request differs from the committed one only at `ss` and `ff`, which this probe never
ran.

`--extract-only` reports carry `status: "not_checked"` and exit 4 by contract: they graded
nothing, which is a result, not a failure. Extracted device counts cross-check against the LVS
run that matched these cells — `aib_io_tx` 138, `aib_io_rx` 42, `aib_io_tx_clk` 276 (= 2 x 138),
`aib_io_rx_clk` 84 (= 2 x 42), and 24 x 138 + 24 x 42 = 4320, the figure
`layout/lvs/README.md` records for the whole column.

The `delta` campaign has **never been submitted to the batch fleet**. Both defects are failures
to *load* a netlist, so they are corner-independent: 45 corners x 2 legs x 2 sides of guaranteed
load failure would say exactly what the one-corner local probe says, at 180 times the cost and
on fleet capacity other sweeps need. When the tool is fixed, `run_pex.sh delta` submits the
committed 45-corner requests with `--backend batch --wait-for-capacity 600`; there is no local
loop and no fallback. That re-run is tracked by #226.

## Reproduce

From the repo root, with the pinned grader (`signoff/KLT_VERSION`) and `PDK_ROOT` set
(`sim/README.md`):

```bash
python3 -I layout/pex/gen_pex_benches.py --check   # benches are fresh
python3 -I layout/pex/test_pex_benches.py          # invariants hold (offline, PDK-free)

source sim/harness/env.sh
layout/pex/run_pex.sh extract                      # four extractions, local, ~4 s
layout/pex/run_pex.sh probe                        # both defects, one corner, local
layout/pex/run_pex.sh delta                        # the campaign -- blocked by defect 2
```

`run_pex.sh` refuses to overwrite a record directory and `--check`s the generator before it
runs anything. The first two commands are what CI runs (`scripts/ci/check_local.sh evidence`);
the rest need a PDK and are not CI-checked, the same arrangement as `layout/README.md`'s
generator.
