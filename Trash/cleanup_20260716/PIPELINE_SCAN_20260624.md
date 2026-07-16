# Pipeline Scan — 2026-06-24 16:45 ET

## ✅ WHAT'S WORKING (WIRED)

### Zo.Space Routes (12/12 — 200 OK)
| Route | Purpose | Status |
|---|---|---|
| /api/tc | Unified TC projections (WNBA/MLB/WC) | ✅ |
| /api/dk-lines | DK lines per sport | ✅ |
| /api/combos | Combo generation | ✅ |
| /api/combo-prob | Combo probability | ✅ |
| /api/pipeline-health | Health check | ✅ |
| /api/daily-log | Daily log access | ✅ |
| /api/wnba-boxscores | WNBA boxscore history | ✅ |
| /api/worldcup-odds | World Cup odds (ML/draw) | ✅ |
| /api/worldcup-props | World Cup player props | ✅ |
| /api/boxscores | Boxscore data | ✅ |
| /api/env-check | Environment check | ✅ |
| /api/pipeline-monitor | Pipeline monitor | ✅ |

### Zo.Space Pages
| Route | Purpose | Status |
|---|---|---|
| / | Homepage | ✅ |
| /nba-tc | WNBA/MLB/WC Dashboard (3-sport tabs) | ✅ |
| /worldcup | World Cup Props (9 stats incl corners) | ✅ |
| /dk-combos | DK Combos Dashboard | ✅ |
| /speaking | Speaking Engagements | ✅ |
| /mirror-workbook | Mirror Workbook | ✅ |

### Local Services (4 running)
| Service | Port | Status |
|---|---|---|
| tc-dashboard-streamlit | 8510 | ✅ |
| dk-combos-engine | 8515 | ✅ |
| soccer-combos-engine | 8516 | ✅ |
| sdio-lines-service | 8520 | ✅ |

### Active Engines (all wired)
- worldcup_picks.py — WC with DK-style ML/draw + self-edge + corners
- mlb_tc_engine.py — MLB (ESPN + Odds API + SDIO)
- daily_picks.py — WNBA/MLB/WC slate
- api_tc_unified.py — Unified TC handler
- consensus_engine.py — Multi-book consensus
- pipeline_master.py — Self-healing runner
- pipeline_health.py — 16 checks

---

## 🔴 WHAT'S NOT WIRED / BROKEN

### 1. Streamlit Dashboard References Dead wc_projections.py
- tc_dashboard.py line 236 shells out to Projects/wc_projections.py (stale, 1.6KB, June 13)
- Should route through worldcup_picks.py or /api/tc
- Impact: WC tab in Streamlit shows stale/empty

### 2. DK Combos Return Empty
- dk-combos-engine returns combos: [], count: 0
- build_pregame_combos.py not wired into daily pipeline
- Impact: No combo legs on dashboard

### 3. SDIO Service Shows 0 Games
- sdio-lines-service returns count: 0, games: []
- MLB picks DO have SDIO lines — but service endpoint doesn't serve them
- Impact: Dashboard can't pull live SDIO feeds

### 4. Missing Automations (9→1?)
- Only visible: TC Pipeline 6:30PM Final Pre-Tip
- Missing: 1:30PM Slate + Injury, Boxscore Capture (3x daily), Daily Backtest, Daily Maintenance, Weekly Rollup, Weekly Health
- Impact: Boxscores not captured, backtests not running

### 5. World Cup Falls Back to Default Stats for 50%+ Players
- Players without historical stats get flat defaults (0.15 goals, 0.5 SOT)
- No differentiation between stars and bench players
- Impact: Props are flat projections for most Panam/Congo players

### 6. SGO API Key — Dead
- SPORTSGAMEOODS_API_KEY returns 400/503 for all active sports
- Not used by pipeline anymore but still stored in secrets

---

## 🟡 NEEDS ENHANCEMENT

### 1. WNBA 100% Self-Edge
- No external player props — all LINE = TC × 0.88
- Need: paid Odds API Business tier or new WNBA props API

### 2. Two Dashboards Maintained Separately
- Streamlit (:8510) and zo.space (/nba-tc) — separate codebases
- Changes to one don't flow to the other

### 3. World Cup Real Odds Paywall
- Odds API free tier blocks soccer_fifa_world_cup (403)
- Upgrade to Business tier would give real DK/FD props

---

## ❌ OBSOLETE FILES — SAFE TO PURGE (~30 files, ~11MB)

### apps/sports-tc/archive/ (15 files, 248KB)
- All v7/v8/v4 archives, old WNBA props, NBA scrape
- Action: delete entire directory

### Duplicate Streamlit Apps (3 copies)
- apps/sports-tc/dashboard/nba_tc_streamlit.py
- apps/sports-tc/tc_pipeline_clean/nba_tc_streamlit.py
- apps/sports-tc/streamlit/nba_tc_streamlit.py
- Action: keep only one active copy

### Stale WC Files (8 files)
- wc_boxscore_backtest.py, wc_historical_backtest.py
- wc_live_stats.py, wc_picks_grader.py, wc_projections.py
- wc_self_edge.py, wc_tc_calibrate.py, wc_tc_math.py
- Action: delete (all replaced by worldcup_picks.py)

### Old WNBA Files (3 files)
- wnba_historical_backtest.py, wnba_pipeline_v2.py, wnba_props_live_pull.py
- Action: delete (superseeded)

### Drive_Sync/ (11MB)
- TC_Desktop_Installer.zip, TC_Workspace_Full.zip, Workbook/ (9MB)
- Action: archive or delete

### Old Scripts (8 files)
- health_check.py, health_check.sh, health_check_*.md (3 files)
- morning_briefing.py, morning_briefing_README.md
- gdrive_sync.py, drive_sync_manifest.json
- refresh_daily_data.sh, system_cleanup.sh, tc_maintenance.sh
- Action: delete or move to Archive

### Miscellaneous
- the-one-football/ (standalone app, not wired)
- live_sports_scrape/NBA_Live_Monitor_Latest.json (NBA off-season)
- Reports/wnba_7d_*.json (stale snapshots)

---

## 🔧 PRIORITY FIXES

| # | Fix | Priority | Effort |
|---|---|---|---|
| 1 | Restore missing automations (boxscore, backtest, maintenance) | P0 | 5 min |
| 2 | Fix Streamlit WC tab — route through worldcup_picks.py | P0 | 10 min |
| 3 | Wire build_pregame_combos.py into daily pipeline | P1 | 15 min |
| 4 | Purge obsolete files (30 files, 11MB) | P1 | 5 min |
| 5 | Fix SDIO service to serve cached lines | P2 | 20 min |
| 6 | Upgrade Odds API — Business tier for WC + WNBA | P2 | $/month |
