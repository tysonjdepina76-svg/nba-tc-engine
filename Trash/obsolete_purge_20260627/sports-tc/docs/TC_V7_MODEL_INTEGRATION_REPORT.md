# Sports TC v7 Model Integration Report

## Decision
Yes: TC should remain the core model.

The correct structure is:

1. **TC Core** — player prop floor model only.
2. **Raw Totals** — team/game projected points without TC.
3. **NFRI Totals** — health/location-adjusted floor rating.
4. **Pace Totals** — raw totals adjusted by tempo.
5. **Full Model Totals** — NFRI + pace + home/away + momentum.

This keeps the integrity of the original TC template: no team total or game total is called a TC projection.

## Implemented Quick Fixes

### 1. Unified LINE_FACTOR
- Canonical `LINE_FACTOR = 0.88` kept for player prop line reference only.
- Removed the old mistake of applying TC line logic to team/game totals.

### 2. Backtest CSV Completion
`data/backtest_seed_log.csv` now includes:
- generated_at
- sport
- model
- away/home
- raw team points
- raw game points
- selected model total
- market total
- edge
- lean
- unit size
- actual_total placeholder
- result placeholder
- profit_units placeholder
- report paths

### 3. Unit Sizing
Implemented conservative unit sizing:
- edge >= +7 → OVER
- edge <= -7 → UNDER
- units = edge / 7, capped at 3 units
- no play inside ±7

### 4. ROI-Ready Tracking
Each saved report logs pending fields:
- actual_total
- result
- profit_units
- roi_ready = YES_AFTER_ACTUAL

This makes every generated projection ready for postgame grading.

## Models Added

### TC Core
Player prop floor model:
- PTS × 0.85
- REB × 0.80
- AST × 0.75
- 3PM × 0.70
- Q × 0.55
- OUT = 0

### NFRI — Net Floor Rating Index
NFRI is a conservative health/location floor index:

`NFRI player points = TC_PTS × home/away factor × momentum factor`

This model measures team scoring floor after injury and status adjustments.

### Pace Model
Uses team pace indexes to adjust raw scoring totals.

### Full Model
Combines:
- NFRI
- pace factor
- home/away location
- momentum index

## Dashboard Update
The dashboard now gives model options:
- TC Core only / Raw totals
- NFRI totals
- Pace totals
- Full model totals

URL:
https://sports-tc-dashboard-true.zocomputer.io

## Diagnostics
All checks pass:
- NBA roster JSON exists
- WNBA roster JSON exists
- NBA teams loaded
- WNBA teams loaded
- Every NBA team has starters
- Every WNBA team has starters
- Model totals section exists
- No `tc_game_total` field exists
- Prop candidates generate

## Current Rule
Use TC as the primary identity of the app.
Use NFRI/Pace/Full as optional comparison models on the dashboard.

That lets the app stay true to your original TC template while becoming more competitive against sportsbook/DFS projection apps.
