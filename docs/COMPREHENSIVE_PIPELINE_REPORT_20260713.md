# TC Sports Intelligence — Comprehensive Pipeline Report

**Generated:** 2026-07-13 20:09 UTC
**Version:** 6.0.0
**Scope:** Full workspace inventory, health, and backtest-ready data

---

## 1. Executive Summary

| Metric | Value |
| --- | --- |
| Active Python modules in `/home/workspace/Projects/` | 90 |
| Catalogued components (docstring'd or class) | 24 |
| Live sports modules | 4 (MLB, WNBA, WC, SOCCER) |
| Off-season modules (disabled, ready to re-enable) | 3 (NBA, NFL, NHL) |
| Health check status | **4/7 OK, 3 warnings, 0 errors** |
| Total pick rows across history | **16,819** |
| Pick log dates | 27 days (oldest → newest) |

The pipeline is **green**. Three sports are active; three are intentionally paused for off-season.

---

## 2. Live Sports Status (Health Check)

| Sport | Status | Engine |
| --- | --- | --- |
| MLB | ✅ OK | BOOK_LINES fetcher |
| WNBA | ✅ OK | TC_ENGINE (`wnba_tc_engine`) |
| WC (World Cup) | ✅ OK | BOOK_LINES fetcher |
| SOCCER | ✅ OK | BOOK_LINES fetcher |
| NBA | ⏸️ Off-season | Auto-enables on next slate |
| NFL | ⏸️ Off-season | Stats wired via `sport_config.py`, auto-runs Aug 6+ |
| NHL | ⏸️ Off-season | Auto-enables on next slate |

`runtime_health_check.py` is registry-driven and exits 0 when 0 errors. ✅

---

## 3. Workspace Inventory

### 3.1 Project tree (`/home/workspace/Projects/`)
- **90 Python modules** (12,569-line `hybrid_tc_engine.py` is the largest)
- Key entry points:
  - `daily_picks.py` — argparse `--sport {wnba,mlb,wc,all}` pipeline
  - `dashboard.py` — Streamlit UI on port 8510
  - `runtime_health_check.py` — registry-driven verification
  - `doc_generator.py` — auto-doc generator (just wired with `is_async` + patch/head endpoints)
  - `backtest_all_sports.py` — multi-strategy historical backtester
  - `tc_pipeline_complete.py` — orchestration root (referenced by doc gen)

### 3.2 Generated docs (`/home/workspace/docs/`)
- `README.md` — pipeline overview + quick start
- `api_docs.json` — endpoint inventory (now includes async + patch/head)
- `components.json` — 24 catalogued classes
- `BACKTEST_COMPONENT_INDEX.md` — backtest class reference (just added)
- `PIPELINE_WORKFLOW.md` — pre-existing workflow doc

### 3.3 Archives (`/home/workspace/archives/legacy_pasted_20260713/`)
Three legacy pasted files archived (kept for diff/audit, not loaded by anything):
- `odds_api_adapter_legacy.py` — superseded by `src/adapters/odds_api.py`
- `runtime_health_check_legacy.py` — superseded by current `runtime_health_check.py`
- `doc_generator_legacy.py` — superseded by current `doc_generator.py`

---

## 4. Backtest Inventory

### 4.1 Catalogued backtest components
- `BacktestResult` — `backtest_all_sports.py` — per-strategy result row
- `HistoricalBacktest` — `backtest_all_sports.py` — multi-sport, multi-strategy backtester (just docstring'd)

### 4.2 Pick log data
- **Location:** `/home/workspace/Daily_Log/YYYY-MM-DD/picks.csv`
- **Schema:** `date, league, matchup, team, player, role, status, stat, direction, market_line, tc_projection, tc_target, edge, threshold, signal, why, raw_average, source, actual, result`
- **Total rows:** 16,819

| League | Rows |
| --- | --- |
| MLB | 9,384 |
| WNBA | 2,343 |
| WORLD CUP / WORLD_CUP | 3,241 |
| (unparsed/legacy) | 1,851 |

| Signal | Rows |
| --- | --- |
| WEAK (edge ≥ 0.5%) | 126 |
| Legacy/unparsed | 16,693 |

| Result | Rows |
| --- | --- |
| PENDING (awaiting grading) | 16,819 |

### 4.3 What backtests can run today
- **Multi-strategy hit-rate replay** — v1, v2, hybrid, ensemble vs graded outcomes (needs `graded_picks.csv`)
- **Per-sport / per-stat / per-direction hit rate** — already wired in `backtest_all_sports.py`
- **Drawdown / streak analysis** — supported via `BacktestResult` dataclass
- **Gaps:** grading pipeline (writes `actual` + `result`) is not in this turn's scope; pick rows are PENDING until the game fires and `graded_picks.csv` is populated by the post-game scraper.

---

## 5. Recent Tooling Upgrades (this session)

1. **Wired `is_async` + patch/head into `doc_generator.py`** — endpoint inventory now reports whether a route is async, and catches `patch_*` / `head_*` functions.
2. **Docstring gap fill** — `BacktestResult` and `HistoricalBacktest` now have greppable one-liner docstrings.
3. **Backtest component index** — `BACKTEST_COMPONENT_INDEX.md` enumerates the two backtest classes with file + docstring.
4. **Legacy archive** — three legacy pasted files moved to `/home/workspace/archives/legacy_pasted_20260713/`.

---

## 6. Quick Start

```bash
# Run daily picks (append mode — sequential runs accumulate)
python3 /home/workspace/Projects/daily_picks.py --sport wnba
python3 /home/workspace/Projects/daily_picks.py --sport mlb
python3 /home/workspace/Projects/daily_picks.py --sport wc

# Health check
python3 /home/workspace/Projects/runtime_health_check.py

# Generate docs
python3 /home/workspace/Projects/doc_generator.py

# Backtest (multi-strategy, multi-sport)
python3 /home/workspace/Projects/backtest_all_sports.py --sport wnba

# Dashboard
streamlit run /home/workspace/Projects/dashboard.py --server.port 8510
```

---

## 7. Known Gaps / Next Steps

- **Grading pipeline** — `actual` and `result` columns are PENDING on all 16,819 rows. Run the post-game scraper / box-score grader to populate, then re-run `backtest_all_sports.py` for hit rates.
- **Old `WORLD CUP` / `WORLD_CUP` league labels** — 3,241 rows use mixed casing. Add a `league` normaliser in `daily_picks.py` if you want clean cuts.
- **Legacy rows without `signal` field** — 16,693 of 16,819 are missing the new `signal` column. These predate the 2026-07-13 dashboard overhaul. Safe to keep, but exclude from any per-signal hit-rate analysis.
