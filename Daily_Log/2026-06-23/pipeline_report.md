# TC Pipeline Daily Report — 2026-06-23

**Status**: 🟢 HEALTHY
**Time**: 2026-06-23 15:39:38 ET

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
| 15:39:38 | OK | Secrets | 3 keys loaded |
| 15:39:38 | OK | ESPN | HTTP 200 |
| 15:39:38 | WARN | Odds API | HTTP 401 (? req left) |
| 15:39:38 | FAIL | SGO | HTTP 400 |
| 15:39:38 | FAIL | TC Projections API | HTTP 503 |
| 15:39:38 | OK | NBA TC Dashboard | HTTP 200 |
| 15:39:39 | OK | Combos API | HTTP 200 |
| 15:39:39 | OK | World Cup Dashboard | HTTP 200 |
| 15:39:39 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 15:39:39 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 15:39:39 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 15:39:39 | FIX | DK Combos | Restarting on port 8515... |
| 15:39:43 | OK | DK Combos | Restarted |
| 15:39:43 | FIX | Soccer Combos | Restarting on port 8516... |
| 15:39:47 | OK | Soccer Combos | Restarted |
| 15:39:47 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 15:40:09 | OK | DailyPicks | Completed (75 lines) |
| 15:40:09 | INFO | Combos | Building pregame combos... |
| 15:40:10 | OK | Combos | Completed |
| 15:40:10 | INFO | Soccer | Running soccer TC engine... |
| 15:40:10 | OK | Soccer | Completed |
| 15:40:10 | OK | picks_csv | 554155 bytes |
| 15:40:10 | OK | picks_json | 2182863 bytes |
| 15:40:10 | OK | last_run | 8972 bytes |
| 15:40:10 | WARN | slate_nba | MISSING |
| 15:40:10 | OK | slate_wnba | 645 bytes |
| 15:40:10 | OK | Purge | Nothing to purge — workspace clean |