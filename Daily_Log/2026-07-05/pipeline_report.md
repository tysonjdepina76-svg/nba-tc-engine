# TC Pipeline Daily Report — 2026-07-05

**Status**: 🟢 HEALTHY
**Time**: 2026-07-05 03:03:49 ET

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
| 03:03:49 | OK | Secrets | 5 keys loaded |
| 03:03:49 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 03:03:49 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 03:03:49 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 03:03:49 | FIX | DK Combos | Restarting on port 8515... |
| 03:03:53 | OK | DK Combos | Restarted |
| 03:03:53 | FIX | Soccer Combos | Restarting on port 8516... |
| 03:03:57 | OK | Soccer Combos | Restarted |
| 03:03:57 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 03:04:00 | OK | DailyPicks | Completed (140 lines) |
| 03:04:00 | INFO | Combos | Building pregame combos... |
| 03:04:02 | OK | Combos | Completed |
| 03:04:02 | INFO | Soccer | Running soccer TC engine... |
| 03:04:03 | OK | Soccer | Completed |
| 03:04:03 | OK | picks_csv | 144 bytes |
| 03:04:03 | WARN | picks_json | 2 bytes |
| 03:04:03 | OK | last_run | 3351 bytes |
| 03:04:03 | WARN | slate_nba | MISSING |
| 03:04:03 | OK | slate_wnba | 288 bytes |
| 03:04:03 | OK | Purge | Nothing to purge — workspace clean |