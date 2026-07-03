# TC Pipeline Daily Report — 2026-07-03

**Status**: 🟢 HEALTHY
**Time**: 2026-07-03 03:04:31 ET

| Metric | Value |
|---|---|
| Checks Passed | 6 |
| Warnings | 2 |
| Failures | 0 |
| Services Repaired | 2 |
| Files Purged | 0 |

## ✅ Passed
- Daily Picks: all sports generated
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'picks_csv': present
- Output 'last_run': present
- Output 'slate_wnba': present

## ⚠️ Warnings
- Output 'picks_json': missing or empty
- Output 'slate_nba': missing or empty

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 03:04:31 | OK | Secrets | 5 keys loaded |
| 03:04:31 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 03:04:31 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 03:04:31 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 03:04:31 | FIX | DK Combos | Restarting on port 8515... |
| 03:04:35 | OK | DK Combos | Restarted |
| 03:04:35 | FIX | Soccer Combos | Restarting on port 8516... |
| 03:04:39 | OK | Soccer Combos | Restarted |
| 03:04:39 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 03:04:44 | OK | DailyPicks | Completed (177 lines) |
| 03:04:44 | INFO | Combos | Building pregame combos... |
| 03:04:48 | OK | Combos | Completed |
| 03:04:48 | INFO | Soccer | Running soccer TC engine... |
| 03:04:50 | OK | Soccer | Completed |
| 03:04:50 | OK | picks_csv | 144 bytes |
| 03:04:50 | WARN | picks_json | 2 bytes |
| 03:04:50 | OK | last_run | 4245 bytes |
| 03:04:50 | WARN | slate_nba | MISSING |
| 03:04:50 | OK | slate_wnba | 424 bytes |
| 03:04:50 | OK | Purge | Nothing to purge — workspace clean |