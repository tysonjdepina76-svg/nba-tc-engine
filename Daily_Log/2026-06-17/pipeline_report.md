# TC Pipeline Daily Report — 2026-06-17

**Status**: 🟢 HEALTHY
**Time**: 2026-06-17 19:03:03 ET

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
| 19:03:03 | OK | Secrets | 3 keys loaded |
| 19:03:03 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 19:03:03 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 19:03:03 | OK | ESPN | HTTP 200 |
| 19:03:03 | WARN | Odds API | HTTP 401 (0 req left) |
| 19:03:03 | FAIL | SGO | HTTP 400 |
| 19:03:03 | FAIL | TC Projections API | HTTP 503 |
| 19:03:04 | OK | NBA TC Dashboard | HTTP 200 |
| 19:03:04 | OK | Combos API | HTTP 200 |
| 19:03:04 | OK | World Cup Dashboard | HTTP 200 |
| 19:03:04 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 19:03:04 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 19:03:04 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 19:03:04 | FIX | DK Combos | Restarting on port 8515... |
| 19:03:08 | OK | DK Combos | Restarted |
| 19:03:08 | FIX | Soccer Combos | Restarting on port 8516... |
| 19:03:12 | OK | Soccer Combos | Restarted |
| 19:03:12 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 19:03:37 | OK | DailyPicks | Completed (86 lines) |
| 19:03:37 | INFO | Combos | Building pregame combos... |
| 19:03:38 | OK | Combos | Completed |
| 19:03:38 | INFO | Soccer | Running soccer TC engine... |
| 19:03:45 | OK | Soccer | Completed |
| 19:03:45 | OK | picks_csv | 34441 bytes |
| 19:03:45 | OK | picks_json | 137979 bytes |
| 19:03:45 | OK | last_run | 6911 bytes |
| 19:03:45 | WARN | slate_nba | MISSING |
| 19:03:45 | OK | slate_wnba | 42016 bytes |
| 19:03:45 | OK | Purge | Nothing to purge — workspace clean |