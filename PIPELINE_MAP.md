# TC Pipeline — Full Architecture Map
## Updated: 2026-07-25 00:10 ET

---

## PIPELINE FLOW

```
                        ┌──────────────────┐
                        │   daily_picks.py  │  ← Master orchestrator
                        │   --sport {mlb|wnba|nba|nfl|nhl|all}
                        └────────┬─────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
    ┌────▼─────┐          ┌─────▼──────┐          ┌─────▼──────┐
    │ GENERATE │          │ RECALIBRATE│          │  ENRICH    │
    │ (per     │──────────▶ (pre+post) │──────────▶ (ESPN,     │
    │  sport)  │          │            │          │  SerpAPI,  │
    └──────────┘          └────────────┘          │  Rosters,  │
                                                   │  Free APIs)│
                                                   └─────┬──────┘
                                                         │
                    ┌────────────────────────────────────┤
                    │                                    │
            ┌───────▼────────┐                  ┌───────▼────────┐
            │   picks.db     │                  │  Daily_Log/    │
            │   (SQLite)     │                  │  YYYY-MM-DD/   │
            └───────┬────────┘                  │  proj_*.json   │
                    │                           └───────┬────────┘
        ┌───────────┼───────────┐                       │
        │           │           │                       │
   ┌────▼────┐ ┌────▼────┐ ┌───▼────┐           ┌──────▼──────┐
   │ Streamlit│ │zo.space │ │tc-api  │           │ Backtest    │
   │ :8510    │ │Routes   │ │:8000   │           │ Engine      │
   └──────────┘ └──────────┘ └────────┘          └─────────────┘
```

---

## FILE TREE — BY LAYER

### 1. ORCHESTRATION (Master)
```
Projects/daily_picks.py          ← Master pipeline. --sport: mlb|wnba|nba|nfl|nhl|all
AGENTS.md                        ← Workspace index
PIPELINE_MAP.md                  ← This file
```

### 2. GENERATORS (Per-Sport Projections)
```
Projects/gen_mlb_today.py        ← MLB: statsapi.mlb.com, per-player stats, hash+tc_math
Projects/gen_wnba_today.py       ← WNBA: data/wnba_player_stats.json, 40/60 season/R5 blend
Projects/gen_nba_today.py        ← NBA: nba_rosters.json + ESPN fallback  [OFF-SEASON]
Projects/gen_nfl_today.py        ← NFL: nfl_rosters.json + ESPN fallback  [PRE-SEASON]
Projects/gen_nhl_today.py        ← NHL: nhl_rosters.json + ESPN fallback  [OFF-SEASON]
```

### 3. RECALIBRATION (Post-Gen Quality Control)
```
Projects/mlb_recalibration.py    ← MLB: drops AVG/OBP/SLG/OPS, 60/40 direction cap
Projects/wnba_recalibration.py   ← WNBA: stat dropout, player blacklist/boost
Projects/nba_recalibration.py    ← NBA: wired, dormant [OFF-SEASON]
Projects/nfl_recalibration.py    ← NFL: wired, dormant [PRE-SEASON]
Projects/nhl_recalibration.py    ← NHL: wired, dormant [OFF-SEASON]
```

### 4. TC MATH (Core Projection Engine)
```
Projects/tc_math.py              ← sport_over_under_signal() — canonical direction+edge
                                  ← SPORT_CONFIGS: min_edge, max_edge, use_pct per sport
                                  ← MLB(0.5, raw) WNBA(0.5, raw) NBA(0.5, raw)
                                  ← NFL(0.5, raw) NHL(0.2, raw)
```

### 5. DATA — ROSTERS
```
data/rosters/mlb_rosters.json    ← 783 players, 30 teams
data/rosters/wnba_rosters.json   ← 208 players, 12 teams
data/rosters/nba_rosters.json    ← 545 players, 30 teams
data/rosters/nfl_rosters.json    ← 192 players, 32 teams (ESPN pre-season limited)
data/rosters/nhl_rosters.json    ← 1051 players, 32 teams (ESPN off-season)
```

### 6. DATA — PLAYER STATS
```
data/wnba_player_stats.json      ← 173 players, season + recent5, built by build_wnba_stats.py
data/nba_player_stats.json       ← Built by build_nba_stats.py
data/nfl_player_stats.json       ← Built by build_nfl_stats.py  [THIN]
data/nhl_player_stats.json       ← Built by build_nhl_stats.py  [THIN]
```

### 7. STATS BUILDERS
```
Projects/build_wnba_stats.py     ← Aggregates 8 backtest directories into player stats
Projects/build_nba_stats.py      ← NBA stats builder
Projects/build_nfl_stats.py      ← NFL stats builder
Projects/build_nhl_stats.py      ← NHL stats builder
```

### 8. ENRICHMENT
```
Projects/src/enhancer.py         ← Multi-source enrichment pipeline
Projects/src/roster_loader.py    ← Loads rosters, enrich_player(), enrich_pick()
Projects/src/api_cap_tracker.py  ← Rate-limit enforcement
Projects/src/explanation_engine.py ← Pick rationale generation
Projects/src/adapters/action_network.py ← Free odds (game-level only)
Projects/src/adapters/free_api_aggregator.py ← ESPN, statsapi, etc.
```

### 9. API (FastAPI on :8000)
```
Projects/api/main.py             ← Main API: /health, /picks, /combos, /backtest, /game-lines
                                  ← ESPN_SB: mlb|wnba|nba|nfl|nhl
                                  ← Sports list: ["mlb","wnba","nba","nfl","nhl"]
Projects/api/live_boxscore.py    ← Live ESPN boxscore fetcher with cap enforcement
Projects/api/mlb_situation.py    ← MLB situational analysis
```

### 10. STREAMLIT DASHBOARD (:8510)
```
Projects/tc_sports_dashboard.py  ← Streamlit dashboard (all sports)
```

### 11. ZO.SPACE DASHBOARDS (true.zo.space)
```
/ (homepage)                     ← Landing page
/nba-tc                          ← Main picks + box scores dashboard
/dashboard                       ← KPI + accuracy dashboard
/live-games                      ← Live box scores + odds + stat leaders
/nfl                             ← NFL schedule + pre-season tracker
/nhl                             ← NHL schedule + off-season tracker
/api/tc                          ← Public picks API
/api/tc-full                     ← Full picks API
/api/tc-alerts                   ← Alert API
/api/accuracy-data               ← Accuracy data
/api/picks-data                  ← Picks data
/api/system-data                 ← System health data
/api/injuries                    ← Injury data
```

### 12. BACKTEST
```
Projects/backtest_engine.py      ← Core backtest engine
Projects/backtest_grader.py      ← Pick grading against boxscores
Projects/run_backtest.py         ← CLI backtest runner
```

### 13. UTILITIES
```
Projects/combo_generator.py      ← Parlay combo generation
Projects/clean_picks.py          ← Data cleaning
Projects/pipeline_audit.py       ← Pipeline audit tool
Projects/history_tracker.py      ← Historical tracking
Projects/email_config.py         ← Email config
Projects/send_email.py           ← Email sender
Projects/update_closing_lines.py ← Closing line updater
Projects/backfill_projections.py ← Projection backfill (ARCHIVED)
Projects/run_full_pipeline_check.py ← End-to-end health check
```

### 14. DATA STORES
```
Projects/data/picks.db           ← SQLite: picks, combos, accuracy tables
Projects/data/tc_pipeline.db     ← SQLite: pipeline state
Daily_Log/YYYY-MM-DD/            ← Daily projection files + last_run.json
```

### 15. REPORTS + ARCHIVES
```
reports/                         ← Backtest reports, audit reports
Archives/backtests/              ← 21 tarballs, 499 files
```

---

## INTEGRATION STATUS — 2026-07-25 00:10 ET

| Component              | MLB     | WNBA    | NBA        | NFL         | NHL        |
|------------------------|---------|---------|------------|-------------|------------|
| Generator              | ✅ LIVE | ✅ LIVE | ✅ WIRED    | ✅ WIRED     | ✅ WIRED    |
| tc_math.sport_over_under_signal | ✅ | ✅ | ✅ | ✅ | ✅ |
| Recalibration          | ✅       | ✅       | ✅          | ✅           | ✅          |
| Rosters                | ✅ 783   | ✅ 208   | ✅ 545      | ✅ 192       | ✅ 1051     |
| Player Stats           | ✅       | ✅ 173   | ✅          | THIN         | THIN       |
| API sports list        | ✅       | ✅       | ✅          | ✅           | ✅          |
| zo.space dashboard     | ✅       | ✅       | ✅ /nba-tc  | ✅ /nfl       | ✅ /nhl     |
| Streamlit              | ✅       | ✅       | ✅          | ✅           | ✅          |
| Live coverage          | LIVE    | LIVE    | OFF-SEASON | PRE-SEASON   | OFF-SEASON |

---

## AUTOMATIONS
All paused (manual maintenance window):
- MLB Morning (9 AM) · WNBA Morning (11 AM) · Combo Refresh (1:30 PM) · Evening Summary (6 PM) · Daily Sports Picks Update

## KNOWN GAPS
- SerpAPI: monthly quota maxed (~8/1 reset)
- Odds API: Free tier active, /odds/ quota-exhausted
- Player props: No free odds source — self-edge only
- SDIO: dead key
- Fangraphs: 403 IP-blocked
- NFL/NHL player stats: thin (off-season, limited ESPN data)
