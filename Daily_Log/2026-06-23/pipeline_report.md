# TC Pipeline Daily Report — 2026-06-23

**Status**: 🟢 HEALTHY
**Time**: 2026-06-23 13:45:04 ET

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
| 13:45:04 | OK | Secrets | 3 keys loaded |
| 13:45:04 | OK | ESPN | HTTP 200 |
| 13:45:04 | WARN | Odds API | HTTP 401 (? req left) |
| 13:45:04 | FAIL | SGO | HTTP 400 |
| 13:45:04 | FAIL | TC Projections API | HTTP 503 |
| 13:45:04 | OK | NBA TC Dashboard | HTTP 200 |
| 13:45:05 | OK | Combos API | HTTP 200 |
| 13:45:05 | OK | World Cup Dashboard | HTTP 200 |
| 13:45:05 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 13:45:05 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 13:45:05 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 13:45:05 | FIX | DK Combos | Restarting on port 8515... |
| 13:45:09 | OK | DK Combos | Restarted |
| 13:45:09 | FIX | Soccer Combos | Restarting on port 8516... |
| 13:45:13 | OK | Soccer Combos | Restarted |
| 13:45:13 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 13:45:36 | OK | DailyPicks | Completed (78 lines) |
| 13:45:36 | INFO | Combos | Building pregame combos... |
| 13:45:36 | OK | Combos | Completed |
| 13:45:36 | INFO | Soccer | Running soccer TC engine... |
| 13:45:36 | OK | Soccer | Completed |
| 13:45:36 | OK | picks_csv | 93711 bytes |
| 13:45:36 | OK | picks_json | 418509 bytes |
| 13:45:36 | OK | last_run | 9436 bytes |
| 13:45:36 | WARN | slate_nba | MISSING |
| 13:45:36 | OK | slate_wnba | 645 bytes |
| 13:45:36 | OK | Purge | Nothing to purge — workspace clean |