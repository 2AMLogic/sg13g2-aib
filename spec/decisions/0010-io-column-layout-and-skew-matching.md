# DR-0010: I/O column layout and skew matching (open question 3)

**Status**: accepted as a method; tool gaps are filed when the work reaches them.
**Rows**: T-13, T-14, T-22, T-23, T-30.

## The question

Is the I/O column best laid out by hand or with `klt` placement, and what does skew
matching across the column require of the tools?

## Evidence (this install; read, nothing run against a layout yet)

- `klt 0.7.1.dev1754+g81ac4d3915c1` lists, for layout: `gen` (a parametrized cell),
  `gen-compose` (place already-generated blocks and library cells into one cell),
  `draw`, `socket-check`, `ring-check`, `tap-distance`, `extract`, `pex`, `lvs`, `drc`.
  `place-and-route` places a *synthesized netlist* against a standard-cell library via
  OpenROAD. No command places an abutted custom cell column or compares delay or RC
  across a set of nets.
- `klt deck info --deck sg13g2` reports no pad or ESD coverage and no ESD diode class
  (filed: `2AMLogic/klayout-tools#3854`); `released: False`.
- A column of identical cells at a fixed pitch is a regular structure; skew across it
  is set by mismatch inside the cell and by the symmetry of the clock distribution, not
  by placement search.

## Decision

Lay the column out as a hand-structured unit cell (one pitch-matched I/O cell, mirrored
copies abutted at the T-22 pitch), composed with `gen-compose` where it expresses the
arrangement and hand-drawn where it does not. The clock to the column is a balanced
tree drawn to be symmetric about the column's centre. The synthesized data path behind
the column goes through the digital flow (`klt synthesize`, `klt place-and-route`).
Skew is verified, not designed by a tool: per-pin `klt extract`/`klt pex` of a
representative subset, comparing extracted R/C of the data and clock nets across
positions, then `SIM-MC` on the extracted cell (T-13, T-14).

What skew matching requires of the tools: (1) per-net extracted R, C and delay for
every position in the column, selectable as a regular structure; (2) a statistic across
the set (spread, worst pair) rather than a per-net listing; (3) DRC and ERC coverage for
the pad and protection structures (#3854). Items (1) and (2) are not shown to exist and
are filed against the tool when #3 first needs them, with the layout in hand, not
before: filing them now would describe a gap this repo has not yet hit.

## Alternatives rejected

- **`klt place-and-route` for the whole column.** It targets a standard-cell netlist;
  the I/O cell is custom, pitch-matched and abutted, and the router has no notion of
  matched clock arrival across the array.
- **Hand layout of everything, including the data path.** The data path is synthesized
  (README scope); only the column is custom.
- **No skew verification beyond `SIM-MC` on the schematic.** Layout-induced skew is the
  array's risk (CLAUDE.md); schematic-only evidence would not see it.
