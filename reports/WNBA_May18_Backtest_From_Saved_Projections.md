# WNBA May 18 Backtest — From Saved TC Projections

**Games:** WSH @ DAL, CON @ POR  
**Projection file used:** `WNBA_TC_Projections_May18_2026.md`  
**Box score sources:** ESPN API final box scores  

## Final scores scraped

| Game | Final | Files |
|---|---|---|
| WSH @ DAL | DAL 92, WSH 69 | `live_sports_scrape/WSH_DAL_boxscore.csv`, `live_sports_scrape/WSH_DAL_boxscore.md` |
| CON @ POR | POR 83, CON 82 | `live_sports_scrape/CON_POR_boxscore.csv`, `live_sports_scrape/CON_POR_boxscore.md` |

## Important note

The saved projection file from May 18 contains WNBA projection tables, but several players/teams were not aligned to the live ESPN final box-score rosters. Because of that, a full player-by-player prop grading would produce many `MISSING` rows and would not be a clean diagnostic.

## Clean team-level result from final scores

| Game | Saved TC lean | Market line | Final total | Result |
|---|---:|---:|---:|---|
| WSH @ DAL | UNDER | 158.5 | 161 | ❌ MISS |
| CON @ POR | UNDER | 168.0 | 165 | ✅ HIT |

**Team-total/context lean record:** 1/2 = **50.0%**

## Next fix required before prop backtesting

Use the corrected WNBA live engine to generate projections directly from ESPN API rosters/player stats, then grade against ESPN API box scores. That prevents stale roster names and team mismatches from contaminating the prop backtest.
