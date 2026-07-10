# TC Pipeline — Scan & Comparison Report
**Date:** 2026-07-07 9:35 PM ET

---

## Pipeline Run Results (Today)

| Sport | Games | Picks | Status |
|-------|-------|-------|--------|
| WNBA | 2 (DAL@NY, CHI@PHX) | 3 | Odds API 400, SGO fallback |
| MLB | 12 | 940 | SportsDataIO lines |
| World Cup | 4 | 0 | Odds API 401 quota maxed, self-edge only |
| **Total** | **18** | **943** | |

---

## `sports_betting_dashboard/` vs Active Pipeline

### ✅ Matching / Working

| Component | `sports_betting_dashboard/` | Our pipeline |
|-----------|---------------------------|-------------|
| scan.sh | ✅ 20+ checks, service/json/fix modes | Runs against same routes |
| data/events/ | ✅ WNBA, MLB, World Cup JSONs | Matches Odds API events |
| data/odds/ | ✅ live snapshots | Same source |
| data/props/ | ✅ mlb_live, wnba_live | Same source |
| scripts/daily.sh | ✅ FIXED (now uses `--sport WNBA` etc) | Was using old positional args |
| scripts/generate.sh | ✅ FIXED (same) | Was using old positional args |
| scripts/start.sh, stop.sh, status.sh | ✅ Service management | Works with :8511 |
| README.md | ✅ Architecture map | Accurate for current state |
| picks.py symlink | ✅ → `Projects/daily_picks.py` | Works |
| models/algorithm_weights.json | ✅ Ensemble weights | Referenced by engine |

### ❌ Missing / Broken

| Component | Status | Fix needed |
|-----------|--------|-----------|
| `fix_pipeline.py` | MISSING | Auto-repair script needs creation |
| `dashboard.py` symlink | MISSING | `tc_dashboard.py` is `.DEPRECATED`, should point to `mlb_dashboard.py` or new unified dashboard |
| `.env` | May be stale | API keys in Zo Secrets, but env file references old keys |

### ⚠️ Warnings

| Issue | Detail |
|-------|--------|
| Odds API quota | Business tier maxed — 401 on World Cup, 400 on WNBA props |
| daily_picks.py syntax | Now requires `--sport WNBA` (not positional `WNBA`) |
| Streamlit :8510 | `tc_dashboard.py` deprecated — MLB dashboard runs on :8511 |
| combo legs | WNBA returning 0 qualified legs (SGO fallback has no prop markets) |

---

## Frontend (`/nba-tc`) Fix Applied

- **LiveStatsPanel** — Removed `sportHasTC()` gate. All sports now show live boxscore stats.
- **Sport-aware columns** — MLB shows AVG/HR/RBI, soccer shows Goals/Shots/Corners.
- **Registry wired** — MLB routes through BOOK_LINES (flat `tc_*` fields), no nested `.tc` crash.
- **Game Lines card** — Multi-book comparison, WNBA fallback notice, sport-aware stat labels.

---

## Next Steps

1. Create `fix_pipeline.py` (auto-repair: restart Streamlit, re-run picks if stale, purge empty dirs)
2. Create `dashboard.py` symlink → `mlb_dashboard.py` or build unified dashboard
3. Monitor Odds API quota reset (monthly + daily)
4. Consider self-edge-only mode for World Cup until quota recovers
