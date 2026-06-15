# Workspace Index

> **Run the pipeline:** `python3 Projects/pipeline_master.py` — self-checks, repairs, generates picks/combos for all sports, purges old files, saves, pushes.

## Core Pipeline (single source of truth)
- `Projects/pipeline_master.py` — **Master self-healing daily runner** — all sports, all checks, auto-repair
- `Projects/pipeline_health.py` — component-level health checks (APIs, services, routes, freshness)
- `Projects/pipeline_assess.py` — diagnostic assessment (APIs, routes, dashboard, combos, automations)
- `Projects/daily_picks.py` — daily slate capture for NBA/WNBA/MLB/NHL/WORLD CUP → `Daily_Log/YYYY-MM-DD/`
- `Projects/consensus_engine.py` — multi-book consensus lines (DK → FD → BetMGM → Caesars → Fanatics → Bovada)
- `Projects/build_pregame_combos.py` — pregame combo builder (TC projections × consensus lines)
- `Projects/tc_math.py` — TC math core (WNBA 40-min norm, PRA/PR/PA, edge, win%)
- `Projects/tc_dashboard.py` — Streamlit dashboard (port 8510)

## Sports Engines
- `Projects/soccer_tc_engine.py` — Soccer TC projections (9 stats incl. corners: G, A, SOT, S, COR, TKL, FC, CRD, PAS)
- `Projects/soccer_combo_engine.py` — Soccer parlay builder (port 8516)
- `Projects/dk_combos_engine.py` — DK combo lines from SGO (port 8515)
- `Projects/worldcup_picks.py` — World Cup FanDuel player props scraper
- `Projects/soccer_live_pull.py` — Soccer game lines (49 books, all leagues)
- `Projects/wnba_pipeline_v2.py` — WNBA backtest pipeline
- `Projects/wnba_props_live_pull.py` — Live WNBA DK player props puller
- `Projects/backtest_pipeline.py` — Odds API × ESPN historical backtest
- `Projects/sportsdata_nfl_engine.py` — NFL engine (SportsData.io)
- `Projects/team_game_mapper.py` — WNBA team alias canonicalization (13 teams, 72 aliases)
- `Projects/player_gamelogs.py` — Last-5-game rolling averages via ESPN
- `Projects/boxscore_saver.py` — Halftime + final boxscore saver (dedup-aware)
- `Projects/mlb_tc_engine.py` — MLB TC projections

## World Cup / Soccer Stats Coverage
- Goals, Assists, Shots, Shots on Target, **Corners**, Tackles, Fouls Committed, Cards, Passes
- 9 stats tracked. Position profiles + league averages per 90 for GK/DEF/MID/FWD
- Output: `Daily_Log/YYYY-MM-DD/soccer_*`

## Live Services
| Service | Port | URL |
|---|---|---|
| Streamlit Dashboard | 8510 | `http://localhost:8510` |
| DK Combos Engine | 8515 | `https://dk-combos-engine-true.zocomputer.io/combos` |
| Soccer Combo Engine | 8516 | `http://localhost:8516/combos` |

## Zo.Space Routes
- `https://true.zo.space/nba-tc` — Live TC dashboard
- `https://true.zo.space/dk-combos` — DK combos dashboard
- `https://true.zo.space/worldcup` — World Cup props dashboard
- `https://true.zo.space/api/tc` — TC engine API
- `https://true.zo.space/api/combos` — Combo generator API
- `https://true.zo.space/api/dk-lines` — DK lines per sport

## Daily Pipeline Output
- `Daily_Log/YYYY-MM-DD/` — picks.{csv,json}, slate_*.json, proj_*.json, combos_*.md, pipeline_report.md
- `Daily_Log/last_run.json` — Latest run summary
- `Daily_Log/last_run_soccer.json` — Soccer run summary

## Automations (15 daily)
- 1:00 PM — Baseline Slate Capture (all sports)
- 1:30 PM — Post-Injury Refresh
- 1:00/3:00/5:00/7:00/9:00 PM — Soccer live pull (World Cup windows)
- 5:00 PM + 6:30 PM — Pre-tip updates + combos
- 8:30/10:30 PM + 12:30 AM — Boxscore capture (halftime + final)
- 4:00 AM — System cleanup + Google Drive sync

## Secrets (in `/root/.zo/secrets.env`)
- `SPORTSGAMEODDS_API_KEY` — Primary feed (NBA player props)
- `ODDS_API_KEY` — Secondary feed (WNBA, soccer, consensus)
- `SPORTS_DATA_API_KEY` — NFL data (SportsData.io)

## Key Rules
- `Projects/pipeline_master.py` is the daily driver — run it, don't manually fix
- `AGENTS.md` is a routing index, not a changelog — keep it concise
- `SYSTEM_MAP.md` has the full system architecture diagram
