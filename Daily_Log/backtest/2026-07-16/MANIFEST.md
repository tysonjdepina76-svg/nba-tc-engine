# Backtest Archive — 2026-07-16

## Picks Summary
- **Total rows**: 640 (622 WNBA projection-only + 18 headline picks)
- **WNBA**: 622 picks, all OVER, edges 0.1%-7.2%
- **MLB**: 0 picks (All-Star break)
- **WC**: 0 active picks (Cape Verde out, self-edge only)
- **Top Edge**: Jackie Young (WNBA) +6.2% PTS OVER

## Files
| File | Description |
|------|-------------|
| `picks.csv` | Full 640-row picks file |
| `proj_WNBA_2026-07-16.json` | Full WNBA slate projections |
| `proj_WNBA_NY_at_DAL.json` | NY @ DAL roster + projections |
| `proj_WNBA_POR_at_WSH.json` | POR @ WSH roster + projections |
| `proj_WNBA_NY@DAL.json` | NY @ DAL (alternate key) |
| `proj_WNBA_POR@WSH.json` | POR @ WSH (alternate key) |
| `proj_MLB_*.json` | MLB projections (off-season) |
| `proj_WC_2026-07-16.json` | WC projections (self-edge) |

## Backtest Instructions
1. After games final, run: `python pipeline/grade_picks.py --date 2026-07-16`
2. Compare `actual` column vs `projection` for hit rate
3. Grade by sport, stat, direction, edge bucket
