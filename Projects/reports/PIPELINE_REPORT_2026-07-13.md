# TC Pipeline Report — 2026-07-13

## Health Check
- 4/7 OK (MLB, WNBA, WC, SOCCER)
- 3 disabled (NBA/NFL/NHL off-season)
- 0 errors

## Picks Generated
- WNBA: 5 picks saved to data/picks/wnba_2026-07-13.csv
- MLB/WC: 0 picks (fetchers returned no player data — self-edge fallback in use)

## Codebase
- 175 Python files (down from 338 — purge removed dead files)
- 0 empty directories (except Trash/)

## Cleanup Actions
- Removed duplicate engine.py / entities.py at root
- Removed fix_pipeline*.py (one-time fix scripts)
- Removed mlb_backtest_today.py (replaced by pipeline)
- Removed stale CSVs (>30d old)
- Removed old logs (>7d old)
- Removed 4 empty directories (models, Daily_Log/boxscores, Daily_Log/budget, Trash root)
- Archived older versions: archive/v1_2026-07-13.tar.gz

## Gaps Closed
- Created src/domain/entities.py (Registry + SportConfig)
- Created src/adapters/cache_adapter.py
- Created src/adapters/odds_api_adapter.py
- Created src/adapters/fantasy_combo_generator.py
- Created tc_dashboard.py (Streamlit UI)
- Created daily_picks.py (cron entry)
- Created requirements.txt
- Created README.md
- Wired all 4 fetchers into Registry
- Wrote 109 integration test (all pass)

## Artifacts
- Archive: archive/v1_2026-07-13.tar.gz (257K)
- Picks: data/picks/wnba_2026-07-13.{csv,json}
- This report: reports/PIPELINE_REPORT_2026-07-13.md
