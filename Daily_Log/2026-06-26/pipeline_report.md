# TC Pipeline Daily Report — 2026-06-26

**Status**: 🟢 HEALTHY
**Time**: 2026-06-26 17:33:33 ET

| Metric | Value |
|---|---|
| Checks Passed | 8 |
| Warnings | 1 |
| Failures | 0 |
| Services Repaired | 2 |
| Files Purged | 32 |

## ✅ Passed
- Daily Picks: all sports generated
- Pregame Combos: built
- Soccer TC Engine: completed
- Output 'picks_csv': present
- Output 'picks_json': present
- Output 'last_run': present
- Output 'slate_wnba': present
- Purge: 32 files removed

## ⚠️ Warnings
- Output 'slate_nba': missing or empty

## Execution Log
| Time | Level | Component | Message |
|---|---|---|---|
| 17:33:33 | OK | Secrets | 3 keys loaded |
| 17:33:33 | OK | Streamlit Dashboard | port 8510 HTTP 200 |
| 17:33:33 | WARN | DK Combos Engine | port 8515 HTTP 404 |
| 17:33:33 | WARN | Soccer Combo Engine | port 8516 HTTP 404 |
| 17:33:33 | FIX | DK Combos | Restarting on port 8515... |
| 17:33:37 | OK | DK Combos | Restarted |
| 17:33:37 | FIX | Soccer Combos | Restarting on port 8516... |
| 17:33:41 | OK | Soccer Combos | Restarted |
| 17:33:41 | INFO | DailyPicks | Running for: WNBA, MLB, WORLD CUP |
| 17:34:15 | OK | DailyPicks | Completed (91 lines) |
| 17:34:15 | INFO | Combos | Building pregame combos... |
| 17:34:15 | OK | Combos | Completed |
| 17:34:15 | INFO | Soccer | Running soccer TC engine... |
| 17:34:15 | OK | Soccer | Completed |
| 17:34:15 | OK | picks_csv | 109641 bytes |
| 17:34:15 | OK | picks_json | 490927 bytes |
| 17:34:15 | OK | last_run | 9116 bytes |
| 17:34:15 | WARN | slate_nba | MISSING |
| 17:34:15 | OK | slate_wnba | 1331 bytes |
| 17:34:15 | FIX | Purge | Removed 32 stale/empty files |