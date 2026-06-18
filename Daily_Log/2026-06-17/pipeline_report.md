# TC Pipeline Daily Report — 2026-06-17

**Status**: 🟢 HEALTHY
**Time**: 2026-06-17 19:01:28 ET

| Metric | Value |
|---|---|
| Checks Passed | 8 |
| Warnings | 1 |
| Failures | 0 |
| Services Repaired | 3 |
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
| 19:01:28 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 19:01:28 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 19:01:28 | OK | ESPN | HTTP 200 |
| 19:01:28 | WARN | Odds API | HTTP 401 (0 req left) |
| 19:01:28 | FAIL | SGO | HTTP 400 |
| 19:01:28 | FAIL | TC Projections API | HTTP 503 |
| 19:01:28 | OK | NBA TC Dashboard | HTTP 200 |
| 19:01:28 | OK | Combos API | HTTP 200 |
| 19:01:29 | OK | World Cup Dashboard | HTTP 200 |
| 19:01:29 | WARN | Streamlit Dashboard | port 8510 DOWN |
| 19:01:29 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 19:01:29 | WARN | Soccer Combo Engine | port 8516 DOWN |
| 19:01:29 | FIX | Streamlit | Restarting on port 8510... |
| 19:01:34 | OK | Streamlit | Restarted |
| 19:01:34 | FIX | DK Combos | Restarting on port 8515... |
| 19:01:38 | OK | DK Combos | Restarted |
| 19:01:38 | FIX | Soccer Combos | Restarting on port 8516... |
| 19:01:42 | OK | Soccer Combos | Restarted |
| 19:01:42 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 19:02:00 | OK | DailyPicks | Completed (86 lines) |
| 19:02:00 | INFO | Combos | Building pregame combos... |
| 19:02:01 | OK | Combos | Completed |
| 19:02:01 | INFO | Soccer | Running soccer TC engine... |
| 19:02:06 | OK | Soccer | Completed |
| 19:02:06 | OK | picks_csv | 34441 bytes |
| 19:02:06 | OK | picks_json | 137979 bytes |
| 19:02:06 | OK | last_run | 6911 bytes |
| 19:02:06 | WARN | slate_nba | MISSING |
| 19:02:06 | OK | slate_wnba | 42016 bytes |
| 19:02:06 | FIX | Purge | Removed 2 stale/empty files |