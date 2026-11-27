# DR-0030: adopt `diodevdd_2kv` as the primary pad diode; T-25 SIM leg at the 0.5 A pulse

**Status**: proposed; ratified by the merge of the pull request that carries it
(DR-0001, issue #196). The device choice itself is the operator ruling of 2026-11-18
(`/fleet:decide` round 20261118-r16, q210, option (a)) recorded at the top of issue #196;
this record states what was adopted and what the transient must show.
**Numbering**: written as DR-0029; renumbered DR-0030 when `main` took DR-0029 for the T-12
conformance leg. The immutable record `sim/esd-transient/records/20261119T085126Z/` still
says DR-0029 in its copied bench. **Review**: the EE-key review of 2026-11-22 requested
changes; "Review round 1" below records what changed.
**Rows**: T-16, T-22, T-24, T-25. **Amends**: nothing. No spec row or limit changes.
T-24 is *held at its fallback column* for this cell by the ruling, as DR-0008 §2 requires
("the fallback applies by a new decision record, not a quiet relaxation"); the spec's
column definitions are unchanged.

## Context

DR-0017 closed T-24 at 96.4 fF by shrinking the primary diode to a 4.5 µm × 4.5 µm
`dpantenna`, and stated the cost: that device is an antenna diode with about 8.5 kΩ of
series resistance at 4.5 µm × 4.5 µm (20 µm²), so it cannot carry the T-25 discharge
credibly. (The secondary `XDp2` is the 2 µm × 2 µm `dpantenna`: from `diodes.lib`
`DEV_A=4, DEV_P=8, DEV_C=4` its series resistance is about 27 kΩ, more than 3× higher.) DR-0018
measured the PDK pad diodes (`sg13g2_esd.lib`) and found the pair cannot close at the
target: with `diodevdd_2kv` as `XDp1`, T-24 is 108.9 fF worst case against the 100 fF
target — inside the 200 fF fallback, outside the target. DR-0018 named the two fallbacks,
each needing its own decision: the PDK `sg13g2_io` cells at 80 µm pitch, or a lower T-25
target. The #337 study (PR merged 2026-11-19, `sim/io-cell-study/records/20261118T213945Z/`)
measured the PDK cells and found no bidirectional cell meets even the 200 fF fallback at
the AIB signalling biases (112.9-195.4 fF for the 4 mA/16 mA cells, 265 fF for the 30 mA
cell), so the numbers went back to the operator beside option (a). The ruling adopted
option (a): `diodevdd_2kv` at 55 µm, T-24 at its fallback column.

The #251 sizing study (`sim/channel-eye/records/20261118T220000Z-t16-sizing/`) had already
run the diode question for T-16: candidate **K02** — `diodevdd_2kv` as `XDp1` at the
committed `XResd` (`w=2u l=1u`) and `XMn1` (`w=20u ng=10`) — screens at a 22.07 ps T-16
worst margin at the declared ±20 % C spread, against S07's 21.70 ps for the antenna diode
(the same netlist that closed T-24 at the target). The study states the conclusion holds
whichever diode #196 selects.

## Decision

1. **Adopt `diodevdd_2kv` as `XDp1`** (anode PAD, cathode VDDIO, the PDK `sg13g2_esd.lib`
   subcircuit instantiated at its shipped `DEV_A=35`), in the committed
   `design/aib_pad_esd.sch` / `.spice`. Nothing else changes: `XResd` stays `w=2u l=1u`
   (#251). The `l=2u` in `design/aib_pad_esd_2kv.spice` is **not** promoted — that file
   predates the #251 shortening (its header says it is evidence only), and the #251 study
   measured the adopted configuration as K02, at the committed 1 µm.
2. **Columns held.**
   - **T-22 at 55 µm (target column).** The cell stays in the 55 µm class; the PDK I/O
     cells at 80 µm are rejected by the study's numbers and the ruling.
   - **T-24 at its fallback column (≤ 200 fF).** Worst case **110.89 fF** on the promoted
     netlist with the #398 receiver (`sim/dc-static/records/20261123T211634Z/`, 45 corners,
     pad at VDDIO, `ss/1.080V/125C`; 97.57 fF at VDDIO/2, 91.84 fF at 0 V). The earlier
     108.92 fF figure (DR-0018's 45-corner run `sim/dc-static/records/20261110T084631Z/`,
     VDDIO/2 bias, binding corner `fs/1.320V/125C`; the #251 candidate table repeats it)
     was measured on the pre-#398 receiver and is superseded. The 100 fF target column is
     **not met**, and the evidence rows still grade the 100 fF limit, so it is a recorded
     failure; that is the ruling's stated cost. `spec/channel-model.md` (T-12) defines the
     channel's 0.1 pF far-end load from T-24's 100 fF target; **that tie is not reconciled
     here** (the T-12 conformance and channel-eye records use 0.1 pF) and is a follow-up. The
     extraction is a model small-signal estimate, no bond pad, no PEX (unchanged caveat).
   - **T-25's `SIM` leg** is answered by the transient below; its verdict is recorded in
     the Result section and the T-22/T-24 columns above are unaffected by it. T-25's
     CDM-voltage half stays unmeasurable (no ESD tester access; `MEAS` is not planned)
     and no CDM level is claimed from a transient.
   - **T-16**: the K02 screen margin is 22.07 ps at the declared spread. The full
     PVT-FULL × spread re-run of the channel benches **on the promoted netlist** is a
     follow-up issue: the #251 finalist validation at PVT-FULL (180/180) ran on the
     antenna-diode netlist (S07), not on K02.
3. **Model check, with its stated test.** The transient below credits two conduction
   models and no others:
   - `diodevdd_2kv` (`sg13g2_esd.lib`): a ngspice level-1 diode with `rs = 289.6/35 ≈
     8.3 Ω` series resistance and **a reverse-breakdown representation stated in the
     card** (`bv = 11.81`, `ibv = 4.744e-016`) — this traces the question DR-0018 left
     open. The forward conduction at 0.5 A is the credited path; the breakdown is not
     exercised (the pad never goes 11.8 V below VDDIO in this bench).
   - `sg13_lv_nmos` (PSP103, `XMn1`/`XMclamp`, grounded gate): PSP103 represents the
     forward drain-body junction conduction natively, and the **gate-grounded snapback
     path is not credited and is not verified** — whether this PSP103 build would
     represent avalanche sustain is not traced. The VSS-side and rail-clamp paths are
     therefore credited only through their junction diodes.
   - The stated test: the `mc_dio_fwd`, `mc_dio_fwd_novdd` and `mc_xmn1_neg` steps of
     the bench measure the first sweep voltage at which each credited path carries 0.5 A,
     on the same PDK model cards at the sizes the committed netlist uses. Expectations
     from the model cards: the diode at 0.5 A sits near a junction knee (≈ 1.1 V) plus
     `I × rs` (≈ 4.1 V), i.e. ≈ 5.2 V above its cathode rail, consistent with DR-0008's
     "3-4 V by ohmic loss alone"; `XMn1`'s junction is a power-junction-scale device with
     a ≈ 1.7 V drop at 0.5 A. Values in this range confirm the models conduct credibly at
     0.5 A; a divergence, a convergence failure or a non-physical I-V would be stated in
     the record and the transient verdict would go back to the operator with both numbers.
     (The transient reports no direct `XMn1` branch current: the PSP103 OSDI build
     exposes no device-current vector, and a mirrored sense device on the pad node would
     be a second, parallel discharge path changing the transient it claims to measure.
     XMn1's conduction is evidenced by the `mc_xmn1_neg` sweep against the transient's
     own pad-voltage trough and recovery.)
4. **The pulse, fixed before the run.** A triangular current pulse forced into PAD:
   0.5 A peak (T-25's discharge current, AIB 1.2 §4.3 Table 19 at 55 µm), 200 ps rise,
   400 ps fall, ≈ 400 ps at half amplitude, one event per polarity, the other polarity
   50 ns away so both fit one transient per supply state. **Source**: T-25 names the CDM
   class (DR-0008); a field-induced CDM pulse is sub-nanosecond (JEDEC JESD22-C101
   class), and the exact tester waveform is not reproducible in SPICE — the class shape
   is used, with the peak matched to the row's 0.5 A. Both polarities run with VDDIO
   powered (1.20 V) and unpowered (held at 0 V by the bench source — a stiff discharged
   rail; a floating-rail CDM with package capacitance is not modeled).
5. **The pass bounds, fixed before the run.** At the nominal corner (mos_tt, 1.20 V,
   27 °C; T-25's grid column is `n/a`, so this is a single-configuration bench):
   - **Positive pulse: peak `|V(PAD)|` ≤ 7.0 V.** DR-0008's first-order arithmetic puts
     the ohmic drop across the pad diode at 0.5 A at 3-4 V; DR-0018's measured forward
     resistance (8.4-8.6 Ω at 0.12-0.13 A overdrive, about 12 Ω chord at 3 V) plus the
     ≈ 1.1 V junction knee at 0.5 A gives a predicted peak near `VDDIO` + knee +
     `I × rs` ≈ 6.2 V. 7.0 V is that prediction plus about 1 V; failing high means the
     declared path is not carrying the discharge.
   - **Negative pulse: peak `|V(PAD)|` ≤ 3.0 V.** The declared path is `XMn1`'s
     drain-body junction; the expected drop at 0.5 A is ≈ 1.7 V (a power-junction-scale
     forward drop, corroborated by `mc_xmn1_neg`); 3.0 V is the expectation plus about
     0.5 V.
   - **Peak `|V(PADI)|` ≤ 3.5 V, either polarity.** The secondary stage (`XDp2`,
     `XMn2`) behind `XResd` must absorb the isolation; 3.5 V is the primary drop's
     magnitude at this pulse plus headroom above the receiver rail.
   - **Protected branch: peak `|I(PADI)|` ≤ 0.05 A (10 % of the pulse), either
     polarity.** Source: circuit arithmetic, **corrected in review round 1**: `XResd`
     (`w=2u l=1u`) is 0.5 square (130 Ω at 260 Ω/sq) plus two contacts (35 Ω·µm / 2 µm
     each, 35 Ω) ≈ 165 Ω, not 260 Ω; into the 0 V ammeter the branch current is
     `V(pad_ti)/R_esd` with `V(pad_ti)` including the rail and the diode knee (≈ 2.25 V),
     so ≈ 37 mA (7.4 % of the pulse) was the right expectation, not ≈ 2 %. The 0.05 A
     bound is unchanged.
   - **Recovery: `|V(PAD)|` 1 ns after its crest ≤ 40 % of its own peak, either
     polarity.** The node must discharge through the clamp path, not sit at its peak:
     `τ = R_path · C_node` with `R_path` from DR-0018's measured forward resistance
     (≈ 8.5 Ω diode, ≈ 4.3 Ω junction) and `C_node` from T-24 (≈ 110 fF) is ≈ 0.5 ns,
     so 1 ns is about 2 time constants and the excess above the conduction knee decays
     to ≈ 14 %; the knee itself is ≈ 12 % of the positive peak, so ≈ 25 % of the peak is
     expected and 40 % bounds it.
   These bounds are stated here before the run and are not edited after it. If the
   transient fails any bound, the record is committed as it ran and the measurement goes
   back to the operator via `loom-daemon operator-decision apply`; T-25 is not relaxed
   and no bound is changed to fit.
6. **The record.** `sim/esd-transient/` (bench, request, one immutable record directory,
   labelled simulated) holds the run. `MEAS` is not planned (no ESD tester access is in
   scope), so the simulated result is the only evidence this row's `SIM` leg can carry.

## Result

Two records exist; the bench changed between them (review round 1), and both stand as
committed (append-only).

**First record, `sim/esd-transient/records/20261119T085126Z/` (ESD subcircuit alone).**
Superseded as the cited evidence by the second: the DUT omitted the tristated driver and the
receiver, so it could not show the driver's drain-well diodes sharing the pulse through
`XRsp`/`XRsn`, nor the receiver's gate load on PADI. Its numbers (pad 6.385/5.186 V
positive, PADI 6.359/5.161 V) are kept as history.

**Cited record, `sim/esd-transient/records/20261123T211728Z/` (whole I/O cell: ESD cell +
tristated `aib_tx_data` on PAD + `aib_rx_data` on PADI; klt exit 3: a result).** The bounds
of §5 are unchanged and were not edited after either run. **T-25's `SIM` leg fails its
pre-stated bound, on the receiver-node isolation:**

- Peak `|V(PADI)|`, positive pulse: **5.131 V powered / 3.910 V unpowered** against 3.5 V:
  both fail. The secondary stage `XDp2` (2 µm antenna diode, ≈ 27 kΩ) does not conduct, so
  PADI follows the pad through `XResd` within the 600 ps pulse. The negative pulse passes
  (1.341 / 1.005 V, `XMn2`'s junction).
- Peak `|V(PAD)|` with the driver attached: 5.158 / 3.937 V positive (bound 7.0), 1.668 /
  1.667 V negative (bound 3.0). These are **lower** than the ESD-only 6.385 / 5.186 V
  because the driver's PMOS drain-well diode shares the current through `XRsp`; they
  confirm the first run's isolated bench was not representative. **They are model
  self-consistency numbers, not a survivability result**: see "Review round 1".
- Protected-branch current ≤ 0.030 A (bound 0.05): pass. Recovery ratio ≤ 0.290 (bound
  0.40): pass. Model-check sweeps unchanged (6.39 V / 5.19 V / −1.73 V).

Per the fail branch: T-25 is not relaxed, no bound was edited after the run, and the
measurement returns to the operator (`loom-daemon operator-decision apply`) with the choice
a passing secondary clamp implies — a conducting `XDp2` costs T-24 (about 26-34 fF more on
the receiver pin, on top of 110.89 fF, before bond-pad or PEX parasitics) and re-opens
T-16's sizing (it loads `C_PADI` behind `XResd`). The adoption in §1 is unaffected: it is
the operator's ruling.

## Review round 1 (EE-key, 2026-11-22): what changed and what did not

- **Provenance / DUT**: the transient bench now carries the tristated driver and the
  receiver; the new record has no home-directory path in `environment.ngspice_binary`, and
  `run_esd_transient.sh` scrubs it for later runs. *Fixed.*
- **Derivations corrected in this record**: binding T-24 corner (`fs/1.320V/125C`, not
  `fs/1.080V/125C`), `XDp2` series resistance (≈ 27 kΩ), `XResd` (≈ 165 Ω) and the
  `I(PADI)` expectation (≈ 37 mA, 7.4 %). *Fixed.*
- **Circular pad-side bounds**: the 7.0 V / 3.0 V pass bounds were derived from the same
  level-1 diode card that is then simulated, and the pad node sits directly on `XMn1`
  (`sg13_lv_nmos`, `BVDSSN013` 2.0 V min / 2.7 V target in `SG13G2_os_process_spec.pdf`
  Rev. 1.2 §2.1) and on the driver's thin-oxide devices; the PSP103 OSDI build has no
  avalanche or snapback, so ngspice carries 5 V across them without breaking down. The
  bounds are **not edited** (they were fixed before the run), but their "pass" verdicts are
  **model self-consistency only**, report-only in the `gf180-io-ring` DR-0006 sense; this
  record does **not** claim the pad survives 0.5 A. The 3.5 V PADI bound is the only one
  tied to a device limit (receiver gate oxide, `V_GS` ≤ 1.65 V at 125 °C). *Disputed as to
  editing a bound after a run; the verdict wording is corrected.*
- **T-24 relaxation**: the operator ruling (q210) holds T-24 at the fallback column; an
  agent does not overrule it and the spec is unchanged. The evidence rows keep grading the
  100 fF limit, so the failure is recorded, not hidden; the stale `dpantenna` record is no
  longer cited. The T-12 far-end-load tie is stated above as unreconciled. *Disputed (a
  ruling, not an agent decision); stale citation fixed.*
- **T-22 pitch, layout and LVS**: not re-derived. The drawn layout predates the promoted
  netlist and the reference netlists are regenerated, not re-LVSed (#435); no signoff
  reading is claimed for this cell. *Still open (follow-up).*
- **T-16 at PVT-FULL** on the promoted netlist: still the screen only. *Still open
  (follow-up).*
- **Other cited records are stale against the promoted netlist**: `main`'s channel-eye,
  clock-path and Monte Carlo records were run with `design/aib_pad_esd.spice` sha256
  `4de31ffa…`; the promoted netlist is `3cb704eb…`. They are allowlisted in
  `scripts/ci/netlist_closure_allowlist.json`, each naming the re-run follow-up.
- **Item 9 inventory**: it lists only the PDK smoke bench by design (no sim family is
  listed); extending it is outside this PR. *Disputed.*

## What is not shown

- **No `MEAS`.** No CDM voltage level is claimed: a 0.5 A transient is not a CDM
  classification, and the "2kv" library naming is not equated with CDM (DR-0008).
- **No `LAYOUT` current-path check.** The `klt` half of T-25 (clamp + diode area and
  current-path width) is not run here.
- **No ESD rules in the DRC deck** (`2AMLogic/klayout-tools#3854`): a passing transient
  does not sign off the ESD structure; it answers the 0.5 A discharge question only.
- **The snapback path is neither credited nor verified** (§3): the PSP103 build's
  avalanche/snapback behaviour is not traced, so the VSS-side and rail-clamp conduction
  the record reports is junction conduction only.
- **Ideal rails.** VDDIO is a stiff bench source at 1.20 V or 0 V: no bond-wire or
  package inductance, no floating-rail charge sharing; the L·di/dt overshoot a real CDM
  event adds at the pad is not modeled (no PDK bond-pad model exists, DR-0008).
- **Single nominal corner.** T-25's grid column is `n/a`; the run is one configuration
  (mos_tt, 1.20 V, 27 °C). Corner spread on the transient is not measured.
- **The receiver input is assumed high-impedance.** The floating-PADI configuration
  models the `aib_rx_data` gate; a real gate leak or a receiver-side ESD path of its own
  would change the `V(PADI)` excursion the record reports.
- **T-16 at PVT-FULL on the promoted netlist** is a follow-up (K02 was screened at the
  spread corners, not validated at PVT-FULL); the committed layout is stale against the
  netlists (#435) and stays stale by this record.

## Effects on other work

- The LVS reference netlists under `layout/lvs/` are regenerated from the sources in the
  PR that carries this record (they are derived, and CI checks them fresh); the **actual
  LVS re-run, the drawn layout and the I/O-column regeneration are follow-up issues**
  (#435), as DR-0018 already anticipated.
- Channel-eye, T-09 and T-16 re-runs on the new netlist are follow-up issues.
- `design/aib_pad_esd_2kv.spice` stays as committed (evidence for DR-0018); its stale
  `l=2u` is documented here and in `design/README.md`.
- The dc-static family's *next* nominal run will pick up the promoted netlist through
  `design/aib_pad_esd.spice`; its committed records are append-only and keep the
  antenna-diode T-24 evidence they were run with.
