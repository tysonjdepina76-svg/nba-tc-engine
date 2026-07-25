# TC Pipeline Workflow — Clean Architecture (June 2026)

> Version 3.0 — All SGO V2 limit=100, no obsolete code, fully wired.

## Active Sports
| Sport | Engine | API Source | Status |
|-------|--------|-----------|--------|
| WNBA | daily_picks.py | Odds API + ESPN (DK fallback) | 🟢 LIVE |
| MLB | daily_picks.py → mlb_tc_engine | SDK/Odds API | 🟢 LIVE |
| World Cup | daily_picks.py → soccer_combo_engine | ESPN + Odds API (self-edge) | 🟢 LIVE |
| NBA | — | — | 🔴 OFF-SEASON |
| NHL | — | — | 🔴 OFF-SEASON |
| NFL | — | — | 🔴 OFF-SEASON |

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AUTOMATIONS (daily)                      │
│  11:00 AM  │  MLB Early + WNBA Injury                        │
│  1:30 PM   │  Slate Refresh + DK Lines                       │
│  4:00 PM   │  World Cup Lineups + Evening MLB                 │
│  6:30 PM   │  Final Projections + Combo Gen                   │
│  8:30 PM   │  Boxscore: Halftime                              │
│  10:30 PM  │  Boxscore: End of Night                          │
│  2:00 AM   │  Daily Backtest (WNBA)                           │
│  4:00 AM   │  System Cleanup                                  │
│  Monday 8A │  Weekly 30-Day Backtest Rollup                   │
└─────────────────────────────────────────────────────────────┘
```

## Core Engines

| File | Purpose | Imports |
|------|---------|---------|
| `Projects/daily_picks.py` | Main orchestrator — projections for WNBA, MLB, World Cup | consensus_engine, api_fallback, soccer_combo_engine, build_pregame_combos |
| `Projects/pipeline_master.py` | Health check + service management + auto-repair | — (self-contained) |
| `Projects/consensus_engine.py` | Multi-book consensus lines (DK → FD → BetMGM → etc.) | team_game_mapper |
| `Projects/api_tc_unified.py` | Zo.space TC API handler | — (self-contained) |
| `Projects/build_pregame_combos.py` | DK combo builder (SGO + Odds API) | — (self-contained) |
| `Projects/dk_combos_engine.py` | DK combo engine server (:8515) | — (self-contained) |
| `Projects/soccer_combo_engine.py` | World Cup combo builder (:8516) | — (self-contained) |
| `Projects/soccer_tc_engine.py` | World Cup TC projections | — (self-contained) |
| `Projects/mlb_tc_engine.py` | MLB TC projections | mlb_sdio_props (fallback) |
| `Projects/mlb_sdio_props.py` | SportsDataIO MLB prop fallback | — (self-contained) |
| `Projects/backtest_pipeline.py` | Daily WNBA backtest runner | — (self-contained) |
| `Projects/backtest_30day.py` | Weekly 30-day rollup | — (self-contained) |
| `Projects/boxscore_saver.py` | Boxscore capture + dedup | — (self-contained) |
| `Projects/tc_dashboard.py` | Streamlit dashboard (:8510) | — (self-contained) |
| `Projects/team_game_mapper.py` | Canonical team name mapping | — (self-contained) |

## Supporting Files

| File | Purpose |
|------|---------|
| `Projects/api_fallback.py` | API fallback chain (SGO → ESPN → offline) |
| `Projects/api_scan.py` | API endpoint health scanner |
| `Cache/` | API response caching (SGO + others) |
| `Projects/wc_self_edge.py` | World Cup self-edge engine (standalone) |
| `Projects/worldcup_picks.py` | World Cup daily scraper (standalone) |
| `Projects/wc_boxscore_backtest.py` | World Cup boxscore backtest (standalone) |
| `Projects/wc_projections.py` | World Cup TC projections (standalone) |
| `Projects/wc_tc_calibrate.py` | World Cup TC calibration |
| `Projects/wc_tc_math.py` | World Cup TC math engine |

## Data Flow

```
Secrets (/root/.zo/secrets.env)
   ├─ ODDS_API_KEY ─────→ consensus_engine, daily_picks, api_tc_unified
   ├─ SPORTSGAMEODDS_API_KEY ─→ build_pregame_combos, dk_combos_engine, api_scan
   ├─ SPORTSDATAIO_API_KEY ──→ mlb_sdio_props (fallback)
   └─ SPORTS_DATA_API_KEY ──→ legacy (same as SPORTSDATAIO)

External APIs
   ├─ api.theoddsapi.com ─── WNBA/MLB odds + player props
   ├─ api.sportsgameodds.com/v2 ── SGO V2 (limit=100, DK lines)
   ├─ site.api.espn.com ─── Free scoreboards + rosters
   └─ api.sportsdata.io ─── MLB fallback props (limited)

Output → /home/workspace/Daily_Log/
   ├─ YYYY-MM-DD/picks.csv          — All picks by date
   ├─ YYYY-MM-DD/picks.json         — Full metadata
   ├─ YYYY-MM-DD/proj_*.json        — Per-game projections
   ├─ YYYY-MM-DD/slate_*.json       — Raw API responses
   ├─ YYYY-MM-DD/combos_*.json      — Qualified combo legs
   ├─ worldcup/YYYYMMDD/props.json  — WC props
   ├─ worldcup/YYYYMMDD/picks.csv   — WC picks
   ├─ backtests/YYYY-MM-DD/         — Daily backtest reports
   ├─ backtests/30day/              — Weekly rollup
   └─ last_run.json                 — Latest summary

Services
   ├─ :8510 — Streamlit dashboard (tc_dashboard.py)
   ├─ :8515 — DK Combos Engine (dk_combos_engine.py —¬ server)
   ├─ :8516 — Soccer Combo Engine (soccer_combo_engine.py —¬ server)
   └─ :3099 — Zo.Space (Hono/Bun, routes below)
```

## Zo.Space Routes

| Route | Type | What It Does |
|-------|------|-------------|
| `/` | page | Homepage (private) |
| `/nba-tc` | page | Main dashboard — all sports + tabs |
| `/api/tc` | api | TC projections by sport/matchup |
| `/api/dk-lines` | api | Multi-book DK lines (SGO → ESPN tiered) |
| `/api/combos` | api | TC-qualified player props |
| `/api/daily-log` | api | Daily picks from Daily_Log |
| `/api/pipeline-health` | api | Full diagnostic |
| `/api/backtest` | api | Historical hit-rate data |
| `/api/env-check` | api | Secrets/environment check |
| `/api/worldcup-props` | api | World Cup player props + edges |
| `/api/wnba-boxscores` | api | WNBA minutes leaders |
| `/api/combo-prob` | api | Game-by-game combo hit probs |

## SGO V2 Migration — Key Changes

- **DEFAULT PAGE SIZE is now 10** (was larger in V1) — ALL calls include `limit=100`
- V1 endpoints (`/v1/events`, `/v1/odds`) fully deprecated
- All 4 active SGO consumers updated:
  - `pipeline_master.py` — health check
  - `dk_combos_engine.py` — player odds fetch
  - `build_pregame_combos.py` — DK combo extraction
  - `api_scan.py` — endpoint scan
- Rate-limit headers logged: `x-requests-remaining` / `X-RateLimit-Remaining`

## Purged (June 27, 2026)

Moved to `Trash/obsolete_purge_20260627/`:
- Dead engines: pipeline_assess, pipeline_health, player_gamelogs, probability_engine, sdio_service, balldontlie_schedule
- Dead NBA/WNBA: tc_math, wnba_historical_backtest, wnba_pipeline_v2, wnba_props_live_pull
- Dead app: apps/sports-tc/ (entire directory — archived NBA engines)
- Dead utils: live_report, multisport_live_pull, api_cache, morning_briefing
- Off-season: sportsdata_nfl_engine, sportsdata_nfl_lines_pull (NFL returns Sep)
- Unrelated: the-one-football/ (NFL player deck, not part of TC pipeline)
- sports_betting_dashboard/scripts/: stale odds scraper utilities

## How to Run

```bash
# Full pipeline (all sports + combos)
python3 /home/workspace/Projects/daily_picks.py WNBA MLB 'WORLD CUP'

# Quick health check (no API calls except health probes)
python3 /home/workspace/Projects/pipeline_master.py --quick --dry-run

# Full health + repair
python3 /home/workspace/Projects/pipeline_master.py

# Daily backtest
python3 /home/workspace/Projects/backtest_pipeline.py --league WNBA --days 1
```

## Key Rules

- NBA and NHL are OFF-SEASON — skip entirely, SGO returns 503 for them
- SGO V2: ALWAYS pass `limit=100` — default is 10 per page
- WNBA DK player props appear 30-60 min before tip
- ESPN DK odds available daytime, absent late night
- All API keys in `/root/.zo/secrets.env`
- World Cup uses self-edge engine (no FD/DK player props on free tier)
- Health checks use `pipeline_master.py --quick`, NOT scan.sh (heavy)
