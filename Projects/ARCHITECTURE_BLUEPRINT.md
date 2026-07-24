# TC SPORTS PIPELINE — FULL ARCHITECTURE BLUEPRINT
**Generated:** 2026-07-21 | **Status:** HEALTHY | **Live Picks:** 810 MLB | **Avg Hit Rate:** 59.4% SELF_EDGE

---

## 1. FILE/FOLDER STRUCTURE

```
/home/workspace/
├── AGENTS.md                              # Workspace index & daily status
├── Projects/                              # *** MAIN PIPELINE ***
│   ├── daily_picks.py                     # 🎯 ENTRY POINT — generates picks by sport
│   ├── generate_projections.py            # 📊 Projection engine (MLB/WNBA/WC)
│   ├── gen_wnba_today.py                  # 🏀 WNBA-specific daily gen
│   ├── tc_math.py                         # 🧮 TC math: projection, edge, CONS, direction
│   ├── sports_registry.py                 # 🗂️ Sport configs, thresholds, stat mapping
│   ├── enrich_from_github_sources.py      # 🔗 GitHub raw data enrichment (season leaders)
│   ├── github_line_sources.py             # 🔗 GitHub raw line sources
│   ├── serp_odds_scraper.py               # 🔍 SerpAPI market line scraper (MAXED)
│   ├── grade_daily_picks.py               # 📋 Grading engine (picks vs boxscores)
│   ├── run_backtest.py                    # 📈 Backtest aggregator
│   ├── backfill_projections.py            # ⏮️ Historical projection backfill
│   ├── mlb_dashboard.py                   # ⚾ MLB-specific dashboard
│   ├── mlb_integration.py                 # ⚾ MLB data integration
│   ├── live_boxscore.py                   # 📡 Live boxscore fetcher
│   ├── smoke_test_pipeline.py             # ✅ Pipeline health test
│   ├── src/
│   │   ├── adapters/
│   │   │   ├── espn.py                    # 📺 ESPN API v2: schedules, game lines
│   │   │   ├── free_api_aggregator.py     # 🆓 statsapi + nba_api + pybaseball (WIRED)
│   │   │   ├── nba_api_adapter.py         # 🏀 NBA live data (OFF-SEASON)
│   │   │   ├── nfl_api_adapter.py         # 🏈 NFL data (OFF-SEASON)
│   │   │   ├── wnba_data_fetcher.py       # 🏀 WNBA roster/stats from ESPN
│   │   │   ├── world_cup_adapter.py       # ⚽ World Cup adapter
│   │   │   ├── mlb_player_prop_fetcher.py # ⚾ MLB prop fetcher
│   │   │   ├── cache_adapter.py           # 💾 API response caching
│   │   │   └── espn_odds_fallback.py      # 📺 ESPN odds fallback
│   │   ├── pipelines/
│   │   │   └── mlb_integration.py         # ⚾ MLB full integration pipeline
│   │   ├── trading/
│   │   │   └── position_manager.py        # 💰 Position sizing / bankroll
│   │   └── tracking/
│   │       └── historical_tracker.py      # 📊 Historical bet tracking
│   └── oddsScraper/                       # 🕷️ Selenium scrapers (DORMANT)
├── tc_engine/                             # 🖥️ Streamlit Dashboard
│   └── dashboard/
│       └── tc_dashboard.py                # Tabs: Picks, Edge Analysis, Live, Explain
├── data/
│   ├── picks/                             # 📁 Daily pick CSVs (mlb_YYYY-MM-DD.csv, etc.)
│   ├── historical/                        # 📚 Full historical archives
│   │   ├── mlb/2025/                      # MLB by date
│   │   ├── wnba/2025/                     # WNBA by date
│   │   ├── nba/2025-26/                   # NBA by date (includes WNBA data)
│   │   └── wc/                            # World Cup
│   └── backtest/                          # 📈 Backtest results
│       └── nfl_2026/odds/                 # NFL ESPN lines
├── Daily_Log/
│   ├── 2026-07-21/                        # Today's logs + projections
│   ├── _archive/                          # Archived daily logs
│   │   ├── 2025-06-13/                    # 🏆 WNBA/NBA FINALS data
│   │   ├── 2026-06-01/                    # WNBA backtests + hits
│   │   └── 2026-06-02/ through 06-08/     # Daily archives
│   ├── backtests/                         # Aggregated backtest results
│   └── last_run.json                      # Latest pipeline run metadata
├── Backtest_Reports/                      # 📋 Backtest reconciliation reports
└── mirror-workbook/                       # 📖 The Mirror Workbook Project
```

---

## 2. DATA PIPELINE FLOW

```
[External APIs]
  │
  ├── ESPN API v2 ───────► schedules, game lines (FREE)
  ├── statsapi (MLB) ────► live player stats (FREE) ✅ WIRED
  ├── nba_api ───────────► WNBA live stats (FREE) ✅ WIRED
  ├── pybaseball ────────► MLB teams, Statcast, park factors ✅ WIRED
  ├── SerpAPI ───────────► market line scraping (MAXED) ⛔
  ├── Odds API ──────────► props/odds (MAXED) ⛔
  ├── SDIO ──────────────► dead key ⛔
  └── GitHub Raw ────────► season leaders, enrichments ✅ WIRED
         │
         ▼
[generate_projections.py]  ← projections for each sport/matchup
         │
         ▼
[daily_picks.py]  ← TC math engine: edge → CONS → direction → pick
  │
  ├── enrich_from_github_sources() ← GitHub season leaders
  ├── enrich_via_free_apis()      ← statsapi + pybaseball live stats
  ├── tc_math.compute_tc_edge()   ← projection vs line → edge score
  ├── tc_math.compute_tc_cons()   ← edge confidence → CONS rating
  └── tc_math.compute_tc_direction() ← OVER/UNDER decision
         │
         ▼
[Outputs]
  ├── Daily_Log/YYYY-MM-DD/picks.csv          ← all picks
  ├── Daily_Log/YYYY-MM-DD/proj_*.json        ← per-matchup projections
  ├── Daily_Log/last_run.json                 ← pipeline metadata
  └── Email → tysonjdepina76@gmail.com, tysondepina99@gmail.com
         │
         ▼
[Dashboard (tc_engine)]  ← Streamlit on :8510, /nba-tc, /dashboard
```

---

## 3. API INTEGRATION MAP

### Active (WIRED)
| Source | File | Data Provided | Status |
|--------|------|--------------|--------|
| **ESPN API v2** | `src/adapters/espn.py` | Schedules, game lines (spread/OU), team scores | ✅ FULLY WIRED |
| **statsapi** | `src/adapters/free_api_aggregator.py` | MLB live player stats, game results | ✅ WIRED |
| **nba_api** | `src/adapters/nba_api_adapter.py` | NBA/WNBA scores, rosters | ✅ WIRED (off-season) |
| **pybaseball** | `src/adapters/free_api_aggregator.py` | MLB teams, Statcast, park factors | ✅ PARTIALLY WIRED |
| **GitHub Raw** | `enrich_from_github_sources.py` | Season leaders, static enrichments | ✅ WIRED |
| **GitHub Lines** | `github_line_sources.py` | Raw line feeds from repos | ✅ WIRED |

### Blocked / Maxed
| Source | File | Issue | Status |
|--------|------|-------|--------|
| **SerpAPI** | `serp_odds_scraper.py` | Monthly quota maxed (resets ~8/1) | ⛔ MAXED |
| **Odds API** | `src/pipelines/mlb_integration.py` | Business tier quota maxed | ⛔ MAXED |
| **SDIO** | config | Dead API key | ⛔ DEAD |
| **Fangraphs** | `free_api_aggregator.py` | 403 IP-blocked | ⛔ BLOCKED |

### Dormant / Not Yet Wired
| Source | File | Status |
|--------|------|--------|
| **Selenium scrapers** | `oddsScraper/` | DORMANT (can replace with agent-browser) |
| **NFL data** | `src/adapters/nfl_api_adapter.py` | INSTALLED, OFF-SEASON |
| **G-League** | Not built | REQUESTED — no adapter |
| **Fantasy Football** | Not built | REQUESTED — in code comments |

---

## 4. STREAMLIT DASHBOARD BLUEPRINT

**Location:** `/home/workspace/tc_engine/dashboard/tc_dashboard.py`  
**Port:** :8510 | **Public:** https://true.zo.space/nba-tc + /dashboard

### Tabs
| Tab | Content | Data Source | Status |
|-----|---------|------------|--------|
| 📋 Picks | Today's generated picks table | `data/picks/*.csv` | ✅ FUNCTIONAL |
| 📊 Edge Analysis | Edge visualization, projection vs line | `tc_math.py` | ✅ FUNCTIONAL |
| 🔴 Live Games | Real-time game status tracker | ESPN API | ✅ BASIC |
| 🧠 Model Explain | SHAP/PDP/ICE explainability | N/A | ⚠️ STUB |

### Missing Dashboards (Planned but not built)
- ❌ **Performance/ROI Dashboard** — No ROI tracking exists
- ❌ **Live Results Dashboard** — No real-time grading feed
- ❌ **Historical Trends** — No aggregated win/loss analysis

---

## 5. CURRENT GAPS & KNOWN ISSUES

| # | Gap | Severity | Real Impact | Explanation |
|---|-----|----------|-------------|-------------|
| 1 | **No auto-grading** | 🔴 CRITICAL | 810 picks/day with zero feedback. You don't know if your model works. Blind betting. | `grade_daily_picks.py` exists but boxscores not being fetched/saved automatically. Needs statsapi live results loop. |
| 2 | **statsapi not fully wired for grading** | 🔴 HIGH | MLB live scores and final results are free, installed, and unused. Can't grade, enrich live, or show live results. | `free_api_aggregator.py` fetches stats but grading pipeline doesn't call it. |
| 3 | **pybaseball partially used** | 🟡 HIGH | Projections use stale season-long data, not today's Statcast (exit velo, spin rate). Significant edge loss. | `get_live_stats()` returns basic stats only. Statcast endpoints not called. |
| 4 | **SerpAPI maxed, no fallback** | 🟡 MEDIUM | All 810 picks are SELF_EDGE. Enrichment silently fails. No injury/news context reaches model. | Resets ~8/1. No fallback scraper. |
| 5 | **Performance dashboard missing** | 🟡 MEDIUM | No ROI tracking. Don't know if profitable or which bet types win most. | Not built yet. |
| 6 | **Live Results dashboard missing** | 🟡 MEDIUM | Users can't see how picks are doing in real time. | Not built yet. |
| 7 | **nba_api not used for WNBA** | 🟢 LOW | Only ESPN rosters, no WNBA player stats. Gap when season resumes. | nba_api installed but WNBA endpoints not called. |
| 8 | **WC calls uncapped after tournament end** | 🟢 LOW | Wasteful API calls for finished tournament. | Need to cap WC in sports_registry. |
| 9 | **NFL/G-League not built** | 🟢 LOW | Limits expansion. Fantasy football code stubs exist. | Requested, not urgent. |

---

## 6. DATA STORAGE & LOGGING

### Daily Picks
- **Path:** `data/picks/{sport}_{YYYY-MM-DD}.csv`
- **Format:** `sport, matchup, player, stat, projection, line, edge, cons, direction, signal, timestamp`
- **Current data:** MLB 7/17-7/21, WNBA 7/13, 7/18-7/20, WC 7/17-7/19

### Projections
- **Path:** `Daily_Log/YYYY-MM-DD/proj_{SPORT}_{HOME}@{AWAY}.json`
- **Format:** JSON with per-player stat projections

### Backtests
- **Path:** `Daily_Log/backtests/combined_backtest.csv`
- **Total:** 2,603 graded picks
- **Combined:** 59.4% hit rate SELF_EDGE signals

### Historical Archives
- `data/historical/mlb/2025/` — MLB from June 2025
- `data/historical/wnba/2025/` — WNBA from June 2025
- `data/historical/nba/2025-26/` — NBA + WNBA from 2025-26 season

### FINALS DATA (Found!)
- `_archive/2025-06-13/` — WNBA Finals 2025 + NBA Finals 2026
- `backtests/` — `nba_ht_401859964_NYK_SAS_raw.json` (halftime backtest)

---

## 7. CONFIGURATION & DEPENDENCIES

### Environment Variables
- `STATSAPI_KEY` — MLB statsapi (optional, works without)
- `SERPAPI_KEY` — SerpAPI (maxed)
- `ODDS_API_KEY` — Odds API (maxed)
- `SDIO_KEY` — SportsDataIO (dead)
- `ESPN_API_KEY` — Not needed (free tier)

### Key Python Packages
`streamlit`, `pandas`, `numpy`, `requests`, `selenium` (dormant), `nba_api`, `pybaseball`, `nfl_data_py`, `scipy`

### Automations
| Name | Schedule | Sport |
|------|----------|-------|
| MLB Morning Line Pull | 9 AM ET | MLB |
| WNBA + WC Morning Projections | 11 AM ET | WNBA, WC |
| Combo Refresh | 1:30 PM ET | All |
| Evening Sports Refresh | 6 PM ET | All |

---

## 8. OVERALL SYSTEM DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                     TC SPORTS PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [FREE APIs]          [BLOCKED APIs]       [DORMANT]         │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐       │
│  │ ESPN v2  │        │ SerpAPI  │        │ Selenium │       │
│  │ statsapi │        │ Odds API │        │ Scrapers │       │
│  │ nba_api  │        │ SDIO     │        └──────────┘       │
│  │ pybaseball│       │ Fangraphs│                            │
│  │ GitHub   │        └──────────┘                            │
│  └────┬─────┘                                                │
│       │                                                      │
│       ▼                                                      │
│  ┌──────────────────────────────────────┐                   │
│  │      PROJECTION ENGINE               │                   │
│  │  generate_projections.py             │                   │
│  │  → Per-player, per-stat projections │                   │
│  └──────────────┬───────────────────────┘                   │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────┐                   │
│  │        TC MATH ENGINE                │                   │
│  │  tc_math.py                          │                   │
│  │  ┌─────────────────────────────────┐ │                   │
│  │  │ COMPUTE TC EDGE                 │ │                   │
│  │  │ edge = (proj - line) /          │ │                   │
│  │  │       (line × adj_factor)       │ │                   │
│  │  │                                 │ │                   │
│  │  │ WEIGHTED COMPOSITE SCORE (MLB)  │ │                   │
│  │  │ W = w1(BA)+w2(OPS)+w3(wOBA)+    │ │                   │
│  │  │     w4(SLG)+w5(ISO)+w6(wRC+)+   │ │                   │
│  │  │     w7(park_factor)+w8(L/R)      │ │                   │
│  │  │                                 │ │                   │
│  │  │ WNBA STAT WEIGHTS                │ │                   │
│  │  │ PTS:0.25, AST:0.20, REB:0.15,    │ │                   │
│  │  │ STL:0.10, BLK:0.10, 3PM:0.10,   │ │                   │
│  │  │ FG%:0.05, TO:0.05               │ │                   │
│  │  │                                 │ │                   │
│  │  │ MLB PITCHER WEIGHTS              │ │                   │
│  │  │ ERA:0.25, WHIP:0.20, K/9:0.15,   │ │                   │
│  │  │ BB/9:0.10, HR/9:0.10,            │ │                   │
│  │  │ GB%:0.05, HardHit%:0.08,        │ │                   │
│  │  │ Barrel%:0.07                     │ │                   │
│  │  └─────────────────────────────────┘ │                   │
│  │  ┌─────────────────────────────────┐ │                   │
│  │  │ COMPUTE TC CONS (CONSISTENCY)   │ │                   │
│  │  │ cons = 1 - min(1, abs(diff)/    │ │                   │
│  │  │        (std_dev × cons_factor)) │ │                   │
│  │  └─────────────────────────────────┘ │                   │
│  │  ┌─────────────────────────────────┐ │                   │
│  │  │ COMPUTE TC DIRECTION             │ │                   │
│  │  │ if edge > 0  → OVER              │ │                   │
│  │  │ if edge < 0  → UNDER             │ │                   │
│  │  │ gated by: CONS ≥ min_cons        │ │                   │
│  │  │          |edge| ≥ min_edge       │ │                   │
│  │  │          line in valid_range     │ │                   │
│  │  └─────────────────────────────────┘ │                   │
│  └──────────────┬───────────────────────┘                   │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────┐                   │
│  │            OUTPUTS                   │                   │
│  │  → picks.csv (810 MLB today)         │                   │
│  │  → proj_*.json (per matchup)         │                   │
│  │  → Email (tysonjdepina76 + 99)       │                   │
│  │  → Dashboard (:8510, /nba-tc)        │                   │
│  └──────────────────────────────────────┘                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. BACKTEST RESULTS SUMMARY

| Source | Picks | Hit Rate | Best Stat | Worst Stat |
|--------|-------|----------|-----------|------------|
| WNBA Live BT (6/11) | 69 | 50.0% | PTS 78.6% | 3PM 35.0% |
| WNBA Graded | 96 | 60.4% | REB 75.0% | HR 0.0% |
| MLB Graded | 5 | 40.0% | RBI/SB 100% | HR/R 0.0% |
| Combined (SELF_EDGE) | 101 | 59.4% | — | — |
| Total Graded | 2,603 | — | — | — |

### WNBA PTS is the standout signal: 11/14 = 79%

### WNBA FINALS 2025: `/home/workspace/Daily_Log/_archive/2025-06-13/finals_2025_wnba.json` (192 KB)
### NBA FINALS 2026: `/home/workspace/Daily_Log/_archive/2025-06-13/finals_2026_nba.json` (233 KB)
### NBA FINALS BACKTEST: `/home/workspace/Daily_Log/_archive/2025-06-13/nba_finals_2026_backtest.md`
