# AGENTS.md — TC Workspace (Clean, Integrated)

## Overview
Single source of truth for the **Triple Conservative (TC) sports betting system**. NBA + WNBA + NCAAB + MLB + NHL + **NFL (2026)**.

## Components

### Health Checks

**Two ways to check system health:**

### 1. Online: `/api/pipeline-health`
- **URL:** https://true.zo.space/api/pipeline-health
- **Type:** Public API, always available
- **Returns:** JSON with status (HEALTHY/DEGRADED/UNHEALTHY), failures count, and detailed per-category results

### 2. Local: `pipeline_health.py`
- **Path:** `/home/workspace/Projects/pipeline_health.py`
- **Run:** `python3 pipeline_health.py` (human-readable) or `python3 pipeline_health.py --json` (machine-readable) or `python3 pipeline_health.py --quick` (skip HTTP checks)
- **8 categories checked:**

| # | Category | What It Checks |
|---|----------|---------------|
| 1 | **API Keys** | ODDS_API_KEY, SPORTSGAMEODDS_API_KEY, SPORTS_DATA_API_KEY — present in secrets file |
| 2 | **External APIs** | ESPN v2 (free), The Odds API (with auth), SportsGameOdds NBA (with auth), SGO WNBA tier check |
| 3 | **Zo.Space Routes** | /api/tc (NBA + WNBA), /api/daily-log, /api/combos, /api/dk-lines |
| 4 | **Local Services** | Streamlit dashboard (ports 8507/8510/8501), DK Combos Engine |
| 5 | **Pipeline Scripts** | daily_picks.py, consensus_engine.py, build_pregame_combos.py — file presence |
| 6 | **Daily Log** | last_run.json freshness (<24h), per-date pick counts for last 14 days |
| 7 | **NFL Engine** | Engine script presence, W1 data pull (16 games, 1484 props from SportsData.io) |
| 8 | **Workspace** | Root workspace — stale files >30 days old |

### Known Warnings
- **SGO WNBA:** Returns "leagueID WNBA is unavailable at your current subscription tier" — NBA works, WNBA requires tier upgrade. Falls back to The Odds API + ESPN for WNBA DK lines.

### 0. NFL Engine (`archive/nfl-backtest-data/sportsdata_nfl_engine_v3.py`)
- **Path:** `/home/workspace/archive/nfl-backtest-data/sportsdata_nfl_engine_v3.py`
- **Run:** `python3 sportsdata_nfl_engine_v3.py 2026REG 1 true`
- **Sources:** SportsData.io (Discovery Lab Odds $99/mo) + The Odds API (free) + ESPN (free)
- **15 prop markets:** Fantasy Points, FP PPR, Total Yards, Receptions, Receiving Yards, Rushing Yards, Rushing Attempts, Total TDs, Passing (Att/Comp/Yds/TD/INT), Rushing/Receiving TDs
- **Output:** `Daily_Log/YYYY-MM-DD/nfl_full_2026REG_W1.json` (~1MB multi-source)
- **Tier limitations:** No schedules, season stats, projections, defensive stats, or DVOA at this tier
- **Defensive stats →** ESPN boxscore API (post-game) or SportsData.io Leagues API (commercial)
- **DVOA →** Football Outsiders FO+ subscription (proprietary, not in any API)
- **Drive:** Engine + README + full pull artifact uploaded to tysondepina99@gmail.com

### 1. Daily Pick Capture (`Projects/daily_picks.py`)
- **Path:** `/home/workspace/Projects/daily_picks.py`
- **Run:** `python3 daily_picks.py NBA WNBA`
- **Output:**
  - `/home/workspace/Daily_Log/YYYY-MM-DD/picks.csv` (47 picks today)
  - `/home/workspace/Daily_Log/YYYY-MM-DD/proj_SPORT_MATCHUP.json` (full rosters)
  - `/home/workspace/Daily_Log/last_run.json` (summary)
- **Today's run:** 3 games, 47 picks, signals: 1 OVER + 2 UNDER

### 2. Streamlit Dashboard (`Dashboard/SportsTC_Streamlit_App.py`)
- **Path:** `/home/workspace/SportsTC_Streamlit_App.py`
- **Run:** `streamlit run SportsTC_Streamlit_App.py --server.port 8510`
- **URL:** http://localhost:8510
- **6 tabs:** Project · Live Stats · Injury · Backtest · Parlay · Slate (auto-populated)
- **Slate tab:** pulls live ESPN data, auto-projects TC for each game, shows edge vs DK total

### 3. API Endpoint (`/api/tc`)
- **Path:** Zo Space route (TypeScript/Hono)
- **URL:** https://true.zo.space/api/tc
- **Modes:** project (default), live-stats, historical
- **Includes:** `valid_props` array with player prop projections ready to backtest
- **Fixes:** route now properly sends API keys via URLSearchParams and has correct WNBA/NBA team name matching via ODDS_NAME_TO_CODE reverse-map

### 4. TC Engine (`Engine/nba_tc_pipeline.py`)
- **Path:** `/home/workspace/tc-clean/CLEAN_CODE/Engine/nba_tc_pipeline.py`
- **Multi-sport support:** NBA + WNBA + NCAAB + MLB + NHL
- **Rosters:** hardcoded for all 30 NBA teams + 12 WNBA teams

### 5. Formulas
```
Player TC   = stat × 0.85 (ACTIVE) | × 0.85 × 0.55 (Q) | × 0 (OUT)
Player T    = floor(TC × 0.88)   # betting target
Edge        = TC − market_line  (positive = value)
Signal      = OVER when diff > 2 | UNDER when diff < -2 | PASS otherwise
```

### 6. Chromebook Desktop (`TC_Desktop_Installer/`)
- Run TC app locally on Chromebook via Crostini Linux
- `bash run_tc_app.sh` → opens browser to localhost:8501

### 7. Parlay Builder (2026-06-02 update)

## Workflow
1. **Daily 9 AM:** automation runs `daily_picks.py`, captures picks, emails summary
2. **Pre-game:** open dashboard, review slate tab, click any game to load into Project
3. **Live:** track picks, update results in `picks.csv` after games
4. **Weekly:** review backtest tab to find best/worst stats, adjust thresholds

## Daily Log Structure
```
/home/workspace/Daily_Log/
├── last_run.json
└── YYYY-MM-DD/
    ├── picks.csv           # ALL picks across all games
    ├── proj_NBA_NYK@SAS.json   # Full roster + TC for each game
    ├── proj_WNBA_SEA@DAL.json
    └── proj_WNBA_MIN@PHX.json
```

## Backtesting
- Read `picks.csv` for a date, compute hit rate by:
  - stat (PTS, REB, AST, 3PM, STL, BLK)
  - direction (OVER vs UNDER)
  - team (NYK, SAS, etc.)
  - matchup
- Update `result` column in `picks.csv` after games
- Thresholds live in `daily_picks.py` — edit and re-run to adjust

## Recent Backtests

### WNBA Live Backtest — June 11, 2026
- **4 games:** CHI@IND (114-106) | NY@ATL (104-90) | PHX@DAL (70-85) | LV@POR (105-89)
- **Picks graded:** 69 (28H/28M/13P = 50.0% hit rate)
- **PTS:** 78.6% (15 picks, 11H/3M/1P) — strongest stat
- **Files:** `Daily_Log/2026-06-11/wnba_live_actuals.json`, `wnba_live_backtest.md`, `wnba_backtest_graded.json`
- **Pipeline:** `wnba_backtest_live.py` — ESPN v2 summary API → boxscore scrape → name-match grading

### Boxscore Backtest — June 13-14, 2026
- **7 games:** IND@CON (85-75) | LV@MIN (100-97) | DAL@POR (83-84) | LA@PHX (111-102) | NYK@SAS (94-90) | NY@TOR (86-102) | (extra game)
- **Picks graded:** 39 across 2 days (H:21 M:12 P:6)
- **Hit rate:** 53.8% overall
- **By stat:** REB 100% (1/1) · PTS 66.7% (4/6) · 3PM 52.6% (10/19) · BLK 50% (1/2) · STL 45.5% (5/11)
- **By team:** MIN 100% · POR 100% · DAL 75% · LA 75% · LV 66.7% · NYK 42.9% · SAS 42.9% · PHX 25%
- **Key issue:** NYK@SAS had 27 picks with 6 NOT_FOUND — bench deep cuts without boxscore data
- **Files:** `Daily_Log/2026-06-13/boxscore_graded.csv`, `Daily_Log/2026-06-14/boxscore_actuals.json`, `Daily_Log/boxscore_backtest_summary.json`

## Automation
- **Rule:** Any TC/picks/edge/betting mention triggers daily log refresh
- **Daily 9 AM:** automation runs `daily_picks.py` and emails summary
- **Manual:** `python3 /home/workspace/Projects/daily_picks.py NBA WNBA`

## Key Files
| File | Purpose |
|------|---------|
| `Projects/daily_picks.py` | Daily log capture |
| `Dashboard/SportsTC_Streamlit_App.py` | Streamlit GUI |
| `Engine/nba_tc_pipeline.py` | Multi-sport engine |
| `TC_Desktop_Installer/` | Chromebook installer |
| `Daily_Log/` | Per-day pick logs |

## Secrets
- `SPORTSGAMEODDS_API_KEY` in `/root/.zo_secrets` (space server env)
- Free tier: events but no odds. Falls back to ESPN for DK totals.

## Updates
- **2026-06-15 (health check fix):** `/api/pipeline-health` was UNHEALTHY (5 failures) — root cause was the route reading `process.env` instead of the secrets file (`/root/.zo/secrets.env`), so all API keys showed as missing and connectivity checks ran without auth (401/404). Fixed by loading secrets from file and passing keys in API requests. Result: HEALTHY (0 failures). SGO key confirmed working (was 401 on June 13, now 200). Created `Projects/pipeline_health.py` as local CLI equivalent. Updated Health Checks section with full 8-category catalog.
- **2026-06-15 (NFL engine comprehensive):** Built NFL engine v3 pulling from SportsData.io (Discovery Lab Odds $99/mo), The Odds API, and ESPN. SportsData.io paid tiers documented: Discovery Lab ($99-149/mo), Leagues API (commercial, contact sales), Global API (100+ sports), Vault (historical). 15/15 prop markets captured. Purged old engine v1/v2 and duplicate data files. DVOA not available via API — requires FO+ subscription. Defensive stats available post-game via ESPN boxscore. Full artifact (1MB) and engine pushed to Drive.
- **2026-06-13 (final):** Full workspace purge — 31 stale files moved to `Daily_Log/_purged_20260613/` (13 boxscore/health/logs + 11 WNBA backtest artifacts + 7 root temp files + API_INTEGRATION_REPORT.md). Pipeline ran: 5 games (1 NBA + 4 WNBA), 48 picks. DK Combos engine confirmed live at `https://dk-combos-engine-true.zocomputer.io/combos?sport=WNBA` (104 WNBA combos, NBA also live). WORLD CUP is active (Canada vs Bosnia, Brazil vs Morocco, Scotland vs Haiti, Australia vs Turkey) but the TC engine is basketball-specific — soccer requires different ESPN endpoints, stats, and math; the `/api/tc` backend returns honest "not yet active" notice rather than faking projections. All zo.space routes error-free. Health check: Odds API ✅, ESPN ✅, SGO ❌ (401 — key may need rotation).
- **2026-06-13 (WNBA combos fix):** WNBA combos now generating correctly — 103 combos across 4 games (IND@CON: 2 qualified, MIN@LV: 4, DAL@POR: 3, LA@PHX: 6). Fixed DK odds bug: was only capturing OVER outcomes from The Odds API; now pulls both OVER and UNDER for PRA/PR/PA markets. DK game totals now populated for all WNBA matchups (previously blank). Google Drive write access re-established. Combo files in `Daily_Log/2026-06-13/`: `wnba_combos.json`, `combos_summary.json`, `combos_*.md` per matchup.
- **2026-06-01:** Built `daily_picks.py`, slate tab, 47-pick log, daily automation
- **Today:** `/api/tc` route now properly sends API keys via URLSearchParams and has correct WNBA/NBA team name matching via ODDS_NAME_TO_CODE reverse-map; SGO key is now properly set in secrets as SPORTSGAMEODDS_API_KEY; new pipeline_health.py diagnostic tool added; stale logs >7 days purged to _archive/