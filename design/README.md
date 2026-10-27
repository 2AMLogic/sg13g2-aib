# design

## synth/: gate-level netlist of `aib_datapath` (T1 item 1, digital)

`klt synthesize` of `rtl/aib_datapath.v` (N = 20, the module default) onto
`sg13g2_stdcell` at the slow corner `slow_1p08V_125C` (exact shipped point:
1.08 V, 125 C). One corner only: a corner changes cell sizing, and timing is
item 5, not this item. No timing, area or power claim is made from it.

| File | What |
|---|---|
| `synth/aib_datapath.synth.json` | the `klt synthesize` request |
| `synth/aib_datapath.report.json` | the report it produced (verbatim) |
| `synth/.klt/synthesize/<run_id>/` | the run's netlist `aib_datapath_synth.v`, `.ys` script |

**Revision.** Synthesized from `main` @ `a800088`. `rtl/shift_redundancy.v`
(last commit `42fa21ca9fa178a70b06cea249bd5a17eb8eec13`) is the pre-decision
T-05 remap; `aib_datapath` does not instantiate it, so the netlist does not
contain the mux. Re-synthesize after #29 / PR #32 settles; that is a new,
dated artifact (a new `run_id`, a new inventory hash).

**Regenerate and check** (needs the PDK and `yosys`; see `signoff/README.md`):

```bash
export PDK_ROOT=<path containing ihp-sg13g2>
uvx --from "klayout-tools==$(cat signoff/KLT_VERSION)" klt synthesize \
  design/synth/aib_datapath.synth.json --pdk ihp-sg13g2 --format json \
  > design/synth/aib_datapath.report.json
# keep only the new design/synth/.klt/synthesize/<run_id>/ (drop *.log), delete older run dirs
python3 -I scripts/ci/check_design_sources.py --regenerate
```

Consistency of a committed report with a fresh run:
`klt synthesize <request> --pdk ihp-sg13g2 --check <report> --rerun` (exit 0 = match).
A re-run writes a new `.klt/synthesize/run-*` directory; delete it.
