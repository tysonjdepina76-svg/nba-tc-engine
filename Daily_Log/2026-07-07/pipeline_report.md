# TC Pipeline Daily Report — 2026-07-07

**Status**: 🟢 HEALTHY
**Time**: 2026-07-07 18:58:21 ET

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
| 18:58:21 | OK | Secrets | 5 keys loaded |
| 18:58:21 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 18:58:21 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 18:58:21 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 18:58:21 | FIX | DK Combos | Restarting on port 8515... |
| 18:58:25 | OK | DK Combos | Restarted |
| 18:58:25 | FIX | Soccer Combos | Restarting on port 8516... |
| 18:58:29 | OK | Soccer Combos | Restarted |
| 18:58:29 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 18:59:05 | OK | DailyPicks | Completed (144 lines) |
| 18:59:05 | INFO | Combos | Building pregame combos... |
| 18:59:12 | OK | Combos | Completed |
| 18:59:12 | INFO | Soccer | Running soccer TC engine... |
| 18:59:13 | OK | Soccer | Completed |
| 18:59:13 | OK | picks_csv | 115078 bytes |
| 18:59:13 | OK | picks_json | 513042 bytes |
| 18:59:13 | OK | last_run | 9649 bytes |
| 18:59:13 | WARN | slate_nba | MISSING |
| 18:59:13 | OK | slate_wnba | 488 bytes |
| 18:59:13 | OK | Purge | Nothing to purge — workspace clean |