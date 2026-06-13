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

## SportsData.io NFL Engine (NEW — 2026-06-13)
- **Key**: `SPORTS_DATA_API_KEY` (sportsdata.io, NFL gambling tier)
- **Endpoints**: `GameOddsByWeek`, `PlayerPropsByWeek`
- **Script**: `SportsData NFL pull script`
- **Line**: `line`

## World Cup 2026 Pipeline (zero impact on basketball TC)
- `Projects/worldcup_picks.py` — standalone daily scraper (ESPN schedule + Odds API player props)
- Data sources: ESPN (free) for matches + The Odds API (free tier) for FanDuel player props
- Props: goals, assists, shots, shots_on_target — completely separate from basketball TC math
- Output: `Daily_Log/worldcup/YYYY-MM-DD/` (matches.json, props.json, picks.csv)
- Dashboard: `https://true.zo.space/worldcup` (live page)
- Automation: runs 5x daily during match windows (1PM, 3PM, 5PM, 7PM, 9PM ET)
- Note: DK soccer props not available via Odds API free tier — FanDuel primary book

## Current State (2026-06-13 — UPDATED 21:44 UTC)
- **Pipeline clean**: `daily_picks.py NBA WNBA` → 5 games, 19 edge-qualified combo legs (NYK@SAS + IND@CON, MIN@LV, DAL@POR, LA@PHX). ZERO errors.
- **pycache purged**: All `__pycache__/` dirs removed from workspace root, Projects/, crypto_sentinel/
- **WNBA combos ENHANCED**: DK odds now pull BOTH OVER + UNDER outcomes, DK game totals populated for all 4 games (168.5–174.5). 103 total combos across 4 WNBA games.
- **Gamelogs integration LIVE**: 913 WNBA + 510 NBA player 5-game rolling averages wired into `/api/tc` via `loadGamelogsCache()`
- **Workspace clean**: No stale root-level JSON/CSV files. No orphan temp files.
- zo.space: 14 routes healthy
- SGO API key needs rotation (401 Unauthorized)

## Gamelogs Cache (NEW)
- `Projects/player_gamelogs.py` — fetches last-5-game box scores from ESPN, computes rolling averages
- Output: `Daily_Log/YYYY-MM-DD/gamelogs_cache_{NBA,WNBA}.json` (per-player rolling 5g avgs)
- `/api/tc` reads cache on every request, overrides ESPN season averages with rolling avgs when available
- Source marker: "live_roster_api+gamelogs_5g_rolling" when gamelogs used, "live_roster_api" otherwise
- Stat mapping: gamelogs `pts/reb/ast/3pm/stl/blk` → ESPN field keys for `bayesShrink()`

## Backtest Pipeline (NEW — 2026-06-13)
- `Projects/backtest_pipeline.py` — standalone Odds API + ESPN backtest (single file, ~984 lines)
- Data flow: Odds API historical (h2h/spreads/totals) → ESPN box scores → TC math → hit rates
- Credit-aware: ONE call per sport per date (NOT per event), max 3 days for scores endpoint
- WNBA 7-day first run: **988 picks, 61.6% overall hit rate** (602/977 + 11 pushes)
- Best stats: PTS 73.1%, STL 62.4%, 3PM 62.3% | Worst: BLK 38.5%
- Best teams: LV 78.2%, ATL 70.6%, SEA 70.1% | Worst: DAL 49.1%, NY 51.8%
- DK combo cross-ref: 0 matches — Odds API historical endpoint does NOT support player props
- Player props + combo lines must come from LIVE endpoint (`/v4/sports/{sport}/events/{id}/odds`)

## Live zo.space routes
- `https://true.zo.space/nba-tc` — live TC dashboard
- `https://true.zo.space/dk-combos` — DK combo lines dashboard
- `https://true.zo.space/worldcup` — World Cup 2026 player props dashboard (goals, assists, shots, shots on target)
- `https://true.zo.space/` — homepage (private)
- `https://true.zo.space/api/tc` — TC engine API (4-tier odds fallback: SGO → ESPN DK → Odds API → WNBA fallback)
- `https://true.zo.space/api/combos` — live combo generator API
- `https://true.zo.space/api/worldcup-props` — serves World Cup props from Daily_Log/worldcup/

## Automations (4 daily, all ET)
- 8:00 AM — `Scripts/refresh_daily_data.sh` + status email
- 9:00 AM — `Projects/daily_picks.py` + summary email
- 1:00 PM, 3:00 PM, 5:00 PM, 7:00 PM, 9:00 PM — `Projects/worldcup_picks.py` (World Cup match windows)
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
