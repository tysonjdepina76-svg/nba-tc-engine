# Sports TC Pipeline Diagnostics

Generated: 2026-05-22 22:35:19

| Check | Status |
|---|---:|
| NBA roster JSON exists | PASS |
| WNBA roster JSON exists | PASS |
| NBA teams loaded | PASS |
| Every NBA team has starters | PASS |
| Every NBA team has injury_notes | PASS |
| WNBA teams loaded | PASS |
| Every WNBA team has starters | PASS |
| Build NBA BOS @ NYK | PASS |
| NBA has model_totals section | PASS |
| NBA no tc_game_total field | PASS |
| NBA prop candidates | PASS |
| Build WNBA DAL @ ATL | PASS |
| WNBA has model_totals section | PASS |
| WNBA no tc_game_total field | PASS |
| WNBA prop candidates | PASS |

## Canonical Rules
- TC is the primary player-prop model.
- Raw/model team and game totals are separate and never labeled TC totals.
- NFRI, Pace, Home Court, and Momentum are optional layers for model totals.
