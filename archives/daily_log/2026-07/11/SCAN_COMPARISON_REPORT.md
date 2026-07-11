# 🏀 Sports Betting Dashboard — Full System Scan & Comparison Report
**Generated:** 2026-07-11 17:40 ET  
**Scan by:** TC Pipeline Operator  
**Scope:** `sports_betting_dashboard/` + `Daily_Log/` + Zo.Space routes + services

---

## 📊 Executive Summary

| Category | Status | Detail |
|----------|--------|--------|
| Pipeline Health | ⚠️ DEGRADED | 5 passed, 2 warnings, 1 failure |
| Dashboard | ✅ Live | `http://localhost:8510` |
| Zo.Space Routes | ✅ 25 routes | 17 API + 8 pages |
| Daily Log | ✅ 32 days | 6/9 → 7/11 |
| Today's Picks | ✅ 5,370 rows | WNBA + MLB + WC |
| Missing Files | ❌ 2 | `mlb_historical.csv`, `Daily_Log/archive/` |

---

## 🗂️ Directory Comparison: Proposed vs. Actual

### ✅ MATCHED (18/20)

| # | File/Dir | Path | Status |
|---|----------|------|--------|
| 1 | `picks.py` | `sports_betting_dashboard/picks.py` | ✅ 1,081 lines |
| 2 | `dashboard.py` | `sports_betting_dashboard/dashboard.py` | ✅ 243 lines |
| 3 | `scan.sh` | `sports_betting_dashboard/scan.sh` | ✅ Health scan |
| 4 | `fix_pipeline.py` | `sports_betting_dashboard/fix_pipeline.py` | ✅ 150 lines |
| 5 | `setup.sh` | `sports_betting_dashboard/setup.sh` | ✅ 96 lines |
| 6 | `scripts/generate.sh` | `sports_betting_dashboard/scripts/generate.sh` | ✅ |
| 7 | `scripts/start.sh` | `sports_betting_dashboard/scripts/start.sh` | ✅ |
| 8 | `scripts/stop.sh` | `sports_betting_dashboard/scripts/stop.sh` | ✅ |
| 9 | `scripts/status.sh` | `sports_betting_dashboard/scripts/status.sh` | ✅ |
| 10 | `scripts/daily.sh` | `sports_betting_dashboard/scripts/daily.sh` | ✅ |
| 11 | `scripts/odds_api_scraper.py` | `sports_betting_dashboard/scripts/odds_api_scraper.py` | ✅ |
| 12 | `data/picks/historical.csv` | `sports_betting_dashboard/data/picks/historical.csv` | ✅ |
| 13 | `data/picks/today_picks.csv` | `sports_betting_dashboard/data/picks/today_picks.csv` | ✅ |
| 14 | `data/events/` | `sports_betting_dashboard/data/events/` | ✅ MLB, WNBA, FIFA WC |
| 15 | `data/odds/` | `sports_betting_dashboard/data/odds/` | ✅ MLB, WNBA, FIFA WC |
| 16 | `data/props/` | `sports_betting_dashboard/data/props/` | ✅ MLB, WNBA live |
| 17 | `models/algorithm_weights.json` | `sports_betting_dashboard/models/algorithm_weights.json` | ✅ |
| 18 | `logs/` (6 scan logs) | `sports_betting_dashboard/logs/` | ✅ |

### ❌ MISSING (2/20)

| # | File/Dir | Detail |
|---|----------|--------|
| 19 | `data/historical/mlb_historical.csv` | No file — only WNBA + World Cup historical exist |
| 20 | `Daily_Log/archive/` | Never created |

---

## 🌐 Zo.Space Routes (25 total)

### API Routes (17)
- `/api/tc` — TC projections engine
- `/api/backtest` — Historical backtest endpoint
- `/api/boxscores` — ESPN boxscore scraper
- `/api/daily-log` — Daily log reader
- `/api/combo-prob` — Combo probability engine
- `/api/combos` — Combo data endpoint
- `/api/dk-lines` — DraftKings lines proxy
- `/api/health` — Health check
- `/api/live-props` — Live prop scanner
- `/api/pipeline-health` — Full pipeline diagnostic
- `/api/props` — Props data
- `/api/sports-config` — Sport schema config
- `/api/streamlit-proxy` — Dashboard proxy
- `/api/wnba-boxscores` — WNBA boxscore data
- `/api/worldcup-events` — World Cup events
- `/api/worldcup-games` — World Cup games
- `/api/worldcup-players` — World Cup player data

### Page Routes (8)
- `/` — Homepage (private)
- `/nba-tc` — **Main TC Dashboard** (private)
- `/dk-combos` — Combo builder (public)
- `/api/fix-pipeline` — Pipeline auto-fix (API page)

---

## 📅 Daily Log Archive (32 days)

```
2026-06-09 through 2026-07-11 (all present)
```

Each day contains:
- `picks.csv` — Full pick list (5,370 rows today)
- `proj_WNBA_*.json` — WNBA projections per game
- `proj_MLB_*.json` — MLB projections per game
- `proj_WORLD_CUP_*.json` — World Cup projections

### Today (7/11) at a glance
| Sport | Picks | Status |
|-------|-------|--------|
| WNBA | ~125 | Live |
| MLB | ~375 | Live |
| World Cup | ~50 | Logged |
| **Total** | **5,370 rows** | **Active** |

---

## 🏀 `/nba-tc` Dashboard Status

| Feature | Status |
|---------|--------|
| Sport Selector | WNBA, MLB, WORLD CUP, NFL |
| Today's Slate Panel | Auto-loads + 5-min refresh |
| Live Stats Monitor | ESPN boxscore with 30s auto-refresh |
| Injury Report | Status-aware TC impact (OUT=0, Q=×0.55) |
| Parlay Builder | Top 8 high-edge picks per game |
| Combo Dashboard | Hit probability per game/leg |
| Backtest | 2026 NBA Playoffs (FINALS: NYK 4-1 SAS) |
| Pipeline Health | API keys, connectivity, routes, services |
| Daily Log | Last run + top 10 picks by edge |
| WNBA Leaders | Minutes leaders + closing lineups (5-day) |
| NFL Panel | SportsData.io lines + player props |

### Registry (sport-aware rendering)
| Sport | Source | `.tc` reads allowed |
|-------|--------|---------------------|
| WNBA | TC_ENGINE | ✅ Yes |
| MLB | TC_ENGINE | ✅ Yes (flat fields) |
| WORLD CUP | TC_ENGINE | ✅ Yes |
| NBA | TC_ENGINE | ✅ Yes (off-season) |
| NFL | BOOK_LINES | ❌ No TC |
| NHL | COMING_SOON | ❌ Disabled |

---

## ⚙️ Services

| Service | Port | Status |
|---------|------|--------|
| Streamlit Dashboard | `:8510` | ✅ Live |
| Zo.Space (Bun/Hono) | `:3099` | ✅ Live |

---

## 🔑 Key Config Files

| File | Path | Purpose |
|------|------|---------|
| `.env` | `sports_betting_dashboard/.env` | API keys & secrets |
| `.env.example` | `sports_betting_dashboard/.env.example` | Template |
| `README.md` | `sports_betting_dashboard/README.md` | Documentation |
| `WIRE.md` | `sports_betting_dashboard/WIRE.md` | Architecture wireframe |
| `algorithm_weights.json` | `sports_betting_dashboard/models/` | Ensemble weights |

---

## 📈 Pipeline Health (last check: 7/9)

| Check | Result |
|-------|--------|
| Pregame Combos | ✅ Built |
| Soccer TC Engine | ✅ Completed |
| `picks_csv` output | ✅ Present |
| `last_run` output | ✅ Present |
| `slate_wnba` output | ✅ Present |
| `picks_json` output | ⚠️ Missing |
| `slate_nba` output | ⚠️ Missing |
| Game over/under | ❌ Unhealthy |

**Status:** DEGRADED (5/8 checks passed)

---

## 🚨 Action Items

1. **Create `data/historical/mlb_historical.csv`** — needed for MLB backtesting
2. **Create `Daily_Log/archive/` directory** — for archived daily logs
3. **Investigate `picks_json` and `slate_nba` warnings** — pipeline health degraded
4. **Review game over/under failure** — single failure in health check

---

## 🔗 Quick Links

- **TC Dashboard:** `https://true.zo.space/nba-tc`
- **Streamlit Dashboard:** `http://localhost:8510`
- **Zo.Space Home:** `https://true.zo.space/`
- **Pipeline Source:** `/home/workspace/sports_betting_dashboard/`
- **Daily Logs:** `/home/workspace/Daily_Log/`
- **Today's Picks:** `/home/workspace/Daily_Log/2026-07-11/picks.csv`

---

*Report generated by TC Pipeline Operator — 2026-07-11 17:40 ET*
