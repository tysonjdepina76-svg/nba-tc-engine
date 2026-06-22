# TC Pipeline Daily Report — 2026-06-22

**Status**: 🟢 HEALTHY
**Time**: 2026-06-22 18:02:53 ET

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
| 18:02:53 | OK | Secrets | 3 keys loaded |
| 18:02:53 | OK | ESPN | HTTP 200 |
| 18:02:53 | WARN | Odds API | HTTP 401 (? req left) |
| 18:02:53 | FAIL | SGO | HTTP 400 |
| 18:02:54 | FAIL | TC Projections API | HTTP 503 |
| 18:02:55 | OK | NBA TC Dashboard | HTTP 200 |
| 18:02:55 | OK | Combos API | HTTP 200 |
| 18:02:56 | OK | World Cup Dashboard | HTTP 200 |
| 18:02:56 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 18:02:56 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 18:02:56 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 18:02:56 | FIX | DK Combos | Restarting on port 8515... |
| 18:03:00 | OK | DK Combos | Restarted |
| 18:03:00 | FIX | Soccer Combos | Restarting on port 8516... |
| 18:03:04 | OK | Soccer Combos | Restarted |
| 18:03:04 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 18:03:47 | OK | DailyPicks | Completed (92 lines) |
| 18:03:47 | INFO | Combos | Building pregame combos... |
| 18:03:48 | OK | Combos | Completed |
| 18:03:48 | INFO | Soccer | Running soccer TC engine... |
| 18:03:48 | OK | Soccer | Completed |
| 18:03:48 | OK | picks_csv | 79946 bytes |
| 18:03:48 | OK | picks_json | 347642 bytes |
| 18:03:48 | OK | last_run | 9280 bytes |
| 18:03:48 | WARN | slate_nba | MISSING |
| 18:03:48 | OK | slate_wnba | 42432 bytes |
| 18:03:48 | OK | Purge | Nothing to purge — workspace clean |