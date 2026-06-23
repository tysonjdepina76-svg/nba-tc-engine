# TC Pipeline Daily Report — 2026-06-23

**Status**: 🟢 HEALTHY
**Time**: 2026-06-23 13:18:46 ET

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
| 13:18:46 | OK | Secrets | 3 keys loaded |
| 13:18:46 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 13:18:46 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 13:18:46 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 13:18:46 | FIX | DK Combos | Restarting on port 8515... |
| 13:18:50 | OK | DK Combos | Restarted |
| 13:18:50 | FIX | Soccer Combos | Restarting on port 8516... |
| 13:18:54 | OK | Soccer Combos | Restarted |
| 13:18:54 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 13:19:16 | OK | DailyPicks | Completed (78 lines) |
| 13:19:16 | INFO | Combos | Building pregame combos... |
| 13:19:17 | OK | Combos | Completed |
| 13:19:17 | INFO | Soccer | Running soccer TC engine... |
| 13:19:17 | OK | Soccer | Completed |
| 13:19:17 | OK | picks_csv | 629935 bytes |
| 13:19:17 | OK | picks_json | 2420597 bytes |
| 13:19:17 | OK | last_run | 9431 bytes |
| 13:19:17 | WARN | slate_nba | MISSING |
| 13:19:17 | OK | slate_wnba | 645 bytes |
| 13:19:17 | OK | Purge | Nothing to purge — workspace clean |