# NBA/WNBA TC Backtest Run Summary

## Consolidated historical prop rows

| Sport | Hits | Graded | Hit Rate |
|---|---:|---:|---:|
| NBA | 1418 | 1666 | 85.1% |
| WNBA | 846 | 948 | 89.2% |

## By sport/stat

| Sport | Stat | Hits | Graded | Hit Rate |
|---|---|---:|---:|---:|
| NBA | 3PM | 273 | 280 | 97.5% |
| NBA | AST | 189 | 281 | 67.3% |
| NBA | BLK | 258 | 266 | 97.0% |
| NBA | PTS | 224 | 290 | 77.2% |
| NBA | REB | 214 | 283 | 75.6% |
| NBA | STL | 260 | 266 | 97.7% |
| WNBA | 3PM | 158 | 158 | 100.0% |
| WNBA | AST | 104 | 158 | 65.8% |
| WNBA | BLK | 158 | 158 | 100.0% |
| WNBA | PTS | 136 | 158 | 86.1% |
| WNBA | REB | 132 | 158 | 83.5% |
| WNBA | STL | 158 | 158 | 100.0% |

## Latest final-boxscore backtest scan

- Final box score report: `live_sports_scrape/NBA_WNBA_Final_Boxscore_Backtest_Report_20260523.md`
- That scan graded 27 rows with 7 hits = 25.9%.
- Note: older saved WNBA projection rows included players who were DNP/MISSING; these must be excluded or marked ungraded, not losses.

## Rule lock

- TC Match applies to player props only: PTS, REB, AST, 3PM, STL, BLK when present.
- Do not use TC Match to grade team totals.
- Backtest schema must include: league, game, team, player, stat, tc/target, actual, pick/direction, hit, source.
