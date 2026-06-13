# WNBA Backtest Report — Pipeline v2 (2026-06-07)

**Date range:** 2026-06-08 → 2026-06-13 (5 days)
**Games covered:** 14 completed WNBA games
**Source:** ESPN v2 scoreboard + boxscore
**Player-games:** 341
**TC picks graded:** 757

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
| ALL | 757 | 463 | 274 | 20 | 62.8% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 171 | 124 | 40 | 7 | 75.6% |
| REB | 166 | 101 | 63 | 2 | 61.6% |
| AST | 152 | 90 | 60 | 2 | 60.0% |
| STL | 107 | 62 | 38 | 7 | 62.0% |
| BLK | 62 | 22 | 40 | 0 | 35.5% |
| TPM | 99 | 64 | 33 | 2 | 66.0% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| SEA | 100 | 68 | 27 | 5 | 71.6% |
| LV | 55 | 42 | 12 | 1 | 77.8% |
| WSH | 64 | 41 | 23 | 0 | 64.1% |
| TOR | 68 | 40 | 27 | 1 | 59.7% |
| CHI | 65 | 39 | 26 | 0 | 60.0% |
| GS | 60 | 39 | 20 | 1 | 66.1% |
| CON | 57 | 36 | 20 | 1 | 64.3% |
| PHX | 68 | 36 | 32 | 0 | 52.9% |
| ATL | 51 | 33 | 15 | 3 | 68.8% |
| IND | 54 | 32 | 19 | 3 | 62.7% |
| NY | 57 | 29 | 24 | 4 | 54.7% |
| DAL | 58 | 28 | 29 | 1 | 49.1% |

## Recommendations & Suggestions

### What to pick more of
- **PTS** — 75.6% over 164 picks. Strong signal.
- **TPM** — 66.0% over 97 picks. Strong signal.
- **STL** — 62.0% over 100 picks. Strong signal.
- **REB** — 61.6% over 164 picks. Strong signal.
- **AST** — 60.0% over 150 picks. Strong signal.

### What to skip or fade
- **BLK** — only 35.5% hit rate over 62 picks. Reduce or skip.

### Top TC performers (best hit rate, min 3 picks)
- **S. Austin** — 8/8 (100.0%)
- **A. Wilson** — 12/12 (100.0%)
- **A. Boston** — 10/11 (90.9%)
- **R. Howard** — 9/10 (90.0%)
- **S. Diggins** — 9/10 (90.0%)
- **C. Gray** — 7/8 (87.5%)
- **A. Thomas** — 7/8 (87.5%)
- **J. Shepard** — 6/7 (85.7%)
- **T. Hayes** — 5/6 (83.3%)
- **B. Sykes** — 10/12 (83.3%)

### Worst TC performers (worst hit rate, min 3 picks)
- **J. Jones** — 0/5 (0.0%)
- **M. Timpson** — 0/4 (0.0%)
- **R. Johnson** — 0/3 (0.0%)
- **I. Borlase** — 0/4 (0.0%)
- **S. Taylor** — 0/6 (0.0%)
- **A. Kuier** — 0/4 (0.0%)
- **C. Leger-Walker** — 1/7 (14.3%)
- **J. Nogic** — 1/7 (14.3%)
- **M. Siegrist** — 1/6 (16.7%)
- **A. Smith** — 1/6 (16.7%)

### Tuning improvements (vs un-tuned baseline)

| Stat | Tuned Hit% | Notes |
|---|---:|---|
| STL | 62.0% | 0.80x CONS, min avg 0.05 |
| BLK | 35.5% | 0.80x CONS, min avg 0.05 |
| REB | 61.6% | 0.85x CONS — strongest signal |

## Files
- Actuals: `/home/workspace/Daily_Log/wnba_pipeline_20260613_051842/actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_pipeline_20260613_051842/proj.csv`
- Summary: `/home/workspace/Daily_Log/wnba_pipeline_20260613_051842/summary.json`
