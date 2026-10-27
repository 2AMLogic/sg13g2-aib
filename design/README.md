# design

Analog design sources for the I/O-cell partition (T1 item 1, analog). Thin-oxide
SG13G2 devices only (T-06), unterminated outputs (T-07).

| Cell | Role | Spec rows it is built toward |
|---|---|---|
| `aib_tx_data` | tristate full-swing data driver, selectable weak pull-up / pull-down | T-06, T-07, T-08, T-28 |
| `aib_rx_data` | single-ended receiver, two inverters, no hysteresis | T-10, T-11 |
| `aib_tx_clk` | clk/clkb forwarded-clock driver: two `aib_tx_data` | T-04 |
| `aib_rx_clk` | clk/clkb forwarded-clock receiver: two `aib_rx_data` | T-04 |
| `aib_pad_esd` | diode pair + rail clamp at the pad, series resistor, secondary diodes | T-24, T-25 |

Each cell is a `.sch` plus `.sym`; the `.spice` next to it is derived with
`klt netlist`, never raw `xschem`. `xschemrc` carries the PDK search path.

**What this directory claims: the sources exist and the netlists are fresh.** Every
size is a first-cut placeholder and nothing here has been simulated, so no spec
row is claimed met. Known open point: an inverter receiver's threshold moves with
the `mos_sf`/`mos_fs` corners and mismatch, so T-10 may need a different receiver;
the Monte Carlo testbench decides. Simulation, layout, LVS and the I/O-cell
assembly are separate issues. The forwarded-clock alignment (DLL) is out of scope.

## Regenerate and check

From the repo root, with the pinned grader (`signoff/KLT_VERSION`):

```bash
K="uvx --from klayout-tools==$(cat signoff/KLT_VERSION) klt"
$K netlist --rcfile design/xschemrc design/aib_tx_data.sch -o design/aib_tx_data.spice          # write
$K netlist --rcfile design/xschemrc design/aib_tx_data.sch -o design/aib_tx_data.spice --check  # exit 0 = fresh
```

xschem writes absolute `** sch_path:` comments; strip the checkout prefix after
writing so the committed file is repo-relative (`--check` ignores those
comments). Re-attest with the recipe in `signoff/README.md`.
