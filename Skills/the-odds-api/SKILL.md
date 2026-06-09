---
name: the-odds-api
description: >-
  Connects to The Odds API ($30/mo plan) to fetch live NBA/WNBA game lines,
  spreads, totals, and player prop odds from DraftKings. Also provides historical
  closing lines for backtesting.
  Activate when the user wants live odds, player props, or historical line data.
compatibility: Created for Zo Computer
metadata:
  author: true.zo.computer
---

# The Odds API

## Status
✅ **Connected** — key `ODDS_API_KEY` loaded from `/root/.zo/secrets.env`
✅ **Plan**: $30/mo (20K requests, historical access, player props on per-game endpoint)
✅ **Live test**: 6 WNBA games with DK lines confirmed at 2026-06-09

## Usage
- Live odds: `GET /v4/sports/basketball_nba/odds` (or `basketball_wnba`)
- Player props (per-game): `GET /v4/sports/{sport}/events/{id}/odds?markets=player_points,...`
- Historical: `GET /v4/historical/sports/{sport}/odds?date=...`

## Pipeline integration
- `/api/tc` calls this as Tier 3 fallback (after SGO → ESPN DK)
- `daily_picks.py` calls `enrich_player_lines()` from `Skills/nba-odds-api/scripts/odds_enricher.py`
- Historical backtest: `Projects/historical_odds_backtest.py`

## Key files
- `Skills/nba-odds-api/scripts/odds_enricher.py` — live player prop enricher
- `Projects/historical_odds_backtest.py` — cross-reference TC vs closing lines
