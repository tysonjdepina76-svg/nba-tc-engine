# NFL Backtest Data

## Active Engine
`sportsdata_nfl_engine_v3.py` — multi-source pull covering all available NFL data.

## API Sources

| Source | Tier | Cost | What You Get |
|--------|------|------|-------------|
| **SportsData.io** | Discovery Lab — Odds | $99/mo | 15 prop markets, game odds, live odds, teams, news |
| **The Odds API** | Free tier | Free | NFL game odds (h2h/spreads/totals), 500 req/mo |
| **ESPN API** | Free | Free | Scoreboard, box scores, player stats (post-game) |

## Prop Markets (15/15 — all available in Discovery Lab Odds)
`Fantasy Points | Fantasy Points PPR | Total Yards | Receptions | Receiving Yards | Rushing Yards | Rushing Attempts | Total Touchdowns | Passing Attempts | Passing Completions | Passing Yards | Passing Touchdowns | Passing Interceptions | Rushing Touchdowns | Receiving Touchdowns`

## Stats Sources
- **Offensive stats**: SportsData.io props (pre-game lines), ESPN boxscores (post-game actuals)
- **Defensive stats**: ESPN boxscores (tackles, sacks, INTs, FF, etc.) — post-game only
- **DVOA**: Not available via API. Requires Football Outsiders FO+ subscription or scraping

## Paid Tiers — SportsData.io

| Tier | Price | Data | How |
|------|-------|------|-----|
| **Discovery Lab — Free** | $0 | Last season's data | Self-serve |
| **Discovery Lab — Odds** | $99/mo | Real odds, next-day delay | Self-serve (current) |
| **Discovery Lab — Fantasy** | $99/mo | Real fantasy stats, next-day delay | Self-serve |
| **Discovery Lab — Fantasy + Odds** | $149/mo | Both combined | Self-serve |
| **Leagues API** | Contact sales | Real-time live data, unlimited calls, all endpoints | Sales |
| **Vault** | Contact sales | 10+ years historical data | Sales |

## Usage
```bash
python3 sportsdata_nfl_engine_v3.py [season] [week] [--stats]
```
