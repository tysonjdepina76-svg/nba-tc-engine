# TC Backtest Results & Recalibration Report

Generated: 2026-07-15

## Data integrity
- Graded source files: 22
- Raw rows read: 16294
- Valid graded rows used: 4148
- Date range: 2026-06-18 through 2026-07-09
- Result counts: {'BLANK': 1326, 'PENDING': 10820, 'H': 2665, 'M': 1483}

## Overall by sport
| Sport | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| MLB | 4146 | 2664 | 1482 | 0 | 64.25% |
| WNBA | 2 | 1 | 1 | 0 | 50.0% |

## By stat
| Group | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| total_bases | 1018 | 719 | 299 | 0 | 70.63% |
| hits | 991 | 632 | 359 | 0 | 63.77% |
| rbi | 977 | 607 | 370 | 0 | 62.13% |
| runs | 977 | 577 | 400 | 0 | 59.06% |
| hits_allowed | 58 | 39 | 19 | 0 | 67.24% |
| strikeouts | 48 | 41 | 7 | 0 | 85.42% |
| earned_runs | 47 | 25 | 22 | 0 | 53.19% |
| hr | 30 | 24 | 6 | 0 | 80.0% |
| PTS | 2 | 1 | 1 | 0 | 50.0% |

## By direction
| Group | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| UNDER | 2881 | 2144 | 737 | 0 | 74.42% |
| OVER | 1267 | 521 | 746 | 0 | 41.12% |

## By edge bucket
| Group | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| <0.5 | 2149 | 1239 | 910 | 0 | 57.65% |
| 0.5-1 | 1193 | 752 | 441 | 0 | 63.03% |
| 1-2 | 441 | 341 | 100 | 0 | 77.32% |
| 2-3 | 277 | 249 | 28 | 0 | 89.89% |
| 3-5 | 62 | 58 | 4 | 0 | 93.55% |
| 5+ | 26 | 26 | 0 | 0 | 100.0% |

## By directional projection gap
| Group | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| <0.5 | 1966 | 1105 | 861 | 0 | 56.21% |
| 0.5-1 | 1308 | 830 | 478 | 0 | 63.46% |
| 1-2 | 508 | 396 | 112 | 0 | 77.95% |
| 2-3 | 277 | 249 | 28 | 0 | 89.89% |
| 3-5 | 63 | 59 | 4 | 0 | 93.65% |
| 5+ | 26 | 26 | 0 | 0 | 100.0% |

## By source
| Group | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| sdio_lines | 4047 | 2637 | 1410 | 0 | 65.16% |
| tc-internal-fallback | 99 | 27 | 72 | 0 | 27.27% |
| ESPN Core API (self-edge) | 2 | 1 | 1 | 0 | 50.0% |

## By team
| Group | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| CHC | 240 | 145 | 95 | 0 | 60.42% |
| MIN | 221 | 150 | 71 | 0 | 67.87% |
| BAL | 215 | 136 | 79 | 0 | 63.26% |
| CHW | 208 | 115 | 93 | 0 | 55.29% |
| MIL | 200 | 125 | 75 | 0 | 62.5% |
| LAD | 194 | 130 | 64 | 0 | 67.01% |
| COL | 187 | 129 | 58 | 0 | 68.98% |
| NYM | 186 | 132 | 54 | 0 | 70.97% |
| TOR | 186 | 119 | 67 | 0 | 63.98% |
| SF | 183 | 109 | 74 | 0 | 59.56% |
| CLE | 175 | 123 | 52 | 0 | 70.29% |
| KC | 168 | 113 | 55 | 0 | 67.26% |
| STL | 156 | 94 | 62 | 0 | 60.26% |
| BOS | 151 | 91 | 60 | 0 | 60.26% |
| SD | 150 | 100 | 50 | 0 | 66.67% |
| SEA | 149 | 98 | 51 | 0 | 65.77% |
| ATL | 133 | 73 | 60 | 0 | 54.89% |
| PIT | 131 | 88 | 43 | 0 | 67.18% |
| MIA | 127 | 93 | 34 | 0 | 73.23% |
| NYY | 110 | 77 | 33 | 0 | 70.0% |
| TB | 109 | 65 | 44 | 0 | 59.63% |
| PHI | 106 | 51 | 55 | 0 | 48.11% |
| TEX | 101 | 59 | 42 | 0 | 58.42% |
| CIN | 92 | 71 | 21 | 0 | 77.17% |
| HOU | 81 | 44 | 37 | 0 | 54.32% |
| DET | 75 | 50 | 25 | 0 | 66.67% |
| ARI | 68 | 55 | 13 | 0 | 80.88% |
| LAA | 44 | 29 | 15 | 0 | 65.91% |
| LV | 2 | 1 | 1 | 0 | 50.0% |

## By matchup
| Group | N | Hits | Misses | Pushes | Hit rate |
|---|---:|---:|---:|---:|---:|
| CHC@BAL | 207 | 120 | 87 | 0 | 57.97% |
| SD@LAD | 171 | 110 | 61 | 0 | 64.33% |
| CHC@NYM | 167 | 122 | 45 | 0 | 73.05% |
| MIL@STL | 164 | 76 | 88 | 0 | 46.34% |
| PHI@CIN | 162 | 90 | 72 | 0 | 55.56% |
| BOS@CHW | 157 | 83 | 74 | 0 | 52.87% |
| KC@NYM | 131 | 74 | 57 | 0 | 56.49% |
| LAD@MIN | 121 | 86 | 35 | 0 | 71.07% |
| ATL@PIT | 120 | 78 | 42 | 0 | 65.0% |
| COL@MIN | 120 | 89 | 31 | 0 | 74.17% |
| LAD@SD | 120 | 84 | 36 | 0 | 70.0% |
| SEA@PIT | 119 | 94 | 25 | 0 | 78.99% |
| CHW@CLE | 118 | 84 | 34 | 0 | 71.19% |
| CLE@MIN | 117 | 62 | 55 | 0 | 52.99% |
| SEA@MIA | 114 | 63 | 51 | 0 | 55.26% |
| BAL@LAA | 112 | 71 | 41 | 0 | 63.39% |
| TOR@SF | 112 | 63 | 49 | 0 | 56.25% |
| ATL@SF | 108 | 58 | 50 | 0 | 53.7% |
| ARI@STL | 104 | 89 | 15 | 0 | 85.58% |
| TEX@TOR | 104 | 65 | 39 | 0 | 62.5% |
| KC@TB | 103 | 77 | 26 | 0 | 74.76% |
| BOS@COL | 102 | 78 | 24 | 0 | 76.47% |
| HOU@TOR | 96 | 62 | 34 | 0 | 64.58% |
| TEX@MIA | 92 | 66 | 26 | 0 | 71.74% |
| CLE@CHW | 91 | 63 | 28 | 0 | 69.23% |
| MIL@CIN | 88 | 76 | 12 | 0 | 86.36% |
| NYY@BOS | 74 | 40 | 34 | 0 | 54.05% |
| CHC@MIL | 68 | 50 | 18 | 0 | 73.53% |
| MIN@NYY | 65 | 43 | 22 | 0 | 66.15% |
| COL@SF | 64 | 38 | 26 | 0 | 59.38% |
| SF@COL | 64 | 46 | 18 | 0 | 71.88% |
| KC@CHW | 62 | 42 | 20 | 0 | 67.74% |
| NYY@DET | 56 | 48 | 8 | 0 | 85.71% |
| STL@CHC | 56 | 41 | 15 | 0 | 73.21% |
| TOR@SEA | 55 | 36 | 19 | 0 | 65.45% |
| BAL@CIN | 48 | 33 | 15 | 0 | 68.75% |
| HOU@DET | 48 | 24 | 24 | 0 | 50.0% |
| TB@HOU | 48 | 25 | 23 | 0 | 52.08% |
| NYY@TB | 45 | 29 | 16 | 0 | 64.44% |
| MIA@STL | 40 | 31 | 9 | 0 | 77.5% |
| NYM@ATL | 36 | 16 | 20 | 0 | 44.44% |
| STL@ATL | 30 | 7 | 23 | 0 | 23.33% |
| TB@KC | 19 | 8 | 11 | 0 | 42.11% |
| DET@TEX | 16 | 2 | 14 | 0 | 12.5% |
| NYM@PHI | 16 | 14 | 2 | 0 | 87.5% |
| SF@ATL | 16 | 8 | 8 | 0 | 50.0% |
| CHI@LV | 2 | 1 | 1 | 0 | 50.0% |

## Recalibration conclusions
- Treat the combined backtest as the canonical graded dataset only after confirming it is not a duplicate of the daily graded files.
- Do not use raw edge magnitude as confidence until the edge buckets improve monotonically; recalibrate edge thresholds from out-of-sample results.
- Keep OVER and UNDER thresholds separate. A large direction gap is visible when one direction materially outperforms the other.
- Do not recalibrate from tiny samples. Require at least 30 graded rows for a sport/stat/team/matchup bucket before changing weights or thresholds.
- Exclude SELF_EDGE or internal-fallback rows from sportsbook-value calibration unless they are analyzed in a separate self-edge cohort.
- Freeze any sport/stat bucket below break-even with adequate sample size until its projection bias is corrected and retested.

## Artifacts
- Machine-readable results: `Backtest_Reports/BACKTEST_RECONCILIATION_20260715.json`
