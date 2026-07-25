# Workspace Index — true.zo.computer

## Current Status (2026-07-25 00:37 AM ET) — DATA-DRIVEN RECAL · INDEPENDENT SPORTS

### ✅ TC_MATH INTEGRATION — ALL 5 SPORTS
**Every generator now uses `sport_over_under_signal()` from `tc_math.py` as the canonical direction + edge source.**

| Sport | Generator | Signal Source | Sport Config | Status |
|-------|-----------|---------------|--------------|--------|
| MLB   | `gen_mlb_today.py` | `sport_over_under_signal(..., "MLB")` | min_edge=0.5, max=8.0 | LIVE |
| WNBA  | `gen_wnba_today.py` | `sport_over_under_signal(..., "WNBA")` | min_edge=0.5, max=15.0 | LIVE |
| NBA   | `gen_nba_today.py` | `sport_over_under_signal(..., "NBA")` | min_edge=0.5, max=15.0 | OFF-SEASON |
| NFL   | `gen_nfl_today.py` | `sport_over_under_signal(..., "NFL")` | min_edge=0.5, max=15.0 | PRE-SEASON |
| NHL   | `gen_nhl_today.py` | `sport_over_under_signal(..., "NHL")` | min_edge=0.2, max=5.0 | OFF-SEASON |

### ✅ INDEPENDENT SPORTS — per-sport try/except; one failing never kills the others
### ✅ DATA-DRIVEN RECALIBRATION — SPORT_CONFIG dict + _apply_recalibration() in daily_picks.py

**Flow**: Hash-based self-edge line (0.98/1.02) → `sport_over_under_signal(projection, line, sport, min_edge=0.0)` → canonical direction + pct-capped edge. Falls back to local direction if INVALID/FLAT.

### ✅ ROSTERS — ALL 5 SPORTS COMPLETE
| Sport | File | Teams | Players | Source |
|-------|------|-------|---------|--------|
| MLB   | `data/rosters/mlb_rosters.json` | 30 | 783 | statsapi |
| WNBA  | `data/rosters/wnba_rosters.json` | 12 | 208 | ESPN |
| NBA   | `data/rosters/nba_rosters.json` | 30 | 545 | ESPN |
| NFL   | `data/rosters/nfl_rosters.json` | 32 | 2,834 | ESPN (full roster endpoint 7/25) |
| NHL   | `data/rosters/nhl_rosters.json` | 32 | 1,051 | ESPN (full roster endpoint 7/25) |

### ✅ PLAYER STATS
| Sport | File | Status |
|-------|------|--------|
| WNBA  | `data/wnba_player_stats.json` | 173 players, season + recent5 |
| MLB   | Live via statsapi | Per-game, cached |
| NBA   | `data/nba_player_stats.json` | Stub (off-season) |
| NFL   | `data/nfl_player_stats.json` | Stub (pre-season) |
| NHL   | `data/nhl_player_stats.json` | Stub (off-season) |

### ✅ RECALIBRATION — 5/5
| Sport | File | Function |
|-------|------|----------|
| MLB   | `mlb_recalibration.py` | `calibrate_mlb_picks()` |
| WNBA  | `wnba_recalibration.py` | `calibrate_wnba_picks()` |
| NBA   | `nba_recalibration.py` | `calibrate_nba_picks()` |
| NFL   | `nfl_recalibration.py` | `calibrate_nfl_picks()` |
| NHL   | `nhl_recalibration.py` | `calibrate_nhl_picks()` |

### ✅ API — main.py 5-SPORT
- `ESPN_SB` dict: all 5 sports mapped to ESPN v2 paths
- `fetch_live_games()`: multi-sport via ESPN_SB lookup
- `system_health_check()`: sports = ["mlb","wnba","nba","nfl","nhl"]
- All endpoints (`/picks/top`, `/box-scores`, `/tc-alerts`, `/injuries`, `/game-lines`, `/live-picks`) accept `sport=mlb|wnba|nba|nfl|nhl`

### ✅ DASHBOARDS — ALL LIVE
| Route | URL | Status |
|-------|-----|--------|
| 🏀 NBA-TC | `https://true.zo.space/nba-tc` | Picks/Box/Combos/Alerts |
| 📊 Dashboard | `https://true.zo.space/dashboard` | KPI/Top Picks/Accuracy |
| 🏟️ Live Games | `https://true.zo.space/live-games` | Box Scores + MLB Diamond |
| 🏈 NFL | `https://true.zo.space/nfl` | Schedule + Pre-season |
| 🏒 NHL | `https://true.zo.space/nhl` | Schedule + Off-season **(NEW 7/25)** |
| 📡 Streamlit | `http://localhost:8510` | 5-sport Combo Ribbon + Bet Slip |
| 🔌 tc-api | `https://tc-api-true.zocomputer.io` | UP |

### ✅ GEN_MLB_TODAY.PY — OUTPUT FORMAT FIXED
- `projections` dict now contains `{stat: {projection, line, edge, direction, period}}` (like WNBA format)
- No separate `lines` dict — unified for `daily_picks.py` loader
- `fc_math.sport_over_under_signal()` computes direction + edge for each stat

### 📁 FULL PIPELINE TREE

```
/home/workspace/
├── AGENTS.md                                    ← THIS FILE
├── Projects/
│   ├── daily_picks.py                           ← MAIN PIPELINE: --sport mlb|wnba|nba|nfl|nhl|all
│   ├── tc_math.py                               ← CANONICAL MATH: over_under_signal, sport_over_under_signal, SPORT_CONFIGS
│   │
│   ├── gen_mlb_today.py                         ← MLB: statsapi per-game, tc_math wired ✅
│   ├── gen_wnba_today.py                        ← WNBA: per-player stats, tc_math wired ✅
│   ├── gen_nba_today.py                         ← NBA: roster self-edge, tc_math wired ✅ (off-season)
│   ├── gen_nfl_today.py                         ← NFL: roster + season avg, tc_math wired ✅ (pre-season)
│   ├── gen_nhl_today.py                         ← NHL: roster + season avg, tc_math wired ✅ (off-season)
│   │
│   ├── mlb_recalibration.py                     ← MLB post-gen: 60/40 cap, stat dropout
│   ├── wnba_recalibration.py                    ← WNBA post-gen: direction diversity
│   ├── nba_recalibration.py                     ← NBA post-gen
│   ├── nfl_recalibration.py                     ← NFL post-gen
│   ├── nhl_recalibration.py                     ← NHL post-gen
│   │
│   ├── backfill_projections.py                  ← Historical backfill
│   ├── backtest_engine.py                       ← Full P&L, Sharpe, Kelly
│   ├── backtest_grader.py                       ← Grade picks vs boxscores
│   ├── combo_generator.py                       ← Parlay combos
│   │
│   ├── api/
│   │   ├── main.py                              ← FastAPI :8000 — 5-sport ESPN_SB, all endpoints
│   │   ├── live_boxscore.py                     ← ESPN boxscore parser + display_stats
│   │   └── mlb_situation.py                     ← MLB situational context
│   │
│   ├── src/
│   │   ├── roster_loader.py                     ← Multi-sport roster enrichment
│   │   ├── enhancer.py                          ← Context enrichment
│   │   ├── explanation_engine.py                ← Pick rationale generation
│   │   ├── api_cap_tracker.py                   ← ESPN API throttle tracker
│   │   └── adapters/
│   │       ├── action_network.py                ← Free game odds (A.N. no key)
│   │       └── free_api_aggregator.py           ← statsapi, pybaseball, nba_api
│   │
│   ├── tc_sports_dashboard.py                   ← Streamlit :8510
│   ├── build_wnba_stats.py                      ← Builds data/wnba_player_stats.json
│   ├── build_nba_stats.py                       ← NBA stats builder
│   ├── build_nfl_stats.py                       ← NFL stats builder
│   ├── build_nhl_stats.py                       ← NHL stats builder
│   │
│   ├── data/
│   │   ├── picks.db                             ← SQLite picks database
│   │   └── tc_pipeline.db                       ← Pipeline state
│   │
│   └── Daily_Log/{YYYY-MM-DD}/
│       ├── proj_MLB_*.json                      ← Per-game MLB projections
│       ├── proj_WNBA_*.json                     ← Per-game WNBA projections
│       ├── proj_NBA_*.json                      ← Per-game NBA projections
│       ├── proj_NFL_*.json                      ← Per-game NFL projections
│       └── proj_NHL_*.json                      ← Per-game NHL projections
│
├── data/
│   ├── rosters/
│   │   ├── mlb_rosters.json                     ← 30 teams, 783 players
│   │   ├── wnba_rosters.json                    ← 12 teams, 208 players
│   │   ├── nba_rosters.json                     ← 30 teams, 545 players
│   │   ├── nfl_rosters.json                     ← 32 teams, 2,834 players
│   │   └── nhl_rosters.json                     ← 32 teams, 1,051 players
│   │
│   └── *player_stats.json                       ← Per-sport stats (WNBA=real, rest=stubs)
│
├── zo.space routes:
│   ├── /nba-tc        (public)                  ← Main picks view
│   ├── /dashboard     (public)                  ← KPI + Top Picks
│   ├── /live-games    (public)                  ← Live box scores + odds
│   ├── /nfl           (public)                  ← NFL schedule + pre-season
│   └── /nhl           (public)                  ← NHL schedule + off-season  **NEW 7/25**
│
└── api routes:
    ├── /api/accuracy-data    (public)          ← Accuracy data
    ├── /api/injuries         (public)          ← Injury reports
    ├── /api/picks-data       (public)          ← Picks data
    ├── /api/system-data      (public)          ← System status
    ├── /api/tc               (public)          ← TC picks
    ├── /api/tc-alerts        (public)          ← TC alerts
    └── /api/tc-full          (public)          ← Full TC data
```

### daily_picks.py — FULLY WIRED
- `--sport` accepts: mlb, wnba, nba, nfl, nhl, all
- Pre-gen + post-gen recalibration hooks for ALL 5 sports
- Enrichment (ESPN, SerpAPI, free APIs, rosters) applies to ALL 5 sports
- `load_projections()` reads unified format: `{stat: {projection, line, edge, direction, ...}}` for all sports
- MLB format fixed: no more separate `lines` dict — unified with other sports

### BACKTEST TRUTH
- **84 WNBA picks from 7/19**: 51 hits, 33 misses = 60.7% hit rate (all UNDER — old engine)
- **3,094 graded_picks rows are junk** — line=0 projections, auto-graded
- **Real grading**: Only the `picks` table with valid market lines

### 🔴 AUTOMATIONS — ALL PAUSED
- MLB Morning (9 AM), WNBA Morning (11 AM), Combo Refresh (1:30 PM), Evening Summary (6 PM)
- Reason: Manual maintenance window

### ⚠️ KNOWN GAPS
- SerpAPI: monthly quota maxed
- Odds API: quota-exhausted. Action Network = game odds only
- Player props: No free source — self-edge only
- NFL/NHL/NBA stats: stubs (off-season / pre-season)

### PERSONA
- **TC Pipeline Engineer** (d5301f09) — active.

### INFRASTRUCTURE
- Streamlit: :8510 (UP) | API: :8000 (UP)
- tc-api: https://tc-api-true.zocomputer.io (UP)

### ⚠️ CONTACT TRUTH
- ONLY phone: 508-840-0794 (SMS +15088400794)
- Email: tysonjdepina76@gmail.com / tysondepina99@gmail.com
