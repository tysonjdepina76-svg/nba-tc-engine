# Multi-Sport Backtest — 2026-06-30

**Method:** Match historical `picks.csv` to `live_sports_scrape/*_final_boxscore.csv` by (sport, matchup, player, stat).

**Caveat:** Only 10 boxscore files exist in `live_sports_scrape/`. Most picks have `market_line` empty (DK feed was silent for WNBA 6/8-6/14). Only picks WITH a real line AND a matching boxscore can be graded.

## Summary

| Sport | Picks | With Line | With Boxscore | Graded | HIT | MISS | PUSH | Hit Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NBA | 864 | 864 | 0 | 0 | 0 | 0 | 0 | n/a% |
| WNBA | 1487 | 1487 | 0 | 0 | 0 | 0 | 0 | n/a% |
| MLB | 4526 | 4526 | 0 | 0 | 0 | 0 | 0 | n/a% |
| SOCCER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a% |

## Boxscores loaded

| Sport | Matchup | Date (file mtime) | Players |
|---|---|---|---:|
| NBA | DAL@ATL | 2026-06-09 | 24 |
| NBA | GS@IND | 2026-06-09 | 24 |
| NBA | GS@NY | 2026-06-09 | 22 |
| NBA | LA@PHX | 2026-06-09 | 25 |
| NBA | NY@CLE | 2026-06-09 | 30 |
| NBA | OKC@SA | 2026-06-09 | 0 |
| NBA | TOR@MIN | 2026-06-09 | 27 |
| WNBA | LA@LV | 2026-06-09 | 22 |
| WNBA | MIN@CHI | 2026-06-09 | 26 |
| WNBA | POR@TOR | 2026-06-09 | 26 |

## Hit rate by stat (where graded)
