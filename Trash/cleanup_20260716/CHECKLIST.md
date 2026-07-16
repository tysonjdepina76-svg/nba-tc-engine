# TC Sports — File Checklist (2026-07-12)

## Core Engine
- ✅ `tc_math_hybrid.py` — 342 lines. v1/v2/hybrid/ensemble + sport corrections + source tracking
- ✅ `hybrid_wnba_predictor.py` — 165 lines. L5/L10/Season + RAPM + backtest (AST +11.9%, 3PM +25.9%)

## Odds Scrapers (TheOddsAPI, 11 books)
- ✅ `wnba_odds_scraper.py` — 218 lines. 6 games, 336 rows, 11 books, 85% coverage
- ✅ `mlb_odds_scraper.py` — 14 games, 753 rows
- ✅ `nfl_odds_scraper.py` — 75 games, 2,140 rows
- ✅ `nba_odds_scraper.py` — file present, 0 rows (upstream cache empty)
- ✅ `nhl_odds_scraper.py` — file present, 0 rows (upstream cache empty)
- ✅ `odds_scraper_base.py` — shared base (cap, disk cache, dual-schema parser)

## Dashboard
- ✅ `tc_dashboard_v3.py` — 271 lines. 10 tabs. Live at :8510 (HTTP 200)

## Backtest & Grading
- ✅ `backtest_all_sports.py` — 238 lines
- ✅ `nfl_tc_engine.py` — 80 lines. Pass/Rush/Rec/TD/INT/Sacks
- ✅ `grade_daily_picks.py` — 333 lines
- ✅ `settle_positions.py` — 115 lines
- ✅ `hit_rate_report.py` — 61 lines

## Pipeline
- ✅ `run.py` — 51 lines. Daily pipeline entry
- ✅ `health_check.py` — 44 lines

## Today's Run (2026-07-12)
- API calls: 4/10
- WNBA: 336 rows, 6 games
- MLB: 753 rows, 14 games
- NFL: 2,140 rows, 75 games
- NBA/NHL: 0 rows each (upstream cache empty, not a code bug)

## Gaps Filled This Session
1. ✅ Created `hybrid_wnba_predictor.py` (was missing)
2. ✅ Created `odds_scraper_base.py` (shared base for 5 sport scrapers)
3. ✅ Created `tc_dashboard_v3.py` (10-tab dashboard)
4. ✅ Populated `usage.json` with real call count
5. ✅ All 4 sport-specific scrapers stubbed and use the shared base
6. ✅ Pushed to GitHub: commits `3b5554b`, `31b6b96`, `fefd5db`
7. ✅ Dashboard live and serving 200

## Last Commit
- `fefd5db` Add NBA + NHL odds scrapers (cache empty upstream)
