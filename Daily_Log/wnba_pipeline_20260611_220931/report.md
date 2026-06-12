# WNBA Backtest Report — Pipeline v2 (2026-06-07)

**Date range:** 2026-06-06 → 2026-06-11 (5 days)
**Games covered:** 14 completed WNBA games
**Source:** ESPN v2 scoreboard + boxscore
**Player-games:** 346
**TC picks graded:** 760

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
| ALL | 760 | 455 | 295 | 10 | 60.7% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 173 | 120 | 51 | 2 | 70.2% |
| REB | 168 | 107 | 58 | 3 | 64.8% |
| AST | 150 | 87 | 60 | 3 | 59.2% |
| STL | 102 | 56 | 45 | 1 | 55.4% |
| BLK | 56 | 17 | 38 | 1 | 30.9% |
| TPM | 111 | 68 | 43 | 0 | 61.3% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| SEA | 104 | 62 | 42 | 0 | 59.6% |
| MIN | 71 | 50 | 21 | 0 | 70.4% |
| GS | 65 | 38 | 23 | 4 | 62.3% |
| LA | 62 | 38 | 24 | 0 | 61.3% |
| CHI | 64 | 37 | 25 | 2 | 59.7% |
| TOR | 62 | 36 | 26 | 0 | 58.1% |
| LV | 51 | 35 | 14 | 2 | 71.4% |
| CON | 57 | 35 | 22 | 0 | 61.4% |
| IND | 67 | 34 | 31 | 2 | 52.3% |
| NY | 58 | 33 | 25 | 0 | 56.9% |
| WSH | 54 | 29 | 25 | 0 | 53.7% |
| ATL | 45 | 28 | 17 | 0 | 62.2% |

## Recommendations & Suggestions

### What to pick more of
- **PTS** — 70.2% over 171 picks. Strong signal.
- **REB** — 64.8% over 165 picks. Strong signal.
- **TPM** — 61.3% over 111 picks. Strong signal.
- **AST** — 59.2% over 147 picks. Strong signal.
- **STL** — 55.4% over 101 picks. Strong signal.

### What to skip or fade
- **BLK** — only 30.9% hit rate over 55 picks. Reduce or skip.

### Top TC performers (best hit rate, min 3 picks)
- **O. Miles** — 10/11 (90.9%)
- **N. Ogwumike** — 9/10 (90.0%)
- **K. Plum** — 9/10 (90.0%)
- **C. Gray** — 8/9 (88.9%)
- **S. Austin** — 8/9 (88.9%)
- **B. Stewart** — 8/9 (88.9%)
- **N. Hiedeman** — 13/15 (86.7%)
- **V. Burton** — 6/7 (85.7%)
- **N. Howard** — 9/11 (81.8%)
- **A. Boston** — 9/11 (81.8%)

### Worst TC performers (worst hit rate, min 3 picks)
- **D. Dantas** — 0/4 (0.0%)
- **R. Carrera** — 0/4 (0.0%)
- **C. Leger-Walker** — 1/7 (14.3%)
- **M. Onyenwere** — 1/6 (16.7%)
- **C. Zandalasini** — 1/4 (25.0%)
- **M. Billings** — 2/8 (25.0%)
- **S. Cunningham** — 2/7 (28.6%)
- **M. Caldwell** — 2/6 (33.3%)
- **G. Amoore** — 3/9 (33.3%)
- **A. Dugalic** — 3/9 (33.3%)

### Tuning improvements (vs un-tuned baseline)

| Stat | Tuned Hit% | Notes |
|---|---:|---|
| STL | 55.4% | 0.80x CONS, min avg 0.05 |
| BLK | 30.9% | 0.80x CONS, min avg 0.05 |
| REB | 64.8% | 0.85x CONS — strongest signal |

## Files
- Actuals: `/home/workspace/Daily_Log/wnba_pipeline_20260611_220931/actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_pipeline_20260611_220931/proj.csv`
- Summary: `/home/workspace/Daily_Log/wnba_pipeline_20260611_220931/summary.json`
