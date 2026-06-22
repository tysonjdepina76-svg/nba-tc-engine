# TC Pipeline Daily Report — 2026-06-22

**Status**: 🟢 HEALTHY
**Time**: 2026-06-22 17:54:18 ET

| Metric | Value |
|---|---|
| Checks Passed | 8 |
| Warnings | 1 |
| Failures | 0 |
| Services Repaired | 2 |
| Files Purged | 12 |

## ✅ Passed
- Daily Picks: all sports generated
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'picks_csv': present
- Output 'picks_json': present
- Output 'last_run': present
- Output 'slate_wnba': present
- Purge: 12 files removed

## ⚠️ Warnings
- Output 'slate_nba': missing or empty

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 17:54:18 | OK | Secrets | 3 keys loaded |
| 17:54:18 | OK | ESPN | HTTP 200 |
| 17:54:18 | WARN | Odds API | HTTP 401 (? req left) |
| 17:54:18 | FAIL | SGO | HTTP 400 |
| 17:54:19 | FAIL | TC Projections API | HTTP 503 |
| 17:54:20 | OK | NBA TC Dashboard | HTTP 200 |
| 17:54:21 | OK | Combos API | HTTP 200 |
| 17:54:21 | OK | World Cup Dashboard | HTTP 200 |
| 17:54:21 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 17:54:21 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 17:54:21 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 17:54:21 | FIX | DK Combos | Restarting on port 8515... |
| 17:54:25 | OK | DK Combos | Restarted |
| 17:54:25 | FIX | Soccer Combos | Restarting on port 8516... |
| 17:54:29 | OK | Soccer Combos | Restarted |
| 17:54:29 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 17:55:17 | OK | DailyPicks | Completed (92 lines) |
| 17:55:17 | INFO | Combos | Building pregame combos... |
| 17:55:18 | OK | Combos | Completed |
| 17:55:18 | INFO | Soccer | Running soccer TC engine... |
| 17:55:18 | OK | Soccer | Completed |
| 17:55:18 | OK | picks_csv | 79946 bytes |
| 17:55:18 | OK | picks_json | 347642 bytes |
| 17:55:18 | OK | last_run | 9272 bytes |
| 17:55:18 | WARN | slate_nba | MISSING |
| 17:55:18 | OK | slate_wnba | 2248 bytes |
| 17:55:18 | FIX | Purge | Removed 12 stale/empty files |