# TC Pipeline Daily Report — 2026-06-23

**Status**: 🟢 HEALTHY
**Time**: 2026-06-23 16:06:32 ET

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
| 16:06:32 | OK | Secrets | 3 keys loaded |
| 16:06:32 | OK | ESPN | HTTP 200 |
| 16:06:32 | WARN | Odds API | HTTP 401 (? req left) |
| 16:06:32 | FAIL | SGO | HTTP 400 |
| 16:06:32 | OK | TC Projections API | HTTP 200 |
| 16:06:33 | OK | NBA TC Dashboard | HTTP 200 |
| 16:06:33 | OK | Combos API | HTTP 200 |
| 16:06:33 | OK | World Cup Dashboard | HTTP 200 |
| 16:06:33 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 16:06:33 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 16:06:33 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 16:06:33 | FIX | DK Combos | Restarting on port 8515... |
| 16:06:37 | OK | DK Combos | Restarted |
| 16:06:37 | FIX | Soccer Combos | Restarting on port 8516... |
| 16:06:41 | OK | Soccer Combos | Restarted |
| 16:06:41 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 16:06:58 | OK | DailyPicks | Completed (75 lines) |
| 16:06:58 | INFO | Combos | Building pregame combos... |
| 16:06:58 | OK | Combos | Completed |
| 16:06:58 | INFO | Soccer | Running soccer TC engine... |
| 16:06:58 | OK | Soccer | Completed |
| 16:06:58 | OK | picks_csv | 292330 bytes |
| 16:06:58 | OK | picks_json | 1284306 bytes |
| 16:06:58 | OK | last_run | 8998 bytes |
| 16:06:58 | WARN | slate_nba | MISSING |
| 16:06:58 | OK | slate_wnba | 422 bytes |
| 16:06:58 | OK | Purge | Nothing to purge — workspace clean |