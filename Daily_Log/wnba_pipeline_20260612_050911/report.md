# WNBA Backtest Report — Pipeline v2 (2026-06-07)

**Date range:** 2026-05-29 → 2026-06-12 (14 days)
**Games covered:** 39 completed WNBA games
**Source:** ESPN v2 scoreboard + boxscore
**Player-games:** 950
**TC picks graded:** 3093

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
| ALL | 3093 | 1653 | 1357 | 83 | 54.9% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 565 | 377 | 173 | 15 | 68.5% |
| REB | 565 | 333 | 223 | 9 | 59.9% |
| AST | 532 | 283 | 243 | 6 | 53.8% |
| STL | 529 | 250 | 243 | 36 | 50.7% |
| BLK | 414 | 138 | 276 | 0 | 33.3% |
| TPM | 488 | 272 | 199 | 17 | 57.7% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| CHI | 270 | 143 | 119 | 8 | 54.6% |
| LA | 223 | 137 | 85 | 1 | 61.7% |
| SEA | 239 | 129 | 106 | 4 | 54.9% |
| MIN | 223 | 126 | 83 | 14 | 60.3% |
| POR | 262 | 125 | 134 | 3 | 48.3% |
| PHX | 264 | 121 | 135 | 8 | 47.3% |
| GS | 224 | 119 | 99 | 6 | 54.6% |
| NY | 219 | 115 | 102 | 2 | 53.0% |
| ATL | 199 | 114 | 76 | 9 | 60.0% |
| LV | 149 | 102 | 44 | 3 | 69.9% |
| IND | 195 | 97 | 90 | 8 | 51.9% |
| TOR | 155 | 87 | 63 | 5 | 58.0% |
| CON | 178 | 87 | 87 | 4 | 50.0% |
| DAL | 149 | 81 | 61 | 7 | 57.0% |
| WSH | 144 | 70 | 73 | 1 | 49.0% |

## Recommendations & Suggestions

### What to pick more of
- **PTS** — 68.5% over 550 picks. Strong signal.
- **REB** — 59.9% over 556 picks. Strong signal.
- **TPM** — 57.7% over 471 picks. Strong signal.
- **AST** — 53.8% over 526 picks. Solid signal.
- **STL** — 50.7% over 493 picks. Solid signal.

### What to skip or fade
- **BLK** — only 33.3% hit rate over 414 picks. Reduce or skip.

### Top TC performers (best hit rate, min 3 picks)
- **J. Shepard** — 14/16 (87.5%)
- **A. Wilson** — 25/30 (83.3%)
- **N. Ogwumike** — 29/36 (80.6%)
- **A. Boston** — 24/30 (80.0%)
- **J. Young** — 24/30 (80.0%)
- **S. Citron** — 14/18 (77.8%)
- **O. Miles** — 21/27 (77.8%)
- **A. Reese** — 26/35 (74.3%)
- **M. Mabrey** — 17/23 (73.9%)
- **E. Williams** — 19/26 (73.1%)

### Worst TC performers (worst hit rate, min 3 picks)
- **A. Kuier** — 0/4 (0.0%)
- **I. Borlase** — 6/27 (22.2%)
- **A. Edwards** — 4/18 (22.2%)
- **A. Smith** — 4/18 (22.2%)
- **G. Jaquez** — 6/22 (27.3%)
- **M. Timpson** — 6/22 (27.3%)
- **C. McMahon** — 6/21 (28.6%)
- **K. Samuelson** — 10/35 (28.6%)
- **L. Betts** — 5/16 (31.2%)
- **R. Gardner** — 9/28 (32.1%)

### Tuning improvements (vs un-tuned baseline)

| Stat | Tuned Hit% | Notes |
|---|---:|---|
| STL | 50.7% | 0.80x CONS, min avg 0.05 |
| BLK | 33.3% | 0.80x CONS, min avg 0.05 |
| REB | 59.9% | 0.85x CONS — strongest signal |

## Files
- Actuals: `/home/workspace/Daily_Log/wnba_pipeline_20260612_050911/actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_pipeline_20260612_050911/proj.csv`
- Summary: `/home/workspace/Daily_Log/wnba_pipeline_20260612_050911/summary.json`
