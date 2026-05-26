# NBA TC MODULE

## Overview
The NBA TC module handles Triple Conservative projections for NBA games.

## Files
- `nba/scraper.py` — Live ESPN scraper
- `nba/engine.py` — TC calculation engine
- `nba/backtest.py` — Backtest suite
- `nba/rosters.py` — Roster data
- `nba/odds.py` — API odds fetcher

## Usage
```bash
python sports_tc.py --sport NBA --game "NYK @ PHI"
python sports_tc.py --sport NBA --list
python sports_tc.py --sport NBA --dashboard
```

## TC Formula
- TC = stat × 0.85
- Questionable = stat × 0.55
- OUT = 0

## Output
- Player projections: PTS, REB, AST, 3PM
- Team totals
- ATS picks
- Parlay legs