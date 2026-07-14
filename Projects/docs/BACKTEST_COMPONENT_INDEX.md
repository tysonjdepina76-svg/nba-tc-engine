# Backtest Component Index
Auto-generated from the doc generator catalog (Projects/doc_generator.py, 2026-07-13).

## Purpose
Quick map of which backtest-related components live in which files, for cross-referencing
when a backtest, prop, or hit-rate question comes up.

## Backtest-related components (2 found)

| Component         | File                   | Docstring                  |
|-------------------|------------------------|----------------------------|
| `BacktestResult`  | `backtest_all_sports.py` | (no docstring) — add one |
| `HistoricalBacktest` | `backtest_all_sports.py` | (no docstring) — add one |

## Where to find backtest output today
- `data/picks/historical.csv` — graded picks (master)
- `data/picks/today_picks.csv` — today's raw picks
- `data/picks/clean_picks.csv` — INVALID removed
- `data/picks/actionable_picks.csv` — positive edge only
- `Daily_Log/last_run.json` — most recent run summary
- `Daily_Log/YYYY-MM-DD/proj_SPORT_MATCHUP.json` — full projections

## Gap: docstrings
Both backtest classes are missing docstrings. Add a one-liner to each so future agents
can grep by purpose without reading the class body.

## Gap: API endpoint coverage
`api_docs.json` shows 0 endpoints — current `*api*.py` files use class methods, not
top-level `get_*` / `post_*` functions, so the AST endpoint scan misses them. Manual
endpoint list lives in `Projects/fastapi_backend.py` if it exists.
