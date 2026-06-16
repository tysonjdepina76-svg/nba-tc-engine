# TC Pipeline Daily Report — 2026-06-15

**Status**: 🟢 HEALTHY
**Time**: 2026-06-15 18:59:32 ET

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
| 18:59:32 | OK | Secrets | 3 keys loaded |
| 18:59:32 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 18:59:32 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 18:59:32 | OK | ESPN | HTTP 200 |
| 18:59:32 | OK | Odds API | HTTP 200 (8413 req left) |
| 18:59:32 | OK | SGO | HTTP 200 |
| 18:59:32 | OK | TC Projections API | HTTP 200 |
| 18:59:32 | OK | NBA TC Dashboard | HTTP 200 |
| 18:59:33 | OK | Combos API | HTTP 200 |
| 18:59:33 | OK | World Cup Dashboard | HTTP 200 |
| 18:59:33 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 18:59:33 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 18:59:33 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 18:59:33 | FIX | DK Combos | Restarting on port 8515... |
| 18:59:37 | OK | DK Combos | Restarted |
| 18:59:37 | FIX | Soccer Combos | Restarting on port 8516... |
| 18:59:41 | OK | Soccer Combos | Restarted |
| 18:59:41 | INFO | DailyPicks | Running for: NBA, WNBA, MLB, NHL, WORLD CUP |
| 18:59:53 | OK | DailyPicks | Completed (83 lines) |
| 18:59:53 | INFO | Combos | Building pregame combos... |
| 18:59:54 | OK | Combos | Completed |
| 18:59:54 | INFO | Soccer | Running soccer TC engine... |
| 18:59:59 | OK | Soccer | Completed |
| 18:59:59 | OK | picks_csv | 3259 bytes |
| 18:59:59 | OK | picks_json | 13421 bytes |
| 18:59:59 | OK | last_run | 6325 bytes |
| 18:59:59 | OK | slate_nba | 42433 bytes |
| 18:59:59 | OK | slate_wnba | 1735 bytes |
| 18:59:59 | OK | Purge | Nothing to purge — workspace clean |