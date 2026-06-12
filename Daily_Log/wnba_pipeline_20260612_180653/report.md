# WNBA Backtest Report — Pipeline v2 (2026-06-07)

**Date range:** 2026-06-07 → 2026-06-12 (5 days)
**Games covered:** 14 completed WNBA games
**Source:** ESPN v2 scoreboard + boxscore
**Player-games:** 344
**TC picks graded:** 762

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
| ALL | 762 | 459 | 285 | 18 | 61.7% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 172 | 121 | 43 | 8 | 73.8% |
| REB | 169 | 104 | 64 | 1 | 61.9% |
| AST | 147 | 87 | 58 | 2 | 60.0% |
| STL | 110 | 62 | 43 | 5 | 59.0% |
| BLK | 62 | 23 | 39 | 0 | 37.1% |
| TPM | 102 | 62 | 38 | 2 | 62.0% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| CHI | 118 | 68 | 48 | 2 | 58.6% |
| LV | 55 | 42 | 12 | 1 | 77.8% |
| TOR | 62 | 39 | 23 | 0 | 62.9% |
| LA | 62 | 39 | 23 | 0 | 62.9% |
| SEA | 58 | 39 | 17 | 2 | 69.6% |
| POR | 62 | 38 | 23 | 1 | 62.3% |
| CON | 57 | 36 | 20 | 1 | 64.3% |
| PHX | 68 | 36 | 32 | 0 | 52.9% |
| ATL | 51 | 33 | 15 | 3 | 68.8% |
| IND | 54 | 32 | 19 | 3 | 62.7% |
| NY | 57 | 29 | 24 | 4 | 54.7% |
| DAL | 58 | 28 | 29 | 1 | 49.1% |

## Recommendations & Suggestions

### What to pick more of
- **PTS** — 73.8% over 164 picks. Strong signal.
- **TPM** — 62.0% over 100 picks. Strong signal.
- **REB** — 61.9% over 168 picks. Strong signal.
- **AST** — 60.0% over 145 picks. Strong signal.
- **STL** — 59.0% over 105 picks. Strong signal.

### What to skip or fade
- **BLK** — only 37.1% hit rate over 62 picks. Reduce or skip.

### Top TC performers (best hit rate, min 3 picks)
- **A. Wilson** — 12/12 (100.0%)
- **A. Boston** — 10/11 (90.9%)
- **N. Ogwumike** — 9/10 (90.0%)
- **K. Plum** — 9/10 (90.0%)
- **R. Howard** — 9/10 (90.0%)
- **N. Hiedeman** — 8/9 (88.9%)
- **F. Johnson** — 7/8 (87.5%)
- **C. Gray** — 7/8 (87.5%)
- **A. Thomas** — 7/8 (87.5%)
- **E. Engstler** — 6/7 (85.7%)

### Worst TC performers (worst hit rate, min 3 picks)
- **J. Jones** — 0/5 (0.0%)
- **M. Timpson** — 0/4 (0.0%)
- **R. Johnson** — 0/3 (0.0%)
- **I. Borlase** — 0/4 (0.0%)
- **A. Kuier** — 0/4 (0.0%)
- **C. Leger-Walker** — 1/7 (14.3%)
- **J. Nogic** — 1/7 (14.3%)
- **S. Taylor** — 2/13 (15.4%)
- **M. Siegrist** — 1/6 (16.7%)
- **A. Smith** — 1/6 (16.7%)

### Tuning improvements (vs un-tuned baseline)

| Stat | Tuned Hit% | Notes |
|---|---:|---|
| STL | 59.0% | 0.80x CONS, min avg 0.05 |
| BLK | 37.1% | 0.80x CONS, min avg 0.05 |
| REB | 61.9% | 0.85x CONS — strongest signal |

## Files
- Actuals: `/home/workspace/Daily_Log/wnba_pipeline_20260612_180653/actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_pipeline_20260612_180653/proj.csv`
- Summary: `/home/workspace/Daily_Log/wnba_pipeline_20260612_180653/summary.json`
