# Per-corner Monte Carlo reading: the study candidate's T-10 confirmation

Committed with the record (append-only evidence). One table, one row per PVT-FULL corner,
read from this record's `report.json.gz`; the same columns and conventions as
`sim/mc/per_corner.md` (draw count, per-corner mean and sample sigma (n-1, the convention
`klt` reports), margin-ranked worst draw and the count of draws outside the row's +-60 mV
limits), with the pooled totals cross-checked against the record's own `yield.json`:
pooled mean 2.741 mV, pooled sigma (n-1) 9.600 mV, 0 of 5400 draws outside the limits,
`klt yield` status `pass` at target_sigma 3 (sigma-to-spec 5.9646). The negative control
(input-side NMOS 4x narrower, 900 draws, seed 4411) is detected.

**0 of 45 corners hold out-of-limit draws** (against the committed cell's 13); the
highest corner mean is +10.781 mV (`ff/1.320V/125C`), the lowest -2.388 mV
(`fs/1.080V/-40C`).

| Corner | Draws | Outside limits | Mean (mV) | Sigma (mV, n-1) | Worst draw (mV) |
|---|---:|---:|---:|---:|---:|
| fs/1.080V/-40C | 120 | 0 | -2.388 | 9.437 | -27.326 |
| ff/1.080V/-40C | 120 | 0 | -1.624 | 8.503 | -20.426 |
| ss/1.200V/-40C | 120 | 0 | -1.615 | 9.058 | -27.250 |
| tt/1.080V/-40C | 120 | 0 | -1.603 | 8.593 | 23.661 |
| fs/1.200V/-40C | 120 | 0 | -1.434 | 9.372 | -27.271 |
| sf/1.080V/-40C | 120 | 0 | -0.958 | 8.899 | -20.650 |
| ss/1.080V/-40C | 120 | 0 | -0.891 | 9.552 | -21.296 |
| ff/1.080V/27C | 120 | 0 | -0.270 | 9.221 | 25.835 |
| fs/1.320V/-40C | 120 | 0 | -0.012 | 8.730 | -22.153 |
| ss/1.080V/27C | 120 | 0 | 0.019 | 8.503 | 24.407 |
| tt/1.200V/-40C | 120 | 0 | 0.131 | 7.525 | -24.564 |
| fs/1.200V/27C | 120 | 0 | 0.151 | 9.548 | 28.786 |
| tt/1.200V/27C | 120 | 0 | 0.260 | 8.711 | -34.135 |
| ff/1.200V/-40C | 120 | 0 | 0.381 | 7.861 | -23.134 |
| sf/1.080V/27C | 120 | 0 | 0.588 | 9.236 | -22.873 |
| ss/1.200V/27C | 120 | 0 | 0.628 | 8.712 | -26.228 |
| fs/1.080V/27C | 120 | 0 | 0.649 | 9.748 | -30.288 |
| sf/1.200V/-40C | 120 | 0 | 1.020 | 9.044 | -27.683 |
| tt/1.080V/27C | 120 | 0 | 1.227 | 8.331 | -20.917 |
| sf/1.320V/-40C | 120 | 0 | 1.296 | 8.592 | 26.911 |
| tt/1.320V/-40C | 120 | 0 | 1.553 | 8.939 | -26.585 |
| ff/1.320V/-40C | 120 | 0 | 1.687 | 9.006 | 23.614 |
| ss/1.320V/27C | 120 | 0 | 1.743 | 9.373 | 25.548 |
| ss/1.320V/-40C | 120 | 0 | 1.749 | 9.219 | 22.840 |
| ss/1.080V/125C | 120 | 0 | 2.164 | 8.503 | 26.555 |
| ff/1.200V/27C | 120 | 0 | 2.216 | 8.622 | 19.417 |
| tt/1.080V/125C | 120 | 0 | 2.533 | 8.697 | 28.852 |
| sf/1.200V/27C | 120 | 0 | 2.815 | 8.079 | 22.101 |
| fs/1.320V/27C | 120 | 0 | 3.384 | 9.208 | 30.056 |
| fs/1.080V/125C | 120 | 0 | 3.545 | 9.543 | 27.485 |
| tt/1.320V/27C | 120 | 0 | 3.685 | 7.626 | 24.130 |
| ss/1.200V/125C | 120 | 0 | 4.401 | 9.109 | 23.774 |
| tt/1.200V/125C | 120 | 0 | 5.261 | 9.093 | 31.908 |
| sf/1.080V/125C | 120 | 0 | 5.296 | 9.280 | 28.960 |
| sf/1.320V/27C | 120 | 0 | 5.473 | 9.263 | 29.363 |
| ff/1.320V/27C | 120 | 0 | 5.824 | 9.221 | 32.699 |
| sf/1.200V/125C | 120 | 0 | 5.849 | 9.463 | 35.337 |
| ff/1.080V/125C | 120 | 0 | 6.100 | 8.852 | 28.830 |
| ss/1.320V/125C | 120 | 0 | 7.419 | 8.509 | 27.801 |
| fs/1.200V/125C | 120 | 0 | 7.651 | 9.600 | 35.180 |
| ff/1.200V/125C | 120 | 0 | 8.877 | 10.807 | 42.298 |
| tt/1.320V/125C | 120 | 0 | 9.068 | 8.366 | 25.995 |
| fs/1.320V/125C | 120 | 0 | 9.298 | 9.397 | 30.108 |
| sf/1.320V/125C | 120 | 0 | 9.438 | 9.549 | 35.439 |
| ff/1.320V/125C | 120 | 0 | 10.781 | 9.465 | 35.846 |
