# TC Pipeline — Master Architecture Wire

**Version**: 3.3  
**Last Updated**: 2026-07-13 11:56 ET  
**Status**: OPERATIONAL — APIs UNCAPPED — 132 WNBA picks + 26 WC self-edge live

---

## 1. System Overview

The TC (Triple Conservative) Pipeline is a multi-sport projection + prop-betting system covering **WNBA**, **MLB**, and **World Cup 2026**.

| Component | File | Status |
|---|---|---|
| Core Engine | `file 'Projects/daily_picks.py'` | ✅ Active (argparse: --sport --date) |
| Dashboard | `file 'sports_betting_dashboard/dashboard.py'` | ✅ RUNNING on :8510 |
| Auto-Repair | `file 'sports_betting_dashboard/fix_pipeline.py'` | ✅ Fixed --sport syntax |
| Health Scanner | `file 'sports_betting_dashboard/scan.sh'` | ✅ v2.1, 0 gaps |
| Setup | `file 'sports_betting_dashboard/setup.sh'` | ✅ Fixed --sport syntax |

---

## 2. Directory Layout

```
sports_betting_dashboard/
├── dashboard.py             # Streamlit UI (:8510) — RUNNING
├── picks.py                 # Legacy shell — real engine is Projects/daily_picks.py
├── fix_pipeline.py          # Auto-repair (mirrors scan.sh --fix)
├── scan.sh                  # Health scan with --json --fix --service modes
├── setup.sh                 # One-time install
├── README.md                # Documentation
├── WIRE.md                  # This file
├── .env                     # Blank reference — real keys in /root/.zo/secrets.env
├── .env.example             # Documented key list
├── data/
│   ├── account/status.json              # API account status
│   ├── events/                          # Cached event data (WNBA, MLB, WC)
│   ├── historical/
│   │   ├── wnba_historical.csv          # 33MB backtest data
│   │   ├── world_cup_historical.csv     # 32MB backtest data
│   │   ├── mlb_historical.csv           # 1.1MB backtest data
│   │   └── historical_coverage.csv      # Coverage metadata
│   ├── picks/
│   │   ├── today_picks.csv              # Today's picks snapshot (1,501 rows)
│   │   └── historical.csv               # → symlink → Daily_Log/backtests/combined_backtest.csv
│   ├── props/                           # mlb_live + wnba_live CSVs/JSONs
│   ├── business_scan/                   # Business-tier scans
│   └── today/                           # → symlink → Daily_Log/2026-07-13
├── logs/
│   ├── daily.log              # Pipeline run log
│   ├── api.log                # API call log
│   └── scans/                 # Historical scan outputs
├── models/
│   └── algorithm_weights.json # Ensemble weights (589 bytes)
└── scripts/
    ├── generate.sh            # Generate picks (WNBA, MLB, World Cup)
    ├── start.sh               # Start dashboard on :8510
    ├── stop.sh                # Stop all TC services
    ├── status.sh              # Quick status check
    ├── daily.sh               # Complete daily routine
    └── odds_api_scraper.py    # Odds API scraper utility
```

---

## 3. Services

| Service | Port | Status | Entrypoint |
|---|---|---|---|
| tc-dashboard-streamlit | 8510 | ✅ RUNNING | `sports_betting_dashboard/dashboard.py` |
| dk-combos-engine | 8515 | ⏸️ PAUSED | Pending API uncap |
| soccer-combos-engine | 8516 | ⏸️ PAUSED | Pending API uncap |
| mlb-cross-dashboard | 8518 | ⏸️ PAUSED | Pending API uncap |

---

## 4. Automations

5 automations active (created 2026-07-13):
- **Daily Pre-Game Scan** — 10:00 AM ET
- **Daily Picks Generation** — 11:00 AM ET  
- **TC Pipeline Midday Refresh** — 4:00 PM ET
- **TC Pipeline Evening Maintenance** — 10:30 PM ET
- **Daily Backtest Report** — 12:30 AM ET

---

## 5. API Keys

| Key | Status | Note |
|---|---|---|
| Odds API (Business) | 🟡 Quota maxed — 401 on /odds/ | events/ works (2088/6667), odds/props 401 |
| SGO | 🔴 Dead — HTTP 429 | Needs new key |
| SportsData.io | 🟡 Rate-limited | |
| ESPN v2 | 🟢 Working | No key needed |

**APIs UNCAPPED** as of 2026-07-13 11:55 ET — all external calls allowed. Odds API quota and SGO rate limits are the remaining bottlenecks.

---

## 6. Data Pipeline

```
daily_picks.py --sport WNBA      → Daily_Log/YYYY-MM-DD/proj_WNBA_MATCHUP.json
daily_picks.py --sport MLB       → Daily_Log/YYYY-MM-DD/proj_MLB_MATCHUP.json
daily_picks.py --sport WORLD_CUP → Daily_Log/YYYY-MM-DD/proj_WORLD_CUP_MATCHUP.json
                                      ↓
                                picks.csv (appended)
                                      ↓
                          today_picks.csv (symlinked snapshot)
```

---

## 7. Zo.Space Routes

Live at https://true.zo.space:

API routes (8):
- `/api/tc` — TC projections (WNBA, MLB, WORLD CUP)
- `/api/daily-log` — Daily log viewer
- `/api/backtest` — Backtest results
- `/api/boxscores` — WNBA + MLB + WC boxscores
- `/api/combos` — Combo picks
- `/api/combo-prob` — Combo probability dashboard
- `/api/worldcup-props` — World Cup props (NEW 7/13)
- `/api/pipeline-health` — Pipeline health diagnostic

Page routes (1):
- `/nba-tc` — Full sports TC dashboard (WNBA, MLB, World Cup, NFL tabs)

---

## 8. Current State (7/13 09:15 ET)

| Item | Status |
|---|---|
| Today's picks | ✅ 1,501 picks in picks.csv + picks.json |
| WNBA projections | ✅ 2 games (LA@ATL, PHX@MIN) |
| World Cup projections | ✅ 2 games (ARG@ENG, ESP@FRA) |
| MLS projections | ✅ slate_MLB.json (303KB) |
| Streamlit dashboard | ✅ RUNNING :8510 |
| /nba-tc page | ✅ LIVE, no runtime errors |
| /api/worldcup-props | ✅ NEW — 2 matches, 324 props |
| DK Combos service | ⏸️ PAUSED — API capped |
| SGO adapter | 🔴 HTTP 429 — key expired |
| ESPN DK odds | 🟡 "4 games, 0 DK" — ESPN not returning odds |

---

## 9. Quick Reference

```bash
# Generate picks (when APIs uncapped)
python3 Projects/daily_picks.py --sport WNBA --date $(TZ='America/New_York' date +%Y-%m-%d)
python3 Projects/daily_picks.py --sport MLB --date $(TZ='America/New_York' date +%Y-%m-%d)
python3 Projects/daily_picks.py --sport WORLD_CUP --date $(TZ='America/New_York' date +%Y-%m-%d)

# Health scan
bash sports_betting_dashboard/scan.sh
bash sports_betting_dashboard/scan.sh --json
bash sports_betting_dashboard/scan.sh --fix

# Dashboard
bash sports_betting_dashboard/scripts/start.sh
bash sports_betting_dashboard/scripts/status.sh
bash sports_betting_dashboard/scripts/stop.sh
```

---

*End of WIRE — Master Architecture Specification for TC Pipeline v3.2*
