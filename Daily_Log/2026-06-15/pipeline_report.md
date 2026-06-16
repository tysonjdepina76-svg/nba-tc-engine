# TC Pipeline Daily Report — 2026-06-15

**Status**: 🟢 HEALTHY
**Time**: 2026-06-15 22:29:43 ET

| Metric | Value |
|---|---|
| Checks Passed | 7 |
| Warnings | 0 |
| Failures | 0 |
| Services Repaired | 2 |
| Files Purged | 0 |

## ✅ Passed
- Daily Picks: all sports generated
- Pregame Combos: built
- Output 'picks_csv': present
- Output 'picks_json': present
- Output 'last_run': present
- Output 'slate_nba': present
- Output 'slate_wnba': present

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 22:29:43 | OK | Secrets | 3 keys loaded |
| 22:29:43 | OK | API_KEY | The Odds API: 0ba1...d130 |
| 22:29:43 | OK | API_KEY | SportsGameOdds: 304f...0c4d |
| 22:29:43 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 22:29:43 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 22:29:43 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 22:29:43 | FIX | DK Combos | Restarting on port 8515... |
| 22:29:47 | OK | DK Combos | Restarted |
| 22:29:47 | FIX | Soccer Combos | Restarting on port 8516... |
| 22:29:51 | OK | Soccer Combos | Restarted |
| 22:29:51 | INFO | DailyPicks | Running for: WNBA, MLB |
| 22:29:56 | OK | DailyPicks | Completed (28 lines) |
| 22:29:56 | INFO | Combos | Building pregame combos... |
| 22:29:57 | OK | Combos | Completed |
| 22:29:57 | OK | picks_csv | 12021 bytes |
| 22:29:57 | OK | picks_json | 60403 bytes |
| 22:29:57 | OK | last_run | 2024 bytes |
| 22:29:57 | OK | slate_nba | 42433 bytes |
| 22:29:57 | OK | slate_wnba | 107385 bytes |
| 22:29:57 | OK | Purge | Nothing to purge — workspace clean |