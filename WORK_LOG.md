# Work Log

Chronological record of merged PRs and closed issues. Maintained by the Guide role.

### 2026-10-27

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
