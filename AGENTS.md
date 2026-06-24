# 2026-06-23 23:27 ET — MLB DASHBOARD FIXED — windows now render full rosters
# Root cause: api_tc_unified.py returned flat away_players/home_players arrays with tc_batting.* nested fields,
# but /nba-tc frontend TeamTable/playerRows expected nested away.all.players[] structure with flat tc_h/line_h/edge_h fields.
# Fixes: (1) api_tc_unified.py reshapes MLB output to nested all/starters/bench + flattens tc/line/edge fields + computes summary fields. 
# (2) /nba-tc TeamLeaders now sport-aware — shows H/HR/RBI/R/SB/AVG for MLB instead of PTS/REB/AST/3PM/STL/BLK.
# Pipeline ran clean: 2 MLB games, 157 picks. DK totals 13.5 (ATL@SD) and 4.5 (ATH@SF).

# 2026-06-23 14:25 ET — MLB FULLY RESTORED — 904 picks, 23 games, SDIO/S
# Root Cause: api.theoddsapi.com changed URL format from /{sport}/odds to /odds/?sport_key={sport}
# World Cup/soccer now pulls DK totals/ML/spreads from ESPN embedded D
# 2026-06-22 16:15 ET — DK LINES RESTORED — Odds API URLs fixed, 12/20 games now live
# All consensus_engine.py + /api/tc URLs updated. API key valid. Free tier = game lines only (no player props).
# MLB: 11/16 games DK LIVES LIVE (totals 7.0-11.5). WNBA: ESPN-embedded DK totals (169.5-178.5). WC: not supported by this API.

## Workspace Index
> **📋 PIPELINE_MAP.md** — Complete function map, API key directory, endpoint status (live-scanned 2026-06-23). Read this FIRST for any pipeline question.
> **2026-06-22 16:15 ET — DK LINES RESTORED after 48hr outage:**
> - **Root cause:** `api.theoddsapi.com` changed URL format. Code was using `/{sport_key}/odds` (404) but correct is `/odds/?sport_key=...`. Also: `ODDS_BASE` was `api.the-odds-api.com/v4` (dead key) vs `api.theoddsapi.com` (live).
> - **Fixes applied:**
>   - `consensus_engine.py`: All 4 URL constructions fixed, added `apiKey` param, secrets loading fixed, MLB_TEAM_MAP added (30 teams), response normalizer for new `books` format
>   - `/api/tc` zo.space route: `ODDS_BASE` updated, `fetchMultiSportDKLines` rewritten for new `/odds/` URL + new `books` response format
> - **Result:** 12/20 games DK LINES LIVE (vs 0 before). MLB totals flowing (7.0-11.5), WNBA via ESPN embedded (169.5-178.5). World Cup still 403 (no soccer_fifa_world_cup key).
> - **Player props:** Not available on free tier — requires Business+ plan for `/props/` endpoint. Self-edge fallback active for WNBA/MLB prop-level picks.
> - **Pipeline:** `daily_picks.py` ran successfully — 866 picks across 20 games for June 22

# 2026-06-20 22:10 ET — Quota Gate Hardwired — WC self-edge now auto-activates when Odds API exhausted
# World Cup dashboard FIXED — props.json overwrite + API fallback

## Workspace Index
> **2026-06-20 00:30 ET — Full integration pass complete:**
> - SGO new key saved (validated, rate-limited), Odds API flaky

> **2026-06-19 18:45 ET — World Cup dashboard FIXED (props.json overwrite + API fallback):**
> - **Root cause:** `Daily_Log/worldcup/20260619/props.json` was overwritten by a pipeline step (likely `daily_picks.py`) with a flat 331-entry picks list (`player/stat/tc_projection/edge` format) instead of match objects with nested `player_props` dict.
> - The `/api/worldcup-props` route iterated each flat entry as if it were a match → 331 fake matches all with `player_count: 0` → dashboard showed "nothing."
> - **Fix #1:** Restored `props.json` from `matches.json` (worldcup_picks.py's canonical output, 4 real matches).
> - **Fix #2:** `/api/worldcup-props` now validates format (checks for `teams` array vs flat `player` string), auto-falls back to `matches.json` when `props.json` is corrupted, and unwraps the `{matches: [...]}` wrapper format.
> - **Result:** 4 matches, 44 players, 132 props, 116 picks (MOR@SCO 26p/78 props LIVE, HAI@BRA 18p/54 props SCHEDULED).
> - **Lingering:** Odds API key still 401 INVALID_KEY — AUS@USA and PAR@TUR show 0 props (no cache). World Cup needs new Odds API key or ESPN-scraped player props for full coverage.
>
> **2026-06-19 18:35 ET — WNBA DK lines FIXED via ESPN embedded odds:**
> - Both Odds API key and SGO key return HTTP 401. WNBA games showed `dk_total: null`, `signal: "NO MARKET"`.
> - `fetchDraftKingsFromESPN()` was added to `/api/tc` `getBestOdds()` 4-tier cascade (SGO → Odds API → ESPN DK → self-edge). ESPN scoreboard returns free DK totals/ML/spreads — no key needed.
> - Result: TOR@CON (DK total 168.5, UNDER, -105/-115), WSH@NY (DK total 168.5, +550/-800).
> - `ml_source: "ESPN DraftKings embedded"` — confirms real DK lines flowing.

> **2026-06-19 03:15 ET — MLB dashboard route fix + Odds API status:**
> - **Odds API key: `INVALID_KEY` 401** — key `304fe645...` was quota-exhausted earlier
> - **MLB self-edge: WORKING** — 555 picks today across 14 games, `tc-internal-fallback` (LINE = TC × 0.88).
> - **Dashboard fix:** Routed MLB through `/api/tc` (was hitting dead Odds API). Now shows 27 props/game from self-edge.

> **2026-06-19 03:15 ET — SportsDataIO MLB Player Props INTEGRATED:**
> - **Endpoint:** `https://api.sportsdata.io/v3/mlb/odds/json/PlayerPropsByDate/YYYY-MM-DD` — PAID unlimited key
> - **1,587 live props** across 14 games, 10 stat types (Hits, Total Bases, Runs, RBIs, HR, Strikeouts, Pitching Hits, Pitching Runs, Pitching Strikeouts, Fantasy Points)
> - **New module:** `Projects/mlb_sdio_props.py` — fetches SDIO props, maps to ESPN team codes + player names, returns `{matchup: {player_name: {stat: line}}}`
> - **Wired into `mlb_tc_engine.py` as Layer 2** (Layer 1: Odds API → Layer 2: SDIO → Layer 3: self-edge)
> - **899 MLB props today, 311 OVER/UNDER signals at EDGE_THRESH_MLB_SDIO=0.5**
> - **Stat mapping:** Hits→hits, Total Bases→total_bases, Runs→runs, Home Runs→hr, Runs Batted In→rbi, Strikeouts→strikeouts, Pitching Hits→hits_allowed, Pitching Runs→earned_runs
> - **`/api/tc` shells out to `mlb_tc_engine.py`** — SDIO props flow through dashboard automatically
> - **AGENTS.md →** added SportsDataIO as primary MLB prop source (replaces dead Odds API)
>
> - **WNBA: 164 picks** via `live_roster_api` self-edge fallback. Already routed through `/api/tc`.
> - **World Cup: 0 picks** — fully dependent on Odds API. No self-edge fallback for soccer yet.
> - **Self-sufficient architecture:** ESPN gamelogs → `mlb_tc_engine.py` / TC math → self-edge LINE → `/api/tc` → dashboard. Zero external API calls for MLB/WNBA projections.

> **2026-06-19 03:15 ET — M**

> **2026-06-19 — Backtest pipeline fix:**
> - Removed stray `sys.exit(1)` at line 826 that was killing backtest_pipeline.py after init
> - Added `ODDS_BASE = "https://api.the-odds-api.com/v4/sports"` constant (was missing)
> - Fixed `ODDS_API_KEY` loading from secrets (was reading `val` but never assigning)
> - Added `grade_daily_pipeline_projections()` fallback — when `--days 1` has insufficient history for leave-one-out TC math, loads daily pipeline's `valid_props` and grades against ESPN boxscores
> - First successful run: 49 picks graded, 57.1% hit rate for June 18 ATL@IND

> **2026-06-18 — Full System Hardwire + Purge:**
> - **37/37 .py files compile clean** — fixed 4 broken files (api_scan.py, team_game_mapper.py, wnba_props_live_pull.py, backtest_pipeline.py)
> **2026-06-18 22:18 ET — Pipeline Master Full Run:**
> - **7 checks passed, 0 failures** — pipeline_master self-check+self-repair+execute cycle clean
> - **2 services auto-repaired** — DK Combos (8515) + Soccer Combos (8516) restarted
> - **Odds API: 180 requests remaining** — free tier healthy, no exhaustion risk
> - **SGO API: 401** — key expired, but MLB now uses Odds API directly (no SGO dependency)
> - **NBA slate: MISSING** — expected, NBA off-season, pipeline gated correctly
> - **Git: pushed** to origin/master

> - **World Cup cache wired** — worldcup_picks.py now uses disk cache (WC_CACHE_DIR), cuts Odds API calls from 8→~3 per run
> - **Pipeline health self-monitoring** — `/api/pipeline-health` checks all services, routes, API keys, cache freshness, automations. Health button wired on `/nba-tc` dashboard.
> - **Automations: 10→7** — deleted 3 duplicates, paused 1. World Cup picks merged into 1:30PM/6:30PM.
> - **Purged:** ~15MB of Archives tar.gz, all __pycache__, stale Daily_Log/cache files
> - **Odds API key:** Free tier (500 req/mo) — `apiKey` query param (not x-api-key header) per v4 spec
> - **Services:** dk-combos-engine (8515) fixed (3 indentation bugs), sdio-lines-service (8520) running, Streamlit (8510) running
> - **Consensus engine:** WNBA 11-player consensus working, PLAYER_MARKETS cleaned (soccer markets removed)
> - **Secrets:** `ODDS_API_KEY` + `SGO_API_KEY` in `/root/.zo/secrets.env` and env


> - Payment at 3:21 PM ET renewed key. New free key works (500 req/mo).
> - Fixed: x-api-key header → apiKey query param across all Odds API calls.
> - Fixed: Added regions=us to all multi-book calls.
> - Fixed: Removed soccer markets from PLAYER_MARKETS (was causing 422).
> - Fixed: Event ID URL path for consensus calls.
> - Data flow: WNBA enrichment (15 DK props), MLB lines (5/7 games), consensus (11-player).
> - Secrets: ODDS_API_KEY in /root/.zo/secrets.env + env. SGO key also live.
> - 2 MLB games not in Odds API feed today (SF@ATL, CHW@HOU) — data availability.

# Workspace Index

> **2026-06-18 — MLB self-edge fallback + Odds API 401 detection:**
> - **Root cause:** Odds API key `0ba199e1...` returns HTTP 401 (expired/invalid). This killed all DK lines for MLB + World Cup, and prevented DK line enrichment for WNBA.
> - **MLB self-edge fix:** `mlb_tc_engine.py` now generates self-edge props when no DK lines available — uses internal LINE = floor(TC × 0.88), EDGE = TC - LINE, threshold 1.0 for self-edge mode. TOR@BOS now produces 46 valid_props (8 active OVER signals) vs 0 before. All 9 MLB games generate 401 total picks.
> - **WNBA unchanged:** Already had self-edge via `/api/tc` `propRowsForBacktest` — 49 valid props for ATL@IND (self-edge, no DK lines).
> - **World Cup:** Cannot self-edge — needs Odds API for live FD/DK player props. Currently 0 props across 3 games.
> - **Health check upgrade:** `pipeline_health.py` now explicitly detects HTTP 401 and flags as FAILURE with message "KEY EXPIRED/INVALID — all DK lines dead".
> - **/api/tc route fix:** `buildMultiSportProjection` now includes `source` field in valid_props mapping (previously stripped).
> - **SGO does NOT support MLB or World Cup** — confirmed via API test (both return `success: false`). SGO only works for NBA/WNBA.

> **2026-06-18 — Automation Consolidation + Cache Gate + SGO Gate + Quota Guard:**
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
| `/api/slate` | API | **NEW 2026-06-24** — Multi-sport slate (WNBA, MLB, NFL, World Cup) with DK totals |
| `/api/backtest` | API | **NEW 2026-06-24** — B |
| `/api/scan` | API | **NEW 2026-06-24** — S |

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

## Automations (7 total, 6 active)
| Time (ET) | Name | Status |
|-----------|------|--------|
| 1:30 PM | Slate + Injury Refresh (includes WC) | ✅ |
| 6:30 PM | Final Pre-Tip (includes WC + combos) | ✅ |
| 8:30/10:30 PM + 12:30 AM | Boxscore Capture (Halftime + Final) | ✅ |
| 2:00 AM | Daily Backtest (Odds API + ESPN settlement) | ✅ |
| 4:00 AM | Daily System Maintenance | ✅ |
| Mon 8:00 AM | Weekly 30-Day Backtest Rollup | ✅ |
| Mon 9:00 AM | Weekly System Health Check | ⏸️ Paused |


> **2026-06-18 consolidation:** 10→7 (deleted 3 duplicates, paused 1). World Cup picks merged into 1:30PM/6:30PM. 1PM pre-injury + 5PM WNBA pre-tip deleted. Health check paused — `/api/pipeline-health` self-monitors.
## Key Rules
- `Projects/pipeline_master.py` is the daily driver — run it, don't manually fix
- `AGENTS.md` is a routing index, not a changelog — keep it concise
- `SYSTEM_MAP.md` has the full system architecture diagram