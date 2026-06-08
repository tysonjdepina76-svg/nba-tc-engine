# WNBA Backtest Report — Pipeline v2 (2026-06-07)

**Date range:** 2026-05-25 → 2026-06-08 (14 days)
**Games covered:** 36 completed WNBA games
**Source:** ESPN v2 scoreboard + boxscore
**Player-games:** 878
**TC picks graded:** 2882

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
| ALL | 2882 | 1451 | 1356 | 75 | 51.7% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 540 | 331 | 200 | 9 | 62.3% |
| REB | 539 | 291 | 237 | 11 | 55.1% |
| AST | 492 | 250 | 227 | 15 | 52.4% |
| STL | 490 | 228 | 243 | 19 | 48.4% |
| BLK | 364 | 117 | 245 | 2 | 32.3% |
| TPM | 457 | 234 | 204 | 19 | 53.4% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| POR | 332 | 162 | 162 | 8 | 50.0% |
| GS | 270 | 134 | 130 | 6 | 50.8% |
| MIN | 217 | 116 | 90 | 11 | 56.3% |
| SEA | 242 | 116 | 122 | 4 | 48.7% |
| ATL | 235 | 105 | 120 | 10 | 46.7% |
| CHI | 208 | 102 | 103 | 3 | 49.8% |
| NY | 198 | 100 | 91 | 7 | 52.4% |
| IND | 173 | 95 | 78 | 0 | 54.9% |
| LA | 175 | 93 | 78 | 4 | 54.4% |
| WSH | 177 | 85 | 91 | 1 | 48.3% |
| TOR | 163 | 82 | 77 | 4 | 51.6% |
| CON | 145 | 75 | 65 | 5 | 53.6% |
| PHX | 151 | 71 | 76 | 4 | 48.3% |
| LV | 113 | 71 | 41 | 1 | 63.4% |
| DAL | 83 | 44 | 32 | 7 | 57.9% |

## Recommendations & Suggestions

### What to pick more of
- **PTS** — 62.3% over 531 picks. Strong signal.
- **REB** — 55.1% over 528 picks. Strong signal.
- **TPM** — 53.4% over 438 picks. Solid signal.
- **AST** — 52.4% over 477 picks. Solid signal.

### What to skip or fade
- **BLK** — only 32.3% hit rate over 362 picks. Reduce or skip.

### Top TC performers (best hit rate, min 3 picks)
- **A. Morrow** — 22/27 (81.5%)
- **J. Young** — 16/20 (80.0%)
- **M. Mabrey** — 19/24 (79.2%)
- **E. Williams** — 18/24 (75.0%)
- **J. Canada** — 18/24 (75.0%)
- **A. Wilson** — 18/24 (75.0%)
- **C. Clark** — 18/24 (75.0%)
- **N. Coffey** — 22/30 (73.3%)
- **J. Shepard** — 8/11 (72.7%)
- **N. Howard** — 18/25 (72.0%)

### Worst TC performers (worst hit rate, min 3 picks)
- **I. Harrison** — 0/15 (0.0%)
- **G. Jaquez** — 0/16 (0.0%)
- **D. Malonga** — 0/12 (0.0%)
- **T. Key** — 1/16 (6.2%)
- **N. Angloma** — 5/21 (23.8%)
- **T. Paopao** — 7/28 (25.0%)
- **D. Bonner** — 7/27 (25.9%)
- **S. Kone** — 6/23 (26.1%)
- **I. Borlase** — 6/23 (26.1%)
- **A. Delaere** — 6/23 (26.1%)

### Tuning improvements (vs un-tuned baseline)

| Stat | Tuned Hit% | Notes |
|---|---:|---|
| STL | 48.4% | 0.80x CONS, min avg 0.05 |
| BLK | 32.3% | 0.80x CONS, min avg 0.05 |
| REB | 55.1% | 0.85x CONS — strongest signal |

## Files
- Actuals: `/home/workspace/Daily_Log/wnba_pipeline_20260608_023534/actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_pipeline_20260608_023534/proj.csv`
- Summary: `/home/workspace/Daily_Log/wnba_pipeline_20260608_023534/summary.json`
