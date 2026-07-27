# TC PIPELINE — FULL SKELETON MAP
## 2026-07-27

```
═══════════════════════════════════════════════════════════════════════════
                            LAYER 0 — DATA SOURCES
═══════════════════════════════════════════════════════════════════════════

  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
  │  statsapi     │  │  ESPN v2 API │  │ pybaseball│  │  nba_api     │
  │  (MLB live)   │  │  (rosters +  │  │ (Statcast │  │  (WNBA stats)│
  │               │  │   schedules) │  │  xBA etc) │  │              │
  └──────┬───────┘  └──────┬───────┘  └─────┬────┘  └──────┬───────┘
         │                 │               │               │
  ┌──────┴───────┐  ┌──────┴───────┐  ┌────┴─────┐  ┌─────┴──────┐
  │TheRundown    │  │ SerpAPI      │  │ Odds API │  │ OddsPapi   │
  │(game lines)  │  │ (QUOTA MAX)  │  │ (QUOTA   │  │ (not yet   │
  │5 calls/day   │  │              │  │  MAXED)  │  │  wired)    │
  └──────┬───────┘  └──────────────┘  └──────────┘  └────────────┘
         │
    FREE TIER ONLY (spread/total/ML — no player props)

═══════════════════════════════════════════════════════════════════════════
                      LAYER 1 — ROSTERS & STATS
═══════════════════════════════════════════════════════════════════════════

  data/rosters/                     data/
  ├── mlb_rosters.json  30 teams    ├── wnba_player_stats.json
  ├── wnba_rosters.json  12 teams   ├── nba_player_stats.json  (stub)
  ├── nba_rosters.json   30 teams   ├── nfl_player_stats.json  (stub)
  ├── nfl_rosters.json   32 teams   └── nhl_player_stats.json  (stub)
  └── nhl_rosters.json   32 teams

  data/schedules/
  └── schedules_master.json  ← build_master_schedule.py

═══════════════════════════════════════════════════════════════════════════
                   LAYER 2 — PROJECTION GENERATORS
═══════════════════════════════════════════════════════════════════════════

  ┌──────────────────────┐
  │ gen_mlb_today.py     │ ← statsapi per-game stats → per-player projections
  │ gen_wnba_today.py    │ ← wnba_player_stats.json → per-player projections
  │ gen_nba_today.py     │ ← nba_player_stats.json  → per-player projections
  │ gen_nfl_today.py     │ ← nfl_player_stats.json  → per-player projections
  │ gen_nhl_today.py     │ ← nhl_player_stats.json  → per-player projections
  └──────────┬───────────┘
             │
        Each generator produces:
        Daily_Log/YYYY-MM-DD/proj_{SPORT}_{AWAY}_at_{HOME}.json
        {
          game_id, away, home, start_time, players: [
            { name, player_id, team, season_stats, projections: {
                STAT: { projection, line, edge, direction }
              }
            }
          ]
        }

═══════════════════════════════════════════════════════════════════════════
                   LAYER 3 — SELF-EDGE LINE ENGINE
═══════════════════════════════════════════════════════════════════════════

  ┌────────────────────────────────────────────────────┐
  │ _self_edge_line(stat, proj_val, hash_seed)         │
  │                                                    │
  │  SELF_EDGE_SPREAD (per stat):                     │
  │    H/2B/3B: 30%     R/RBI/BB: 20%                 │
  │    HR/SB/K/ER: 25%  Rate stats: 15%               │
  │                                                    │
  │  MIN_SELF_EDGE = 0.05 (absolute floor)            │
  │                                                    │
  │  Line = proj × (1 ± spread)                       │
  │  Direction = hash_seed % 4 (quarter rotation)      │
  │  Edge = max(|proj - line|, 0.05)                  │
  └───────────────────────┬────────────────────────────┘
                          │
  ┌───────────────────────┴────────────────────────────┐
  │ sport_over_under_signal(projection, line, sport)   │
  │                                                    │
  │  Located in tc_math.py — canonical direction       │
  │  + edge source for ALL 5 sports                   │
  │                                                    │
  │  SPORT_CONFIGS:                                   │
  │    MLB:  min_edge=0.5,  max=8.0                   │
  │    WNBA: min_edge=0.5,  max=15.0                  │
  │    NBA:  min_edge=0.5,  max=15.0                  │
  │    NFL:  min_edge=0.5,  max=15.0                  │
  │    NHL:  min_edge=0.2,  max=5.0                   │
  │                                                    │
  │  When line is self-edge (min_edge=0.0):            │
  │    → FLAT/INVALID fallback = local direction       │
  └────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                  LAYER 4 — MAIN PIPELINE (daily_picks.py)
═══════════════════════════════════════════════════════════════════════════

  python3 daily_picks.py --sport mlb|wnba|all

  ┌────────────────────────────────────────────────────┐
  │ STEP 1: load_projections(sport)                   │
  │   Reads Daily_Log/{date}/proj_{SPORT}_*.json      │
  │   Unifies all games → flat list of stat-rows      │
  │   Output format: {name, team, sport, stat,        │
  │     matchup, projection, line, edge, direction}   │
  └───────────────┬────────────────────────────────────┘
                  │
  ┌───────────────┴────────────────────────────────────┐
  │ STEP 2: ENRICHMENT (per sport)                    │
  │                                                    │
  │  enrich_lines_via_espn()                           │
  │    → Tags with ESPN context (not line replacement) │
  │                                                    │
  │  enrich_projections_with_therundown()              │
  │    → Replaces market_line with live game lines     │
  │    → Capped at 5 calls/day (free tier)            │
  │    → PRESERVES self-edge values (no recompute)    │
  │                                                    │
  │  enrich_with_free_apis()                           │
  │    → statsapi (player_stat_data) + pybaseball     │
  │    → Cached stats, budget-guarded                 │
  │                                                    │
  │  enrich_with_rosters()                             │
  │    → team_id, position, status from roster files  │
  └───────────────┬────────────────────────────────────┘
                  │
  ┌───────────────┴────────────────────────────────────┐
  │ STEP 3: RECALIBRATION (pre + post)                │
  │                                                    │
  │  _apply_recalibration(sport, items, stage)         │
  │                                                    │
  │  PRE-stage:                                        │
  │    → Drops rate stats (AVG, OBP, SLG, OPS)        │
  │    → Filters blacklisted players                  │
  │    → Enforces 60/40 direction cap                 │
  │                                                    │
  │  POST-stage:                                       │
  │    → Final direction balance check                │
  │    → Edge threshold filtering                     │
  └───────────────┬────────────────────────────────────┘
                  │
  ┌───────────────┴────────────────────────────────────┐
  │ STEP 4: SAVE                                       │
  │                                                    │
  │  → picks.db (SQLite): INSERT OR REPLACE           │
  │    Columns: date, league, player, team, stat,     │
  │    tc_projection, market_line, edge, direction,   │
  │    reason, matchup, signal, actual, hit, profit    │
  │                                                    │
  │  → Filter: |edge| < 0.01 → SKIP (noise filter)    │
  │                                                    │
  │  → Combo generation: top 25 parlays               │
  │                                                    │
  │  → last_run.json: timestamp + counts              │
  └────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                     LAYER 5 — GRADING ENGINE
═══════════════════════════════════════════════════════════════════════════

  Projects/sports_grading_engine.py
  ┌────────────────────────────────────────────────────┐
  │ grade_picks(picks_df, sport, date_str)             │
  │                                                    │
  │ Direction-aware logic:                            │
  │   OVER:  hit = actual >= projection               │
  │   UNDER: hit = actual <= projection               │
  │                                                    │
  │ Data sources for actuals:                         │
  │   MLB:  statsapi boxscores (schedule + game_data) │
  │   WNBA: ESPN boxscores                            │
  │   NBA:  nba_api (off-season)                      │
  │   NFL:  ESPN (pre-season)                         │
  │   NHL:  NHL API (off-season)                      │
  └────────────────────────────────────────────────────┘

  Grading scripts:
  ├── grade_mlb_0725.py            ← one-shot grader
  ├── regrade_mlb_statcast.py     ← direction-aware with Statcast
  ├── regrade_self_edge.py        ← before/after self-edge comparison
  └── backtest_selfedge_v2.py     ← v2 backtest with stat-aware spread

═══════════════════════════════════════════════════════════════════════════
                     LAYER 6 — BACKTEST ENGINE
═══════════════════════════════════════════════════════════════════════════

  Projects/backtest_engine.py
  ┌────────────────────────────────────────────────────┐
  │ Full P&L, Sharpe ratio, Kelly criterion            │
  │ Historical pick grading against boxscores         │
  └────────────────────────────────────────────────────┘

  Projects/combo_generator.py
  ┌────────────────────────────────────────────────────┐
  │ Parlay combination builder from top picks         │
  └────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                     LAYER 7 — OUTPUT SURFACES
═══════════════════════════════════════════════════════════════════════════

  ZO.SPACE ROUTES (10 pages + 7 API routes):
  ┌───────────────────────────────────────────────────┐
  │ /                 Home (public)                   │
  │ /nba-tc           Main picks + box + combos       │
  │ /dashboard        KPI, top picks, accuracy        │
  │ /live-games       Live box scores + MLB diamond   │
  │ /mlb              MLB live + picks                │
  │ /wnba             WNBA live + picks               │
  │ /nfl              NFL schedule                    │
  │ /nhl              NHL schedule                    │
  │ /speaking         Tyson speaking page             │
  │ /mirror-workbook  The Mirror Workbook (private)   │
  ├───────────────────────────────────────────────────┤
  │ /api/tc           TC picks endpoint               │
  │ /api/tc-full      Full TC data                    │
  │ /api/tc-alerts    TC alerts                       │
  │ /api/picks-data   Picks data                      │
  │ /api/accuracy-data Accuracy data                  │
  │ /api/injuries     Injury reports                  │
  │ /api/system-data  System status                   │
  └───────────────────────────────────────────────────┘

  SERVICES (ALL PAUSED — manual only):
  ┌───────────────────────────────────────────────────┐
  │ tc-api              FastAPI :8000                 │
  │ tc-streamlit        Streamlit :8510               │
  │ tc-streamer         Background data streamer      │
  │ Automations (4)     Scheduled tasks               │
  └───────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                    LAYER 8 — RECALIBRATION MODULES
═══════════════════════════════════════════════════════════════════════════

  Per-sport post-generation calibration:

  mlb_recalibration.py    → calibrate_mlb_picks()
    Drops: AVG, OBP, SLG, OPS (rate stats)
    Caps:  60/40 direction split
    Edge:  threshold filtering by stat type

  wnba_recalibration.py   → calibrate_wnba_picks()
  nba_recalibration.py    → calibrate_nba_picks()
  nfl_recalibration.py    → calibrate_nfl_picks()
  nhl_recalibration.py    → calibrate_nhl_picks()

═══════════════════════════════════════════════════════════════════════════
                    DATA FLOW — END TO END
═══════════════════════════════════════════════════════════════════════════

  statsapi ──→ gen_mlb_today.py ──→ proj_MLB_*.json
                   │                      │
            _self_edge_line()     daily_picks.py
            (stat-aware spread)   ──→ enrichment
                   │                      │
            sport_over_under_     recalibration (pre/post)
            signal()                     │
                   │               picks.db + CSV
            projection files       ──→ grading engine
                                        │
                                   zo.space dashboards
                                   (10 routes, 7 APIs)

═══════════════════════════════════════════════════════════════════════════
                    KNOWN GAPS & LIMITATIONS
═══════════════════════════════════════════════════════════════════════════

  🔴 NO REAL MARKET LINES → self-edge is direction-blind
  🔴 Odds API: quota maxed (Business tier)
  🔴 SerpAPI: monthly quota maxed
  🟡 TheRundown: free tier (5 calls/day, game lines only, no props)
  🟡 OddsPapi: not wired (free tier, 250 req/mo, unlimited sports)
  🟡 crash_guard.py / orchestrator_full.py: not on disk
  🟡 Stat augmentation: wired but dormant in regrade scripts
  🟢 All 5 sports: gen scripts wired with tc_math
  🟢 All 5 sports: rosters complete
  🟢 Self-edge: stat-aware spreads active
  🟢 10 dashboards: live on zo.space
  🟢 Grading engine: unified, direction-aware
```
