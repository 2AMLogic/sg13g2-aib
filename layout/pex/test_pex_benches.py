#!/usr/bin/env python3
"""Offline self-test for layout/pex: the invariants `klt pex` and item 7 need.

PDK-free, fleet-free, writes nothing. These are the properties that are easy to
break by editing a bench or the generator by hand, and that cost a whole pex run
to discover otherwise.

    python3 -I layout/pex/test_pex_benches.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import gen_pex_benches as g  # noqa: E402

FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'ok  ' if ok else 'FAIL'}  {name}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


def main() -> int:
    # 1. The committed files are what the generator writes.
    for rel, text in g.files().items():
        p = HERE / rel
        check(f"fresh: {rel}", p.exists() and p.read_text() == text,
              "stale -- run python3 -I layout/pex/gen_pex_benches.py")

    for top in g.TOPS:
        bench = (HERE / f"benches/tb_dc_static_{top}.cir").read_text()
        dut = (HERE / f"benches/{top}.dut.spice").read_text()
        req = json.loads((HERE / f"benches/request_dc_static_{top}.json").read_text())

        # 2. Exactly one `.include`/`.inc` per bench body. More is a hard error in
        #    `klt pex` (it cannot tell which one is the DUT); none means there is
        #    no swap point for the extracted netlist.
        incs = [ln for ln in bench.splitlines()
                if ln.strip().lower().startswith((".include", ".inc "))]
        check(f"{top}: exactly one .include", len(incs) == 1, f"found {len(incs)}")

        # 3. ... and it names this top's DUT file, which is what pex re-points.
        check(f"{top}: .include names {top}.dut.spice",
              bool(incs) and f"{top}.dut.spice" in incs[0])

        # 4. The DUT's declared pins are the LVS reference's pins, in order --
        #    the pin list `--pins`/`--rename-declared-pins` reproduces on the
        #    extracted side. A difference here is pin_order/count_mismatch.
        ref = g.ref_pins(top)
        decl = next((ln.split()[2:] for ln in dut.splitlines()
                     if ln.lower().startswith(".subckt") and ln.split()[1] == top), None)
        check(f"{top}: DUT pin list == layout/lvs/{top}.ref.spice", decl == ref,
              f"{decl} != {ref}")
        check(f"{top}: extraction.json pins == DUT pins",
              json.loads((HERE / "benches/extraction.json").read_text())
              ["tops"][top]["pins"] == ref)

        # 5. The DUT is self-contained: a nested include would be a second file
        #    `klt pex` neither reads nor swaps.
        check(f"{top}: DUT has no .include of its own",
              not any(ln.strip().lower().startswith((".include", ".inc "))
                      for ln in dut.splitlines()))

        # 6. Every instance of the top in the bench passes as many nodes as the
        #    DUT declares pins. ngspice 42 silently mis-simulates a mismatch.
        for ln in bench.splitlines():
            t = ln.split()
            if t and t[0].upper().startswith("X") and t[-1] == top:
                check(f"{top}: {t[0]} passes {len(ref)} nodes",
                      len(t) - 2 == len(ref), f"{len(t) - 2} nodes for {len(ref)} pins")

        # 7. Measurement names are the item 5 set, so a row maps the same way
        #    here as it does under 5.analog, and every one is a name the row
        #    split knows about.
        names = [m["name"] for s in req["analysis_steps"] for m in s["measurements"]]
        names += [m["name"] for m in req.get("measurements", [])]
        item5 = {m["name"] for s in g.dc.DC_STEPS for m in s["measurements"]}
        item5 |= {m["name"] for m in g.dc.DC_TOP}
        check(f"{top}: measurement names are the item 5 set",
              set(names) <= item5, f"extra: {sorted(set(names) - item5)}")
        check(f"{top}: every measurement is declared in MEASUREMENT_NEEDS",
              all(n in g.MEASUREMENT_NEEDS for n in names))

        # 8. ... and this leg only carries measurements its bench can support.
        have = g.LEGS[top]["sources"]
        check(f"{top}: no measurement needs a source this bench lacks",
              all(g.MEASUREMENT_NEEDS[n] <= have for n in names),
              f"{[n for n in names if not g.MEASUREMENT_NEEDS[n] <= have]}")

        # 9. Every source a step alters is one the bench defines.
        defined = {ln.split()[0] for ln in bench.splitlines() if ln.strip()
                   and ln.split()[0][0].upper() in "VIBRCL"}
        for s in req["analysis_steps"]:
            missing = [k for k in s["alter"] if k.split(".")[0] not in defined]
            check(f"{top}: step {s['name']} alters only defined sources",
                  not missing, f"missing {missing}")

        # 10. The corner grid is item 5's PVT-FULL, not a narrowed one: the
        #     committed request is the campaign, and run_pex.sh narrows a copy.
        c = req["corners"]
        n = len(c["process"]) * len(c["supply_v"]["vddio"]) * len(c["temperature_c"])
        check(f"{top}: PVT-FULL, 45 corners", n == 45, f"{n} corners")
        check(f"{top}: corner grid == item 5's", c == g.dc.corners())

        # 11. The batch backend and the fleet's mandatory capacity wait.
        check(f"{top}: backend batch", req.get("backend") == "batch")
        check(f"{top}: capacity_wait_s 600",
              (req.get("batch") or {}).get("capacity_wait_s") == 600)
        # A request with no `backend` field hits the dropped-osdi_preload defect
        # (README defect 1), so the field is load-bearing, not decoration.
        check(f"{top}: osdi_preload declared", bool(req["options"].get("osdi_preload")))

    # 12. The rows each leg claims are rows item 5 grades, and between them the
    #     two legs name every dc-static row -- so the split moved the measurement
    #     point without dropping a row.
    manifest = json.loads((ROOT / "signoff/block-manifest.json").read_text())
    graded = {r for e in manifest["evidence"]["5.analog"]
              if "dc-static" in e["file"] for r in e["rows"]}
    claimed = {r for leg in g.LEGS.values() for r in leg["rows"]}
    check("rows claimed are rows 5.analog grades on dc-static",
          claimed <= graded, f"not graded there: {sorted(claimed - graded)}")
    check("every dc-static row is claimed by some leg",
          graded <= claimed, f"dropped: {sorted(graded - claimed)}")

    print(f"\n{len(FAILURES)} failure(s)" if FAILURES else "\nall checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
