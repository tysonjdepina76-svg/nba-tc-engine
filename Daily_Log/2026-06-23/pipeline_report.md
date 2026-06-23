# TC Pipeline Daily Report — 2026-06-23

**Status**: 🟢 HEALTHY
**Time**: 2026-06-23 14:10:32 ET

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
| 14:10:32 | OK | Secrets | 3 keys loaded |
| 14:10:32 | OK | ESPN | HTTP 200 |
| 14:10:33 | WARN | Odds API | HTTP 401 (? req left) |
| 14:10:33 | FAIL | SGO | HTTP 400 |
| 14:10:33 | FAIL | TC Projections API | HTTP 503 |
| 14:10:33 | OK | NBA TC Dashboard | HTTP 200 |
| 14:10:33 | OK | Combos API | HTTP 200 |
| 14:10:34 | OK | World Cup Dashboard | HTTP 200 |
| 14:10:34 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 14:10:34 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 14:10:34 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 14:10:34 | FIX | DK Combos | Restarting on port 8515... |
| 14:10:38 | OK | DK Combos | Restarted |
| 14:10:38 | FIX | Soccer Combos | Restarting on port 8516... |
| 14:10:42 | OK | Soccer Combos | Restarted |
| 14:10:42 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 14:11:09 | OK | DailyPicks | Completed (75 lines) |
| 14:11:09 | INFO | Combos | Building pregame combos... |
| 14:11:09 | OK | Combos | Completed |
| 14:11:09 | INFO | Soccer | Running soccer TC engine... |
| 14:11:09 | OK | Soccer | Completed |
| 14:11:09 | OK | picks_csv | 93246 bytes |
| 14:11:09 | OK | picks_json | 416374 bytes |
| 14:11:09 | OK | last_run | 8947 bytes |
| 14:11:09 | WARN | slate_nba | MISSING |
| 14:11:09 | OK | slate_wnba | 645 bytes |
| 14:11:09 | OK | Purge | Nothing to purge — workspace clean |