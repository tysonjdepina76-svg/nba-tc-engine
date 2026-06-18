# TC Pipeline Daily Report — 2026-06-17

**Status**: 🟢 HEALTHY
**Time**: 2026-06-17 22:25:52 ET

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
| 22:25:52 | OK | Secrets | 4 keys loaded |
| 22:25:52 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 22:25:52 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 22:25:52 | OK | ESPN | HTTP 200 |
| 22:25:52 | WARN | Odds API | HTTP 401 (0 req left) |
| 22:25:53 | FAIL | SGO | HTTP 429 |
| 22:25:54 | FAIL | TC Projections API | HTTP 503 |
| 22:25:55 | OK | NBA TC Dashboard | HTTP 200 |
| 22:25:56 | OK | Combos API | HTTP 200 |
| 22:25:56 | OK | World Cup Dashboard | HTTP 200 |
| 22:25:56 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 22:25:56 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 22:25:56 | WARN | Soccer Combo Engine | port 8516 DOWN |
| 22:25:56 | FIX | DK Combos | Restarting on port 8515... |
| 22:26:00 | OK | DK Combos | Restarted |
| 22:26:00 | FIX | Soccer Combos | Restarting on port 8516... |
| 22:26:04 | OK | Soccer Combos | Restarted |
| 22:26:04 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 22:26:42 | OK | DailyPicks | Completed (54 lines) |
| 22:26:42 | INFO | Combos | Building pregame combos... |
| 22:26:43 | OK | Combos | Completed |
| 22:26:43 | INFO | Soccer | Running soccer TC engine... |
| 22:26:57 | OK | Soccer | Completed |
| 22:26:57 | OK | picks_csv | 22103 bytes |
| 22:26:57 | OK | picks_json | 88381 bytes |
| 22:26:57 | OK | last_run | 3365 bytes |
| 22:26:57 | WARN | slate_nba | MISSING |
| 22:26:57 | OK | slate_wnba | 216571 bytes |
| 22:26:57 | OK | Purge | Nothing to purge — workspace clean |