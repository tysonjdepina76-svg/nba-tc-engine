# TC Pipeline Daily Report — 2026-06-17

**Status**: 🟢 HEALTHY
**Time**: 2026-06-17 21:42:54 ET

| Metric | Value |
|---|---|
| Checks Passed | 8 |
| Warnings | 1 |
| Failures | 0 |
| Services Repaired | 2 |
| Files Purged | 2 |

## ✅ Passed
- Daily Picks: all sports generated
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'picks_csv': present
- Output 'picks_json': present
- Output 'last_run': present
- Output 'slate_wnba': present
- Purge: 2 files removed

## ⚠️ Warnings
- Output 'slate_nba': missing or empty

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 21:42:54 | OK | Secrets | 4 keys loaded |
| 21:42:54 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 21:42:54 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 21:42:54 | OK | ESPN | HTTP 200 |
| 21:42:54 | WARN | Odds API | HTTP 401 (0 req left) |
| 21:42:54 | FAIL | SGO | HTTP 429 |
| 21:42:54 | FAIL | TC Projections API | HTTP 503 |
| 21:42:55 | OK | NBA TC Dashboard | HTTP 200 |
| 21:42:55 | OK | Combos API | HTTP 200 |
| 21:42:55 | OK | World Cup Dashboard | HTTP 200 |
| 21:42:55 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 21:42:55 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 21:42:55 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 21:42:55 | FIX | DK Combos | Restarting on port 8515... |
| 21:42:59 | OK | DK Combos | Restarted |
| 21:42:59 | FIX | Soccer Combos | Restarting on port 8516... |
| 21:43:03 | OK | Soccer Combos | Restarted |
| 21:43:03 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 21:43:16 | OK | DailyPicks | Completed (57 lines) |
| 21:43:16 | INFO | Combos | Building pregame combos... |
| 21:43:17 | OK | Combos | Completed |
| 21:43:17 | INFO | Soccer | Running soccer TC engine... |
| 21:43:24 | OK | Soccer | Completed |
| 21:43:24 | OK | picks_csv | 22103 bytes |
| 21:43:24 | OK | picks_json | 88381 bytes |
| 21:43:24 | OK | last_run | 3804 bytes |
| 21:43:24 | WARN | slate_nba | MISSING |
| 21:43:24 | OK | slate_wnba | 216519 bytes |
| 21:43:24 | FIX | Purge | Removed 2 stale/empty files |