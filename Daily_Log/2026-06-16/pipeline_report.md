# TC Pipeline Daily Report — 2026-06-16

**Status**: 🟢 HEALTHY
**Time**: 2026-06-16 13:16:54 ET

| Metric | Value |
|---|---|
| Checks Passed | 7 |
| Warnings | 1 |
| Failures | 0 |
| Services Repaired | 3 |
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
| 13:16:54 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 13:16:54 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 13:16:54 | OK | ESPN | HTTP 200 |
| 13:16:54 | OK | Odds API | HTTP 200 (4510 req left) |
| 13:16:54 | FAIL | SGO | HTTP 400 |
| 13:16:56 | FAIL | TC Projections API | HTTP 503 |
| 13:16:56 | OK | NBA TC Dashboard | HTTP 200 |
| 13:16:57 | OK | Combos API | HTTP 200 |
| 13:16:57 | OK | World Cup Dashboard | HTTP 200 |
| 13:16:57 | WARN | Streamlit Dashboard | port 8510 DOWN |
| 13:16:57 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 13:16:57 | WARN | Soccer Combo Engine | port 8516 DOWN |
| 13:16:57 | FIX | Streamlit | Restarting on port 8510... |
| 13:17:02 | OK | Streamlit | Restarted |
| 13:17:02 | FIX | DK Combos | Restarting on port 8515... |
| 13:17:06 | OK | DK Combos | Restarted |
| 13:17:06 | FIX | Soccer Combos | Restarting on port 8516... |
| 13:17:10 | OK | Soccer Combos | Restarted |
| 13:17:10 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 13:18:01 | OK | DailyPicks | Completed (75 lines) |
| 13:18:01 | INFO | Combos | Building pregame combos... |
| 13:18:02 | OK | Combos | Completed |
| 13:18:02 | INFO | Soccer | Running soccer TC engine... |
| 13:18:12 | OK | Soccer | Completed |
| 13:18:12 | OK | picks_csv | 91271 bytes |
| 13:18:12 | OK | picks_json | 453481 bytes |
| 13:18:12 | OK | last_run | 8855 bytes |
| 13:18:12 | WARN | slate_nba | MISSING |
| 13:18:12 | OK | slate_wnba | 640 bytes |
| 13:18:12 | OK | Purge | Nothing to purge — workspace clean |