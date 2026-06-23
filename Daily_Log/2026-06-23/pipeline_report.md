# TC Pipeline Daily Report — 2026-06-23

**Status**: 🟢 HEALTHY
**Time**: 2026-06-23 17:33:41 ET

| Metric | Value |
|---|---|
| Checks Passed | 7 |
| Warnings | 1 |
| Failures | 0 |
| Services Repaired | 2 |
| Files Purged | 0 |

## ✅ Passed
- Daily Picks: all sports generated
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'picks_csv': present
- Output 'picks_json': present
- Output 'last_run': present
- Output 'slate_wnba': present

## ⚠️ Warnings
- Output 'slate_nba': missing or empty

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 17:33:41 | OK | Secrets | 3 keys loaded |
| 17:33:41 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 17:33:41 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 17:33:41 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 17:33:41 | FIX | DK Combos | Restarting on port 8515... |
| 17:33:45 | OK | DK Combos | Restarted |
| 17:33:45 | FIX | Soccer Combos | Restarting on port 8516... |
| 17:33:49 | OK | Soccer Combos | Restarted |
| 17:33:49 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 17:34:22 | OK | DailyPicks | Completed (72 lines) |
| 17:34:22 | INFO | Combos | Building pregame combos... |
| 17:34:22 | OK | Combos | Completed |
| 17:34:22 | INFO | Soccer | Running soccer TC engine... |
| 17:34:22 | OK | Soccer | Completed |
| 17:34:22 | OK | picks_csv | 115169 bytes |
| 17:34:22 | OK | picks_json | 511569 bytes |
| 17:34:22 | OK | last_run | 8528 bytes |
| 17:34:22 | WARN | slate_nba | MISSING |
| 17:34:22 | OK | slate_wnba | 422 bytes |
| 17:34:22 | OK | Purge | Nothing to purge — workspace clean |