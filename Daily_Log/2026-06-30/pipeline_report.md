# TC Pipeline Daily Report — 2026-06-30

**Status**: 🟢 HEALTHY
**Time**: 2026-06-30 03:02:40 ET

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
| 03:02:40 | OK | Secrets | 5 keys loaded |
| 03:02:40 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 03:02:40 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 03:02:40 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 03:02:40 | FIX | DK Combos | Restarting on port 8515... |
| 03:02:44 | OK | DK Combos | Restarted |
| 03:02:44 | FIX | Soccer Combos | Restarting on port 8516... |
| 03:02:48 | OK | Soccer Combos | Restarted |
| 03:02:48 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 03:02:53 | OK | DailyPicks | Completed (27 lines) |
| 03:02:53 | INFO | Combos | Building pregame combos... |
| 03:02:54 | OK | Combos | Completed |
| 03:02:54 | INFO | Soccer | Running soccer TC engine... |
| 03:02:54 | OK | Soccer | Completed |
| 03:02:54 | OK | picks_csv | 519 bytes |
| 03:02:54 | OK | picks_json | 1337 bytes |
| 03:02:54 | OK | last_run | 835 bytes |
| 03:02:54 | WARN | slate_nba | MISSING |
| 03:02:54 | OK | slate_wnba | 157 bytes |
| 03:02:54 | OK | Purge | Nothing to purge — workspace clean |