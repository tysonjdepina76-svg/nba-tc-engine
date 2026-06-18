# TC Pipeline Daily Report — 2026-06-18

**Status**: 🟢 HEALTHY
**Time**: 2026-06-18 15:19:49 ET

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
| 15:19:49 | OK | Secrets | 5 keys loaded |
| 15:19:49 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 15:19:49 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 15:19:49 | OK | ESPN | HTTP 200 |
| 15:19:50 | WARN | Odds API | HTTP 404 (? req left) |
| 15:19:50 | FAIL | SGO | HTTP 429 |
| 15:19:51 | FAIL | TC Projections API | HTTP 503 |
| 15:19:52 | OK | NBA TC Dashboard | HTTP 200 |
| 15:19:53 | OK | Combos API | HTTP 200 |
| 15:19:54 | OK | World Cup Dashboard | HTTP 200 |
| 15:19:54 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 15:19:54 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 15:19:54 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 15:19:54 | FIX | DK Combos | Restarting on port 8515... |
| 15:19:58 | OK | DK Combos | Restarted |
| 15:19:58 | FIX | Soccer Combos | Restarting on port 8516... |
| 15:20:02 | OK | Soccer Combos | Restarted |
| 15:20:02 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 15:20:22 | OK | DailyPicks | Completed (55 lines) |
| 15:20:22 | INFO | Combos | Building pregame combos... |
| 15:20:23 | OK | Combos | Completed |
| 15:20:23 | INFO | Soccer | Running soccer TC engine... |
| 15:20:24 | OK | Soccer | Completed |
| 15:20:24 | OK | picks_csv | 5435 bytes |
| 15:20:24 | OK | picks_json | 21169 bytes |
| 15:20:24 | OK | last_run | 5514 bytes |
| 15:20:24 | WARN | slate_nba | MISSING |
| 15:20:24 | OK | slate_wnba | 640 bytes |
| 15:20:24 | FIX | Purge | Removed 2 stale/empty files |