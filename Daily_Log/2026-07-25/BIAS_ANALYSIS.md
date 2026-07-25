# Systemic Bias Analysis — July 25, 2026

## Root Cause

**line < projection ALWAYS → 100% OVER picks across all sports.**

### WNBA (`gen_wnba_today.py` L72)
```python
line = round(val * 0.95, 1) if val > 0 else -0.5
```
Example: 20.0 PTS → line = 19.0 → diff = +1.0 → OVER

### MLB (`gen_mlb_today.py` L200-201)
```python
margin = DEFAULT_LINE_MARGIN.get(stat, 0.5)
lines[stat] = round(proj_final - margin, 3)
```
Example: 1.2 H → margin 0.5 → line = 0.7 → diff = +0.5 → OVER

### Core Math (`daily_picks.py` L704)
```python
edge = proj - line
direction = "OVER" if edge > 0 else "UNDER"
```
No sport configs, no shrinkage, no min_edge thresholds, no consensus. Raw subtraction.

## The Fix (BUILT, NOT WIRED)

`tc_math.py` (359 lines) is the canonical library. Contains:

| Function | Purpose | Status |
|---|---|---|
| `over_under_signal()` | Core projection vs line with min_edge | UNUSED |
| `sport_over_under_signal()` | Sport-specific configs (min_edge, max_edge, use_pct) | UNUSED |
| `shrink_projection()` | Bayesian regression toward market line | UNUSED |
| `consensus_line()` | Multi-book median/mean/sharp | UNUSED |
| `mlb_over_under_signal()` | MLB-specific with stat-appropriate thresholds | UNUSED |
| `calculate_expected_value()` | EV with American odds | UNUSED |
| `kelly_criterion()` | Kelly stake sizing | UNUSED |
| `backtest_picks()` | Full backtest with hit rate, ROI, Sharpe | UNUSED |

**Zero files import `tc_math`.**
Only reference: `Archives/pipeline_cleanup_20260723/src/core_math_engine.py` — an archived file.

## Sport Configurations (tc_math.py SPORT_CONFIGS)

| Sport | min_edge | use_pct | max_edge | Status |
|---|---|---|---|---|
| NBA | 0.5 | false | 15.0 | Config exists, never called |
| WNBA | 0.5 | false | 15.0 | Config exists, never called |
| NFL | 0.5 | false | 15.0 | Config exists, never called |
| MLB | 0.5 | false | 8.0 | Config exists, never called |
| NHL | 0.2 | false | 5.0 | Config exists, never called |

## Band-aid: WNBA Recalibration

`wnba_recalibration.py` (181 lines):
- Drops P+R+A (52.4% coin flip)
- Blacklists 7 zero-hit players
- Applies stat weights
- **Direction diversity**: flips 20% weakest picks if >90% one direction

**But**: runs AFTER `edge = proj - line` has already cooked the direction. Only bandaids the symptom.

## Version History

| File | Location | Size | Status |
|---|---|---|---|
| `tc_math.py` (current) | `Projects/` | 359 lines | Complete, UNWIRED |
| `tc_math.py` (v1) | `Archives/pipeline_cleanup/` | 29 lines | Old — implied prob + vig only |
| `tc_math_hybrid.py` | `Archives/purge/stale_py/` | 329 lines | v2 with ensemble + backtest, stale |

## Fix Plan

One change in `daily_picks.py` line 704:
```python
# BEFORE (current — biased)
edge = proj - line
direction = "OVER" if edge > 0 else "UNDER"

# AFTER (wire tc_math)
from tc_math import sport_over_under_signal, SPORT_CONFIGS
direction, edge = sport_over_under_signal(proj, line, sport.upper())
```

This uses sport-specific:
- min_edge thresholds (filter noise)
- max_edge caps (prevent outliers)
- use_pct vs absolute edge per sport
- min_market_line validation

**Single change fixes WNBA + MLB + NFL simultaneously.**
