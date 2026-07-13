# Sports Betting Pipeline

TC (Triple Conservative) sports betting system — WNBA / MLB / World Cup props.

## Quick Start

```bash
# Generate today's picks (lowercase sport names required)
python3 Projects/daily_picks.py --sport wnba
python3 Projects/daily_picks.py --sport mlb
python3 Projects/daily_picks.py --sport wc

# Run health scan
bash sports_betting_dashboard/scan.sh

# Fix common issues
python3 sports_betting_dashboard/fix_pipeline.py

# View picks
cat sports_betting_dashboard/data/picks/actionable_picks.csv
```

## File Layout

```
sports_betting_dashboard/
├── picks.py                     # Shell — real engine is Projects/daily_picks.py
├── dashboard.py                 # Streamlit UI (:8510)
├── fix_pipeline.py              # Auto-repair (--sport wnba/mlb/wc)
├── scan.sh                      # Health scanner v2.1
├── setup.sh                     # One-time setup
├── README.md                    # This file
├── WIRE.md                      # Architecture spec
├── PIPELINE_ASSESSMENT_*.md     # Latest line-by-line audit
│
├── config/
│   ├── algorithm_weights.json   # Ensemble weights (single source)
│   ├── thresholds.json          # Edge thresholds per sport
│   ├── sports.json              # Sport definitions
│   └── parlay_rules.json        # Parlay builder rules
│
├── data/
│   ├── historical.csv           # Combined backtest (1,161 rows)
│   ├── today.json               # Live slate
│   ├── events/                   # Cached event data
│   ├── odds/                     # Cached odds data
│   ├── props/                    # Live prop CSVs
│   ├── picks/
│   │   ├── today_picks.csv      # All projections (3,812 rows)
│   │   ├── clean_picks.csv      # Non-INVALID filtered (2,930 rows)
│   │   └── actionable_picks.csv # Positive-edge only (2,352 rows)
│   └── historical/
│       ├── wnba_historical.csv
│       ├── mlb_historical.csv
│       ├── world_cup_historical.csv
│       └── *_backtest.csv       # Per-sport backtest results
│
├── logs/
│   ├── daily.log
│   ├── api.log
│   └── scan_*.txt               # Historical scan outputs
│
└── scripts/
    ├── generate.sh              # Generate picks for all sports
    ├── daily.sh                 # Complete daily routine
    ├── start.sh                 # Start dashboard
    ├── stop.sh                  # Stop services
    ├── status.sh                # Quick health check
    └── odds_api_scraper.py      # API scraper utility
```

## Dashboard

- Local: http://localhost:8510
- Zo.Space: https://true.zo.space/nba-tc
- API: https://true.zo.space/api/tc?sport=WNBA&away=NY&home=LV

## API Keys

```
ODDS_API_KEY=...            # The Odds API key
SPORTSGAMEODDS_API_KEY=...  # SportsGameOdds API key
SPORTS_DATA_API_KEY=...     # SportsData.io key (NFL)
```
