# TC Pipeline Daily Report — 2026-07-01

**Status**: 🟢 HEALTHY
**Time**: 2026-07-01 03:02:58 ET

| Metric | Value |
|---|---|
| Checks Passed | 6 |
| Warnings | 2 |
| Failures | 0 |
| Services Repaired | 2 |
| Files Purged | 0 |

## ✅ Passed
- Daily Picks: all sports generated
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'picks_csv': present
- Output 'last_run': present
- Output 'slate_wnba': present

## ⚠️ Warnings
- Output 'picks_json': missing or empty
- Output 'slate_nba': missing or empty

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 03:02:58 | OK | Secrets | 5 keys loaded |
| 03:02:58 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 03:02:58 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 03:02:58 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 03:02:58 | FIX | DK Combos | Restarting on port 8515... |
| 03:03:02 | OK | DK Combos | Restarted |
| 03:03:02 | FIX | Soccer Combos | Restarting on port 8516... |
| 03:03:06 | OK | Soccer Combos | Restarted |
| 03:03:06 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 03:03:08 | OK | DailyPicks | Completed (18 lines) |
| 03:03:08 | INFO | Combos | Building pregame combos... |
| 03:03:13 | OK | Combos | Completed |
| 03:03:13 | INFO | Soccer | Running soccer TC engine... |
| 03:03:13 | OK | Soccer | Completed |
| 03:03:13 | OK | picks_csv | 144 bytes |
| 03:03:13 | WARN | picks_json | 2 bytes |
| 03:03:13 | OK | last_run | 391 bytes |
| 03:03:13 | WARN | slate_nba | MISSING |
| 03:03:13 | OK | slate_wnba | 152 bytes |
| 03:03:13 | OK | Purge | Nothing to purge — workspace clean |