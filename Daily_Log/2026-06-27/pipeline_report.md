# TC Pipeline Daily Report — 2026-06-27

**Status**: 🟢 HEALTHY
**Time**: 2026-06-27 11:41:50 ET

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
| 11:41:50 | OK | Secrets | 4 keys loaded |
| 11:41:50 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 11:41:50 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 11:41:50 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 11:41:50 | FIX | DK Combos | Restarting on port 8515... |
| 11:41:54 | OK | DK Combos | Restarted |
| 11:41:54 | FIX | Soccer Combos | Restarting on port 8516... |
| 11:41:58 | OK | Soccer Combos | Restarted |
| 11:41:58 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 11:43:40 | OK | DailyPicks | Completed (104 lines) |
| 11:43:40 | INFO | Combos | Building pregame combos... |
| 11:43:40 | OK | Combos | Completed |
| 11:43:40 | INFO | Soccer | Running soccer TC engine... |
| 11:43:40 | OK | Soccer | Completed |
| 11:43:40 | OK | picks_csv | 375187 bytes |
| 11:43:40 | OK | picks_json | 1652085 bytes |
| 11:43:40 | OK | last_run | 11124 bytes |
| 11:43:40 | WARN | slate_nba | MISSING |
| 11:43:40 | OK | slate_wnba | 1324 bytes |
| 11:43:40 | OK | Purge | Nothing to purge — workspace clean |