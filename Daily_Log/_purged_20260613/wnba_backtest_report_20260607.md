# WNBA Backtest Report — 2026-06-07

**Games covered:** 9 completed WNBA games (2026-06-04 → 2026-06-06)
**Games:** ATL@IND, GS@MIN, CON@CHI, DAL@LA, PHX@POR, SEA@MIN, GS@LV, WSH@ATL, IND@NY, CHI@TOR
**Source:** ESPN v2 boxscores
**Total player-games:** 248
**Total TC picks graded:** 364

## Overall Hit Rate

| Bucket | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| ALL | 364 | 164 | 194 | 6 | 45.8% |

## Hit Rate by Stat

| Stat | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| PTS | 82 | 40 | 39 | 3 | 50.6% |
| REB | 85 | 46 | 37 | 2 | 55.4% |
| AST | 67 | 33 | 33 | 1 | 50.0% |
| STL | 45 | 14 | 31 | 0 | 31.1% |
| BLK | 33 | 11 | 22 | 0 | 33.3% |
| TPM | 52 | 20 | 32 | 0 | 38.5% |

## Hit Rate by Team

| Team | Picks | Hit | Miss | Push | Hit% |
|---|---:|---:|---:|---:|---:|
| ATL | 79 | 32 | 45 | 2 | 41.6% |
| CHI | 72 | 32 | 40 | 0 | 44.4% |
| GS | 74 | 38 | 35 | 1 | 52.1% |
| IND | 69 | 33 | 35 | 1 | 48.5% |
| MIN | 70 | 29 | 39 | 2 | 42.6% |

## Methodology

TC projection = leave-one-out mean × per-stat CONS (PTS/REB/AST/3PM=0.85x, STL/BLK=0.80x). Grade = actual vs TC projection: HIT if actual > TC, MISS if actual < TC, PUSH if |actual - TC| < 0.1. Players with raw_avg < 0.5 excluded.

## Files

- Actuals: `/home/workspace/Daily_Log/wnba_recent_actuals.json`
- Picks:   `/home/workspace/Daily_Log/wnba_recent_proj.csv`
## Recommendations & Suggestions

### What to pick more of
- **REB** — 55.4% hit rate over 83 picks. Strong signal.
- **PTS** — 50.6% hit rate over 79 picks. Solid signal.
- **AST** — 50.0% hit rate over 66 picks. Solid signal.

### What to skip or fade
- **STL** — only 31.1% hit rate. Consider reducing or skipping.
- **BLK** — only 33.3% hit rate. Consider reducing or skipping.
- **TPM** — only 38.5% hit rate. Consider reducing or skipping.

### Team-level takeaways
- **GS** — 52.1% hit rate, 73 picks → NEUTRAL
- **IND** — 48.5% hit rate, 68 picks → NEUTRAL
- **CHI** — 44.4% hit rate, 72 picks → NEUTRAL
- **MIN** — 42.6% hit rate, 68 picks → NEUTRAL
- **ATL** — 41.6% hit rate, 77 picks → AVOID

### Top TC performers (hit the most)
- **C. Clark** — 9/10 (90.0%)
- **N. Hillmon** — 8/10 (80.0%)
- **T. Hayes** — 8/10 (80.0%)
- **A. Boston** — 6/11 (54.5%)
- **G. Williams** — 6/10 (60.0%)
- **N. Coffey** — 6/11 (54.5%)
- **K. Cardoso** — 6/8 (75.0%)
- **R. Banham** — 6/9 (66.7%)
- **E. Williams** — 6/10 (60.0%)
- **A. Gray** — 5/8 (62.5%)

### Worst TC performers (most misses)
- **R. Howard** — 6/9 miss (33.3%)
- **T. Paopao** — 6/8 miss (25.0%)
- **L. Hull** — 6/8 miss (25.0%)
- **M. Hines-Allen** — 6/9 miss (33.3%)
- **K. Charles** — 6/7 miss (14.3%)
- **N. Cloud** — 6/9 miss (33.3%)
- **A. Reese** — 5/8 miss (37.5%)
- **S. Kone** — 5/7 miss (28.6%)
- **I. Borlase** — 5/7 miss (28.6%)
- **A. Boston** — 5/11 miss (54.5%)

### Tuning suggestions
- **Overall hit rate: 45.8%** (TC formula at 0.85x avg)
  - TC is **conservative at 0.85x**, but hitting <50% suggests the base average is overweighting recent high games.
  - Consider tightening to **0.80x** for STL/BLK (which are noisier) and keeping PTS/REB/AST at 0.85x.
- **STL/BLK are noisy** — limit to +1.5 lines or skip altogether in WNBA.
- **WNBA backtest uses leave-one-out** from 3 days of data. Real production uses ESPN's season-long averages and injury filters, which should tighten variance.
- **Add team-pace adjustment** — fast-paced teams (LV, CHI) over/under-projected in current model.
- **Track rest days / back-to-backs** — biggest source of variance not yet captured.

### Next backtest priorities
1. Add WNBA box-score fetch for **last 14 days** (currently 3) to deepen sample
2. Pull in **DK prop lines** to grade against market, not just TC projection
3. Add **starter-locked** rosters (current uses whoever played, regardless of starter/bench)
4. Add **minutes projection** as a gate — drop players projected under 12 min
