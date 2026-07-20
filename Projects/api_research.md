# Sports API Research — 2026-07-19

## 🏆 BEST OPTION: BALLDONTLIE (balldontlie.io)

**One API covers all 3 sports we need.**

| Sport | Stats | Betting Odds | Player Props | Roster/Players |
|-------|-------|-------------|-------------|----------------|
| WNBA | ✅ | ✅ (paid) | ✅ (paid) | ✅ |
| MLB | ✅ | ✅ (paid) | ✅ (paid) | ✅ |
| World Cup 2026 | ✅ | ✅ (paid) | N/A | ✅ |

### Plans
| Plan | Price | Rate Limit | Odds/Props | Historical |
|------|-------|-----------|-------------|------------|
| Free | $0 | 5 req/min/sport | ❌ No | ❌ |
| All-Star | $9.99/mo | 60 req/min/sport | ✅ Yes | ❌ |
| GOAT | $39.99/mo | 300 req/min/sport | ✅ Yes | ✅ Historical odds |

### Endpoints We Need
- `GET /wnba/player_props` — WNBA player prop lines
- `GET /mlb/player_props` — MLB player prop lines  
- `GET /fifa/betting_odds` — World Cup odds
- `GET /wnba/stats` — WNBA game stats (free tier gives this)
- `GET /mlb/stats` — MLB game stats (free tier gives this)
- `GET /fifa/matches` — WC schedule/results

### Integration Ready
- MCP server: `github.com/balldontlie-api/mcp`
- OpenAPI spec available
- Python SDK available
- Google Sheets integration

### How It Solves Our Problem
Currently all 486 picks are SELF_EDGE because SDIO, SerpAPI, and Odds API are all down.
BALLDONTLIE at $9.99/mo gives us real market lines for WNBA and MLB player props,
plus WC betting odds — replacing all 3 dead sources with one API.

---

## ALTERNATIVES

### 2. API-SPORTS (api-sports.io)
- 3 separate APIs: api-basketball, api-baseball, api-football
- Free tier: 100 req/day each (300 total/day across sports)
- Pro: $19/mo each sport
- Con: Must manage 3 separate API keys. No player props — game odds only.
- World Cup: api-football covers FIFA World Cup 2026 ✅

### 3. The Odds API (the-odds-api.com)  
- Free tier: 500 req/month — too low for daily pipeline
- Pro: starts at ~$100/mo
- Con: Already had Business tier quota exhausted previously

### 4. football-data.org
- Free forever: 12 major European leagues only
- Con: Soccer only, European leagues only — no World Cup, no WNBA, no MLB

### 5. TheStatsAPI
- $50/mo: 150 competitions, xG, odds
- Con: Soccer only, no WNBA/MLB

---

## RECOMMENDATION

**BALLDONTLIE All-Star ($9.99/mo)** — one API key, covers WNBA + MLB + WC,
has player prop lines we need for TC picks, clean OpenAPI docs, MCP server ready,
and at $10/mo it's cheaper than any combination of alternatives.

Next step: Sign up at balldontlie.io → get API key → wire into TC pipeline
(update `daily_picks.py` to use BALLDONTLIE as line source, replacing SDIO + SerpAPI).
