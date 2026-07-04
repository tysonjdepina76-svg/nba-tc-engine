# TC Pipeline Daily Report — 2026-07-04

**Status**: 🟢 HEALTHY
**Time**: 2026-07-04 03:04:27 ET

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
| 03:04:27 | OK | Secrets | 5 keys loaded |
| 03:04:27 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 03:04:27 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 03:04:27 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 03:04:27 | FIX | DK Combos | Restarting on port 8515... |
| 03:04:31 | OK | DK Combos | Restarted |
| 03:04:31 | FIX | Soccer Combos | Restarting on port 8516... |
| 03:04:35 | OK | Soccer Combos | Restarted |
| 03:04:35 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 03:04:39 | OK | DailyPicks | Completed (160 lines) |
| 03:04:39 | INFO | Combos | Building pregame combos... |
| 03:04:41 | OK | Combos | Completed |
| 03:04:41 | INFO | Soccer | Running soccer TC engine... |
| 03:04:42 | OK | Soccer | Completed |
| 03:04:42 | OK | picks_csv | 144 bytes |
| 03:04:42 | WARN | picks_json | 2 bytes |
| 03:04:42 | OK | last_run | 3799 bytes |
| 03:04:42 | WARN | slate_nba | MISSING |
| 03:04:42 | OK | slate_wnba | 287 bytes |
| 03:04:42 | OK | Purge | Nothing to purge — workspace clean |