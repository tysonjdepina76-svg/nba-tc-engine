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
| ALL | 2882 | 1319 | 1488 | 75 | 47.0% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 540 | 286 | 244 | 10 | 54.0% |
| REB | 539 | 287 | 238 | 14 | 54.7% |
| AST | 492 | 241 | 240 | 11 | 50.1% |
| STL | 490 | 203 | 271 | 16 | 42.8% |
| BLK | 364 | 104 | 255 | 5 | 29.0% |
| TPM | 457 | 198 | 240 | 19 | 45.2% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| POR | 332 | 152 | 168 | 12 | 47.5% |
| GS | 270 | 132 | 131 | 7 | 50.2% |
| SEA | 242 | 113 | 123 | 6 | 47.9% |
| MIN | 217 | 102 | 109 | 6 | 48.3% |
| NY | 198 | 97 | 98 | 3 | 49.7% |
| ATL | 235 | 92 | 136 | 7 | 40.4% |
| CHI | 208 | 87 | 113 | 8 | 43.5% |
| IND | 173 | 82 | 84 | 7 | 49.4% |
| WSH | 177 | 81 | 95 | 1 | 46.0% |
| LA | 175 | 79 | 90 | 6 | 46.7% |
| PHX | 151 | 71 | 79 | 1 | 47.3% |
| TOR | 163 | 70 | 90 | 3 | 43.8% |
| CON | 145 | 69 | 72 | 4 | 48.9% |
| LV | 113 | 55 | 54 | 4 | 50.5% |
| DAL | 83 | 37 | 46 | 0 | 44.6% |

## Recommendations & Suggestions

### What to pick more of
- **REB** — 54.7% over 525 picks. Solid signal.
- **PTS** — 54.0% over 530 picks. Solid signal.
- **AST** — 50.1% over 481 picks. Solid signal.

### What to skip or fade
- **BLK** — only 29.0% hit rate over 359 picks. Reduce or skip.

### Top TC performers (best hit rate, min 3 picks)
- **L. Lacan** — 10/14 (71.4%)
- **M. Caldwell** — 21/30 (70.0%)
- **J. Shepard** — 8/12 (66.7%)
- **S. Cunningham** — 13/20 (65.0%)
- **A. Morrow** — 18/28 (64.3%)
- **K. Samuelson** — 16/25 (64.0%)
- **J. Melbourne** — 18/29 (62.1%)
- **M. Mabrey** — 14/23 (60.9%)
- **J. Salaun** — 21/35 (60.0%)
- **N. Howard** — 15/25 (60.0%)

### Worst TC performers (worst hit rate, min 3 picks)
- **I. Harrison** — 0/15 (0.0%)
- **G. Jaquez** — 0/16 (0.0%)
- **D. Malonga** — 0/12 (0.0%)
- **T. Key** — 2/16 (12.5%)
- **N. Angloma** — 5/21 (23.8%)
- **D. Bonner** — 7/27 (25.9%)
- **S. Kone** — 6/23 (26.1%)
- **A. Delaere** — 6/23 (26.1%)
- **A. Ogunbowale** — 4/13 (30.8%)
- **A. Kosu** — 7/22 (31.8%)

### Tuning improvements (vs un-tuned baseline)

| Stat | Tuned Hit% | Notes |
|---|---:|---|
| STL | 42.8% | 0.80x CONS, min avg 0.05 |
| BLK | 29.0% | 0.80x CONS, min avg 0.05 |
| REB | 54.7% | 0.85x CONS — strongest signal |

## Files
- Actuals: `/home/workspace/Daily_Log/wnba_pipeline_20260608_020106/actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_pipeline_20260608_020106/proj.csv`
- Summary: `/home/workspace/Daily_Log/wnba_pipeline_20260608_020106/summary.json`
