# Workspace Index

> **Read this first.** For full system map (zo.space routes, automations, outputs,
> gaps, quick-start commands) see `SYSTEM_MAP.md` at the workspace root.

Main areas of the workspace, by relevance.

## Sports TC Engine (primary, single source of truth)
- `Projects/tc_math.py` — TC math core (WNBA 40-min norm, PRA/PR/PA builders, edge, win%)
- `Projects/daily_picks.py` — daily slate capture → `Daily_Log/YYYY-MM-DD/`
- `Projects/build_pregame_combos.py` — offline combo builder (consumes tc_math + /api/combos). **Multi-book fallback**: DK → FanDuel → BetMGM → Fanatics → Bovada
- `Projects/balldontlie_schedule.py` — diagnostic only: game schedules from balldontlie.io (no props/odds)
- `Projects/tc_dashboard.py` — st
- `Projects/wnba_pipeline` — WNBA backtest pipeline (14 days, 2882 picks, 47% HR)
- `Daily_Log/wnba_pipeline_*/` — pipeline v2 outputs (actuals.json, proj.csv, report.md)
- `Archives/WNBA_Backtests/` — archived backtest reports
- `Projects/team_game_mapper.py` — 13 WNBA teams, 72 aliases (city/nickname/abbr/alternate), 3-step match (alias → token overlap → start-time proximity). ESPN is the canonical key; Odds API event_id is cross-referenced.
- `Projects/wnba_props_live_pull.py` — fetches Odds API WNBA events, builds canonical ESPN↔Odds map, pulls DK player props per event. 6/15 first run: **300 real DK rows** (LV@DAL 140, LA@GS 160). Output:
  - `Daily_Log/wnba_props_2026-06-15_dk.csv` — 300 rows, 9 stat markets
  - `Daily_Log/wnba_props_2026-06-15_raw.json` — full per-book payload + canonical map
  - `Reports/wnba_live_dk_props_20260615.md` — best-juice top-20 (heavy Under-3PM favored)

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

## World Cup 2026 + Soccer Pipeline (UPDATED 2026-06-15)
- `Projects/worldcup_picks.py` — RESTORED (was prematurely archived). Standalone daily scraper (ESPN schedule + Odds API **FanDuel** player props: goals, assists, shots, shots_on_target). 4 WC matches today = 333 props. This is the production WC scraper.
- `Projects/soccer_live_pull.py` — complementary: pulls h2h/spreads/totals across 49 books for 11 active soccer leagues (game lines only, since free tier blocks player props for `us,eu,uk` regions — FanDuel-only is the workaround the WC scraper uses).
- Free Odds API tier supports game lines (h2h/spreads/totals) only — 422 on player props (needs paid tier)
- 49 books available including DK, FD, BetMGM, BetRivers, Fanatics
- WC 2026 schedule: 6/15-7/15 group stage, 7/16-7/31 knockout
- Output: `Daily_Log/soccer/YYYY-MM-DD/{events,lines,summary}.json`
- 1PM/3PM/5PM/7PM/9PM automations (agent 8e9d600e) call the new puller
- Archive: `Archives/OBSOLETE_PROJECTS_2026-06-15/worldcup_picks.py` (362 lines, superseded)

## 2026-06-15 (late morning): Team Roster Sync + API Purge + Drive Backup

**NHL roster fixed:** Page `/nba-tc` NHL_TEAMS now 32 teams (added CHI, VAN, UTA, alphabetized). Matches API `/api/tc` NHL_NAME_TO_CODE (32 entries).

**API purge:** Removed stale `"Arizona Coyotes":"ARI"` from NHL_NAME_TO_CODE (team moved to Utah in 2024, ARI conflicts with MLB Diamondbacks).

**All 6 sports synced page↔API:**
| Sport | Teams | Status |
|---|---|---|
| NBA | 30 | Clean |
| WNBA | 15 | Clean |
| NFL | 32 | Clean |
| MLB | 30 | Clean |
| NHL | 32 | Clean |
| WORLD CUP | 41 | Clean |

**Drive backup:** `TC_Dashboard_State_2026-06-15.md` uploaded to Google Drive (tysondepina99@gmail.com).

## 2026-06-15 (15:55 ET): Full Dashboard Audit + Gap Fixes

**Audit scope:** All 15 zo.space routes, all 6 sports, every panel in `/nba-tc`.

**Gaps found + fixed:**

| Gap | Fix |
|---|---|
| `/api/dk-lines` MLB: Arizona Diamondbacks → "AZ" | Corrected to "ARI" |
| `/api/dk-lines` NHL: missing CHI, VAN, UTA | Added all 3 (now 32 teams, matches `/api/tc` NHL_NAME_TO_CODE) |
| `/nba-tc` NFL / Fantasy tab was a stub (tab existed, no panel) | Wired `NFLPanel()` — shows SportsData.io live lines, DK total/spread/ML, props count, quick link to Project Game tab |

**Verified — all 6 sports firing:**
| Sport | Project Game | Live Stats | DK Lines Source | Status |
|---|---|---|---|---|
| NBA | ✅ Full TC | ✅ ESPN scoreboard | SGO → ESPN DK → Odds API | Clean |
| WNBA | ✅ Full TC | ✅ ESPN scoreboard | SGO → ESPN DK → Odds API → market fallbacks | Clean |
| NFL | ✅ DK lines | ⚠️ No live players | SportsData.io cached daily | Live lines functional, no player stats |
| WORLD CUP | ✅ DK lines | ⚠️ No live players | Odds API | Lines functional, no player stats |
| MLB | ✅ DK lines | ⚠️ No live players | Odds API | Lines functional, no player stats |
| NHL | ✅ DK lines | ⚠️ No live players | Odds API | Lines functional, no player stats |

**Known limitations (not fixable without new data sources):**
- Non-basketball live stats (NFL/MLB/NHL/WORLD CUP) return empty player arrays — ESPN's scoreboard API only exposes detailed player stats for basketball sports
- World Cup page (`/worldcup`) is standalone (not integrated into `/nba-tc` dashboard)
- WNBA player props depend on Odds API tier

**Routes verified:** 15 total (8 API + 7 page routes). All sync successfully.

## Current State (2026-06-15 06:00 ET — UPDATED)

- **ALL_SPORTS pipeline**: `daily_picks.py` now defaults to `("NBA", "WNBA", "MLB", "NHL", "WORLD CUP")`. Non-basketball sports (MLB, NHL, WORLD CUP) log DK total/spread/ML lines per game. Basketball sports (NBA, WNBA) get full player props + combos.
- **Multi-source consensus engine**: `Projects/consensus_engine.py` — fetches ALL books (DK, FD, BetMGM, Caesars, Fanatics, Bovada, etc.), builds trimmed-mean consensus per player/stat. Daily cache avoids double-counting Odds API tokens.
- **Sports covered**: NBA, WNBA, NHL, MLB, MLS (and EPL/LaLiga/SerieA/Ligue1/Bundesliga stubbed).
- **build_pregame_combos.py**: NBA uses SGO (primary) → Odds API consensus (fallback). WNBA uses Odds API consensus (primary). Multi-book fallback when DK is empty.
- **daily_picks.py**: enrichment now uses `consensus_engine.get_best_line()` instead of the old single-book `odds_enricher`.
- **BallDontLie diagnostic**: `Projects/balldontlie_schedule.py` — schedule-only tool (no props, no projections). Needs `BALLDONTLIE_API_KEY` in secrets.
- **Streamlit dashboard**: `Projects/tc_dashboard.py` — merged into real pipeline data (`Daily_Log/YYYY-MM-DD/picks.csv`). Run: `streamlit run Projects/tc_dashboard.py --server.port 8518`
- **Tokens saved**: Consensus engine caches per-event → one Odds API call per event per day (was 2+ with old approach).
- **Pipeline clean**: `daily_picks.py NBA WNBA` → 0 errors, 0 upcoming (all Saturday games completed).

## 2026-06-15: Team-Game Mapper + Live WNBA DK Props (BREAKTHROUGH)

**Root cause of 7-day empty WNBA slate:** team aliases across books (SGO/Odds API/SportsData/BetMGM) did not match internal 3-letter codes. SGO is also WNBA-unavailable at our tier.

**Fix shipped:** `Projects/team_game_mapper.py` — 13 WNBA teams, 72 aliases (city/nickname/abbr/alternate), 3-step match (alias → token overlap → start-time proximity). ESPN is the canonical key; Odds API event_id is cross-referenced.

**Live pull:** `Projects/wnba_props_live_pull.py` — fetches Odds API WNBA events, builds canonical ESPN↔Odds map, pulls DK player props per event. 6/15 first run: **300 real DK rows** (LV@DAL 140, LA@GS 160). Output:
- `Daily_Log/wnba_props_2026-06-15_dk.csv` — 300 rows, 9 stat markets
- `Daily_Log/wnba_props_2026-06-15_raw.json` — full per-book payload + canonical map
- `Reports/wnba_live_dk_props_20260615.md` — best-juice top-20 (heavy Under-3PM favored)

**Game-line coverage gap:** WAS@CON (6/17) and NY@CHI (6/18) have no DK props posted yet (24-48h out). POR@MIN (6/16) is now mapped after adding Portland Fire + Toronto Tempo to the alias dict.

**Integration:** `consensus_engine.py` now imports `canon_abbr` from `team_game_mapper` and uses it to canonicalize Odds API bookmaker team names.

## 2026-06-13: Multi-Sport Direction-Agnostic Fix
- `/api/tc` `fetchMultiSportDKLines` and `buildMultiSportProjection` now accept reversed matchups
- MLB, NHL, WORLD CUP, NBA, WNBA all work regardless of which team is passed as away/home
- Fix matches the NBA/WNBA `fetchDKOdds` pattern: checks both fwdMatch and revMatch
- All 5 sports return 200 from `/api/tc`; DK lines populate when live games exist
- WNBA has 6-game slate today (IND@CON, MIN@LV, DAL@POR, LA@PHX, ATL@TOR, WSH@NY)
- Combos engine: NBA 37 lines, WNBA 115 lines ready

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

## Automations (10 daily, 1 weekly — all ET)

**Boxscore Pipeline (NEW — 2026-06-15):**
- 8:30 PM, 10:30 PM, 12:30 AM — `Projects/boxscore_saver.py` → halftime + final boxscores. **Dedup-aware**: event_id registry prevents double-saving. Output: `Daily_Log/halftime/`, `Daily_Log/final/`, registry at `Daily_Log/boxscore_registry.json`
- 4:00 AM — `Scripts/system_cleanup.sh` → dedup boxscores, purge stale caches, rotate logs >30d, pipeline health snapshot, Google Drive sync
- Monday 9:00 AM — `Scripts/health_check.py` → full system health report (API keys, endpoints, services, data freshness, boxscore registry count)

**TC Pipeline (ALL SPORTS — updated 2026-06-15):**
- 1:00 PM — Baseline Slate Capture (all sports): `python3 Projects/daily_picks.py NBA WNBA MLB NHL WORLD CUP`
- 1:30 PM — Post-Injury Refresh (all sports): same + combos
- 5:00 PM — All Sports Pre-Tip Update: same + combos
- 6:30 PM — Final Pre-Tip (all sports): same + combos + health check
- 1:00 PM, 3:00 PM, 5:00 PM, 7:00 PM, 9:00 PM — `Projects/soccer_live_pull.py` (World Cup match windows — FanDuel player props)

## Archives
- `Archives/INTEGRATION_2026-06-09_obsolete/` — 21 files archived on this pass (orphan Projects + orphan root files)
- `Archives/GEMINI_2026-06-08_obsolete/` — 3 superseded TC engine versions
- `Archives/WNBA_Backtests/` — historical backtest runs

## Daily Pipeline Output
- `Daily_Log/<YYYY-MM-DD>/` — slate_NBA.json, slate_WNBA.json, slate_MLB.json, slate_NHL.json, slate_WORLD_CUP.json, picks.{csv,json}, proj_*.json, combos_*.md, combos_summary.json
- `Daily_Log/last_run.json` — latest summary across all sports
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

## 2026-06-14: Multi-Sport Consensus Engine + Pipeline Assessment

- `Projects/consensus_engine.py` — multi-book consensus (DK→FD→BetMGM→Caesars→Fanatics→Bovada), trimmed-mean aggregation, daily token cache
- `list_sport_games()` — zero-token-cost events list for any sport (no odds call)
- `Projects/pipeline_assess.py` — single command health check: API keys, routes, dashboards, automations, daily log, cache, credits remaining. Run: `python3 Projects/pipeline_assess.py`
- `Projects/tc_dashboard.py` — Streamlit dashboard on port 8510, reads real pipeline data from Daily_Log
- **5 daily automations**: 1PM (pre-injury), 1:30PM (post-injury refresh), 5PM (WNBA+NBA update), 6:30PM (final pre-tip), + World Cup 5x daily
- **Odds API**: 13,956 credits remaining (6,044 used this month — ~17k/mo pace on $30 tier, well under limit)
- **Streamlit services**: port 8510 (tc_dashboard), port 8515 (dk-combos-engine)

## 2026-06-15 (evening): Soccer Wired + Disk Cache + Tabbed Dashboard

**Soccer**