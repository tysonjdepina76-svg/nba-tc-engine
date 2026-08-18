# TC SPORTS SYSTEM — MULTI-SPORT DATA AGGREGATION + BACKTESTING (2026-08-17)

## Current Focus
Building a multi-sport (NFL, MLB, WNBA, NBA, NHL) historical data warehouse for backtest grading and algorithm training. All data sourced from free public APIs — no paid keys in use.

## Data Sources (Free Only)
| Source | Sports | What It Gives |
|--------|--------|---------------|
| `nfl_data_py` (nflverse) | NFL | Player stats, team stats, schedules, rosters, depth charts, injuries, PBP, NGS, FTN |
| `statsapi` (MLB) | MLB | Player stats, pitching staff, bullpen, closers, Statcast |
| `nba_api` | NBA | Player/team stats, schedules |
| `espn-api` / `nhlpy` | NHL | Skater/goalie stats, schedules |
| ESPN API | WNBA, NFL preseason | Schedules, game summaries |
| PFR manual scrape | NFL | Defense vs Position (QB/RB/TE/WR), team defense, advanced defense |

## Data Inventory (`Projects/data/`)
### NFL (`data/nfl/2024/`)
- `nflverse_player_stats_2024.parquet` — full player season stats
- `nflverse_stats_player_week_2024.csv` — weekly player stats
- `nflverse_team_stats_2024.csv` — team season totals
- `defense_vs_qb.json`, `defense_vs_rb.json`, `defense_vs_te.json` — DvP tables
- `standings.json`, `playoffs.json` — AFC/NFC standings + playoff results
- `depth_charts_2024.parquet`, `injuries_2024.parquet` — depth + injury data
- `ngs_passing.parquet`, `ngs_receiving.parquet`, `ngs_rushing.parquet` — Next Gen Stats
- `pbp.parquet` — play-by-play (large)
- `games_2024.parquet` — schedules + results
- Also: `data/nfl/2023/` and `data/nfl/2025/` (preseason only for 2025)

### MLB (`data/mlb/`)
- `batting_stats_2023-2025.parquet` — 3 seasons
- `pitcher_stats_2023-2025.parquet` — 3 seasons
- `pitching_staff_2023-2025.parquet` — staff rosters
- `bullpen_2023-2025.json` — bullpen arms per team
- `closers_2023-2025.json` — bullpen arms per team
- `starting_rotation_2023-2025.json` — rotations
- `statcast_pitcher_agg_2023.parquet` — Statcast metrics

### WNBA (`data/wnba/`)
- `rosters_2023-2025.parquet` — player rosters
- `teams.parquet` — team info
- 2026: in-progress

### NBA (`data/nba/`)
- `nba/2023/schedule.parquet`, `nba/2024/schedule.parquet` — schedules only (GAP: season dirs 2022_23/2023_24/2024_25 empty; no player/team stats pulled)
- Off-season: no live data needed; caps open for bulk backfill

### NHL (`data/nhl/`)
- `goalies_2022_23.parquet` through `goalies_2024_25.parquet`
- `skaters_2022_23.parquet` through `skaters_2024_25.parquet`
- `nhl/2023/schedule.parquet`, `nhl/2024/schedule.parquet` — schedules (GAP: no 2024_25 dir)

## Key Files
| File | Purpose |
|------|---------|
| `Projects/src/daily_picks.py` | Main pick generator (MLB + WNBA, uses argparse `--sport`) |
| `Projects/src/post_game.py` | Post-game grading with boxscore parsing + fuzzy name matching |
| `Projects/src/pitcher_features.py` | MLB pitcher K/9, ERA, WHIP from statsapi |
| `Projects/src/handedness.py` | Pitcher/batter handedness — platoon advantage filter |
| `Projects/src/injuries.py` | WNBA injury reports from ESPN |
| `Projects/src/mlb_savant.py` | Statcast pitcher metrics (xERA, whiff%, barrel%) |
| `Projects/src/nfl_depth.py` | NFL depth chart loader from parquet |
| `Projects/src/sync_to_supabase.py` | Push picks to Supabase REST API |
| `Projects/src/grade_date.py` | Grade all ungraded picks for a date+sport |
| `Projects/src/email_reports.py` | Daily email report |
| `Projects/core/` | NFL projection engine + schedule + sport-specific engines |
| `Daily_Log/` | Daily pick CSVs, projections, backtest reports |

## Pipeline
```
daily_picks.py --sport mlb    → generates MLB picks for today's slate
daily_picks.py --sport wnba   → generates WNBA picks
post_game.py                  → grades picks against boxscores
grade_date.py                 → bulk grade by date+sport
```
## Historical Data-Build Pipeline (warehouse)
```
src/builders/                     → per-sport builder modules
  mlb_pitching_builder.py         → pitcher K/ER/H/BB/HR/OUTS proj (statsapi)
  nfl_defense_builder.py          → NFL defense/DvP builder
  nfl_qb_builder.py               → NFL QB builder
  wnba_builder.py                 → WNBA roster/stat builder
src/backfill_github_all_sports.py → backfill last N days from free GitHub sources (nflverse, statsapi, nba_api)
src/adapters/                     → free-api and github source adapters
src/ingest_pfr_defense_2023.py    → PFR manual defense ingest
src/close_gaps.py                 → gap-closure helper (NBA wiring via nba_api)
```

## Known Gaps (2026-08-17)
- **NBA**: `nba/2022_23`, `nba/2023_24`, `nba/2024_25` dirs exist but EMPTY; only `schedule.parquet` for 2023/2024. No player/team stats. `nba_api` is the free source (off-season open).
- **WNBA**: `wnba/2025` dir missing (only `rosters_2025.parquet`); 2026 dir empty (current season). No free player-boxscore source — grade via ESPN single-game summaries.
- **NHL**: no `nhl/2024_25` dir (only 2023/2024 schedules; skater/goalie parquet at top level).
- **MLB**: statcast only for 2023; 2024/2025 statcast metrics missing (basic stats via statsapi OK).
- **NFL**: 2023+2024 complete; 2025 nflverse weekly/snap not yet backfilled.
- **Dup daily_picks**: `/home/workspace/Projects/daily_picks.py` (root, 68KB) DIFFERS from `src/daily_picks.py` (13KB). Root is canonical entrypoint; confirm which is live before editing.

## WNBA Data Gap
No free public API provides WNBA player-level boxscore stats reliably:
- BallDontLie: 404
- wehoop: unavailable
- nba_api WNBA boxscores: timeout-heavy
- BigBallsData: requires free API key (not yet set up)
- ESPN boxscore API: works one game at a time, no bulk historical pull
- Fallback: ESPN game summary API for grading

## Notebooks (`Notebooks/`)
- `nfl_stats_aggregation_20240811.ipynb`
- `nfl_pre_compute_20240811.ipynb`
- `NFL_2024_ReAggregate.ipynb`
- `analyze_mlb_picks_20240811.ipynb`
- `debug_nfl_data_20240811.ipynb`
- `debug_nfl_data_20240812.ipynb`

## API Caps
- All external APIs capped until scheduled crons fire
- Free sources only: statsapi, nba_api, ESPN API, nfl_data_py
- Paid keys (Odds API, SportsDataIO, SGO) are dead or quota-exhausted — never retry them

## WNBA Lines + Props (2026-08-17)
- Generation created `src/wnba_slate_props_export.py` (run: `python3 -m src.wnba_slate_props_export <days>`)
- Outputs: `Projects/data/wnba/wnba_slate_LINES_2026-08-17.json`, `wnba_slate_PROPS_2026-08-17.json` (373 player prop projections across 16 upcoming games), `Daily_Log/wnba_slate_REPORT_2026-08-17.md`
- Props derived from nba_api WNBA game logs (GitHub/free source, cached in `Projects/data/github/wnba/`).
- Real market prop lines NOT available free: DraftKings Akamai-blocked; Action Network free endpoint = moneyline/spread/total only; Odds API quota maxed (do not retry).

## API Caps (uncapped 2026-08-17)
- `src/api_cap_tracker.py` now has an UNCAPPED OVERRIDE block (all limits -1); cap_check() always True except discovery_labs (hard-blocked).
- Free GitHub sources active: statsapi (MLB), nba_api (WNBA/NBA), nfl_data_py (NFL), nhlpy (NHL).
- Uncapping does not restore exhausted paid quota (Odds API, SharpAPI, SportsDataIO).

## 2026-08-17 Pipeline Fixes Applied
| Fix | File | Detail |
|-----|------|--------|
| League casing | `src/daily_picks.py` | All `'MLB'`→`'mlb'`, `'WNBA'`→`'wnba'` |
| Dupe purge | DB | Deleted 140 uppercase MLB dupe rows |
| OVER threshold | `src/daily_picks.py` line 33 | Raised OVER from 0.15→0.20 (UNDER stays 0.08) |
| grade_date import | `src/grade_date.py` | Rewired to `src.post_game.grade_date` |
| Pitcher guard | `src/pitcher_features.py` | isinstance check before .get() |
| WNBA fallback | `src/wnba_projections.py` | ESPN fallback via scoreboard API |
| Team prop grading | `src/grade_team_props.py` | Added `grade_date_team_props()` via ESPN inning stats |
| ESPN→statsapi resolver | `src/post_game.py` | Added `_resolve_mlb_game_pk()` |
| Dynamic thresholds | `src/daily_picks.py` | `_get_thresholds(league)` calls `calibrated_thresholds.get_dynamic_threshold()` with 0.20/0.08 floor; 10 call sites replaced |
| 1st inning props | `src/grade_team_props.py` | 100 props graded across 8/15-8/17 via ESPN inning stats |

## Automations (2026-08-17 14:40 — all active)

## Current State (8/17 17:15 ET)
- **247 total picks**: MLB 10 (action_network moneyline) + WNBA 237 (SELF_EDGE player props)
- MLB: 10 game-level moneyline picks (7 HOME, 3 AWAY) from real Action Network lines
- WNBA: 237 player prop picks (133 OVER, 104 UNDER) from self-edge projections
- Source breakdown: all MLB = `action_network`, all WNBA = `SELF_EDGE`
- Game lines cached: `/home/workspace/Daily_Log/mlb_game_lines_2026-08-17.json`

## MLB Game-Line Pipeline (NEW 8/17 17:15)
- `src/extract_game_lines.py` — fetches Action Network + ESPN via browser, caches game lines to disk
- `src/generate_mlb_game_picks.py` — reads cached lines, generates moneyline picks, inserts to picks.db
- `src/line_provider.py` — MLB routes to Action Network game lines; player props return None
- Flow: `extract_game_lines.py` → `generate_mlb_game_picks.py` → picks.db → dashboards
- Sandbox limitation: Action Network/ESPN APIs blocked from direct curl; browser proxy used for fetch

## Architecture Rule — TC Math Boundary (8/17 17:15 ET)
- **TC Math / Self-Edge applies ONLY to: WNBA player props, NFL player props**
- **MLB: uses real market lines from Action Network (free, game-level: moneyline/spread/total)**
- **MLB player props: NOT generated — no free source provides real MLB player prop lines**
- **NFL preseason: real DK lines via ESPN adapter for spread/over-under (no player props)**

## Nightly Cron
```bash
# Grade at 22:00 ET daily
0 22 * * * cd /home/workspace/Projects && python3 src/grade_date.py --date $(date +\%F) >> /dev/shm/grade.log 2>&1
```

## 2026-08-17 14:35 — Full Pipeline Wired + Fixed (all changes saved to disk)
Fixed 3 runtime bugs that were showing as warnings in every run:
- **`get_live_stats` undefined** → added `from src.adapters.free_api_aggregator import get_live_stats` at line 190 of `Projects/daily_picks.py`. `enrich_via_free_apis()` now actually enriches projections instead of early-returning.
- **`update_wnba_roster_status()` missing arg** → call at line 998 now passes `_roster_path = Projects/data/rosters/wnba_rosters.json`; WNBA injury status now applies.
- **WNBA scoreboard `dates=sport` bad request** → `gen_wnba_today.py::_fetch_scoreboard` now strips dashes and validates `YYYYMMDD` regex; non-date strings fall back to today instead of building an invalid URL.

Verified clean end-to-end run (14:34 ET):
- `daily_picks.py --sport all` → **433 picks** (MLB 258, WNBA 175) saved to `Daily_Log/last_run.json`
- DB counts: mlb 16,673 · wnba 2,432 · nfl 4 (lowercase leagues)
- Fangraphs 403 warning is benign — that's a paid/blocked source, falls back to free statsapi data (does NOT affect picks)
- NBA/NFL/NHL correctly report "no projection files" — off-season, no games to pick
- Dashboard localhost:8510 OK (HTTP 200), reads DB + last_run.json directly so it already reflects this state

## Reconcile 2026-08-17 16:00 ET — Competing Copies Resolved
Audited every live entrypoint vs stale root copies. Canonical = `src/`. Resolution:
- **Live generator = `src/daily_picks.py`** (writes picks.db with correct schema + writes `Daily_Log/last_run.json` from DB). Root `daily_picks.py` (68KB, argparse `--sport all`) is STALE — do not edit it.
- **Crontab reconciled** to src: 8am→`src/daily_picks.py --sport all`, 10pm grade→`src/grade_date.py --date $(date +\F)`, 11pm→`src/edge_engine/update_calibration.py`, 11:30pm→`src/sync_to_supabase.py`. Old references to root `daily_picks.py`/`regrade_picks.py` removed (regrade logic lives in `src/regrade_all_outstanding.py`).
- Grading entrypoints in src only: `src/grade_date.py` (per-date, CLI), `src/grade_wrapper.grade_date` (API), `src/post_game.py` (boxscore+fuzzy), `src/regrade_all_outstanding.py` (bulk), `src/grade_team_props.py` (team 1st-inning props).
- **Dashboards, LIVE (do not duplicate):**
  - `src/tc_dashboard.py` → 8510 (summary, reads picks.db + last_run.json)
  - `src/dashboard.py` → 8511 WNBA / 8514 NBA / 8516 NHL / (8515 NFL) via `-- --sport <X>`
  - `api/main.py` (uvicorn:8000) + `real_time_streamer.py` (8001)
- **Archived / obsolete (reference only, not run):** root `daily_picks.py`, `regrade_picks.py`, `tc_dashboard.py`, `tc_sports_dashboard.py`, `dashboard/*.py` (MLB/NBA table widgets superseded by src/dashboard.py). Backtest code under `backtest_archives/` is historical snapshots — never edited.
- Retain per-sport compartmentalization: each sport has its own projection file, generator section, and grader; the DB `league` column keeps sports strictly separated.

## NFL Preseason Pipeline — 2026-08-17 (Live, No Hardcodes)
- `src/espn_nfl_live.py` — NEW live ESPN API adapter: `fetch_upcoming_games()` hits ESPN v2 sports API, returns games with DraftKings spread/over-under/moneyline. Returns dicts: `{away, home, matchup, date, status, spread, over_under, away_ml, home_ml, provider}`.
- `src/nfl_preseason_picks.py` — **PURGED hardcoded PRESEASON_GAMES**. Now calls `espn_nfl_live.fetch_upcoming_games()` → `filter_dk_games()` → generates spread + over/under picks from real DK lines. Insert matches picks.db schema (league, player, stat, tc_projection, market_line, edge, matchup, direction, source=espn_draftkings). Picks dated by GAME DAY, not run day.
- 36 NFL picks in DB: 4 old (Aug 15 completed) + 32 new (Aug 21-24 upcoming)
- NFL dashboard: port 8515, fixed case (NFL→nfl) + date >= filter for future slates
- **Do NOT run `daily_picks.py --sport nfl`** for preseason — it expects projection files. Use `nfl_preseason_picks.py` directly.
- `src/dashboard.py` `load_picks()`: `sport.lower()` + NFL fallback query `date >= ?` when `date = ?` returns empty

## Dashboard URLs (2026-08-17 16:25 ET)
| Port | Sport | Status |
|------|-------|--------|
| 8510 | TC Summary | HTTP 200 |
| 8511 | WNBA | HTTP 200 |
| 8512 | MLB | HTTP 200 |
| 8515 | NFL | HTTP 200 |

## 2026-08-17 19:30 ET — Pick-Cards Dashboard Fix + WNBA Logos + Combo Separation
### Pick-Cards Dashboard (https://true.zo.space/pick-cards) — FIXED
- **Bug**: Combos were creating 169 ghost "game" entries (players string as matchup, 0 picks, no logos).
- **Fix**: Backend API now separates `combos[]` from `game_list[]`. Combos are at top-level response, not in-game entries.
- **WNBA logos**: Uploaded 13 WNBA team logos (ATL, CHI, CON, DAL, GS, IND, LA, LV, MIN, NY, PHX, SEA, WSH) as space assets at `/logos/{abbr}.png`.
- **Result**: 11 games (10 MLB, 1 WNBA), 247 picks, 1531 combos, all logos rendered.

### Pipeline State (19:30 ET)
- **MLB**: 10 game-level moneyline picks from Action Network lines (7 HOME, 3 AWAY)
- **WNBA**: 237 player prop picks (DAL @ GS) — SELF_EDGE projections
- **NFL**: 32 preseason picks (8/21: 12 picks, 8/22: 22 picks, 9/10: 6 picks) — ESPN DK lines
- **Combos**: 1531 WNBA combos available in API, rendering on pick-cards page

### Dashboards
| Port | Sport | Status |
|------|-------|--------|
| 8510 | TC Summary | HTTP 200 |
| 8511 | WNBA | HTTP 200 |
| 8512 | MLB | HTTP 200 |
| 8515 | NFL | HTTP 200 |

### Known Gaps (unchanged from earlier)
- **MLB player props**: No free source for real MLB player prop lines. Only game-level lines available.
- **WNBA props**: SELF_EDGE only — no real market prop lines.
- **NBA/NHL**: Off-season, no live data needed.
- **NFL regular season**: Starts Sep 10. Preseason pipeline active.


## game_id_resolver (NEW 2026-08-17)
-  — Unified resolver: MLB→statsapi, WNBA→ESPN, NFL→ESPN (preseason+reg)
-  — MLB OVER discount factors (HR 0.88, SB 0.85, RBI 0.92, R 0.94, H 0.96, K 1.02)
-  — Team abbreviation consistency audit
-  — Integration script (init cache, audit, verify)
-  wired into  in 
- Backfill:  resolved 215 historical NULLs; ~1000 remain (old data)
- WNBA Blocks excluded:  in generate_wnba_picks()
