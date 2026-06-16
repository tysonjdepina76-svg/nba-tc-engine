# TC Pipeline Daily Report — 2026-06-15

**Status**: 🟢 HEALTHY
**Time**: 2026-06-15 23:47:25 ET

| Metric | Value |
|---|---|
| Checks Passed | 8 |
| Warnings | 0 |
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
- Output 'slate_nba': present
- Output 'slate_wnba': present

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 23:47:25 | OK | Secrets | 3 keys loaded |
| 23:47:25 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 23:47:25 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 23:47:25 | OK | ESPN | HTTP 200 |
| 23:47:25 | OK | Odds API | HTTP 200 (5899 req left) |
| 23:47:25 | OK | SGO | HTTP 200 |
| 23:47:25 | FAIL | TC Projections API | HTTP 503 |
| 23:47:25 | OK | NBA TC Dashboard | HTTP 200 |
| 23:47:25 | OK | Combos API | HTTP 200 |
| 23:47:26 | OK | World Cup Dashboard | HTTP 200 |
| 23:47:26 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 23:47:26 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 23:47:26 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 23:47:26 | FIX | DK Combos | Restarting on port 8515... |
| 23:47:30 | OK | DK Combos | Restarted |
| 23:47:30 | FIX | Soccer Combos | Restarting on port 8516... |
| 23:47:34 | OK | Soccer Combos | Restarted |
| 23:47:34 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 23:47:36 | OK | DailyPicks | Completed (11 lines) |
| 23:47:36 | INFO | Combos | Building pregame combos... |
| 23:47:36 | OK | Combos | Completed |
| 23:47:36 | INFO | Soccer | Running soccer TC engine... |
| 23:47:41 | OK | Soccer | Completed |
| 23:47:41 | OK | picks_csv | 98 bytes |
| 23:47:41 | OK | picks_json | 440 bytes |
| 23:47:41 | OK | last_run | 675 bytes |
| 23:47:41 | OK | slate_nba | 42433 bytes |
| 23:47:41 | OK | slate_wnba | 107504 bytes |
| 23:47:41 | OK | Purge | Nothing to purge — workspace clean |