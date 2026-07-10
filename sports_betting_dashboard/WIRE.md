# TC Pipeline — Master Architecture Wire

**Version**: 3.0  
**Last Updated**: 2026-07-09  
**Status**: OPERATIONAL (19/21 checks passing)

---

## 1. System Overview

The TC (Triple Conservative) Pipeline is a multi-sport projection + prop-betting system covering **WNBA**, **MLB**, and **World Cup 2026**. It generates TC projections, derives DK-implied edges, builds consensus picks, and surfaces everything through a Streamlit dashboard, Zo.Space API routes, and daily automation.

### Active Sports (July 2026)
| Sport | Status | Projection Engine | Odds Source |
|---|---|---|---|
| WNBA | ✅ ACTIVE | `wnba_pipeline_v2.py` | Odds API (Business tier) |
| MLB | ✅ ACTIVE | `mlb_tc_engine.py` | Odds API (Business tier) |
| World Cup | ✅ ACTIVE | `worldcup_picks.py` | Odds API (Business tier) |
| NBA | ❌ OFF-SEASON | — | — |
| NHL | ❌ OFF-SEASON | — | — |
| NFL | ⏳ PRESEASON (Aug 2026) | TBD | SportsData.io |

---

## 2. Architecture Diagram

```
                    ┌────────────────────────────────────────┐
                    │          ODDS API (Business Tier)        │
                    │  200K req/mo · props · multi-book       │
                    └──────────┬─────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │ WNBA Events │   │ MLB Events │   │  WC Events  │
     │  + Odds     │   │  + Odds    │   │   + Odds    │
     └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
           │                │                │
           ▼                ▼                ▼
     ┌─────────────────────────────────────────────┐
     │           daily_picks.py (argparse)          │
     │  --sport WNBA | --sport MLB | --sport WORLD_CUP │
     │        Ensemble: TC + DK + Consensus + Momentum │
     └─────────────────┬───────────────────────────┘
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐
     │picks.csv│ │picks.json│ │proj_*.json│
     │(append) │ │         │ │+ combos   │
     └────┬────┘ └────┬────┘ └─────┬─────┘
          │           │            │
          ▼           ▼            ▼
   ┌─────────────────────────────────────┐
   │         Daily_Log/YYYY-MM-DD/       │
   │  picks.csv  picks.json  proj_*.json │
   │  combos_*.json  consensus.json      │
   └──────────────┬──────────────────────┘
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
┌─────────┐ ┌──────────┐ ┌──────────┐
│Streamlit│ │Zo.Space  │ │Google    │
│ :8510   │ │API Routes│ │Drive/DOCX│
└─────────┘ └──────────┘ └──────────┘
```

---

## 3. File Inventory & Purpose

### 3.1 Core Pipeline (`/home/workspace/Projects/`)

| File | Purpose | Status |
|---|---|---|
| `daily_picks.py` | Main engine — argparse `--sport` entrypoint | ✅ |
| `consensus_engine.py` | Consensus pick aggregator | ✅ |
| `api_tc_unified.py` | Python handler for /api/tc | ✅ |
| `mlb_tc_engine.py` | MLB-specific TC projections | ✅ |
| `wnba_pipeline_v2.py` | WNBA pipeline v2 | ✅ |
| `worldcup_picks.py` | World Cup projection engine | ✅ |
| `build_pregame_combos.py` | Pre-game combo builder | ✅ |

### 3.2 Dashboard (`/home/workspace/sports_betting_dashboard/`)

| File | Purpose | Lines | Status |
|---|---|---|---|
| `dashboard.py` | Streamlit multi-sport UI (port 8510) | 243 | ✅ |
| `scan.sh` | Health scan — 21 checks, 4 modes | 300+ | ✅ v2.1 |
| `fix_pipeline.py` | Auto-repair (mirrors scan.sh --fix) | 150+ | ✅ |
| `setup.sh` | One-time install + verification | 90+ | ✅ |
| `README.md` | Architecture + quick start | — | ✅ |
| `.env.example` | API key documentation | 20 | ✅ |
| `.env` | Live env vars (gitignored) | — | ✅ |
| **`WIRE.md`** | **This document — master architecture spec** | — | ✅ NEW |

### 3.3 Scripts (`scripts/`)

| File | Purpose | Lines | Status |
|---|---|---|---|
| `daily.sh` | Daily runner: picks → sync → scan → log | 42 | ✅ |
| `generate.sh` | Generate picks for all 3 sports | 10 | ✅ |
| `start.sh` | Start Streamlit on :8510 | 9 | ✅ |
| `stop.sh` | Stop all TC services | 6 | ✅ |
| `status.sh` | Quick status overview | 51 | ✅ |
| `odds_api_scraper.py` | Odds API scraper — NBA off-season aware | — | ✅ |

### 3.4 Data (`data/`)

| Path | Purpose | Status |
|---|---|---|
| `data/picks/today_picks.csv` | Symlink → Daily_Log/YYYY-MM-DD/picks.csv | ✅ |
| `data/picks/historical.csv` | Backtest archive (headers only) | ⚠️ EMPTY |
| `data/events/*.json` | Live events per sport (3 active) | ✅ |
| `data/odds/*.json` | Live odds snapshots (3 active) | ✅ |
| `data/props/*.json` / `*.csv` | Live player props | ✅ |
| `data/historical/wnba_historical.csv` | WNBA backtest data (33MB) | ✅ |
| `data/historical/world_cup_historical.csv` | World Cup backtest data (32MB) | ✅ |
| `data/historical/historical_coverage.csv` | Coverage index | ✅ |
| `data/historical/api_schema.json` | API schema reference | ✅ |
| `data/sports/all_sports.json` | Sport definitions | ✅ |
| `data/account/status.json` | API call budget tracking | ✅ |
| `data/business_scan/` | Business tier scan report | ✅ |
| `data/fix_report.json` | Last auto-repair report | ✅ |

### 3.5 Models (`models/`)

| File | Purpose | Status |
|---|---|---|
| `algorithm_weights.json` | Ensemble weights per sport + thresholds | ✅ |

### 3.6 Logs (`logs/`)

| File | Purpose | Status |
|---|---|---|
| `daily.log` | Daily routine summary (rotated) | ⚠️ MISSING |
| `api.log` | API call audit trail | ⚠️ MISSING |
| `scan_YYYYMMDD.txt` | Per-day scan reports (3 historical) | ✅ |
| `comparison_20260707.md` | Daily comparison report | ✅ |

---

## 4. API Route Map (Zo.Space)

| Route | Method | Params | Returns | Status |
|---|---|---|---|---|
| `/api/tc` | GET | `sport`, `away`, `home` | Projections JSON | ✅ |
| `/api/slate` | GET | — | Today's games across all sports | ✅ |
| `/api/backtest` | GET | `days` | Hit-rate data | ✅ |
| `/api/scan` | GET | — | Health check — all subsystems | ✅ |
| `/api/daily-log` | GET | `days` | Daily picks history | ✅ |
| `/api/combos` | GET | — | DK combos | ✅ |
| `/api/dk-lines` | GET | `sport` | DK lines | ✅ |
| `/api/combo-prob` | GET | `mode=best` | Combo hit probabilities | ✅ |
| `/api/pipeline-health` | GET | — | Deep health diagnostics | ✅ |
| `/nba-tc` | PAGE | — | TC Dashboard (React page) | ✅ |

---

## 5. Service Topology

| Service | Port | Process | Status |
|---|---|---|---|
| Streamlit Dashboard | 8510 | `streamlit run dashboard.py` | ✅ LIVE |
| Zo.Space Server | 3099 | Hono/Bun internal | ✅ LIVE |
| MLB Live Dashboard | 8511 | `streamlit run mlb_dashboard.py` | ✅ LIVE |

---

## 6. Automation Schedule

| # | Automation Name | Time (ET) | Purpose |
|---|---|---|---|
| 1 | TC Pipeline — 1:30PM Slate + Injury + Health Check | 1:30 PM | Primary slate pull + injury scan |
| 2 | TC Pipeline — 6:30PM Final Pre-Tip + Combo Lock | 6:30 PM | Final odds refresh + combo generation |
| 3 | Boxscore Capture — Halftime and Final | 8:30 PM | Capture closing lines + results |
| 4 | Daily System Maintenance | 10:30 PM | Cleanup, symlink refresh, log rotation |
| 5 | Daily Backtest Report | 12:30 AM | Generate backtest hit-rate report |
| 6 | Weekly 30-Day Backtest Rollup | 2:00 AM (Mon) | Aggregate 30-day backtest |
| 7 | World Cup Lineup Lock & Evening MLB Updates | — | World Cup + MLB evening refresh |
| 8 | MLB & WNBA Injury & Game Update | — | Injury + lineup updates |
| 9 | NFL Preseason Scheduler & OddsAPI Status Update | — | NFL readiness + API budget monitor |
| 10 | WNBA Daily Picks and HTTP Calls Report | — | WNBA picks + HTTP call report |

---

## 7. Data Flow — Pick Generation

```
1. Odds API Fetch (events + odds + props)
   ↓
2. daily_picks.py --sport {SPORT}
   ├── Load events from data/events/{sport}.json
   ├── Load odds from data/odds/{sport}_live.json
   ├── Run TC engine (sport-specific)
   ├── Apply ensemble weights (algorithm_weights.json)
   │   ├── TC base projection (45-50%)
   │   ├── DK-derived edge (20-30%)
   │   ├── Consensus signal (15-20%)
   │   └── Momentum adjustment (10-30%)
   ├── Filter by min_confidence (0.55)
   └── Write picks.csv (APPEND mode) + picks.json
   ↓
3. Daily_Log/YYYY-MM-DD/
   ├── picks.csv      — all picks (append-safe)
   ├── picks.json     — structured JSON
   ├── proj_SPORT_@.json — per-game projections
   ├── combos_SPORT.json — combo picks
   └── consensus.json — consensus picks
   ↓
4. Dashboard / API surface
   ├── Streamlit :8510 reads from Daily_Log
   ├── Zo.Space API reads from Daily_Log
   └── data/picks/today_picks.csv ← symlink
```

---

## 8. Ensemble Algorithm

```json
{
  "ensemble": {
    "tc_base": 0.45,
    "dk_derived": 0.25,
    "consensus": 0.20,
    "momentum": 0.10
  },
  "sport_overrides": {
    "WNBA":  { "tc_base": 0.50, "dk_derived": 0.20, "consensus": 0.20, "momentum": 0.10 },
    "MLB":   { "tc_base": 0.40, "dk_derived": 0.30, "consensus": 0.15, "momentum": 0.15 },
    "WORLD CUP": { "tc_base": 0.35, "dk_derived": 0.15, "consensus": 0.20, "momentum": 0.30 }
  },
  "min_confidence": 0.55,
  "thresholds": {
    "blowout_margin": 15,
    "garbage_time_q": 4,
    "min_minutes": 8,
    "min_projection": 0.5
  }
}
```

---

## 9. API Budget Tracking

| Metric | Value |
|---|---|
| Tier | Business (200K req/month) |
| Daily Limit | 6,667 requests |
| Today's Usage | 2,088 requests (31%) |
| Remaining | 4,579 |
| Primary Consumer | 1:30 PM slate run |
| 6:30 PM Strategy | Cache-first, defer to next reset if >80% used |

---

## 10. Error Handling & Auto-Repair

### scan.sh Modes
| Mode | Behavior |
|---|---|
| (default) | Full scan → stdout + save to `logs/scan_YYYYMMDD.txt` |
| `--json` | JSON output to `data/scan_report.json` |
| `--fix` | Auto-repair: run pipeline, restart Streamlit, refresh odds, purge empties |
| `--service` | Lightweight cron-mode scan (6 checks) |

### fix_pipeline.py Repairs
1. **No picks today** → runs `daily_picks.py` for all 3 sports
2. **Streamlit down** → kill + restart on :8510
3. **Stale symlink** → re-point `today_picks.csv`
4. **Empty cache dirs** → purge
5. **Missing dashboard.py** → alert

---

## 11. Gaps Identified & Enhancement Specs

### 11.1 ⚠️ CRITICAL — Missing Log Files
| Gap | Impact | Fix |
|---|---|---|
| `logs/daily.log` | No persistent daily audit trail | Create stub with header |
| `logs/api.log` | No API call audit | Create stub with header |

### 11.2 ⚠️ MODERATE — Empty historical.csv
`data/picks/historical.csv` has headers only (0 data rows). The real backtest data lives in `data/historical/wnba_historical.csv` (33MB) and `data/historical/world_cup_historical.csv` (32MB).

**Spec**: Aggregate backtest data from historical CSVs + Daily_Log backtests into a unified `historical.csv` with columns: `date,league,matchup,player,team,stat,direction,tc_projection,actual,result`.

### 11.3 ⚠️ ENHANCEMENT — MLB historical data missing
No `mlb_historical.csv` in `data/historical/` — MLB lacks the deep backtest coverage that WNBA and World Cup have.

**Spec**: Run MLB backtest pipeline against archived ESPN boxscores.

### 11.4 💡 ENHANCEMENT — Live Prop Scanner
The blowout/garbage-time engine exists (`blowout_garbage_engine.py`) but isn't wired into the dashboard.

**Spec**: Add a "Live Mode" tab to Streamlit dashboard that:
- Monitors for blowout triggers (margin ≥15)
- Surfaces bench-degraded TC projections
- Outputs 4-6 legs sorted by edge

### 11.5 💡 ENHANCEMENT — picks.py Symlink
`README.md` references `picks.py → Projects/daily_picks.py` but this doesn't exist. Create the symlink for backward compatibility.

### 11.6 💡 ENHANCEMENT — DOCX Report Generation
The DOCX pipeline (`gen_tc_docx.py`) works but isn't automated. Wire it into the daily automation for email delivery.

**Spec**: Daily automation generates formatted DOCX with stat leader symbols (★PTS ◆REB ▲AST ●3PM ◇STL ■BLK) → uploads to Google Drive → emails link.

### 11.7 💡 ENHANCEMENT — Slack/Discord Alerts
No real-time alerting for:
- Pipeline failures
- Edge >2.0 props (high-value alerts)
- Blowout triggers
- API budget >80%

**Spec**: Add webhook integration for instant alerts.

### 11.8 💡 ENHANCEMENT — NFL Preseason Readiness
NFL preseason starts August 2026. SportsData.io key is configured. Need:
- NFL TC engine port (adapt from NBA patterns)
- Preseason roster scraping
- DK odds mapping for NFL props

---

## 12. Operational Commands

```bash
# Generate picks
bash sports_betting_dashboard/scripts/generate.sh

# Full health scan
bash sports_betting_dashboard/scan.sh

# Auto-repair
python3 sports_betting_dashboard/fix_pipeline.py

# Quick status
bash sports_betting_dashboard/scripts/status.sh

# Start/stop services
bash sports_betting_dashboard/scripts/start.sh
bash sports_betting_dashboard/scripts/stop.sh

# Daily runner
bash sports_betting_dashboard/scripts/daily.sh
```

---

## 13. Key Paths Reference

```
/home/workspace/
├── Projects/daily_picks.py              # Main engine
├── Daily_Log/
│   ├── last_run.json                    # Latest pipeline run
│   ├── YYYY-MM-DD/picks.csv             # Daily picks (append mode)
│   ├── YYYY-MM-DD/proj_*.json           # Per-game projections
│   ├── backtests/combined_backtest.csv  # Historical backtest
│   └── boxscore_registry.json           # Boxscore index
├── sports_betting_dashboard/
│   ├── dashboard.py                     # Streamlit :8510
│   ├── scan.sh                          # Health scan
│   ├── fix_pipeline.py                  # Auto-repair
│   ├── WIRE.md                          # ← THIS FILE
│   └── data/                            # Live data cache
└── AGENTS.md                            # Workspace index
```

---

## 14. Check Results (Last Scan: 2026-07-08)

| # | Check | Status |
|---|---|---|
| 1 | PIPELINE_RUN | ✅ |
| 2 | PICKS_TODAY | ✅ (703 picks) |
| 3 | PROJ_FILES | ✅ |
| 4 | COMBOS | ✅ |
| 5 | WNBA_TC_ENGINE | ✅ |
| 6 | COMBO_FRESH | ✅ |
| 7 | MLB_FIELDS | ✅ |
| 8 | STREAMLIT | ✅ (:8510) |
| 9-16 | ROUTES (/api/tc, /slate, /scan, /backtest, /daily-log, /combos, /dk-lines, /combo-prob) | ✅ ALL 200 |
| 17 | CONSENSUS | ✅ |
| 18 | ODDS_CACHE | ✅ |
| 19 | BOXSCORES | ✅ |
| 20 | BACKTEST | ✅ |
| 21 | API_LIMITS | ✅ (31%) |

**Result: 19/21 PASSING**

---

*End of WIRE — Master Architecture Specification for TC Pipeline v3.0*
