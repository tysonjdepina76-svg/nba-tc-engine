# NBA/WNBA Final Box Score Backtest — 2026-05-23

## Schema repair applied
- Rows with no matching box-score player are now marked **DNP/MISSING**, not counted as losses.
- Backtest requires saved fields: `date, league, game_id, team, player, stat, tc, target, pick, actual, result, source`.
- TC Match remains **player props only**: PTS, REB, AST, 3PM. Team/game totals are not TC Match.

Final box score files scanned: 9
Rows found: 27
Graded rows matched: 27
Hit rate: 7/27 = 25.9%


## Audit Correction — Why the 25.9% was misleading

The prior 25.9% scan is **not a valid model-grade**. It mixed a stale May 14 projection source with May 23 final box scores and counted several non-matched/DNP rows as zero-stat losses. That created false losses, especially for Napheesa Collier, Courtney Vandersloot, and Emma Cannon rows where the matching box-score row was not present in the May 23 files.

### Corrected grading rule
- Grade only rows with a matching player in the final box score.
- If the player is not in the final box score, mark `DNP/MISSING` and exclude from hit rate.
- Require schema fields: `date, league, game_id, team, player, stat, tc, target, pick, actual, result, source`.
- Pick filter: only export rows where `pick` is explicit (`OVER` or `UNDER`) and edge meets minimum threshold. Full roster projections stay available but are not graded as picks.

## By stat
| Stat | Hits | Graded | Hit Rate |
|---|---:|---:|---:|
| 3PM | 0 | 6 | 0.0% |
| AST | 2 | 7 | 28.6% |
| PTS | 3 | 8 | 37.5% |
| REB | 2 | 6 | 33.3% |

## Graded + missing rows
| Player | Team | Stat | TC | Target | Actual | Result | Source |
|---|---|---:|---:|---:|---:|---:|---|
| Napheesa Collier | MIN | PTS | 21.8 | 18.5 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Napheesa Collier | MIN | REB | 8.5 | 7.2 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Napheesa Collier | MIN | AST | 3.2 | 2.7 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Napheesa Collier | MIN | 3PM | 1.5 | 1.3 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Kayla McBride | MIN | PTS | 14.5 | 12.3 | 13.0 | ✅ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Kayla McBride | MIN | REB | 2.8 | 2.4 | 4.0 | ✅ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Kayla McBride | MIN | AST | 2.5 | 2.1 | 2.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Kayla McBride | MIN | 3PM | 2.2 | 1.9 | 1.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Natasha Howard | MIN | PTS | 14.2 | 12.1 | 13.0 | ✅ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Natasha Howard | MIN | REB | 6.8 | 5.8 | 6.0 | ✅ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Natasha Howard | MIN | AST | 1.8 | 1.5 | 3.0 | ✅ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Natasha Howard | MIN | 3PM | 0.9 | 0.8 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Jacy Sheldon | CHI | PTS | 8.5 | 7.2 | 5.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Jacy Sheldon | CHI | REB | 2.2 | 1.9 | 1.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Jacy Sheldon | CHI | AST | 3.0 | 2.5 | 1.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Jacy Sheldon | CHI | 3PM | 1.5 | 1.3 | 1.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Courtney Vandersloot | CHI | PTS | 8.9 | 7.6 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Courtney Vandersloot | CHI | REB | 3.0 | 2.5 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Courtney Vandersloot | CHI | AST | 7.1 | 6.0 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Courtney Vandersloot | CHI | 3PM | 1.1 | 0.9 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Emma Cannon | LA | PTS | 9.2 | 7.8 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Emma Cannon | LA | REB | 5.5 | 4.7 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Emma Cannon | LA | AST | 1.5 | 1.3 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Emma Cannon | LA | 3PM | 0.8 | 0.7 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Kayla McBride | MIN | PTS | 12.3 | 13.0 | 13.0 | ✅ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Napheesa Collier | MIN | PTS | 18.5 | 19.0 | 0.0 | ❌ | WNBA_PROP_PROJECTIONS_MAY14.md |
| Natasha Howard | MIN | AST | 1.5 | 2.0 | 3.0 | ✅ | WNBA_PROP_PROJECTIONS_MAY14.md |