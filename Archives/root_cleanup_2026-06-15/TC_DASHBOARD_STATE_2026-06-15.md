# Sports TC Dashboard — Integration State
## 2026-06-15 11:45 ET

### Routes Live (15 total)
| Route | Type | Status |
|---|---|---|
| `/` | page (private) | Home |
| `/nba-tc` | page (public) | Main dashboard |
| `/dk-combos` | page (public) | Combos/Parlay |
| `/worldcup` | page (public) | World Cup |
| `/mirror-workbook` | page (private) | Mirror |
| `/api/tc` | API (public) | TC engine |
| `/api/dk-lines` | API (public) | DK lines |
| `/api/daily-log` | API (public) | Daily log |
| `/api/pipeline-health` | API (public) | Health check |
| `/api/combo-prob` | API (public) | Combo probability |
| `/api/combos` | API (public) | Combos |
| `/api/wnba-boxscores` | API (public) | WNBA box scores |
| `/api/env-check` | API (public) | Environment |
| `/api/worldcup-odds` | API (public) | World Cup odds |
| `/api/worldcup-props` | API (public) | World Cup props |

### Team Rosters — All Sports Complete
| Sport | Teams | Status |
|---|---|---|
| NBA | 30 | ✓ |
| WNBA | 15 | ✓ |
| NFL | 32 | ✓ |
| MLB | 30 | ✓ |
| NHL | 32 | ✓ (added CHI, VAN, UTA) |
| WORLD CUP | 41 | ✓ |

### Recent Fixes Applied
- NHL_TEAMS: Added CHI, VAN, UTA → 32 teams, alphabetized
- NHL API map: Removed stale "Arizona Coyotes":"ARI" (team moved to Utah, ARI belongs to MLB)
- Page ↔ API fully synced

### API Feeds
- ESPN roster/stats/live: Active (NBA, WNBA, MLB, NHL, WORLD CUP)
- The Odds API: Conditional (DK lines for non-basketball sports)
- SportsGameOdds: Conditional (primary paid feed)
- SportsData.io: NFL pregame lines
- WNBA market fallbacks: Active (when ESPN/Odds API returns no lines)

### TC Formula
- Q_MULT: 0.55 (questionable players)
- STAT_CONS: pts/reb/ast/tpm: 0.85, stl/blk: 0.80
- LINE_FACTOR: 0.88
- WNBA: 40/48 minute normalization, REB/AST lift 1.025

### Dashboard Tabs
1. Project Game — slate, odds, TC projections, stat leaders, full rosters
2. Live Stats — ESPN scoreboard, 30s auto-refresh
3. Injury Report — OUT/DNP/Q filters, TC impact
4. Backtest — 2026 Playoffs (48 games, Finals: NYK 4-1 SAS)
5. Daily Log — picks from Daily_Log/
6. Parlay Builder — top 8 edge picks per game
7. Pipeline Health — API keys, connectivity, routes, services
8. Combos — game-by-game hit probability
9. WNBA — minutes leaders, closing lineups
10. NFL / Fantasy — SportsData.io lines, props

### Key URLs
- Dashboard: https://true.zo.space/nba-tc
- Combos: https://true.zo.space/dk-combos
