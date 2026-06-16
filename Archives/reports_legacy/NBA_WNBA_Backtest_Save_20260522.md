# NBA/WNBA Backtest Save — May 22, 2026

**Saved at:** 2026-05-23T19:07:51

## Rule locked into backtest package
- TC Match is **player-prop only**: points, rebounds, assists, and 3-point shots made.
- Game/team totals are **not** graded using TC Match.
- Backtest rows must preserve: `league`, `game`, `team`, `player`, `stat`, `tc`, `target/line`, `actual`, `pick`, `hit`, and `source_file`.

## Final box score files saved
- `live_sports_scrape/DAL_ATL_401856927_final_boxscore.csv`
- `live_sports_scrape/GS_IND_401856928_final_boxscore.csv`
- `live_sports_scrape/GS_NY_401856924_final_boxscore.csv`
- `live_sports_scrape/LA_PHX_401856926_final_boxscore.csv`
- `live_sports_scrape/TOR_MIN_401856925_final_boxscore.csv`

## Halftime/live box score files saved
- `live_sports_scrape/CON_SEA_401856929_halftime_boxscore.csv`

## Existing NBA/WNBA backtest files indexed
- `tc-workspace/data/NBA_BACKTEST_LOG.csv`
- `tc-workspace/data/WNBA_BACKTEST_LOG.csv`
- `tc-workspace/reports/BOS_vs_PHI_Full_Series_Backtest.md`
- `tc-workspace/reports/BOS_vs_PHI_Game5_TC_v8_BACKTEST.md`
- `tc-workspace/reports/NBA_BACKTEST_LOG.md`
- `tc-workspace/reports/NBA_Conference_Finals_WNBA_TC_Backtest.md`
- `tc-workspace/reports/NBA_Playoffs_Round1_Backtest.md`
- `tc-workspace/reports/NBA_TC_Backtest_Apr19.md`
- `tc-workspace/reports/NBA_TC_Backtest_Log.md`
- `tc-workspace/reports/NBA_TC_CLE_NYK_ECF_Game1_Pregame_Backtest.md`
- `tc-workspace/reports/NBA_TC_Playoffs_Backtest_Report.md`
- `tc-workspace/reports/TC_Backtest_Hit_Rate_Report_20260521.md`
- `tc-workspace/reports/TC_Backtest_Projections_May18_2026.md`
- `tc-workspace/reports/TC_Historical_Prop_Backtest_Report_20260521.md`
- `tc-workspace/reports/TC_Prop_Bet_Backtest_Report_20260521.md`
- `tc-workspace/reports/WNBA_BACKTEST_ACTUAL_VS_TC.md`
- `tc-workspace/reports/WNBA_BACKTEST_LOG.md`
- `tc-workspace/reports/WNBA_BACKTEST_MAY14.md`
- `tc-workspace/reports/WNBA_BACKTEST_MAY14.txt`
- `tc-workspace/reports/WNBA_BACKTEST_ROSTER_REPORT.md`
- `tc-workspace/reports/WNBA_May18_Backtest_From_Saved_Projections.md`
- `tc-workspace/reports/WNBA_TC_ROSTER_BACKTEST_MAY14.md`

## Next grading step
Use the saved final box scores against saved projection cards only when the projection card includes player/stat/TC/target/pick direction. Missing pick direction should be marked `UNGRADED`, not a loss.