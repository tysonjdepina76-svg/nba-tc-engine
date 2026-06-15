# SPORTS TC — PROJECT AGENTS.md

## Overview
`/home/workspace/sports_tc/` is the master directory for the NBA + WNBA Triple Conservative betting system.

## Directory Structure
```
sports_tc/
├── sports_tc.py          # MASTER ENGINE (NBA + WNBA unified)
├── AGENTS.md             # This file
├── nba/
│   ├── README.md
│   ├── scraper.py        # NBA live ESPN scraper
│   ├── engine.py         # NBA TC engine
│   ├── backtest.py       # NBA backtest suite
│   └── rosters.py        # NBA roster data
├── wnba/
│   ├── README.md
│   ├── scraper.py        # WNBA live ESPN scraper
│   ├── engine.py         # WNBA TC engine
│   ├── backtest.py       # WNBA backtest suite
│   └── rosters.py        # WNBA roster data (13 teams)
├── dashboard/
│   └── app.py            # Interactive dashboard app
├── archive/              # Archived outputs
├── docs/                 # Documentation
└── data/
    └── backtest_log.csv   # Backtest results
```

## How to Run

### Master Engine
```bash
python /home/workspace/sports_tc/sports_tc.py --sport NBA --game "NYK @ PHI"
python /home/workspace/sports_tc/sports_tc.py --sport WNBA --game "MIN @ DAL"
python /home/workspace/sports_tc/sports_tc.py --sport NBA --dashboard
python /home/workspace/sports_tc/sports_tc.py --sport WNBA --list
python /home/workspace/sports_tc/sports_tc.py --sport NBA --backtest
```

### Dashboard
```bash
python /home/workspace/sports_tc/dashboard/app.py
```

## TC Formula (same for NBA + WNBA)
- `TC = stat × 0.85`
- `Questionable = stat × 0.55`
- `OUT = 0`
- `Line = stat × 0.88`
- `Edge = TC − Line`

## TC Output (per player)
- TC_PTS — projected points
- TC_REB — projected rebounds
- TC_AST — projected assists
- TC_3PM — projected 3-point shots made

## Workflow
1. Pick sport (NBA or WNBA)
2. Select game from list
3. System scrapes live injury report from ESPN
4. System generates starting lineup (active players, best 5)
5. System runs TC projections for all players
6. System outputs: injury report → starting 5 → full roster projections
7. Picks: ATS + Parlay legs (NO O/U — prop bets only)

## API Key
- Stored in `~/.zo/secrets.env` as `ODDS_API_KEY`
- Used for live odds fetch

## Archive
- Output files are timestamped and moved to `sports_tc/archive/`
- Backtest logs go to `sports_tc/data/backtest_log.csv`