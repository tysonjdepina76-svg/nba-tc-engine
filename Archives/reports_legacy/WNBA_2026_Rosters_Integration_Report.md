# WNBA 2026 Rosters — Live API Integration Report

## What was corrected

- Built/updated `wnba_tc_live_engine.py` to pull **current 2026 WNBA rosters** from ESPN APIs.
- Integrated `tc_engine.py` so WNBA calls use the live ESPN roster engine first, then fallback only if API fails.
- Removed reliance on stale partial WNBA roster files for current projections.
- Preserved the core TC rule:
  - TC applies only to **player props**: PTS, REB, AST, 3PM.
  - Team/game totals are raw point projections only and **do not** use TC Match.

## Live ESPN team coverage confirmed

ESPN current WNBA team list returns 15 teams:

| Abbr | Team |
|---|---|
| ATL | Atlanta Dream |
| CHI | Chicago Sky |
| CON | Connecticut Sun |
| DAL | Dallas Wings |
| GS | Golden State Valkyries |
| IND | Indiana Fever |
| LV | Las Vegas Aces |
| LA | Los Angeles Sparks |
| MIN | Minnesota Lynx |
| NY | New York Liberty |
| PHX | Phoenix Mercury |
| POR | Portland Fire |
| SEA | Seattle Storm |
| TOR | Toronto Tempo |
| WSH | Washington Mystics |

## APIs used

- ESPN WNBA scoreboard API for current slate.
- ESPN WNBA team roster API for active roster and injury/status.
- ESPN WNBA athlete overview/statistics APIs for PTS, REB, AST, and 3PM averages.

## Files updated

- `wnba_tc_live_engine.py`
- `tc_engine.py`

## Verification

- Syntax check passed for both files.
- Live test ran successfully for `DAL @ CHI` using ESPN live roster data.
- Generated current WNBA slate report successfully through `wnba_tc_live_engine.py`.
