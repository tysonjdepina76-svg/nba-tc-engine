# Workspace Index

> **Read this first.** For full system map (zo.space routes, automations, outputs,
> gaps, quick-start commands) see `SYSTEM_MAP.md` at the workspace root.

Main areas of the workspace, by relevance.

## Sports TC Engine (primary, single source of truth)
- `Projects/tc_math.py` — TC math core (WNBA 40-min norm, PRA/PR/PA builders, edge, win%)
- `Projects/daily_picks.py` — daily slate capture → `Daily_Log/YYYY-MM-DD/`
- `Projects/build_pregame_combos.py` — offline combo builder (consumes tc_math + /api/combos)
- `Projects/wnba_pipeline` — WNBA backtest pipeline (14 days, 2882 picks, 47% HR)
- `Daily_Log/wnba_pipeline_*/` — pipeline v2 outputs (actuals.json, proj.csv, report.md)
- `Archives/WNBA_Backtests/` — archived backtest reports

## WNBA Calibration (2026-06-12)
- Best alpha = 7.0 for PTS/REB/AST/TPM, 5.0 for STL → 61.8% HR (5-day, 14g, 762 picks)
- 14-day overall: 54.9% (39 games, 3093 picks). Baseline Bayes (alpha=2.0): 51.7%
- Archive: `Archives/WNBA_Backtests/model_tuning_v3.json` (71.4% combined)
- `/api/tc` live route applies `bayesShrink()` with `L_PRIOR` + `STAT_BAYES_ALPHA`
- `tc_math.py` synced to same constants. `ceiling_recommend()` added
- BLK is monitor-only (37.1%). PTS=73.8% best single stat
- Key reports: `Reports/wnba_player_probability_20260612.md`, `Reports/wnba_backtest_comprehensive_20260612.md`

## Live Services
- `dk-combos-engine` (svc_id `svc__D_fVMtKoFg`, port 8515) → `https://dk-combos-engine-true.zocomputer.io/combos?sport=WNBA` (104 WNBA combos)

## Current State (2026-06-12)
- Projects: 13 production scripts
- Reports: 7 files
- Scripts: 6 files
- Obsolete reports purged to `Archives/CLEANUP_2026-06-12_obsolete/`
- Boxscore/halftime scrapers: `boxscore_live_scraper.py`, `halftime_final_boxscores.py`

## Live zo.space routes
- `https://true.zo.space/nba-tc` — live TC dashboard
- `https://true.zo.space/combos` — combo generator + parlay builder
- `https://true.zo.space/` — homepage (private)
- `https://true.zo.space/api/tc` — TC engine API (4-tier odds fallback: SGO → ESPN DK → Odds API → WNBA fallback)
- `https://true.zo.space/api/combos` — live combo generator API

## Automations (3 daily, all ET)
- 8:00 AM — `Scripts/refresh_daily_data.sh` + status email
- 9:00 AM — `Projects/daily_picks.py` + summary email
- 5:00 PM — `daily_tip_report.py` + `generate_report.py` + pre-tip email

## Archives
- `Archives/INTEGRATION_2026-06-09_obsolete/` — 21 files archived on this pass (orphan Projects + orphan root files)
- `Archives/GEMINI_2026-06-08_obsolete/` — 3 superseded TC engine versions
- `Archives/WNBA_Backtests/` — historical backtest runs

## Daily Pipeline Output
- `Daily_Log/<YYYY-MM-DD>/` — slate_NBA.json, slate_WNBA.json, picks.{csv,json}, proj_*.json, combos_*.md, combos_summary.json, dk_scrape_*.json
- `Daily_Log/last_run.json` — latest summary
- `Daily_Log/refresh_daily_data_<YYYYMMDD>.log` — pipeline log
- `Reports/nba_pre_tip_<YYYYMMDD>.md` + `Reports/wnba_pre_tip_<YYYYMMDD>.md`

## Secrets (read at runtime by /api/tc from /root/.zo/secrets.env)
- `SPORTSGAMEODDS_API_KEY` — ✅ loaded, NBA player props working
- `ODDS_API_KEY` — ✅ loaded, NBA + WNBA, 5 books (DK/FD/Fanatics/MGM/Bovada)
- `SPORTS_DATA_IO_KEY` — ✅ saved, limited tier (NBA scores/odds only, no WNBA, no projections)

## Odds API Enrichment
- `Skills/nba-odds-api/scripts/odds_enricher.py` — injects additional data into the odds API response using a two-step fetch approach; markets available per tier vary based on the underlying data source and subscription level.

## Critical rules
- `/api/tc` is the single source of truth for projections — never duplicate its math
- Use `edit_space_route()` for zo.space edits, NEVER file tools on those routes
- Use `edit_automation()` to update scheduled agents
- `AGENTS.md` (this) + `SYSTEM_MAP.md` are durable memory for future agents
