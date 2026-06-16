# TC App Clean Live API Report

Date: 2026-05-21

## Completed

The TC app has been cleaned and rebuilt around the intended live-data workflow.

## Live App Design Now Implemented

### Data Sources

- NBA rosters: ESPN live roster/stat APIs
- WNBA rosters: ESPN live roster/stat APIs
- Injury/status: ESPN athlete status and injury fields
- ML/spread/total: ESPN live scoreboard odds when the selected matchup is on the current board

### Removed From Active Route

- No hard-wired NBA roster table
- No hard-wired WNBA roster table
- No partial static player arrays controlling projections
- No UI dependency on old four-stat-only output

### Projection Output

Every live player now receives six-stat TC projections:

1. PTS
2. REB
3. AST
4. 3PM
5. STL
6. BLK

Every stat also includes:

- TC value
- T target/line value
- Edge value

### Team Output

For each team:

- Starting five
- Bench
- Full roster
- Injury/status notes
- Team TC totals by stat

### Game Output

For each selected matchup:

- TC combined points
- TC line
- TC edge
- Projected winner
- Projected TC spread
- Market total if available
- Total lean
- Spread lean if available
- ML/spread display if available
- Bench edge
- Injury count
- Written assessment summary

## Test Summary

Diagnostic endpoint tests ran against 11 NBA/WNBA matchups.

- Tests run: 11
- Failures: 0
- Page HTTP status: 200
- Space route errors: 0

## Active Routes Updated

- `https://true.zo.space/api/tc`
- `https://true.zo.space/nba-tc`

## Full Diagnostics File

See: `TC_App_Diagnostics_Report_20260521.md`

## Final Status

Clean live TC app is operational.