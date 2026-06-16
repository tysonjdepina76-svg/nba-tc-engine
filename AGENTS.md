# Workspace Index

> **2026-06-15 — NBA/NHL gating:** `/api/tc` and `/api/dk-lines` gated NBA + NHL (disabled). Pipeline defaults to WNBA/MLB/World Cup. Streamlit dashboard shut down for NBA, services consolidated to WNBA + soccer only.

> **Workspace cleaned:** Obsolete root files (`SportsTC_Streamlit_App.py`, `daily_tip_report.py`, `generate_report.py`, etc.) moved to `Archives/root_cleanup_2026-06-15/`. `__pycache__` dirs purged. Inactive duplicate automation deleted.

> **Run the pipeline:** `python3 Projects/pipeline_master.py` — self-checks, repairs, generates picks/combos for WNBA, MLB, World Cup. Auto-repairs Streamlit + DK Combos + Soccer Combos.

## Core Pipeline (single source of truth)
- `Projects/pipeline_master.py` — **Master self-healing daily runner** — WNBA, MLB, World Cup, auto-repair
- `Projects/pipeline_health.py` — component-level health checks (APIs, services, routes, freshness)
- `Projects/pipeline_assess.py` — diagnostic assessment
- `Projects/daily_picks.py` — daily slate capture → `Daily_Log/YYYY-MM-DD/`
- `Projects/consensus_engine.py` — multi-book consensus lines (DK → FD → BetMGM → Caesars → Fanatics → Bovada)
- `Projects/build_pregame_combos.py` — pregame combo builder (TC projections × consensus lines)
- `Projects/tc_math.py` — TC math core (WNBA 40-min norm, PRA/PR/PA, edge, win%)
- `Projects/tc_dashboard.py` — Streamlit dashboard (port 8510)

## Sports Engines (active)
- `Projects/soccer_tc_engine.py` — Soccer TC projections (9 stats: G, A, SOT, S, COR, TKL, FC, CRD, PAS)
- `Projects/soccer_combo_engine.py` — Soccer parlay builder (port 8516)
- `Projects/dk_combos_engine.py` — DK combo lines from SGO (port 8515)
- `Projects/worldcup_picks.py` — World Cup FanDuel player props scraper
- `Projects/wnba_pipeline_v2.py` — WNBA backtest pipeline
- `Projects/wnba_props_live_pull.py` — Live WNBA DK player props puller
- `Projects/mlb_tc_engine.py` — MLB TC projections
- `Projects/player_gamelogs.py` — Last-5-game rolling averages via ESPN
- `Projects/boxscore_saver.py` — Halftime + final boxscore saver (dedup-aware)

## Gated / Archived
- NBA, NHL, NFL — gated in `/api/tc` + `/api/dk-lines`. To reactivate, remove the gate from those routes.

## Live Services
| Service | Port | URL |
|---|---|---|
| Streamlit Dashboard | 8510 | `http://localhost:8510` |
| DK Combos Engine | 8515 | `https://dk-combos-engine-true.zocomputer.io/combos` |
| Soccer Combo Engine | 8516 | `http://localhost:8516/combos` |

## Zo.Space Routes
| Route | Type | Purpose |
|-------|------|---------|
| `/` | Page | Homepage |
| `/nba-tc` | Page | WNBA/MLB/World Cup TC Dashboard |
| `/dk-combos` | Page | DK Combos Dashboard |
| `/worldcup` | Page | World Cup Props |
| `/speaking` | Page | Tyson DePina — Speaking Engagements (public) |
| `/mirror-workbook` | Page | The Mirror Workbook (private) |
| `/api/tc` | API | TC projections (WNBA, MLB, WORLD CUP) |
| `/api/dk-lines` | API | DK lines per sport |
| `/api/combos` | API | Combo generation |
| `/api/combo-prob` | API | Combo probability |
| `/api/pipeline-health` | API | Pipeline health check |
| `/api/daily-log` | API | Daily log access |
| `/api/wnba-boxscores` | API | WNBA boxscore history |
| `/api/worldcup-odds` | API | World Cup odds |
| `/api/worldcup-props` | API | World Cup player props |

## Daily Pipeline Output
- `Daily_Log/YYYY-MM-DD/` — picks.{csv,json}, slate_*.json, proj_*.json, combos_*.md, pipeline_report.md
- `Daily_Log/last_run.json` — Latest run summary
- `Daily_Log/last_run_soccer.json` — Soccer run summary

## Automations (8 active)
| Time (ET) | Name | Status |
|-----------|------|--------|
| 1:00 PM | Slate Capture (Pre-Injury) | ✅ |
| 1:30 PM | Post-Injury Refresh | ✅ |
| 1:00/3:00/5:00/7:00/9:00 PM | World Cup Picks | ✅ |
| 5:00 PM | WNBA Pre-Tip Update | ✅ |
| 6:30 PM | Final Pre-Tip Capture + Cleanup | ✅ |
| 8:30/10:30 PM + 12:30 AM | Boxscore Capture (Halftime + Final) | ✅ |
| 4:00 AM | Daily System Maintenance | ✅ |
| Mon 9:00 AM | Weekly System Health Check | ✅ |

## Key Rules
- `Projects/pipeline_master.py` is the daily driver — run it, don't manually fix
- `AGENTS.md` is a routing index, not a changelog — keep it concise
- `SYSTEM_MAP.md` has the full system architecture diagram