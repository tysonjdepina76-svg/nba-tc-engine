# TC App Diagnostics + Cleanup Report — Live NBA/WNBA Roster Projection System

Date: 2026-05-21  
Zo route tested: `https://true.zo.space/nba-tc`  
API route tested: `https://true.zo.space/api/tc`

## Executive Finding

The TC app had to be corrected into a true live-scrape/API system. The previous route still carried static/hard-wired roster behavior and only projected four stats. That did not match the intended design.

The app is now cleaned so the active TC route uses live API data for both NBA and WNBA:

- Live ESPN roster/stat API for all teams.
- Live ESPN scoreboard odds for ML/spread/total when the selected matchup is on the current board.
- Full roster projections split into starters and bench.
- Six-stat TC output for every player:
  - Points
  - Rebounds
  - Assists
  - 3-point shots made
  - Steals
  - Blocks
- Injury/status report.
- Game assessment with projected winner, TC spread, market total lean, spread lean, bench edge, and injury count.

## What Was Wrong

| Area | Problem | Correction |
|---|---|---|
| Roster source | Old app behavior depended on hard-wired roster arrays. | Removed hard-wired rosters from the live route. `/api/tc` now fetches ESPN live rosters. |
| NBA/WNBA parity | NBA and WNBA were not following the same live workflow. | Both leagues now use the same API pattern: roster → stat hydration → starter/bench split → injury/status → game assessment. |
| Stat coverage | App only displayed PTS/REB/AST/3PM. | Added STL and BLK for six-stat projections. |
| Starter logic | Starters were just top static players or implied rows. | Starters are inferred live as the top five active players by minutes + production until official lineups are posted. |
| Bench logic | Bench could only show what existed in partial static data. | Bench now includes all non-starting active players returned by ESPN. |
| Injury reports | Injury/status detail was limited. | Status is parsed from ESPN athlete status/injury fields and displayed as injury/status notes. |
| ML/spread | ML/spread was not integrated into the app assessment. | Added live ESPN scoreboard odds when the matchup is active on the scoreboard. |
| Game assessment | App had no complete game assessment. | Added projected winner, TC margin, total lean, spread lean, bench edge, and injury count. |
| UI table | Table did not support 6 stats, T targets, or stat edges. | Rebuilt table to show TC value plus T target/edge for each of six stats. |

## Python Criteria Reviewed

I reviewed the existing TC project code and aligned the live app to the settled criteria found across the Python engines:

- TC base formula: `stat × 0.85`
- Questionable adjustment: `× 0.55`
- OUT adjustment: `0`
- T/line target: `stat × 0.88`
- Separate starters and bench.
- Full roster output, not only top players.
- Injury-adjusted projections.
- Game-level assessment using TC combined totals and market odds where available.
- ML/spread/total display when odds API/source returns those values.

Important source files reviewed:

- `sports-tc/AGENTS.md`
- `sports-tc/sports_tc.py`
- `sports-tc/master_tc.py`
- `sports-tc/archive/nba_tc_engine.py`
- `sports-tc/archive/wnba_tc_injury_adjusted.py`
- `nba_tc/nba_tc_engine.py`
- `nba_tc/roster_scraper.py`

## Live Route Cleanup Applied

### `/api/tc`

The route was rewritten as a clean live API route.

Current behavior:

1. Normalize team abbreviations for NBA and WNBA.
2. Fetch selected away/home rosters from ESPN.
3. Hydrate every player with season averages from ESPN Core stats.
4. Compute six TC stats per player:
   - `tc_pts`
   - `tc_reb`
   - `tc_ast`
   - `tc_3pm`
   - `tc_stl`
   - `tc_blk`
5. Compute T targets and edges:
   - `line_pts`, `edge_pts`
   - `line_reb`, `edge_reb`
   - `line_ast`, `edge_ast`
   - `line_3pm`, `edge_3pm`
   - `line_stl`, `edge_stl`
   - `line_blk`, `edge_blk`
6. Split players into:
   - `starters`
   - `bench`
   - `all`
7. Generate injury/status report.
8. Fetch scoreboard odds for active games:
   - ML
   - spread
   - total
9. Generate game assessment.

### `/nba-tc`

The page was rebuilt to display the full live API output:

- NBA + WNBA selectors.
- All 30 NBA teams.
- 15 WNBA team options already represented in the route.
- Full roster tables for away and home.
- Six-stat projection columns.
- T target/edge under every stat.
- ML/spread/market total panel.
- Game assessment panel.
- Injury/status panel.

## Diagnostic Test Results After Cleanup

Full endpoint diagnostic tested 11 matchups across NBA and WNBA.

| Matchup | Away Rows | Away Starters | Away Bench | Home Rows | Home Starters | Home Bench | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| NBA CLE @ NYK | 18 | 5 | 13 | 18 | 5 | 13 | Pass |
| NBA PHI @ BOS | 17 | 5 | 12 | 16 | 5 | 10 | Pass |
| NBA GSW @ LAC | 19 | 5 | 10 | 18 | 5 | 11 | Pass |
| NBA DAL @ OKC | 18 | 5 | 5 | 18 | 5 | 12 | Pass |
| NBA MIL @ NYK | 17 | 5 | 3 | 18 | 5 | 13 | Pass |
| NBA SAS @ HOU | 18 | 5 | 12 | 17 | 5 | 9 | Pass |
| WNBA GS @ NY | 14 | 5 | 6 | 16 | 5 | 5 | Pass |
| WNBA DAL @ CHI | 14 | 5 | 9 | 14 | 5 | 4 | Pass |
| WNBA SEA @ PHX | 15 | 5 | 7 | 14 | 5 | 7 | Pass |
| WNBA LV @ IND | 12 | 5 | 5 | 14 | 5 | 9 | Pass |
| WNBA TOR @ WSH | 14 | 5 | 5 | 14 | 5 | 8 | Pass |

Failures: **0**

## Smoke Tests Passed

- `/api/tc` returns HTTP 200 for tested NBA and WNBA games.
- Every tested player row includes six TC stat keys.
- Every tested player row includes six T target keys.
- Every tested player row includes six edge keys.
- Every tested team returns exactly five starters when active roster count allows it.
- Bench rows are generated from live roster data.
- `/nba-tc` returns HTTP 200.
- Zo Space error log is clear.

## Remaining Notes

- ESPN scoreboard odds only appear when the selected matchup is on the current scoreboard. If the game is not active/current, the app still generates full roster projections and game assessment, but ML/spread may show no live market.
- Official starting lineups are not always available pregame through ESPN roster endpoints. Until official lineups are posted, starters are inferred using minutes + production, which matches the existing Python app logic pattern.
- No static roster arrays remain in the live `/api/tc` route.

## Final Status

The TC app is now a clean live NBA/WNBA roster projection system. It generates full roster starters/bench projections with six stats, injury/status reports, ML/spread context when available, and game assessment for both leagues.