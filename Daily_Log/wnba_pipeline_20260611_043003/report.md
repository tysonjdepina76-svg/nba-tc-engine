# WNBA Backtest Report — Pipeline v2 (2026-06-07)

**Date range:** 2026-05-28 → 2026-06-11 (14 days)
**Games covered:** 37 completed WNBA games
**Source:** ESPN v2 scoreboard + boxscore
**Player-games:** 900
**TC picks graded:** 2865

## Methodology

TC formula: leave-one-out mean × per-stat CONS multiplier
- PTS/REB/AST/3PM = 0.85x
- STL/BLK = 0.80x (tighter — these are noisier in WNBA)
- Starter gate: drop players with last-game minutes < 12
- Team-pace: +3% for ATL,CHI,IND,LV, -3% for MIN,NY,SEA
- B2B: -5% if back-to-back detected
- Grade: HIT if actual > TC, MISS if actual < TC, PUSH if |actual − TC| < 0.1

## Overall Hit Rate

| Bucket | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| ALL | 2865 | 1471 | 1314 | 80 | 52.8% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 530 | 332 | 189 | 9 | 63.7% |
| REB | 525 | 296 | 221 | 8 | 57.3% |
| AST | 486 | 249 | 220 | 17 | 53.1% |
| STL | 481 | 228 | 228 | 25 | 50.0% |
| BLK | 382 | 125 | 257 | 0 | 32.7% |
| TPM | 461 | 241 | 199 | 21 | 54.8% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| GS | 271 | 133 | 128 | 10 | 51.0% |
| LA | 223 | 129 | 89 | 5 | 59.2% |
| SEA | 239 | 122 | 110 | 7 | 52.6% |
| MIN | 223 | 119 | 95 | 9 | 55.6% |
| CHI | 211 | 115 | 94 | 2 | 55.0% |
| IND | 210 | 102 | 103 | 5 | 49.8% |
| POR | 224 | 102 | 119 | 3 | 46.2% |
| PHX | 192 | 93 | 93 | 6 | 50.0% |
| LV | 152 | 87 | 59 | 6 | 59.6% |
| CON | 178 | 84 | 88 | 6 | 48.8% |
| ATL | 142 | 83 | 52 | 7 | 61.5% |
| TOR | 155 | 81 | 67 | 7 | 54.7% |
| NY | 157 | 78 | 78 | 1 | 50.0% |
| DAL | 144 | 74 | 65 | 5 | 53.2% |
| WSH | 144 | 69 | 74 | 1 | 48.3% |

## Recommendations & Suggestions

### What to pick more of
- **PTS** — 63.7% over 521 picks. Strong signal.
- **REB** — 57.3% over 517 picks. Strong signal.
- **TPM** — 54.8% over 440 picks. Solid signal.
- **AST** — 53.1% over 469 picks. Solid signal.
- **STL** — 50.0% over 456 picks. Solid signal.

### What to skip or fade
- **BLK** — only 32.7% hit rate over 382 picks. Reduce or skip.

### Top TC performers (best hit rate, min 3 picks)
- **S. Citron** — 15/18 (83.3%)
- **A. Wilson** — 20/26 (76.9%)
- **N. Ogwumike** — 27/36 (75.0%)
- **O. Miles** — 21/28 (75.0%)
- **J. Shepard** — 11/15 (73.3%)
- **K. Cardoso** — 18/25 (72.0%)
- **A. Boston** — 20/28 (71.4%)
- **C. Clark** — 21/30 (70.0%)
- **S. Rivers** — 21/30 (70.0%)
- **J. Canada** — 16/23 (69.6%)

### Worst TC performers (worst hit rate, min 3 picks)
- **D. Dantas** — 0/12 (0.0%)
- **R. Carrera** — 0/9 (0.0%)
- **G. Jaquez** — 3/18 (16.7%)
- **A. Edwards** — 4/18 (22.2%)
- **N. Puoch** — 3/13 (23.1%)
- **C. McMahon** — 6/21 (28.6%)
- **M. Billings** — 8/26 (30.8%)
- **L. Betts** — 5/16 (31.2%)
- **A. Delaere** — 8/24 (33.3%)
- **I. Harrison** — 6/18 (33.3%)

### Tuning improvements (vs un-tuned baseline)

| Stat | Tuned Hit% | Notes |
|---|---:|---|
| STL | 50.0% | 0.80x CONS, min avg 0.05 |
| BLK | 32.7% | 0.80x CONS, min avg 0.05 |
| REB | 57.3% | 0.85x CONS — strongest signal |

## Files
- Actuals: `/home/workspace/Daily_Log/wnba_pipeline_20260611_043003/actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_pipeline_20260611_043003/proj.csv`
- Summary: `/home/workspace/Daily_Log/wnba_pipeline_20260611_043003/summary.json`
