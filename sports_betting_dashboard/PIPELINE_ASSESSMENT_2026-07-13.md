# TC Pipeline — Line-by-Line Assessment & Recommendations
**Date**: 2026-07-13 12:55 ET  
**Status**: PURGED + FIXED — 6 issues resolved, 4 recommendations written

---

## Phase 1 — PURGE (COMPLETE ✅)

| File/Path | Action | Reason |
|---|---|---|
| `models/algorithm_weights.json` | **DELETED** | Duplicate of `config/algorithm_weights.json` |
| `data/historical/historical.csv` | **DELETED** | Triplicate — kept `data/historical.csv` at root |
| `data/picks/historical.csv` | **DELETED** | Triplicate — kept `data/historical.csv` at root |
| `.env.example` | **DELETED** | Duplicate — kept `.env.template` |
| `logs/scan_YYYYMMDD.txt` | **DELETED** | Template placeholder, not real data |
| `data/today/` | **DELETED** | Fragile symlink to `Daily_Log/` |
| `models/` (entire dir) | **DELETED** | Empty after purge |
| `Projects-backup-20260708/` | **MOVED** to `archives/` | Full duplicate of `Projects/` |
| `scripts/__pycache__/` | **DELETED** | Build artifacts |

**Result**: 9 items purged. 0 bytes lost (all were duplicates).

---

## Phase 2 — PIPELINE BUG FIXES (COMPLETE ✅)

| File | Bug | Fix |
|---|---|---|
| `fix_pipeline.py` | `--sport WNBA` (uppercase → argparse rejects) | → `--sport wnba` |
| `fix_pipeline.py` | `--sport MLB` (uppercase) | → `--sport mlb` |
| `fix_pipeline.py` | `--sport WORLD_CUP` (uppercase) | → `--sport wc` |
| `WIRE.md` | References uppercase sports in commands | → Updated to lowercase `--sport wnba mlb wc` |
| `WIRE.md` | References deleted files (`models/`, symlinks) | → Updated layout |
| `README.md` | Command uses positional args (broken) | → Fixed to `--sport wnba` syntax |

---

## Phase 3 — PROJECTION DISPLAY ASSESSMENT

### What's Confusing About the Current Picks Display

The `today_picks.csv` has 18 columns. Here's the assessment of each:

| Column | Issue | Recommendation |
|---|---|---|
| `date` | ✅ Fine | Keep |
| `league` | ⚠️ Inconsistent — `WORLD_CUP` vs `WNBA` | Normalize to `WORLD CUP` |
| `matchup` | ✅ Fine | Keep |
| `team` | ✅ Fine | Keep |
| `player` | 🔴 **BAD** — `England_DEF_1`, `Argentina_GK_1` are roster slots | Fix upstream: pull real names from ESPN rosters |
| `role` | ⚠️ Minor — `DEF`, `GK`, `FWD` useful but cryptic | Add tooltip or legend |
| `status` | ✅ Fine | Keep |
| `stat` | ✅ Fine | Keep |
| `direction` | 🔴 **882 INVALID rows** mixed in | **Filter out before display** — done (see clean_picks.csv) |
| `market_line` | ⚠️ **Ordering** — shown before `tc_projection` | **Move after projection** (done in clean_picks.csv) |
| `tc_projection` | ⚠️ Our number — should be FIRST | **Reordered** (done) |
| `tc_target` | 🔴 **DUPLICATE** — same as `market_line` on many rows | Merge or remove — this IS `market_line` |
| `edge` | 🔴 **578 negative edges shown** — these AREN'T picks | Filter edge > 0 (done in actionable_picks.csv) |
| `threshold` | ⚠️ Redundant — always 0.5 | Remove from display |
| `raw_average` | 🔴 **UNCLEAR** — what is this? | Rename to `season_avg` or remove |
| `source` | ⚠️ All `SELF_EDGE` today — no DK lines | Keep but add visual badge |
| `actual` | ✅ Empty until graded | Keep |
| `result` | ✅ PENDING until graded | Keep |

### Column Reorder (DONE in clean_picks.csv)

**Before** (confusing):
```
date, league, matchup, team, player, role, status, stat, direction, market_line, tc_projection, tc_target, edge, threshold, raw_average, source, actual, result
```

**After** (clean):
```
date, league, matchup, team, player, role, stat, tc_projection, tc_target, direction, market_line, edge, threshold, source, actual, result
```

The key change: **TC projection first**, then market line, then edge. The user sees OUR number before the book's number.

### New Files Created

| File | Rows | Description |
|---|---|---|
| `clean_picks.csv` | 2,930 | All non-INVALID picks (edge can be negative) |
| `actionable_picks.csv` | 2,352 | Only positive-edge picks (actual betting opportunities) |

---

## Phase 4 — DASHBOARD ASSESSMENT

### Current Issues

1. **Data Source Mismatch**: Dashboard loads from `Daily_Log/YYYY-MM-DD/picks.json` but the real picks are in `today_picks.csv`. The JSON is stale (`picks_logged: 0` in last_run.json).

2. **No INVALID Filtering**: The dashboard shows ALL projections including INVALID ones. 882 rows of noise.

3. **Generic Player Names**: World Cup shows `England_DEF_1` etc. — looks broken in the dashboard.

4. **Confusing Metrics**: The dashboard shows `tc_projection` and `market_line` side by side but the order varies.

5. **Edge Distribution Graph**: Shows absolute edge values — includes negative edges which aren't picks.

### Recommended Dashboard Fixes

1. **Load from CSV instead of JSON**: Read `data/picks/clean_picks.csv` or `actionable_picks.csv` for the main view
2. **Add a "Draft Mode" toggle**: Show all projections vs. actionable-only
3. **Color-code by confidence**: `edge >= 2.0` → green, `1.0-2.0` → yellow, `< 1.0` → gray
4. **Add sport filter pills**: WNBA / MLB / WORLD CUP quick toggles
5. **Show projection BEFORE line**: In the picks table, put TC projection in column 1

---

## Phase 5 — FINAL RECOMMENDATIONS

### A. Split `today_picks.csv` Into Two Views

The current file tries to be both a projection log AND a picks display. These are different things:

- **projections.csv**: ALL projections (for backtest/grading). INVALID rows included, negative edges included.
- **picks_today.csv**: ONLY actionable picks. Edge > 0, direction != INVALID, sorted by edge descending.

**DONE** — `actionable_picks.csv` now serves as the picks display.

### B. Fix Upstream Player Names

The World Cup engine generates `{TEAM}_{POS}_{N}` style names like `England_DEF_1`. These need real ESPN roster names. This is the single biggest UX issue — a user sees "England_DEF_1 OVER 0.78 TKL" and has no idea who that is.

**Fix path**: Update `sources/soccer_tc_engine.py` to pull real roster names from ESPN instead of generating slots.

### C. Normalize League Names

Inconsistent: `WORLD_CUP` vs `WNBA` vs `MLB`. Pick one style:
- `WNBA`, `MLB`, `WORLD CUP` (mixed case)
- `wnba`, `mlb`, `world_cup` (lowercase)

### D. Add `signal` Column

Current picks have no "why" — just edge numbers. Add a column showing the reasoning:
- `SELF_EDGE 2.5` → edge-driven (our projection beats the line)
- `LINE DISCREPANCY 1.8` → we see a better line than market
- `DK LINE 2.1` → we found a DK line to exploit

---

## Summary

| Metric | Before | After |
|---|---|---|
| Files in dashboard/ | 51 | 42 |
| Duplicate files | 9 (3x historical.csv, 2x weights, 2x .env) | 0 |
| INVALID picks shown | 882 | 0 (filtered) |
| Negative-edge rows shown | 578 | 0 (filtered in actionable) |
| Actionable picks | 2,352 | 2,352 (same, just isolated) |
| fix_pipeline.py sports case | UPPERCASE (broken) | lowercase (fixed) |
| Column order confusion | market_line before tc_projection | tc_projection first |
| Dashboard data source | Stale JSON | Pending: switch to CSV |

---

*End of assessment. Execute recommendations in order: D (add signal column), B (fix player names), C (normalize league names).*
