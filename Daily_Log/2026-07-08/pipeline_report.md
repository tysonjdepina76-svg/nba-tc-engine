# TC Pipeline Daily Report — 2026-07-08

**Status**: 🔴 UNHEALTHY
**Time**: 2026-07-08 03:04:57 ET

| Metric | Value |
|---|---|
| Checks Passed | 3 |
| Warnings | 4 |
| Failures | 1 |
| Services Repaired | 2 |
| Files Purged | 0 |

## ✅ Passed
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'last_run': present

## ⚠️ Warnings
- Output 'picks_csv': missing or empty
- Output 'picks_json': missing or empty
- Output 'slate_nba': missing or empty
- Output 'slate_wnba': missing or empty

## ❌ Failures
- Daily Picks: failed

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 03:04:57 | OK | Secrets | 5 keys loaded |
| 03:04:57 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 03:04:57 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 03:04:57 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 03:04:57 | FIX | DK Combos | Restarting on port 8515... |
| 03:05:01 | OK | DK Combos | Restarted |
| 03:05:01 | FIX | Soccer Combos | Restarting on port 8516... |
| 03:05:05 | OK | Soccer Combos | Restarted |
| 03:05:05 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 03:05:06 | FAIL | DailyPicks | Exit 2: usage: daily_picks.py [-h] --sport {NBA,WNBA,NFL,MLB,SOCCER,NHL,WORLD_CUP}
                      [--date DATE] [--dry-run]
daily_picks.py: error: the following arguments are required: --sport |
| 03:05:06 | INFO | Combos | Building pregame combos... |
| 03:05:11 | OK | Combos | Completed |
| 03:05:11 | INFO | Soccer | Running soccer TC engine... |
| 03:05:12 | OK | Soccer | Completed |
| 03:05:12 | WARN | picks_csv | MISSING |
| 03:05:12 | WARN | picks_json | MISSING |
| 03:05:12 | OK | last_run | 669 bytes |
| 03:05:12 | WARN | slate_nba | MISSING |
| 03:05:12 | WARN | slate_wnba | MISSING |
| 03:05:12 | OK | Purge | Nothing to purge — workspace clean |