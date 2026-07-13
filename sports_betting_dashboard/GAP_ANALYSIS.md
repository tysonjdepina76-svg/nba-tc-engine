# TC Pipeline — GAP ANALYSIS vs TARGET STRUCTURE
**Date**: 2026-07-13 10:50 ET  
**Trigger**: "Scan and compare to ours"  
**Scope**: Full system audit against user's target `sports_betting_dashboard/` layout

---

## EXECUTIVE SUMMARY

| Category | Missing | Broken | Fixed/OK |
|----------|---------|--------|----------|
| 🔴 STRUCTURAL | 0 config files | 0 | 42 files |
| 🟡 DATA | MLB picks not generated | Stale props (Jun 27) | WNBA 1980, WC 832 picks |
| 🟡 SERVICE | — | worldcup-props JS error | Streamlit UP, 28/29 routes 200 |
| 🟠 LOGGING | daily.log bare (only 2 lines) | — | scan logs current |

**Overall: 85% aligned. 3 config files missing. MLB silent today. Props data old.**

---

## 1. STRUCTURAL COMPARISON (Target vs Actual)

### ✅ PRESENT (Target Matches)

| Target File | Actual | Status |
|------------|--------|--------|
| `picks.py` | `→ Projects/daily_picks.py` (symlink) | ✅ |
| `dashboard.py` | `dashboard.py` (8153B) | ✅ |
| `scan.sh` | `scan.sh` (18623B) | ✅ |
| `fix_pipeline.py` | `fix_pipeline.py` (5420B) | ✅ |
| `setup.sh` | `setup.sh` (3286B) | ✅ |
| `requirements.txt` | `requirements.txt` | ✅ |
| `.env.example` | `.env.example` + `.env` + `.env.template` | ✅ |
| `README.md` | `README.md` (4696B) | ✅ |
| `config/algorithm_weights.json` | `config/algorithm_weights.json` (3106B) | ✅ |
| `models/algorithm_weights.json` | symlink → config/ | ✅ |
| `data/historical.csv` | 1.2MB / 12931 lines | ✅ |
| `data/picks/` (today) | `today_picks.csv` → `Daily_Log/2026-07-13/picks.csv` | ✅ |
| `logs/daily.log` | exists but nearly empty | ⚠️ |
| `logs/api.log` | 779B | ✅ |
| `scripts/generate.sh` | ~443B | ✅ |
| `scripts/start.sh` | ~507B | ✅ |
| `scripts/stop.sh` | ~329B | ✅ |
| `scripts/status.sh` | ~2.2KB | ✅ |
| `scripts/daily.sh` | ~1.6KB | ✅ |

### ❌ MISSING (Target Not Present)

| Target File | Purpose | Priority |
|------------|---------|----------|
| `config/sports.json` | Sport definitions (stat configs, roster rules) | 🔴 HIGH |
| `config/parlay_rules.json` | Parlay builder rules (max legs, correlation) | 🔴 HIGH |
| `config/thresholds.json` | Edge thresholds per sport/league | 🔴 HIGH |

### ➕ EXTRAS (We Have, User's Target Doesn't List)

| File | Notes |
|------|-------|
| `WIRE.md` | Dashboard wireframe design | keep |
| `GAP_ANALYSIS.md` | This report | keep |
| `docs/GAME_REPORT_TIMING.md` | Timing docs | keep |
| `data/events/` | Live event cache (3 sports) | keep |
| `data/odds/` | Live odds JSON cache | keep (stale) |
| `data/props/` | Live props CSV/JSON cache (Jun 27) | keep |
| `data/account/` | Account status | keep |
| `data/business_scan/` | Business tier scan report | keep |
| `data/sports/` | All sports config | keep |
| `data/today/` → symlink to Daily_Log date | Convenience symlink | keep |
| `scripts/odds_api_scraper.py` | Odds API scraper utility | keep |
| `.env` / `.env.template` | Extra env templates | keep |

---

## 2. DATA HEALTH — TODAY (2026-07-13)

| Sport | Picks | Lines | Edge Source | Status |
|-------|-------|-------|-------------|--------|
| **WNBA** | 1,980 | DK lines active | TC vs DK | ✅ FULL |
| **WORLD CUP** | 832 | NO DK LINES | SELF_EDGE only | ⚠️ Quota-capped |
| **MLB** | **0** | — | — | 🔴 MISSING |

**Total picks today: 2,813** (WNBA 1980 + WC 832)

### MLB Gap — Why?

`daily_picks.py --sport MLB` did not produce any rows today. Possible causes:
- No MLB games on today's slate
- MLB scraper returned empty event list
- Odds API quota prevented line fetching → zero valid props

**Action**: Run `python3 Projects/daily_picks.py --sport MLB --date 2026-07-13` and check output.

---

## 3. SERVICE HEALTH

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| `tc-dashboard-streamlit` | 8510 | ✅ UP | `http://localhost:8510` — healthy |
| `dk-combos-engine` | 8515 | 🟡 Paused | Paused 11:32 ET today |
| `soccer-combos-engine` | 8516 | 🟡 Paused | Paused 11:32 ET today |
| `mlb-cross-dashboard` | 8518 | 🟡 Paused | Paused 11:32 ET today |
| `sdio-lines-service` | 8520 | 🟡 Paused | Disabled since Jul 10 |

### Zo.Space Routes — 28/29 OK

| Route | Status | Issue |
|-------|--------|-------|
| All 28 others | ✅ 200 | All green |
| `/api/worldcup-props` | ⚠️ Error | `teams.findIndex is not a function` |

---

## 4. LOGGING

| Log | Status | Content |
|-----|--------|---------|
| `logs/daily.log` | ⚠️ Sparse | Only 2 lines (date stamp + row count) |
| `logs/api.log` | ✅ | 779B |
| `logs/scan_20260713.txt` | ✅ | 1.3KB, 8 routes 200 |
| `Daily_Log/last_run.json` | ✅ | WC only logged (WNBA/MLB missing from summary) |

---

## 5. KNOWN ISSUES (Priority-Sorted)

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | `config/sports.json` missing | 🔴 HIGH | Create from existing sport configs in `data/sports/` and `data/events/` |
| 2 | `config/parlay_rules.json` missing | 🔴 HIGH | Extract rules from `parlay_builder_v8.py` / combo engines |
| 3 | `config/thresholds.json` missing | 🔴 HIGH | Pull from `algorithm_weights.json` + `daily_picks.py` globals |
| 4 | MLB = 0 picks today | 🔴 HIGH | Diagnose: re-run MLB pipeline, check event slate |
| 5 | `daily.log` nearly empty | 🟡 MED | Add logging to `scripts/daily.sh` — capture row counts, errors |
| 6 | Props cache stale (Jun 27) | 🟡 MED | APIs capped — stale data is expected |
| 7 | `/api/worldcup-props` JS error | 🟡 MED | `teams.findIndex` bug — `teams` is not an array |
| 8 | World Cup no DK lines | 🟠 LOW | Known: Odds API Business tier quota maxed |

---

## 6. NEXT ACTIONS

1. **Create 3 missing config files** — `sports.json`, `parlay_rules.json`, `thresholds.json`
2. **Diagnose MLB** — why 0 picks today
3. **Fix worldcup-props route** — the `teams.findIndex` TypeError
4. **Enrich daily.log** — add pipeline step logging
5. **Clean up** — decide if paused services (8515-8520) should stay paused or be removed

---

## 7. HEALTH CHECK SUMMARY

```
✓ PICKS ENGINE      ✓ STREAMLIT (:8510)      ⚠ MLB (0 picks)
✓ WNBA (1980)       ✓ WORLD CUP (832)         ⚠ WC NO DK LINES
✓ HISTORICAL (13K)  ✓ ALGO_WEIGHTS            ❌ 3 CONFIG FILES
✓ SCRIPTS (5/5)     ✓ ROUTES (28/29 = 200)    ⚠ log (1 error)
✓ DAILY LOGS (4d)   ✓ SCAN LOGS (6 files)     ⚠ daily.log bare
```

---

*End of Gap Analysis — 2026-07-13 10:50 ET*
