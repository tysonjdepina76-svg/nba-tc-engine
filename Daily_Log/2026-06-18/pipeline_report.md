# TC Pipeline Daily Report — 2026-06-18

**Status**: 🟢 HEALTHY
**Time**: 2026-06-18 22:18:00 ET

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
| 22:18:00 | OK | Secrets | 3 keys loaded |
| 22:18:00 | OK | ESPN | HTTP 200 |
| 22:18:00 | OK | Odds API | HTTP 200 (180 req left) |
| 22:18:01 | FAIL | SGO | HTTP 401 |
| 22:18:01 | FAIL | TC Projections API | HTTP 503 |
| 22:18:01 | OK | NBA TC Dashboard | HTTP 200 |
| 22:18:01 | OK | Combos API | HTTP 200 |
| 22:18:02 | OK | World Cup Dashboard | HTTP 200 |
| 22:18:02 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 22:18:02 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 22:18:02 | WARN | Soccer Combo Engine | port 8516 DOWN |
| 22:18:02 | FIX | DK Combos | Restarting on port 8515... |
| 22:18:06 | OK | DK Combos | Restarted |
| 22:18:06 | FIX | Soccer Combos | Restarting on port 8516... |
| 22:18:10 | OK | Soccer Combos | Restarted |
| 22:18:10 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 22:18:13 | OK | DailyPicks | Completed (15 lines) |
| 22:18:13 | INFO | Combos | Building pregame combos... |
| 22:18:14 | OK | Combos | Completed |
| 22:18:14 | INFO | Soccer | Running soccer TC engine... |
| 22:18:14 | OK | Soccer | Completed |
| 22:18:14 | OK | picks_csv | 9272 bytes |
| 22:18:14 | OK | picks_json | 37854 bytes |
| 22:18:14 | OK | last_run | 1124 bytes |
| 22:18:14 | WARN | slate_nba | MISSING |
| 22:18:14 | OK | slate_wnba | 36089 bytes |
| 22:18:14 | OK | Purge | Nothing to purge — workspace clean |