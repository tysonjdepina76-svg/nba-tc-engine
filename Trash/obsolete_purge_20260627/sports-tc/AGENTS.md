# Sports TC — Agent Reference

## What This Project Is

NBA + WNBA Triple Conservative (TC) betting engine. Two independent models:
- **TC Match** = player prop floors for PTS/REB/AST/3PM
- **v8 Game Total** = raw pts + star mult + bench diff + home court (separate from TC Match)

## Source of Truth

`file 'tc-workspace/apps/sports-tc/tc_pipeline_clean/tc_engine.py'`

This is the canonical v8 engine. It supersedes all other versions.
All future work should extend this file, not fork from `master_tc.py` or `scripts/`.

## Key Constants

```python
# TC Match (player props only)
CONS_PTS = 0.85, CONS_REB = 0.80, CONS_AST = 0.75, CONS_3PM = 0.70
GAP_PTS = -3.0, GAP_REB = -1.5, GAP_AST = -1.0, GAP_3PM = -0.8
Q_FACTOR = 0.55, OUT_FACTOR = 0.0

# v8 Game Total (separate model)
STAR_MULTIPLIER = 0.90  # All-NBA first team
ALL_NBA_PLAYERS = { ... }  # star lookup
BENCH_DIFF_THRESHOLD = 15.0  # PPG
BENCH_DIFF_BONUS = 4.0  # pts added
HOME_COURT_BONUS = 2.0
```

## Critical Rule

> TC Match does NOT apply to team totals or game totals.
> TC Match = player props only (PTS/REB/AST/3PM).
> v8 Game Total = separate calibration from raw points.

## Files to Know

| File | Purpose |
|------|---------|
| `tc_pipeline_clean/tc_engine.py` | Main engine + FastAPI + CLI |
| `tc_pipeline_clean/nba_tc_streamlit.py` | Streamlit dashboard |
| `master_tc.py` | Legacy v4 engine (TC Match only, pre-v8) |
| `api.py` | Legacy FastAPI (pre-v8) |
| `TC_Game_Total_Integration_Report.md` | Full v8 design doc |

## Common Tasks

```bash
# Project a game
python tc_pipeline_clean/tc_engine.py --game "SAS @ OKC" --total 218.5

# Backtest
python tc_pipeline_clean/tc_engine.py --sport NBA --backtest

# Run dashboard
streamlit run tc_pipeline_clean/nba_tc_streamlit.py

# Start API
uvicorn tc_pipeline_clean.tc_engine:app --host 0.0.0.0 --port 8001
```

## Roster Updates

When updating rosters, update BOTH:
1. `tc_pipeline_clean/tc_engine.py` (NBA_TEAMS / WNBA_TEAMS dicts)
2. `master_tc.py` (NBA_ROSTERS / WNBA_ROSTERS dicts)

Keep them in sync. `master_tc.py` is used by `api.py`. `tc_engine.py` is the v8 source of truth.

## Series Bench Tracking

Bench differential is tracked in `SERIES_BENCH_PTS` dict. For playoff series, add per-game bench pts:
```python
SERIES_BENCH_PTS["OKC"]["G5"] = 38.0
```
This feeds the v8 bench differential adjustment.
