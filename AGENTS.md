# Workspace Index

> **2026-06-18 — Automation Consolidation + Cache Gate + SGO Gate + Quota Guard:**
> - **Automation consolidation:** 10 automations → 10 (same count, deactivated 2 duplicates, reduced WC from 5×→2× daily). Deactivated 1PM Slate Capture (duplicate of 1:30PM) and 5PM WNBA Pre-Tip (90min before 6:30PM, minimal data change). 1:30PM now includes pipeline_assess + worldcup_picks. 6:30PM now includes worldcup_picks. World Cup picks reduced from 5× daily (1/3/5/7/9 PM) to 2× daily (1:30 PM + 6:30 PM, synced with TC pipeline). **Total pre-tip API calls: 4 daily_picks runs → 2 (50% reduction). Total WC API calls: 5→2 (60% reduction).**
> - **Cache gate in daily_picks.py:** `_quota_guard()` checks quota_exhausted.json at runtime — if all Odds API keys are exhausted AND cache is warm (<2hr), skips live API calls entirely, serving from disk cache. Prevents wasted 401/429 calls.
> - **SGO gate in daily_picks.py:** `_sgo_rate_limited()` checks api_registry.json — if all SGO endpoints are 429, enrichment skips SGO and goes direct to consensus/self-edge fallback. Stops 3 wasted 429 calls per game.
> - **World Cup ESPN fix:** api_scan.py changed from `soccer/World%20Cup/scoreboard` (HTTP 400) → `soccer/fifa.world/scoreboard` (HTTP 200). Registry now 8/12 OK.
> - **Purge:** Removed empty cache dir, archived duplicate .py files from `Archives/source_cleanup_2026-06-17/`, purged all __pycache__ dirs.

> **2026-06-18 — MLB boxscore support + June 14-17 backfill:**
> -

> **2026-06-16 — NBA/NHL off-season:** NBA Finals and Stanley Cup Final are both done. SGO endpoints for NBA and NHL are blocked (HTTP 503). The pipeline no longer calls NBA or NHL — `daily_picks.py`, `pipeline_master.py`, and all automations now run WNBA + MLB + World Cup only.

> **2026-06-17 — API Registry + Unified Cache System:** `Projects/api_scan.py` probes 12 endpoints (Odds API, SGO, ESPN, SportsDataIO) and writes `Daily_Log/api_registry.json` with scan timestamp, status, latency, free_tier flag, and `last_used_at`. `Projects/api_cache.py` provides `cached_get(name, url, ttl)` — primary read path; disk cache `Daily_Log/cache/api/{name}.json`, default 2-hour TTL, registry auto-bumped on hit. `python3 Projects/api_cache.py warm` pre-populates from registry. Cache hits: ~1ms (vs 50-200ms network). Run scan whenever a new API is added or rate limit issues surface.

> **2026-06-17 — Soccer boxscore capture added:** `Projects/soccer_boxscore_capture.py` captures World Cup final boxscores from ESPN plays API (player-level stats: goals, assists, shots, SOT, cards, fouls, saves, tackles, passes). Basketball (WNBA/NBA) remains in `Projects/boxscore_saver.py`. Both use separate dedup registries (`wc_boxscore_registry.json` vs `boxscore_registry.json`). "Boxscore Capture" automation (8:30/10:30/12:30 PM ET) now runs both scripts.

> **2026-06-17 — WC_NAME_TO_CODE added:** `/api/tc` now maps all 48 Odds API World Cup team names → ESPN 3-letter abbreviations (e.g. "DR Congo" → "COD"). Previously COD@POR showed "NO DK LINES" because `matchOddsTeam` couldn't resolve "DR Congo" — now all 4 active WC games pull DK totals/ML/spreads. `WC_NAME_TO_CODE` lives in `/api/tc` alongside `MLB_NAME_TO_CODE` and `NHL_NAME_TO_CODE`.

> **2026-06-17 — World Cup player props integrated into `/api/tc`:** `buildMultiSportProjection` now loads WC player props from `Daily_Log/worldcup/YYYYMMDD/props.json` (output of `worldcup_picks.py`). For WORLD CUP and SOCCER sports, the function loads the locally-cached props and maps them into roster format. All 3 active WC games (CRO@ENG, PAN@GHA, COL@UZB) now return full player rosters with FanDuel props. `normMultiSport` updated with WC_NAME_TO_CODE support. `/api/worldcup-odds` TEAM_ABBREV replaced with full WC_NAME_TO_CODE (48 teams).

> **2026-06-17 — WNBA prop edge thresholds lowered + internal fallback:** `/api/tc` `PROP_EDGE_FILTERS` was NBA-calibrated (PTS:2.5, REB:2.0, AST:2.0, 3PM:1.0, STL:0.8, BLK:0.8) — WNBA consensus lines are tighter so edges rarely exceeded these. Now split into `PROP_EDGE_FILTERS_NBA` (unchanged) and `PROP_EDGE_FILTERS_WNBA` (PTS:1.5, REB:1.0, AST:1.0, 3PM:0.5, STL:0.5, BLK:0.5) via `getPropFilters(sport)`. Also added self-edge fallback: when Odds API player props are unavailable (quota exhausted), `propRowsForBacktest` uses internal `edge_pts`/`edge_reb`/etc. instead of returning all NO LINE. Result: WNBA combos went from 0 qualified across 6 games → 82 qualified legs.

> **2026-06-17 — Multi-tier API fail-safe deployed (`api_fallback.py`):** When Odds API primary key hits monthly quota, the system auto-detects exhaustion and falls through tiers:
> - **Tier 0:** Disk cache — per-game, daily; zero API calls on re-runs
> - **Tier 1:** SGO (MLB only) — zero Odds API cost; proven working
> - **Tier 2:** `ODDS_API_KEY` (primary, $25/mo) — tried first
> - **Tier 3:** `ODDS_API_KEY_FREE` (free tier, 500 req/mo) — tried when primary exhausted  
> - **Tier 4:** Self-edge — internal TC projections without market verification
> 
> Quota is detected at runtime via 401 `OUT_OF_USAGE_CREDITS` and persisted to `~/.zo/quota.json` for the day. `daily_picks.py` replaced its dual `enrich_player_lines()` + `fetch_consensus_for_matchup()` calls (4 Odds API hits per WNBA game) with a single `FallbackManager.enrich()` call (2 hits via Tier 2/3, cached after). MLB now routes through SGO exclusively. To activate the free tier fallback, add `ODDS_API_KEY_FREE` to `/root/.zo/secrets.env`.
> 
> **Cache:** `~/.zo/odds_cache/YYYY-MM-DD/` — each game cached after first fetch, TTL 2 hours. Re-runs cost zero Odds API calls.

> **2026-06-15 — NBA/NHL gating (now superseded):** `/api/tc` and `/api/dk-lines` were gated to disable NBA + NHL. Pipeline defaults to WNBA/MLB/World Cup. Streamlit dashboard shut down for NBA, services consolidated to WNBA + soccer only.

> **2026-06-17 — Workspace purge + route fix:** Purged ~3MB of obsolete Archives dirs (`_ALL_OBSOLETE_*`, `archive_legacy`, `obsolete_dashboard_dupes`, `reports_legacy`, `root_cleanup_*`, `source_cleanup_*`), duplicate project copies (`backtest/`, `data/`, `nba-tc-workspace/`), and all empty directories. `/api/dk-lines` default sport changed from NBA (off-season → 503) to WNBA. Health checks consolidated: `/api/pipeline-health` is the single canonical health endpoint — old `Scripts/health_check.py` and `Projects/pipeline_health.py` are deprecated fallbacks. Health route now includes combos, World Cup, and WNBA boxscores in its probe set.

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
- `Projects/boxscore_saver.py` — Halftime + final boxscore saver (dedup-aware, WNBA/NBA)
- `Projects/soccer_boxscore_capture.py` — World Cup final boxscore capture (ESPN plays → player stats)

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
| `/worldcup` | Page | World Cup Props — stat-by-stat team leaders, FanDuel primary book (DK has no props). 9-stat tabs (goals, assists, shots, SOT, corners, tackles, cards, fouls, passes) — Odds API currently returns assists/shots/SOT only. |
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
| `/api/worldcup-props` | API | World Cup player props + stat leaders per team |

## Daily Pipeline Output
- `Daily_Log/YYYY-MM-DD/` — picks.{csv,json}, slate_*.json, proj_*.json, combos_*.md, pipeline_report.md
- `Daily_Log/last_run.json` — Latest run summary
- `Daily_Log/last_run_soccer.json` — Soccer run summary
- `Daily_Log/wc_boxscores/` — Per-game World Cup final boxscore JSONs (17 games, June 11-16)

## Backtest Data
- `Daily_Log/wc_boxscore_registry.json` — Index of 17 completed WC group games (IDs, scores, status)
- `Daily_Log/wc_backtest_master.json` — Master backtest manifest (all games, dates, scores)
- `Daily_Log/wc_player_stats_backtest.csv` — 879 player records with goals, assists, shots, SOT, fouls, cards, offsides, saves
- `Daily_Log/wc_player_stats_backtest.json` — Same data in JSON format
- `Daily_Log/boxscore_registry.json` — NBA/WNBA halftime+final registry (legacy)
- `Daily_Log/boxscore_backtest_summary.json` — NBA/WNBA backtest summary (June 13-14)

## Automations (10 active)
| Time (ET) | Name | Status |
|-----------|------|--------|
| 1:00 PM | Slate Capture (Pre-Injury) | ✅ |
| 1:30 PM | Post-Injury Refresh | ✅ |
| 1:00/3:00/5:00/7:00/9:00 PM | World Cup Picks | ✅ |
| 5:00 PM | WNBA Pre-Tip Update | ✅ |
| 6:30 PM | Final Pre-Tip Capture + Cleanup | ✅ |
| 8:30/10:30 PM + 12:30 AM | Boxscore Capture (Halftime + Final) | ✅ |
| 2:00 AM | Daily Backtest (Odds API + ESPN settlement) | ✅ |
| 4:00 AM | Daily System Maintenance | ✅ |
| Mon 8:00 AM | Weekly 30-Day Backtest Rollup | ✅ |
| Mon 9:00 AM | Weekly System Health Check | ✅ |

## Key Rules
- `Projects/pipeline_master.py` is the daily driver — run it, don't manually fix
- `AGENTS.md` is a routing index, not a changelog — keep it concise
- `SYSTEM_MAP.md` has the full system architecture diagram