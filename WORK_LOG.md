# Work Log

Chronological record of merged PRs and closed issues. Maintained by the Guide role.

### 2026-11-23

- **Issue #398** (in progress): adopt the supply-referenced RX input stage for the `aib_rx_data` data lanes — receive split landed (`aib_rx_inv` carries the committed inverter for the clock legs), T-10 passes on the adopted cell (0/5400 out), layout/DRC/LVS/PEX re-attested, T-19 recorded as the adoption's failing row (#190 tracks the output-stage fix)
- **PR #391**: mc: re-run T-15/T-16 Monte Carlo on the current cells; both rows pass the 7-sigma gate
- **Issue #385** (closed): T1 item 6 (analog): re-run the T-15 / T-16 Monte Carlo campaigns on the current cells — the cited failing records predate two resizes
- **PR #421**: chore(sim): remove the closed T-16 attribution scaffolding
- **Issue #420** (closed): Hoist duplicated PWL stimulus helpers into sim/gen_common.py
- **Issue #418** (closed): Remove the closed T-16 attribution scaffolding from sim/channel-eye (record is self-contained)
- **PR #417**: fix(ci): fail CI when a record deck's .include stops resolving
- **PR #416**: fix: pin content_hash on every pinnable evidence citation in the signoff manifest
- **PR #413**: evidence: re-cite item 5 analog records re-run on the post-e47bb80 pad cell
- **PR #412**: chore(sim): remove the closed T-16 sizing-study scaffolding
- **PR #410**: feat(ci): check cited sim records' netlist closures against the tree
- **PR #399**: evidence(sim): screen and confirm a supply-referenced RX input stage for T-10
- **Issue #415** (closed): signoff/block-manifest.json: 18 of 37 evidence entries carry no content_hash pin
- **Issue #414** (closed): Record bench decks' .include paths are staging-dir-relative, so archived decks can silently stop resolving
- **Issue #411** (closed): Remove the completed #251 T-16 sizing-study scaffolding (12 files, 2576 lines)
- **Issue #408** (closed): T1 item 5 (analog): re-run the cited dc-static, channel-eye and clock-path records on the current cells — each cites aib_pad_esd at its pre-e47bb80 hash
- **Issue #405** (closed): No CI check binds a cited analog record's netlist_closure to the tree, so a design/*.spice change silently staleness-es cited evidence
- **Issue #386** (closed): T-10: receiver threshold fails Monte Carlo on systematic corner shift (8 of 45 corner means outside +-60 mV) — sizing study for the aib_rx_data input stage

### 2026-11-22

- **PR #409**: test: guard test_checkers SUITES and loading against check_local.sh
- **PR #404**: refactor: split scripts/ci/test_checkers.py into four sibling suites
- **Issue #406** (closed): Nothing asserts test_checkers.py's SUITES matches check_local.sh, and no CI job runs the aggregator
- **Issue #401** (closed): Split monolithic scripts/ci/test_checkers.py (2,635 lines) into focused sibling suites
- **PR #402**: docs: correct the Resd PolyRes coordinates in layout/README.md
- **Issue #394** (closed): Correct the Resd PolyRes coordinates recorded in layout/README.md (#387 regeneration)
- **PR #390**: fix(layout,ci): draw Resd at the netlist l=1u and check the device table in CI
- **Issue #387** (closed): layout: the committed I/O column still draws Resd 2 um x 2 um while design/aib_pad_esd.spice is l=1u — regenerate before the item 7 delta campaign

### 2026-11-21

- **PR #393**: feat(sim,signoff): add the T-12 channel-model conformance bench and cite its record
- **Issue #384** (closed): T-12: give the channel-model row a gradable SIM leg (conformance bench for spec/channel/channel_rc.cir) so item 5 / analog can reach met

### 2026-11-20

- **PR #389**: refactor: share the T-16 edge selection and drop the card re-parse in gen_t16attr
- **Issue #388** (closed): Share the T-16 edge selection and remove the SPICE card parser from gen_t16attr
- **PR #382**: docs: fix stale 8-gap count in signoff/README and date the item-5 grader probes
- **Issue #380** (closed): signoff/README.md still says "8 real gaps" for item 5 / analog after DR-0026 and DR-0028 cut the row set to 18/5
- **Issue #379** (closed): Guide docs tick still stages README.md without re-attesting item 10: #284's guard diagnoses the round trip but does not prevent it

### 2026-11-19

- **PR #365**: docs: date DR-0017/DR-0018 staleness prose and retire #140 as the live layout tracker
- **Issue #362** (closed): design/README.md and DR-0017 cite closed #140 as the live tracker for a layout regeneration that e47bb80 made stale again
- **PR #337**: evidence(sim): study the PDK sg13g2_io pad cells against T-24 and T-08
- **PR #371**: check_inventory_klt_pin: compare each ngspice pin to the newest smoke record
- **PR #370**: docs(spec): drop T-05's SIM leg and leave the analog row set (DR-0028)
- **PR #369**: signoff: enforce each inventory's klt pin against its envelope's grader version
- **Issue #368** (closed): Item 9 analog: committed smoke record 20261119T000247Z ran ngspice-47 while the inventory pins ngspice-46
- **Issue #333** (closed): Remove T-05’s standalone SIM leg from analog signoff and preserve its timing evidence
- **Issue #324** (closed): item9-digital inventory pins klt 0.8.0 while its envelope is produced by 0.9.0 (unchecked pin drift)
- **PR #364**: docs: signoff README item 5 gap paragraph counts four pending, two standing gaps
- **PR #363**: docs: restate the ruled #251 T-16 margin question in sim/README.md
- **PR #358**: docs: align signoff/README gap count and tracker list with the manifest; record the ruled #251 decision in ROADMAP
- **Issue #360** (closed): signoff/README.md:144 still says five of the six analog gaps are pending and T-05 is the only standing gap (the manifest says two are standing)
- **Issue #359** (closed): Residual pending-form #251 mentions in sim/README.md after the operator ruling
- **Issue #352** (closed): Residual post-DR-0026 gap-count and closed-tracker citations in signoff/README.md (and ROADMAP.md's #251 bullet)
- **PR #356**: docs: retire T-12's #193 tracker in the three narrative READMEs
- **PR #355**: chore: drop the drifted generated finalist sizing request (request_t16sz_fin_S07.json)
- **PR #353**: signoff: describe T-12's closed trackers (#193, #251) in past tense in both gap strings
- **PR #349**: docs: align item-5 gap prose with the manifest after DR-0026
- **Issue #354** (closed): T-12's tracker is still #193 in three narrative docs after PR #353 corrects the manifest (the #350/#352 scope seam)
- **Issue #351** (closed): Remove sim/channel-eye/request_t16sz_fin_S07.json: unguarded generated request that has drifted from its generator
- **Issue #350** (closed): T-12's declared-gap tracker in block-manifest.json is a closed issue (#193), and its named follow-up #251 is closed too
- **Issue #347** (closed): Live #216 T-05 tracker citations remain outside the signoff/ sim/ spec/ grep scope (layout/pex/README.md, ROADMAP.md)
- **PR #343**: signoff: repoint T-05 standing-gap tracker to #333
- **PR #345**: refactor(sim): read OpenVAF pins from build-osdi.sh --print-pins, drop restated copy
- **Issue #261** (closed): Stop restating the OSDI pins in sim/pdk.json: one of the two copies is wrong about who reads it

### 2026-11-18

- **PR #342**: fix(clock-path): scope clk-pair parser to top-level instances and positional model
- **PR #339**: fix(pdk): name run_smoke.sh as a consumer in the osdi_toolchain _comment
- **Issue #340** (closed): check_clk_pair.py's netlist parser reads .subckt bodies as top-level instances and mis-parses models with trailing parameters
- **PR #338**: spec: grade T-04's clk/clkb arrangement on the clock-path netlist, not RTL
- **PR #335**: docs(verification): drop unenforced pass counts from klt snippet
- **PR #332**: feat(design): shorten aib_pad_esd XResd to 1u for T-16 margin
- **PR #331**: docs: drop unenforced bench pass counts from README repro snippet
- **PR #329**: ci(rtl): assert expected test counts for positive klt benches
- **PR #328**: docs(spec): drop the SIM leg from T-02 and T-04 and leave the analog row set
- **PR #325**: refactor: run RTL benches through the pinned klt, remove local cocotb runner
- **PR #323**: fix(sim): drop runner_version_check warn override from request generators
- **PR #322**: chore: remove superseded Yosys smoke generator, re-attest item 9
- **PR #321**: docs(spec): add DR-0025 recording sibling results as T-21 SIM evidence
- **PR #320**: chore(sim): remove unrecorded channel-eye positive-control bench
- **Issue #334** (closed): Unenforced bench pass counts survive in verification/README.md after #330
- **Issue #330** (closed): README repro snippet carries a second, unenforced copy of the bench pass counts
- **Issue #327** (closed): T-04 RTL leg is not graded under item 6 digital partition
- **Issue #326** (closed): check_local.sh rtl asserts only klt's exit code, not the pass counts its own labels claim
- **Issue #251** (closed): T-16 margin falls to 1.3 ps at the declared +20 % channel C (passes, but the +-20 % spread eats 9.5 of its 10.9 ps)
- **Issue #245** (closed): Remove verification/run_tb.py: run the cocotb benches through the pinned klt functional-verification the evidence already uses
- **Issue #241** (closed): Remove the batch runner_version_check "warn" override from the five request generators
- **Issue #220** (closed): Remove the channel-eye positive-control bench: its TX copy no longer matches design/aib_tx_data.spice
- **Issue #216** (closed): Item 5 / analog can never read `met` while T-02 and T-04 are by-design standing gaps
- **Issue #213** (closed): Remove sim/rtl-synth/run_synth.sh: the Yosys smoke is superseded by klt synthesize (keep its record)

### 2026-11-17

- **PR #316**: ci: cover layout/pex records in the structural evidence check and clean up run_pex.sh aborts
- **PR #314**: fix(pex): stop run_pex.sh recording a klt usage error as a result
- **Issue #315** (closed): layout/pex records are append-only frozen but never structurally checked: a partial records/<stamp>/ with no record.json is committable

### 2026-11-15

- **PR #311**: ci: guard the inline sha256-formula duplication class under scripts/ci
- **PR #309**: ci: catch empty-directory and gitignored writes in the strict-flag refusal test
- **PR #308**: ci: fail check_attested_paths on zero checked paths and require the declared hash_algorithm
- **PR #306**: fix: verify evidence per-path pins without gating on the aggregate hash
- **PR #305**: docs: re-point closed klayout-tools#5493 citations to open gap #5494
- **PR #303**: ci: extend the manifest_pins guard to the scripts/ci generators
- **PR #300**: fix: tolerate a request with no measurements; add --allow-empty-rows
- **PR #298**: docs: state the graded T1 signoff status in the README, checked against the record
- **PR #296**: ci: derive the strict-flag and freshness test subjects from tracked gen_*.py discovery
- **PR #288**: ci: fail fast when a hash-bound attested path drifts from its envelope
- **PR #268**: docs: roadmap as of 2026-11-13
- **Issue #304** (closed): The inline-sha256-formula duplication class under scripts/ci has no guard
- **Issue #307** (closed): The strict-flag write assertion cannot see a gitignored or empty-directory write
- **Issue #301** (closed): check_evidence_pins.py: a multi-source record with no aggregate content_hash skips its per-path pins entirely
- **Issue #299** (closed): check_attested_paths.py: make its own assumptions loud (zero-paths-checked, declared hash_algorithm)
- **Issue #292** (closed): The manifest-pin consolidation guard does not cover gen_*.py: a generator can regrow a private sha()
- **Issue #287** (closed): layout/pex/README.md cites klayout-tools#5493 as an open blocker, but it closed 2026-11-13 (docs-only); the live capability gap is #5494
- **Issue #284** (closed): Guard against docs PRs that edit README.md without re-attesting T1 item 10
- **Issue #281** (closed): run_dc_static.sh esd-diode leg cannot write a record: a KeyError today, and #267's empty-rows refusal once that is fixed
- **Issue #270** (closed): README status and maturity-ladder position contradict the committed signoff record
- **Issue #266** (closed): Derive the strict-flag test's generator set in test_checkers.py: the hand-kept allowlist cannot contain a failing generator
- **PR #297**: ci: check every cited evidence record binds the shipped stream
- **Issue #273** (closed): Pin content_hash on stream-bound signoff evidence so a stale input binding fails a gate
- **PR #295**: ci: fail when a tracked record file is matched by an ignore rule
- **Issue #263** (closed): Add a CI check that no tracked evidence file is silently ignored
- **PR #293**: mc: per-corner reading of the failing T-10, T-15 and T-16 MC records
- **Issue #269** (closed): Monte Carlo: add a per-corner reading of the failing T-10, T-15 and T-16 records (klt yield pools the 45 corners)
- **PR #291**: fix: gen_specs.py parses argv strictly before touching the committed ERC specs
- **Issue #277** (closed): layout/erc/gen_specs.py reads no sys.argv: a mistyped --check silently rewrites both committed ERC specs
- **PR #290**: fix(sim): remove an aborted record dir and refuse record directories with no record.json
- **Issue #276** (closed): A batch run aborted after the record dir is created leaves a committable records/ directory with no record.json
- **PR #289**: refactor: define the manifest pin contract once in scripts/ci/manifest_pins.py
- **Issue #283** (closed): Define the manifest pin check once: two checkers hand-keep the derived_inputs contract and four define sha()
- **PR #286**: refactor: drop dead placement/router plumbing from gen_io_column
- **Issue #274** (closed): Remove the dead placement/router plumbing in layout/gen_io_column.py: the _WIDTH global carries two constants
- **PR #279**: fix(sim): parse gen_t16attr.py's OUTDIR with argparse so --check exits 2
- **Issue #271** (closed): gen_t16attr.py takes --check as an output directory instead of a flag
- **PR #272**: evidence(pex): re-bind item 7.analog extraction to the post-#248 stream
- **Issue #253** (closed): pex: re-run the item 7.analog extraction on the post-#248 stream (the record binds the pre-#248 hash)
- **PR #262**: fix(gitignore): un-ignore rtl-synth Yosys logs, drop two dead rules, re-aim stale comments
- **Issue #260** (closed): Remove four .gitignore rules for paths this repo never had, and point the Yosys-log negation at sim/rtl-synth/records

### 2026-11-14

- **PR #282**: fix(layout): parse attest_item2.py flags strictly so a typo cannot rewrite the envelope
- **Issue #265** (closed): layout/attest_item2.py: strict flag parsing -- a mistyped --check rewrites the committed signoff attestation
- **PR #275**: fix(sim): parse channel_eye_post flags strictly and refuse an ungraded summary
- **Issue #267** (closed): channel_eye_post.py: lenient flag parsing and an unguarded empty rows summary commit a record with no verdicts
- **Issue #257** (closed): Consolidate duplicated PWL stimulus helpers into sim/gen_common.py
- **PR #264**: fix(sim): parse gen_redundancy_mux flags strictly and share the PWL builders
- **Issue #256** (closed): Convert gen_redundancy_mux.py to the shared write-or-check helper: it still regenerates on a mistyped --check
- **PR #258**: fix(ci): base the append-only check on the default branch, not the pre-push head
- **Issue #255** (closed): check_sim_append_only.py: a record's README is frozen, contradicting the checker's own docstring (and the push-event BASE makes it worse)
- **PR #254**: fix(layout): order the I/O-column slots with both spares at one end (DR-0016)
- **Issue #248** (closed): I/O column: put both spares at one end (DR-0016) and check the slot order - the column already draws 22 cells per direction
- **PR #252**: feat(sim): add the T-12 ±20 % channel R/C spread run and report it per spread corner
- **Issue #193** (closed): T-12 gap: no channel record varies kr/kc, so no CH result covers the declared +/-20 % R/C spread
- **PR #250**: test(ci): list the LVS reference check and assert the check list is complete
- **Issue #236** (closed): Two more gaps in the one check list: layout/lvs/gen_reference.py --check is unlisted, and nothing asserts the list is complete

### 2026-11-13

- **Issue #54** (closed): T1 item 5 (analog) family: clock-path PVT-FULL (T-17/T-04/T-02)
- **PR #243**: refactor(pex): reduce gen_pex_benches main() to the shared write-or-check helper
- **Issue #239** (closed): Convert the seventh write-or-check copy: layout/pex/gen_pex_benches.py should use the shared helper
- **PR #237**: feat(verification): refuse a request key run_tb.py does not read
- **Issue #231** (closed): run_tb.py silently ignores request keys it does not read
- **Issue #219** (closed): Run the committed sim self-tests in CI: 18 tests and two generator --check modes are in no check list
- **PR #235**: ci: run the channel-eye and T-19 bench self-tests in the PDK-free list
- **Issue #228** (closed): Record dc-static runs through the shared batch harness: it is the one item 5 family still recorded by hand, and its four records have four shapes
- **PR #242**: feat(sim): record dc-static runs through the shared batch harness
- **Issue #227** (closed): Share one write-or---check helper across the six generators: the loop is copied six times with three behaviours
- **PR #238**: refactor: share one write-or-check helper across the six generators
- **Issue #230** (closed): Item 8 report grades from a hand-kept row map that omits 13 rows the manifest already cites, three of them recorded failures: check the map against the manifest
- **PR #240**: fix(item8): grade every row the manifest cites, flipping item 8 to fail
- **Issue #192** (closed): T-05 SIM leg: no testbench measures the redundancy mux's added load and delay
- **PR #233**: feat(sim,spec): measure the T-05 redundancy mux's added load and delay over PVT-FULL
- **Issue #217** (closed): Define each cocotb bench once: run_tb.py and the klt functional-verification requests hold two copies
- **PR #222**: refactor(verification): define each cocotb bench once, in its klt request
- **Issue #218** (closed): T-22/T-23: layout/stats/t22-t23.json says met but nothing reads it, and the item 8 report says not-yet-measured - wire it in or stop grading there
- **PR #221**: feat(measurements): grade T-22 and T-23 from the layout stats record
- **Issue #81** (closed): T1 item 7 (post-layout verification, analog): klt pex delta report for the I/O cells on the SIM rows
- **PR #225**: feat(layout): add klt pex extraction evidence and benches for T1 item 7 (analog)
- **Issue #184** (closed): Define the PVT-FULL corner bundle once: three copies disagree on the diode section
- **PR #210**: sim: define the PVT-FULL corner bundle once and check every request against it
- **Issue #223** (closed): main is red: sim harness test_clock_path fails on the committed clock-path record's report.json
- **PR #224**: test(sim): exclude a record's decompressed report.json from the bench-file set
- **Issue #189** (closed): Share one batch-run-and-record script between run_channel_eye.sh and run_clock_path.sh (the copies have drifted)
- **PR #211**: refactor(sim): share one batch run-and-record harness between the channel-eye and clock-path runners
- **Issue #42** (closed): T1 item 5 (corner verification, analog): PVT-FULL klt sim envelopes for the I/O-cell SIM rows
- **PR #199**: evidence(signoff): cite three klt sim envelopes for item 5 / analog and declare the full row set
- **Issue #212** (closed): DR-0022's correction about where a wrongly cited T-02 lands does not reproduce on the pinned grader
- **PR #215**: docs(DR-0022): amend the grader-bucket claim for a wrongly cited T-02
- **Issue #203** (closed): Generate the sim/dc-static requests from one description (request_2kv.json is a hand copy of request.json)
- **PR #214**: refactor(sim): generate the three dc-static requests from one description
- **Issue #180** (closed): Draw ESD devices and resistors from the checked device table in gen_io_column.py (drawn values are duplicated literals)
- **PR #207**: layout: draw the ESD devices and TX resistors from the checked device table
- **Issue #202** (closed): Generate the three hand-copied negative controls from their sources (LVS rewired references, T-10 control bench)
- **PR #209**: refactor: generate the three hand-copied negative controls from their sources
- **Issue #173** (closed): Run CI checks through scripts/ci/check_local.sh: the hand-kept mirror has drifted
- **PR #208**: ci: run the PDK-free checks through scripts/ci/check_local.sh
- **Issue #174** (closed): Stop committing the four generated T-16 attribution requests (regenerated by run_t16attr.sh)
- **PR #206**: chore(sim): untrack the four generated T-16 attribution requests
- **Issue #191** (closed): T-02 and T-04 SIM legs have no numeric bound, so their PVT-FULL measurements can only be reported
- **PR #204**: docs(spec): decide the T-02 and T-04 SIM legs as a pointer and a report-only leg
- **Issue #187** (closed): layout: I/O column layout and LVS references still draw the pre-#164 predriver NOR (ng=2); item 4 analog reads met against a stale reference
- **PR #200**: layout: draw the predriver pull-ups at ng = 4 and regenerate the analog evidence
- **Issue #186** (closed): dll-interface.md: move D-9 / G3 off 'pending #54' now that the clock-path record is on main
- **PR #197**: docs(spec): record D-9 / G3 as not triggered, with the T-17 record's scope
- **Issue #175** (closed): T-21 SIM: forwarded-clock alignment contract is a declared gap; compare against the SG13G2 DLL canary
- **PR #179**: docs(spec): re-compare T-21 against the DLL canary at 381d989 and record the gaps as DR-0020
- **PR #178**: feat(sim): record the 45-corner clock-path PVT-FULL run (T-17 pass, T-04/T-02 reported)
- **Issue #146** (closed): T-09: re-run the skew/timing row on the DR-0017 driver
- **Issue #165** (closed): Generate LVS negative-control netlists instead of committing 290 KB near-copies

### 2026-11-12

- **PR #169**: feat(mc): record T-19 capture-window Monte Carlo campaign (passes at 7 sigma)
- **Issue #138** (closed): T1 item 6 (Monte Carlo): capture-window campaign T-19 (klt yield)
- **PR #166**: Bump Repo Skills 0.25.10 -> 0.26.1
- **PR #164**: design: widen TX predriver NOR pull-up to balance rise/fall delay (T-16)
- **Issue #142** (closed): channel-eye: T-16 data-clock skew fails at 29/45 CH corners (binding mos_ss 1.08 V 125 C)
- **Issue #44** (closed): T1 item 6 (Monte Carlo): klt yield campaigns for the STAT rows; not-applicable statement for the digital partition

### 2026-11-11

- **PR #162**: sim: attribute T-16 offset to cell asymmetry and TX loading
- **Issue #161** (closed): Attribute the T-16 systematic offset (65 ps at mos_ss / 1.08 V / 125 C): cell path imbalance, channel, or measurement
- **PR #158**: ci: hash-pin routed SPEF and DEF and fail on drift
- **Issue #126** (closed): Stop committing unreferenced routed SPEF and DEF (~47k lines)

### 2026-11-10

- **PR #155**: docs(sim): align T-16 required N in MC README with recorded 1318
- **Issue #154** (closed): sim/mc: T-16 required N in README (1436) disagrees with record (1318)
- **PR #153**: feat(sim): record T-15/T-16 RX skew Monte Carlo over the channel
- **Issue #137** (closed): T1 item 6 (Monte Carlo): RX skew campaigns T-15/T-16 over the channel (klt yield)
- **PR #150**: feat(sim): channel-eye CH/TC records on the DR-0017 driver, T-09 evidence
- **PR #149**: sim: dedicated ESD diode fails T-24 by 8.9 fF; record DR-0018
- **PR #148**: feat: regenerate I/O column layout for DR-0017 driver and ESD sizing
- **PR #132**: design: size I/O driver and ESD diode jointly to close T-06/T-08/T-24
- **Issue #147** (closed): T-25 ESD: decide the dedicated PDK ESD diode against T-24 pin-capacitance margin
- **Issue #140** (closed): layout: regenerate I/O-cell layout, LVS references and analog DRC/LVS evidence for DR-0017 driver and diode
- **Issue #130** (closed): I/O cell fails DC static rows T-06 (loaded), T-08 and T-24 at PVT-FULL

### 2026-11-08

- **PR #141**: sim: add 45-corner CH and TC channel-eye records
- **PR #139**: sim: T-10 Monte Carlo campaign and item 6 digital not_applicable
- **PR #131**: sim: record 45-corner dc-static PVT-FULL run
- **Issue #53** (closed): T1 item 5 (analog) family: channel eye, overshoot and energy PVT-FULL (T-01/T-09/T-18/T-26)
- **Issue #52** (closed): T1 item 5 (analog) family: DC static characteristics PVT-FULL (T-06/T-07/T-08/T-11/T-24/T-28)

### 2026-11-07

- **PR #128**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **PR #124**: refactor(lvs): remove superseded --diagnostic generator path
- **PR #123**: chore(sim): remove four regenerable single-corner request copies
- **Issue #117** (closed): Remove sim/channel-eye/req_commit_*.json: single-corner copies of request_*_1g.json (~1758 lines)
- **Issue #103** (closed): Remove superseded LVS diagnostic set and --diagnostic generator path

### 2026-11-05

- **PR #121**: refactor(signoff): build item 2 envelopes with klt signoff --attest 2
- **PR #119**: feat(signoff): pin klt 0.9.0 and grade item 11 digital met
- **Issue #120** (closed): Replace hand-built item 2 attest scripts with klt signoff --attest 2 (available in pinned 0.9.0)
- **Issue #83** (closed): T1 item 11 (power delivery, digital): re-grade 11.digital under the klt release carrying klayout-tools#4199 (tapless PDN)

### 2026-11-03

- **PR #114**: chore(sim): drop variant-b scratch94 probe inputs, keep variant a
- **Issue #111** (closed): Remove sim/channel-eye/scratch94: superseded #94 probe inputs (~2960 lines)

### 2026-11-02

- **PR #113**: fix(sim): run channel-eye grid as one-unit batch jobs and keep resume dir
- **PR #110**: fix(design): replace pad-ESD Dn1 dantenna with grounded-gate NMOS Mn1 so the channel-eye transient completes
- **Issue #94** (closed): channel-eye: four-lane 1 Gb/s transient aborts (timestep too small) at mos_tt 1.20 V 27 C, CH and TC

### 2026-11-01

- **PR #108**: feat(rtl): rewrite T-05 shift remap to DR-0016 layout, state 22-cell span
- **Issue #105** (closed): T-05 after DR-0016: rewrite the RTL to the two-signal shift with both spares at one end, and state the 22-cell span in the clock-tree record
- **PR #32**: spec: propose two-signal shift with both spares at one end (T-05, DR-0016)
- **PR #101**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-31

- **PR #100**: docs: record grounded-gate NMOS scratch probe that clears the channel-eye abort
- **PR #98**: docs: record stimulus-side bisect of the channel-eye abort (lane-A intrinsic, numerical, not an overshoot)
- **PR #96**: docs: record cell-level aib_pad_esd bisect of the channel-eye abort
- **PR #95**: docs: record four-lane channel-eye abort bisect results

### 2026-10-30

- **PR #72**: chore(sim): remove stale pad-ESD bisect probe
- **Issue #67** (closed): Remove bisect_esd.py: stale #60 probe silently emits mislabelled netlists
- **Issue #60** (closed): aib_pad_esd: XDn2 dantenna on the inner pad node aborts the channel transient (Timestep too small)

### 2026-10-29

- **PR #90**: feat: pin derived item-7 SDFs in the manifest and check they reproduce
- **Issue #88** (closed): Stop committing the two derived item-7 SDFs (regenerated by run_evidence.py)

### 2026-10-28

- **PR #86**: feat: generate CI-checked characterization report for T1 item 8
- **Issue #82** (closed): T1 item 8 (characterization report): per-row aggregated report over all 30 T- rows, both partitions
- **PR #85**: feat: cite SDF-annotated post-route functional run as 7.digital
- **Issue #80** (closed): T1 item 7 (post-layout verification, digital): SDF-annotated functional run on the routed aib_datapath netlist
- **PR #77**: feat(erc): add klt erc supply specs and reports for I/O cells and data path; cite item 11
- **Issue #41** (closed): T1 item 11 (power delivery, structural): klt erc supply specs for the I/O cells and the data path
- **PR #75**: feat(lvs): cite a whole-column analog LVS report for the item 4 analog row
- **Issue #40** (closed): T1 item 4 (LVS clean): LVS of the I/O cells against their schematics and of the data path with power_connectivity

### 2026-10-27

- **PR #73**: fix(layout): finger widths from netlist totals; clear clamp tap from PADI diode so analog LVS matches
- **PR #71**: feat(layout): LVS of the data path (match) and the I/O cells (mismatch)
- **PR #69**: feat(signoff): record per-partition klt drc reports and cite as T1 item 3
- **Issue #70** (closed): layout: I/O cell stream differs from the item 1 netlists (PADI on VSS, ng=2 finger width)
- **Issue #39** (closed): T1 item 3 (DRC clean): klt drc on the I/O-cell and data-path layouts with coverage disclosed
- **PR #66**: feat(layout): routed aib_datapath from klt place-and-route with item 2 digital attestation
- **PR #64**: fix(design): swap pad-ESD secondary NMOS-side diode to a grounded-gate NMOS junction
- **Issue #38** (closed): T1 item 2 (layout, digital): place-and-route aib_datapath to a committed routed GDS with a PDN
- **PR #62**: docs(sim): record pad-ESD transient bisect and add probe netlist generator
- **PR #61**: feat(sim): channel-eye PRBS-7 bench with separate CH and TC requests
- **PR #59**: feat(signoff): cite klt functional-verification and multi-corner STA for item 5 digital
- **PR #58**: fix(design): make driver and clamp w the total width so fingers meet wmin
- **PR #57**: feat(sim): DC static testbenches and 45-corner request (no record yet)
- **PR #55**: feat(layout): generate 55 um I/O cell and column stream with item 2 attestation
- **PR #51**: feat(signoff): attest T1 item 10 and update README to the ratified spec
- **PR #48**: feat: commit aib_datapath netlist with freshness check and item 1 digital attestation
- **PR #47**: feat: add analog I/O-cell schematics, netlists and item-1 attestation
- **Issue #56** (closed): design: aib_tx_data driver fingers are below the model minimum width (w is total width in sg13_lv_*)
- **Issue #46** (closed): T1 item 10 (repo hygiene): item 10 inventory, attest envelope, and README spec table update
- **Issue #43** (closed): T1 item 5 (corner verification, digital): multi-corner klt sta and the RTL functional suite for the data path
- **Issue #37** (closed): T1 item 2 (layout, analog): I/O cell layout at the 55 µm pitch with documented provenance
- **Issue #36** (closed): T1 item 1 (design sources, digital): commit the aib_datapath gate-level netlist with a freshness check and attest it
- **Issue #35** (closed): T1 item 1 (design sources, analog): schematics and derived netlists for the TX driver, RX receiver and forwarded-clock I/O cells
- **PR #49**: feat(signoff): attest T1 item 9 for both partitions, bump klt to 0.8.0
- **Issue #45** (closed): T1 item 9 (testbenches shipped): item 9 inventories and attestations for both partitions

### 2026-10-24

- **PR #30**: docs: record that the shift-redundancy RTL differs from AIB 1.2 section 3.3.1

### 2026-10-23

- **PR #26**: feat: add DDR/SDR serializer, deserializer and L1 loopback RTL with latency bench
- **PR #25**: feat: add shift-redundancy remap RTL with exhaustive single-fault cocotb bench
- **Issue #24** (closed): RTL: DDR/SDR serializer, deserializer and L1 loopback with cycle-accounted latency (T-02, T-27, T-29)
- **Issue #23** (closed): RTL: shift-redundancy remap for one 20+2 channel with an exhaustive single-fault cocotb bench (T-05)

### 2026-10-22

- **PR #21**: fix: wire package.json test/check scripts to the real CI checks
- **Issue #20** (closed): Wire package.json check:ci/test/lint placeholders to the real CI checks (stub theater)

### 2026-10-21

- **PR #17**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-20

- **PR #7**: ci: add signoff record and evidence-format/append-only checks
- **Issue #5** (closed): T1 item 10: add a block manifest, a committed signoff record and a PDK-free CI that keeps evidence formats valid
- **PR #12**: docs(spec): record sibling spec-review comment in DR-0014
- **PR #11**: docs(spec): propose DR-0014 on finer forwarded-clock alignment

### 2026-10-17

- **PR #8**: docs(spec): ratify target spec, channel model, test configuration, DLL interface
- **PR #6**: feat(sim): pin SG13G2 PDK and OSDI toolchain, add four-device MOS smoke
- **PR #1**: chore(loom): Install Loom 0.19.1180
- **Issue #2** (closed): Draft and ratify the target spec
- **Issue #4** (closed): T1 item 9: pin IHP-Open-PDK, adopt the sibling OSDI model build by pinned reference, and commit a smoke simulation

