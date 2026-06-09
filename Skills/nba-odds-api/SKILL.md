---
name: nba-odds-api
description: >
  Connects to The Odds API to fetch live NBA game lines, spreads, totals, and
  player prop odds from multiple sportsbooks (DraftKings, FanDuel, etc.).
  Used to power the Triple Conservative (TC) betting system.
  Activate when the user wants live odds, odds scraping, or automated betting picks.
compatibility: Created for Zo Computer
metadata:
  author: true.zo.computer
allowed-tools: Bash, Read, Write
---
# NBA Odds API Skill

## What it does
Fetches real-time NBA odds from **The Odds API** (v4) and processes them through the
Triple Conservative (TC) pipeline to generate edge-qualified picks.

## Setup

### 1. Get your API key
1. Sign up at https://the-odds-api.com/account/
2. Copy your API key (starts with `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
3. Save it in Zo → [Settings > Advanced](/?t=settings&s=advanced) as secret `ODDS_API_KEY`

### 2. Install dependencies
```bash
cd /home/workspace/Skills/nba-odds-api/scripts
pip install -r requirements.txt
```

## Usage

### Fetch live NBA odds
```bash
cd /home/workspace/Skills/nba-odds-api/scripts
python odds_fetcher.py --sport basketball_nba --regions us --markets h2h,spreads,totals
```

### Fetch player prop odds
```bash
python odds_fetcher.py --sport basketball_nba --markets player_points
```

### Run full TC pipeline (fetch → process → generate picks)
```bash
python odds_fetcher.py --mode tc --date 2026-04-27
```

## Key endpoints used

| Endpoint | Purpose |
|---|---|
| `GET /v4/sports/{sport}/odds` | Get odds for all upcoming games |
| `GET /v4/sports/{sport}/events/{id}/odds` | Get odds for specific game |
| `GET /v4/sports` | List available sports |

## Bookmakers included
DraftKings, FanDuel, BetMGM, Caesars, Pinnacle (Sharp)

## Output files
- `~/.zo/odds/live_odds.json` — raw odds data
- `~/.zo/odds/(tc_picks_YYYY-MM-DD).md` — TC-processed picks report

## TC Integration
The script reads player stats from `STATS` dict in `triple_conservative_v5.py` and
applies TC formulas (0.85× player pts, 0.88× team totals) to derive projections.
Valid picks require edge ≥ 2 pts (legs) or ≥ 3 pts (props).

## Rate limits
- Free tier: 500 requests/month, 1 request/sec
- Paid plans: higher limits — see https://the-odds-api.com/account/

## Market codes
- `h2h` = Moneyline
- `spreads` = Point spread
- `totals` = Over/Under totals
- `player_points` = Player props (points)
- `player_rebounds` = Player props (rebounds)
- `player_assists` = Player props (assists)

## Enricher (new)
- `scripts/odds_enricher.py` — two-step player prop injector for daily_picks.py
  - Step 1: fetch sports-wide odds (h2h,spreads,totals) to get game IDs
  - Step 2: fetch event-specific odds (player_points, player_rebounds, player_assists)
  - Returns game odds + per-player PTS/REB/AST lines from DK
  
## Key status
- `ODDS_API_KEY` (`0ba199e...`) — ✅ working for NBA + WNBA, 5 bo