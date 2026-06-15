# TC Pipeline Daily Report — 2026-06-15

**Status**: 🟢 HEALTHY
**Time**: 2026-06-15 15:29:22 ET

| Metric | Value |
|---|---|
| Checks Passed | 8 |
| Warnings | 0 |
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
- Output 'slate_nba': present
- Output 'slate_wnba': present

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 15:29:22 | OK | Secrets | 3 keys loaded |
| 15:29:22 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 15:29:22 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 15:29:22 | WARN | Streamlit Dashboard | port 8510 DOWN |
| 15:29:22 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 15:29:22 | WARN | Soccer Combo Engine | port 8516 DOWN |
| 15:29:22 | FIX | Streamlit | Restarting on port 8510... |
| 15:29:27 | OK | Streamlit | Restarted |
| 15:29:27 | FIX | DK Combos | Restarting on port 8515... |
| 15:29:31 | OK | DK Combos | Restarted |
| 15:29:31 | FIX | Soccer Combos | Restarting on port 8516... |
| 15:29:35 | OK | Soccer Combos | Restarted |
| 15:29:35 | INFO | DailyPicks | Running for: NBA, WNBA, MLB, NHL, WORLD CUP |
| 15:29:43 | OK | DailyPicks | Completed (86 lines) |
| 15:29:43 | INFO | Combos | Building pregame combos... |
| 15:29:44 | OK | Combos | Completed |
| 15:29:44 | INFO | Soccer | Running soccer TC engine... |
| 15:29:49 | OK | Soccer | Completed |
| 15:29:49 | OK | picks_csv | 3031 bytes |
| 15:29:49 | OK | picks_json | 12553 bytes |
| 15:29:49 | OK | last_run | 6721 bytes |
| 15:29:49 | OK | slate_nba | 42433 bytes |
| 15:29:49 | OK | slate_wnba | 1735 bytes |
| 15:29:49 | OK | Purge | Nothing to purge — workspace clean |