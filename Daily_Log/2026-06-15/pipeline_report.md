# TC Pipeline Daily Report — 2026-06-15

**Status**: 🟢 HEALTHY
**Time**: 2026-06-15 15:33:22 ET

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
| 15:33:22 | OK | Secrets | 3 keys loaded |
| 15:33:22 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 15:33:22 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 15:33:22 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 15:33:22 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 15:33:22 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 15:33:22 | FIX | DK Combos | Restarting on port 8515... |
| 15:33:26 | OK | DK Combos | Restarted |
| 15:33:26 | FIX | Soccer Combos | Restarting on port 8516... |
| 15:33:30 | OK | Soccer Combos | Restarted |
| 15:33:30 | INFO | DailyPicks | Running for: NBA, WNBA, MLB, NHL, WORLD CUP |
| 15:33:36 | OK | DailyPicks | Completed (86 lines) |
| 15:33:36 | INFO | Combos | Building pregame combos... |
| 15:33:38 | OK | Combos | Completed |
| 15:33:38 | INFO | Soccer | Running soccer TC engine... |
| 15:33:44 | OK | Soccer | Completed |
| 15:33:44 | OK | picks_csv | 3031 bytes |
| 15:33:44 | OK | picks_json | 12553 bytes |
| 15:33:44 | OK | last_run | 6721 bytes |
| 15:33:44 | OK | slate_nba | 42433 bytes |
| 15:33:44 | OK | slate_wnba | 1735 bytes |
| 15:33:44 | OK | Purge | Nothing to purge — workspace clean |