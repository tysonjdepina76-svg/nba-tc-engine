# API Integration Health Report
**Generated**: 2026-06-11 22:35 ET

## Secrets Status
| Secret | Status | Source |
|--------|--------|--------|
| SPORTSGAMEODDS_API_KEY | ✅ Loaded | /root/.zo/secrets.env |
| ODDS_API_KEY | ✅ Loaded | /root/.zo/secrets.env |

## Odds API Account
- **Rate Limit Remaining**: 18,264 requests
- **Rate Limit Used**: 1,736 requests  
- **Total Sports Available**: 165
- **WNBA Sport Key**: `basketball_wnba` ✅ Active

## WNBA Market Availability
| Market | Available | Endpoint |
|--------|-----------|----------|
| h2h (moneyline) | ✅ | /sports/basketball_wnba/odds |
| spreads | ✅ | /sports/basketball_wnba/odds |
| totals | ✅ | /sports/basketball_wnba/odds |
| player_points | ✅ | /sports/basketball_wnba/events/{id}/odds |
| player_rebounds | ✅ | /sports/basketball_wnba/events/{id}/odds |
| player_assists | ✅ | /sports/basketball_wnba/events/{id}/odds |

**Note**: Player props NOT available on bulk `/odds` endpoint. Must use `/events/{id}/odds` for WNBA.

## Today's WNBA Slate (2026-06-11)
| Game | Event ID | DraftKings Props | Books Available |
|------|----------|------------------|-----------------|
| CHI @ IND | aa2e0973... | 10 players (PTS/REB/AST) | DK, FanDuel, BetRivers, MGM |
| NY @ ATL | e653a87b... | 10 players | DK, FanDuel |
| PHX @ DAL | ea094671... | 10 players | DK |
| LV @ POR | b4000f48... | 8 players | DK |

## Pipeline Integration Status
| Component | Status | Notes |
|-----------|--------|-------|
| `daily_picks.py` secret loader | ✅ Fixed | Now loads before imports |
| `odds_enricher.py` WNBA support | ✅ Fixed | Fuzzy name matching + sport key |
| DK line merge into picks | ✅ Working | PTS/REB/AST matched to DK lines |
| 3PM/STL/BLK props | ⚠️ No DK lines | Odds API doesn't offer these markets |

## Stat Coverage
**TC Pipeline generates props for**: PTS, REB, AST, 3PM, STL, BLK  
**DK lines available for**: PTS, REB, AST only  
**Match rate**: ~30% of picks get DK lines (PTS/REB/AST props only)

## Recommendations
1. ✅ **FIXED**: Secret loader now runs before imports
2. ✅ **FIXED**: WNBA fuzzy name matching (Diggins → Diggins-Smith)
3. ⚠️ **KNOWN LIMIT**: 3PM/STL/BLK props have no DK market — TC projections only
4. Future: Consider adding PrizePicks or Underdog for 3PM/STL/BLK prop lines

## Endpoints Verified
- `/sports/basketball_wnba/odds` — ✅ Works (game lines only)
- `/sports/basketball_wnba/events/{id}/odds?markets=player_points,player_rebounds,player_assists` — ✅ Works
- DK bookmaker id: `draftkings` — ✅ Confirmed

## Files Modified
1. `/home/workspace/Projects/daily_picks.py` — Fixed secret loader + DK merge
2. `/home/workspace/Skills/nba-odds-api/scripts/odds_enricher.py` — Fixed WNBA fuzzy match + time window
