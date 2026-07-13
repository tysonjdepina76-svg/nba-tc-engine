# TC Pipeline — Master Architecture Wire

**Version**: 3.4  
**Last Updated**: 2026-07-13 13:00 ET  
**Status**: OPERATIONAL — Purged + fixed — 2,352 actionable picks, 2,930 clean

---

## 1. System Overview

The TC (Triple Conservative) Pipeline is a multi-sport projection + prop-betting system covering **WNBA**, **MLB**, and **World Cup 2026**.

| Component | File | Status |
|---|---|---|
| Core Engine | `file 'Projects/daily_picks.py'` | ✅ Active (--sport wnba/mlb/wc) |
| Dashboard | `file 'sports_betting_dashboard/dashboard.py'` | ✅ RUNNING on :8510 |
| Auto-Repair | `file 'sports_betting_dashboard/fix_pipeline.py'` | ✅ Fixed — lowercase sports |
| Health Scanner | `file 'sports_betting_dashboard/scan.sh'` | ✅ v2.1 |
| Setup | `file 'sports_betting_dashboard/setup.sh'` | ✅ |

---

## 2. Cleaned Directory Layout (post-purge 7/13)

```
sports_betting_dashboard/
├── dashboard.py             # Streamlit UI (:8510)
├── picks.py                 # Shell — real engine is Projects/daily_picks.py
├── fix_pipeline.py          # Auto-repair (--sport wnba/mlb/wc)
├── scan.sh                  # Health scan with --json --fix --service modes
├── setup.sh                 # One-time install
├── README.md                # Documentation
├── WIRE.md                  # This file
├── PIPELINE_ASSESSMENT_*.md # Latest audit
├── .env                     # Blank reference
├── .env.template            # Documented key list (single source)
│
├── config/                  # SINGLE source of truth
│   ├── algorithm_weights.json   # Ensemble weights
│   ├── thresholds.json          # Edge thresholds per sport
│   ├── sports.json              # Sport definitions
│   └── parlay_rules.json        # Parlay builder rules
│
├── data/
│   ├── historical.csv           # Combined backtest (1,161 rows)
│   ├── today.json               # Live slate snapshot
│   ├── events/                   # Cached event data (WNBA, MLB, WC)
│   ├── odds/                     # Cached odds data
│   ├── props/                    # Live prop CSVs + JSONs
│   ├── picks/
│   │   ├── today_picks.csv      # ALL projections (3,812 rows)
│   │   ├── clean_picks.csv      # Non-INVALID filtered (2,930 rows)
│   │   └── actionable_picks.csv # Positive-edge only (2,352 rows)
│   ├── historical/
│   │   ├── wnba_historical.csv
│   │   ├── mlb_historical.csv
│   │   ├── world_cup_historical.csv
│   │   └── *_backtest.csv
│   ├── business_scan/           # Business-tier API scans
│   └── account/status.json      # API account status
│
├── logs/
│   ├── daily.log
│   ├── api.log
│   └── scan_*.txt               # Historical scan outputs
│
└── scripts/
    ├── generate.sh              # Generate picks (wnba/mlb/wc)
    ├── start.sh                 # Start dashboard on :8510
    ├── stop.sh                  # Stop all TC services
    ├── status.sh                # Quick status check
    ├── daily.sh                 # Complete daily routine
    └── odds_api_scraper.py      # Odds API scraper utility
```

**Purging Summary** (7/13): Removed `models/` (dup of config/), 2x extra `historical.csv` copies, `.env.example` (dup), `scan_YYYYMMDD.txt` placeholder, `data/today/` symlink, and archived `Projects-backup-20260708/`. 9 items removed, 3 new clean CSV views created.

---

## 3. Data Pipeline

```
daily_picks.py --sport wnba  → Daily_Log/YYYY-MM-DD/proj_WNBA_MATCHUP.json
daily_picks.py --sport mlb   → Daily_Log/YYYY-MM-DD/proj_MLB_MATCHUP.json
daily_picks.py --sport wc    → Daily_Log/YYYY-MM-DD/proj_WORLD_CUP_MATCHUP.json
                                    ↓
                              picks.csv (appended — ALL projections)
                                    ↓
                     ┌──────────────┼──────────────┐
                     ↓              ↓              ↓
             today_picks.csv  clean_picks.csv  actionable_picks.csv
             (all 3,812)     (2,930 non-INV)  (2,352 edge>0)
```

---

## 4. Pick File Guide

| File | Purpose | Filter |
|---|---|---|
| `today_picks.csv` | Complete projection log (for backtest/grading) | None — all rows including INVALID |
| `clean_picks.csv` | Projections without INVALID noise | Removes direction=INVALID |
| `actionable_picks.csv` | Actual betting picks | Edge > 0 AND direction ≠ INVALID |

---

## 5. Services

| Service | Port | Status |
|---|---|---|
| tc-dashboard-streamlit | 8510 | ✅ RUNNING |
| dk-combos-engine | 8515 | ⏸️ PAUSED — API quota |
| soccer-combos-engine | 8516 | ⏸️ PAUSED — API quota |
| mlb-cross-dashboard | 8518 | ⏸️ PAUSED — API quota |

---

## 6. Zo.Space Routes

8 API routes + 1 page route live at https://true.zo.space:

- `/api/tc` — TC projections
- `/api/daily-log` — Daily log viewer
- `/api/backtest` — Backtest results
- `/api/boxscores` — Boxscores
- `/api/combos` — Combo picks
- `/api/combo-prob` — Combo probability
- `/api/worldcup-props` — World Cup props
- `/api/pipeline-health` — Pipeline health
- `/nba-tc` — Full dashboard page

---

## 7. Quick Reference

```bash
# Generate picks (lowercase sport names REQUIRED)
python3 Projects/daily_picks.py --sport wnba
python3 Projects/daily_picks.py --sport mlb
python3 Projects/daily_picks.py --sport wc

# Health scan
bash sports_betting_dashboard/scan.sh
bash sports_betting_dashboard/scan.sh --json
bash sports_betting_dashboard/scan.sh --fix

# Dashboard
bash sports_betting_dashboard/scripts/start.sh
bash sports_betting_dashboard/scripts/status.sh

# View picks
cat sports_betting_dashboard/data/picks/actionable_picks.csv
```

---

## 8. Known Issues (7/13)

| Issue | Severity | Status |
|---|---|---|
| World Cup player names are generic (`England_DEF_1`) | HIGH | Pending fix in soccer_tc_engine.py |
| Odds API Business tier quota maxed (401 on /odds/) | MEDIUM | events/ still works |
| SGO API key expired (429) | MEDIUM | Needs new key |
| Dashboard reads stale JSON instead of CSV | LOW | Pending switch |
| League names inconsistent (WORLD_CUP vs WNBA) | LOW | Pending normalize |

---

*End of WIRE v3.4 — Updated post-purge 2026-07-13*
