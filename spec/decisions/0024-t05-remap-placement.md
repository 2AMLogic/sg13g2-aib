# DR-0024: where the T-05 shift-redundancy remap lives — ahead of the TX input register

**Status**: proposed; ratified by the merge of the pull request that carries it (DR-0001).
**Rows**: T-05 (and, as consumers of the numbers, T-13 and T-20).
**Amends**: DR-0023 (decision point 1, the placement, and the stand-in of point 2 — both
are superseded *for the design*, and stand unchanged as the description of what
`sim/redundancy-mux/records/20261113T160050Z/` measured). **Related**: DR-0003 (spares per
direction), DR-0016 (the two-wire shift), DR-0006 (the timing budget T-20 checks), DR-0022
(a `SIM` leg with no bound). **Filed as**: #232.

## Context

DR-0023 had to **declare** where the remap sits before the T-05 `SIM` leg could be measured
at all: `tx_remap` / `rx_remap` are RTL only, `rtl/aib_datapath.v` instantiates neither, and
the committed netlist predates them. It declared the placement the ratified row already
presumed — on the serialized wire, between the serializer mux and `aib_tx_data`'s `DIN` —
with `sg13g2_mux2_1` standing in for the stage, and said in as many words that a sized or
buffered stage would give different numbers and that the alternative placement was not to be
assumed on no evidence.

The first record under that decision measured the stand-in and **it does not fit**: up to
**0.184 UI** of common added delay at 1 Gb/s, against a timing budget whose margin line
closes by **7.5 ps** (`spec/target-spec.md`, "Timing budget": 0.400 − 0.150 − 0.030 −
0.0625 − 0.050 = 0.1075 UI against T-20's ≥ 0.10 UI). Every data lane gains the stage and
the forwarded-clock lane does not, so the term is a data-to-clock offset and lands in T-20.

This record decides where the remap lives. It is a spec change to a ratified row, made the
way DR-0001 provides for: a new decision record naming the row and the evidence.

## Evidence

Two PVT-FULL records of the same bench, both 45 corners, batch fleet, every measurement
reported and none graded (T-05's `SIM` leg has no bound — DR-0023, unchanged here):

- `sim/redundancy-mux/records/20261113T160050Z/` — the drive-1 stand-in in the DR-0023
  placement. Four lanes: baseline, control, remap selected to `A0` and to `A1`.
- `sim/redundancy-mux/records/20261113T174852Z/` — the same deck extended to six lanes,
  adding the two **sized** in-lane stages this record had to weigh: `sg13g2_mux2_2`
  (drive 2), and `sg13g2_mux2_1` followed by `sg13g2_buf_4`. The drive-1 lanes are
  re-measured in the same deck, so the sizing comparison is a difference inside one
  simulation.

Both records pass 45/45 corners with `klt sim` exit 0, 0 failed and 0 errored, and the
second carries **no solver diagnostic at all** (the first has one benign `singular_matrix`
on a control-lane node, named in `sim/README.md`). The six-lane deck reproduces the
four-lane one where they overlap, which is what makes the two comparable: the re-measured
drive-1 lanes read `t05_add_r_s` **53.786 .. 128.150 ps** and `t05_add_f_s`
**71.134 .. 183.889 ps**, against 53.786 .. 128.150 ps and 71.134 .. 183.889 ps in the
first record — agreement to six significant figures, and 0.2 fs at the nominal corner. The
negative control is clean in both (worst |`t05_ctl_*`| 2.1 x 10^-10 ps over the new grid,
about twelve orders of magnitude below the terms read against it).

### What an in-lane stage costs, sized and unsized

Common added delay at the TX pad, with-remap minus baseline, over the 45-corner grid:

| remap stage | rise, `t05_add*_r_s` | fall, `t05_add*_f_s` | per-corner worst | corners over 0.10 UI | corners over the 7.5 ps spare |
|---|---|---|---|---|---|
| `sg13g2_mux2_1`, drive 1 — the DR-0023 stand-in | 53.8 .. 128.2 ps | 71.1 .. 183.9 ps | 71.2 .. 184.2 ps | 30 / 45 | **45 / 45** |
| `sg13g2_mux2_2`, drive 2 | 21.9 .. 56.0 ps | 52.9 .. 153.9 ps | 52.9 .. 153.9 ps | 14 / 45 | **45 / 45** |
| `sg13g2_mux2_1` + `sg13g2_buf_4` | 46.1 .. 113.9 ps | 63.0 .. 181.2 ps | 63.0 .. 181.2 ps | 25 / 45 | **45 / 45** |

The drive-1 row's per-corner worst takes the `A1`-selected lane in as well (`t05_add1_*`),
which is why it reads 184.2 ps where its fall range stops at 183.9; the two sized lanes are
measured through `A0` only, because the select-dependent term sizing would change is
0.289 ps worst case (below). Fall is the slower edge at **45 of 45** corners for all three
stages. 1 UI = 1000 ps at the 1 Gb/s target, so 0.10 UI = 100 ps.

Read against the **7.5 ps** the budget has spare, every row of that table is seven to
twenty-five times too large — and the best corner of the *best* option is 7.1 times it. The
reason is in the decomposition, and it is not loading: the serializer gets *faster* when the
remap is inserted (it drives two mux inputs,
4.5–5.3 fF, instead of one `DIN`, 29.6–33.6 fF), and the whole cost is the remap stage
**inheriting** that ~30 fF load:

| remap stage | load term at the serializer output | stage term | net at the pad, worst |
|---|---|---|---|
| drive 1 | −87.6 .. −39.1 ps | +94.5 .. +259.9 ps | 184.2 ps |
| drive 2 | −87.5 .. −38.4 ps | +64.0 .. +228.1 ps | 153.9 ps |
| drive 1 + `buf_4` | −87.6 .. −39.1 ps | +86.8 .. +256.7 ps | 181.2 ps |

(`t05_load*_*` and `t05_stage*_*`, rise and fall pooled.) The load term is the same in all
three — the serializer drives a mux *input* either way, and `sg13g2_mux2_2`'s `A0`/`A1`
devices are the same size as `sg13g2_mux2_1`'s — so sizing acts only on the stage term, which
it cuts by **32 %** at its rise minimum (94.5 → 64.0 ps) and **12 %** at its fall maximum
(259.9 → 228.1 ps). That carries the per-corner-worst **net added delay at the pad** down
**26 %** at the best corner (71.2 → 52.9 ps) and **16 %** at the worst (184.2 → 153.9 ps).
The buffered stage buys less — 8.2 % and 1.2 % of the stage term, 11 % and 1.6 % of the net
at the pad: `sg13g2_buf_4` drives the load with four times the strength, and then
spends most of what it saves on its own stage delay and on the extra input the mux has to
charge.

Sizing also makes one term **worse**. The remap adds pulse-width distortion to the data
lane that the forwarded clock does not see — `t05_pwd*_s`, the fall-minus-rise of its own
added delay — and doubling the output drive helps the rising edge about **twice** as much
as the falling one (per-corner rise-gain / fall-gain ratio **1.18 .. 3.75**, median **1.93**;
mean gains 48.0 ps rise against 24.0 ps fall):

| remap stage | added pulse-width distortion |
|---|---|
| drive 1 | 15.2 .. 56.8 ps |
| drive 2 | 24.8 .. **101.7 ps** |
| drive 1 + `buf_4` | 0.5 .. 78.8 ps |

So a sized in-lane stage is not a smaller version of the same problem: the term T-20 carries
shrinks by a sixth and the duty-cycle term T-19's aperture would carry nearly doubles.

## Decision

**1. The remap sits ahead of the TX input register, not on the serialized wire.** In RTL
terms: `tx_remap` is instantiated twice in the TX datapath — once on the `d0` bus and once
on the `d1` bus — and its 22 outputs drive the `d0` / `d1` inputs of 22 `aib_tx_slice`
instances. The mux is then **combinational logic in front of the slice's posedge input
register** (`a0`/`a1`, `rtl/aib_tx_slice.v`), in the half-rate 500 MHz domain, instead of a
gate on the serialized wire.

**2. Both of the leg's delay terms are therefore zero by construction at the TX output,
and T-05 contributes a term to neither T-20 nor T-13.** The serialized path — input
register → `o_n`/`o_p` → `wire_o = clk ? o_n : o_p` → `aib_tx_data` — is bit-for-bit what
it is today, repaired or not, because the input register **re-times** everything the remap
does to an edge of the forwarded clock:

- the **common** added delay (the data-to-clock offset T-20 was carrying, up to 0.184 UI as
  measured) disappears — a data lane and the forwarded-clock lane gain the same nothing;
- the **select-dependent** delay between the mux's `A0` and `A1` paths (0.289 ps worst case,
  reported into T-13 under DR-0023) disappears with it: whether a wire is repaired changes
  which input of a mux ahead of a register is selected, not when that register's output
  switches.

Both become differences in **setup time** at the input register instead (point 3). This is
the whole reason for the choice: sizing shrinks a gate delay, and the measurements above
show by how much; only moving the stage removes it.

**3. The cost moves to datapath setup time, where it is graded by static timing analysis,
not by T-20 or T-13.** The remap delay, and the small difference between its two input
paths, now land on the path from whatever drives `tx_d0`/`tx_d1` to the slice input
register's `D`, inside a **2 ns** clock period rather than a 1000 ps UI. The measured stage
term is the right order of magnitude for that path (+94.5 .. +259.9 ps for the drive-1 cell,
driving a ~30 fF `DIN`; in the new placement it drives a flop input, which is far lighter),
so this
is a setup-margin question for synthesis and P&R to answer — item 7 / digital evidence —
and not a term in the T-20 budget. **This record does not claim that path closes**: it
claims the term leaves T-20, and names the re-synthesis that must confirm the new one as a
follow-up below.

**4. The RX side mirrors it.** `rx_remap` goes behind the RX capture register, for the same
reason and with the same consequence for T-19's capture aperture. It is **not measured**
here — the T-05 `SIM` leg names the lane to the TX cell — and the follow-up that
instantiates it carries that measurement if the RX path turns out to need one.

**5. No bound changes.** T-13, T-19, T-20 and every line of the timing budget are
untouched. T-05's `SIM` leg still has **no bound of its own** (DR-0023 point 5, unchanged):
its measurements are reported, never graded. What *does* change is DR-0023's statement of
where they are consumed — under this record the two rows they reported into, T-20 and
T-13, receive **no term from T-05**, because point 2 removes both from the TX output rather
than shrinking either. T-05 stays a declared gap in `signoff/block-manifest.json`, in the
form DR-0022 established.

**6. The two records stay as they are.** They measure the in-lane arrangement, which is now
the *rejected* alternative; that is what evidence for a rejection looks like, and records
are append-only. DR-0023 is amended, not withdrawn: it remains the description of what was
measured and why the stand-in was chosen.

## Alternatives rejected

- **Size or buffer the in-lane stage** — *measured, and it does not close*.
  `sg13g2_mux2_2` leaves a per-corner worst of **52.9 .. 153.9 ps** — over the 7.5 ps spare
  at all 45 corners and over T-20's whole 0.10 UI target at 14 of them, with the
  pulse-width distortion nearly doubled; `sg13g2_mux2_1` + `sg13g2_buf_4` leaves
  **63.0 .. 181.2 ps**, over 0.10 UI at 25 of 45. The best corner of the better of the two
  options is still **7.1 times** the budget's 7.5 ps.
  Sizing shrinks the term by a sixth where it binds, which leaves it seven to twenty times
  the budget's spare — short by an order of magnitude, not by a margin that a cell choice
  could close. A larger buffer does not change the verdict either — the `buf_4` lane shows the
  buffer's own stage delay replacing most of what it saves on the load, which is why it beats
  the drive-1 cell by little and `sg13g2_mux2_2` not at all; `buf_8`/`buf_16` would push more
  of the same trade. Evidence: `records/20261113T174852Z/`.
- **A replica remap stage in the forwarded-clock lane**, to cancel the common term —
  **not measured, rejected on argument.** It converts a data-to-clock offset into a
  cell-to-cell mismatch term in T-13 and T-16, and it puts the *same* pulse-width
  distortion (15.2 .. 56.8 ps measured on the drive-1 stage, 24.8 .. 101.7 ps on the
  drive-2 one) onto the forwarded clock as duty-cycle error, which T-19's capture aperture
  then pays for. Removing the stage is strictly better than cancelling it,
  so no bench was built for this.
- **Re-allocate the T-20 budget** to make room for the in-lane term — **refused.** T-20's
  ≥ 0.10 UI and the budget lines behind it are ratified numbers, and #136 (T-13) and #177
  (T-19/T-20) are still open; relaxing a bound so a result passes is exactly what this repo
  does not do (CLAUDE.md, DR-0001). Had options 1 and 2 both failed, the route was to stop
  and route the question to the operator, not to edit the allocation. They did not: option 2
  removes the term.
- **Leaving the placement undecided until the remap is built.** The placement determines
  whether T-20 carries a 0.07–0.18 UI term, which is the difference between a budget that
  closes and one that does not. Deciding it after synthesis would mean synthesizing the
  arrangement this record rejects.

## Consequences

- `spec/target-spec.md` T-05 is edited to state the placement and what the `SIM` leg means
  under it; the row's Target, Fallback and Stretch values are unchanged.
- DR-0023's status line gains the `Amended by` pointer; nothing else in it changes.
- `sim/redundancy-mux/` keeps both records and the six-lane deck. The deck still measures
  the **rejected** in-lane arrangement — that is its purpose now, and `sim/README.md` says
  so. No further in-lane campaign is planned.
- Nothing is built by this record. `design/`, `rtl/` and the committed netlist are
  unchanged, exactly as they were under DR-0023.

### Follow-ups this record files (none done here)

1. **#246 — instantiate the remap in the TX datapath** (`loom:triage`, parked
   `loom:blocked` behind this record): two `tx_remap` instances on the
   `d0` / `d1` buses ahead of 22 `aib_tx_slice` instances, with `rx_remap` mirrored behind
   the RX capture register; extend the datapath benches to the 22-wire direction. Note that
   **PR #107 rewrites `rtl/shift_redundancy.v`** and is operator-held — that follow-up meets
   it, this record does not (it edits no RTL).
2. **#247 — re-synthesize and re-place-and-route** (`loom:triage`, parked `loom:blocked`
   behind #246 and #232) with the remap in, and confirm the new
   `tx_d0`/`tx_d1` → input-register path closes setup at 500 MHz over the corners item 7 /
   digital grades. This is the claim decision point 3 defers, and it is where the moved term
   is answered.
3. **#248 — spare placement and slot order in the I/O column** (`loom:curated`): put both
   spares at one end per DR-0016 and check the slot order. The column already draws 22
   cells per direction — which is what the remap makes real in the datapath — so the
   column skew work (T-13, #136) and the layout rows see 22, not 20.
