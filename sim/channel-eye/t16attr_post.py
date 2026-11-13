#!/usr/bin/env python3
"""Turn the four t16attr `klt sim` reports into the attribution table (issue #161).

Stdlib only. Usage: python3 -I t16attr_post.py LABEL=DIR [LABEL=DIR ...]   (each DIR holds {ch,id}_{ss,tt}.json.gz)
Prints JSON on stdout. Stages: 0 stimulus, 1 TX cell output, 2 TX pad, 3 RX-side pin.
Clock reference time at stage s is the mean of the two single-ended clock lanes' 50 % crossings
(rxc and rxcb cross in opposite directions); the bench's csig is their differential crossing.
skew_s = T_clock_s - T_data_s. Telescoping terms (ps):
  stimulus  = skew_0 - 500            (stimulus offset error; 0 by construction)
  driver    = skew_1 - skew_0         (TX cell: clock-pair mean vs data lane)
  esd_tx    = skew_2 - skew_1         (TX pad ESD series resistor)
  link      = skew_3 - skew_2         (channel, or nothing for the ideal connection)
  diff_x    = csig - T_clock_3        (differential crossing of csig vs mean of single-ended crossings)
  t16       = 500 + sum of the above; `residual` = t16 from probes - t16 the bench card reports.
"""
import gzip
import json
import sys
from pathlib import Path

NAMES = ["t16_dr_cr_long", "t16_dr_cr_short", "t16_dr_cf_long", "t16_dr_cf_short",
         "t16_df_cr_long", "t16_df_cr_short", "t16_df_cf_long", "t16_df_cf_short"]


def load(path):
    rep = json.load(gzip.open(path, "rt"))
    (c,) = rep["corners"]
    assert c["status"] in ("pass", "fail"), (path, c["status"])
    return {m["name"]: m["value"] for m in c["measurements"]}


def attribute(v, nm):
    ps = lambda x: x * 1e12
    t = lambda lane, s: v[f"att_{nm}__{lane}{s}"]
    clk = lambda s: (t("p", s) + t("n", s)) / 2
    skew = [ps(clk(s) - t("a", s)) for s in range(4)]
    out = {"stimulus": skew[0] - 500, "driver": skew[1] - skew[0], "esd_tx": skew[2] - skew[1],
           "link": skew[3] - skew[2], "diff_x": ps(v[f"att_{nm}__csig"] - clk(3))}
    probe = 500 + sum(out.values())
    out["t16_probe_ps"] = probe
    out["t16_bench_ps"] = ps(v[nm])
    out["t16_dsa_cross_ps"] = ps(v[f"att_{nm}__csig"] - v[f"att_{nm}__dsa"])
    out["residual"] = probe - ps(v[nm])
    out["delay_ps"] = {  # per-lane delay from the ideal stimulus crossing, by stage
        "data": [ps(t("a", s) - t("a", 0)) for s in range(1, 4)],
        "clk_mean": [ps(clk(s) - clk(0)) for s in range(1, 4)],
        "clk_p": [ps(t("p", s) - t("p", 0)) for s in range(1, 4)],
        "clk_n": [ps(t("n", s) - t("n", 0)) for s in range(1, 4)]}
    return out


def main(argv):
    res = {}
    for arg in argv:
        label, d = arg.split("=", 1)
        for link in ("ch", "id"):
            for corner in ("ss", "tt"):
                v = load(Path(d) / f"{link}_{corner}.json.gz")
                res[f"{label}_{link}_{corner}"] = {nm: attribute(v, nm) for nm in NAMES}
    json.dump(res, sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
