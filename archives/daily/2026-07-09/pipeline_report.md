# TC Pipeline Daily Report — 2026-07-09

**Status**: 🔴 UNHEALTHY
**Time**: 2026-07-09 15:05:47 ET

| Metric | Value |
|---|---|
| Checks Passed | 5 |
| Warnings | 2 |
| Failures | 1 |
| Services Repaired | 2 |
| Files Purged | 0 |

## ✅ Passed
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'picks_csv': present
- Output 'last_run': present
- Output 'slate_wnba': present

## ⚠️ Warnings
- Output 'picks_json': missing or empty
- Output 'slate_nba': missing or empty

## ❌ Failures
- Daily Picks: failed

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 15:05:47 | OK | Secrets | 5 keys loaded |
| 15:05:47 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 15:05:47 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 15:05:47 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 15:05:47 | FIX | DK Combos | Restarting on port 8515... |
| 15:05:51 | OK | DK Combos | Restarted |
| 15:05:51 | FIX | Soccer Combos | Restarting on port 8516... |
| 15:05:55 | OK | Soccer Combos | Restarted |
| 15:05:55 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 15:05:55 | FAIL | DailyPicks | Exit 2: usage: daily_picks.py [-h] --sport {NBA,WNBA,NFL,MLB,SOCCER,NHL,WORLD_CUP}
                      [--date DATE] [--dry-run]
daily_picks.py: error: argument --sport: invalid choice: 'WORLD CUP' (choose  |
| 15:05:55 | INFO | Combos | Building pregame combos... |
| 15:05:56 | OK | Combos | Completed |
| 15:05:56 | INFO | Soccer | Running soccer TC engine... |
| 15:05:57 | OK | Soccer | Completed |
| 15:05:57 | OK | picks_csv | 594 bytes |
| 15:05:57 | WARN | picks_json | 2 bytes |
| 15:05:57 | OK | last_run | 1995 bytes |
| 15:05:57 | WARN | slate_nba | MISSING |
| 15:05:57 | OK | slate_wnba | 724 bytes |
| 15:05:57 | OK | Purge | Nothing to purge — workspace clean |