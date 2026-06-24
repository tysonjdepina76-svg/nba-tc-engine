# Sports Betting Pipeline

TC (Triple Conservative) sports betting system. WNBA / MLB / World Cup props with DK-derived edges.

## Quick Start

```bash
# Generate today's picks
python3 Projects/daily_picks.py WNBA MLB 'WORLD CUP'

# Run health scan
bash sports_betting_dashboard/scan.sh

# Fix common issues
python3 sports_betting_dashboard/fix_pipeline.py
```

## Architecture

```
sports_betting_dashboard/
├── picks.py                 → daily_picks.py (Projects/)
├── dashboard.py             → Streamlit UI (Projects/)
├── scan.sh                  # Health scan — check every subsystem
├── fix_pipeline.py          # Auto-repair broken states
├── setup.sh                 # One-time install
├── .env                     # API keys (gitignored)
├── README.md                # This file
├── data/
│   ├── picks.csv            # Today's ranked picks (from picks.json)
│   └── historical.csv       # Backtest archive (graded picks)
├── logs/
│   ├── daily.log            # Daily routine summary
│   └── scan_YYYYMMDD.txt    # Daily scan reports
├── models/
│   └── algorithm_weights.json  # Ensemble weights per sport
└── scripts/
    ├── generate.sh          # Generate picks for today
    ├── start.sh             # Start Streamlit + services
    └── stop.sh              # Stop services
```

## API Routes (Zo.Space)

| Route | Purpose |
|---|---|
| `/api/tc` | Projections — `?sport=WNBA&away=NY&home=LV` |
| `/api/slate` | Today's games across all sports |
| `/api/backtest` | Hit-rate data — `?days=7` |
| `/api/scan` | Health check — all subsystems |
| `/api/daily-log` | Daily picks — `?days=3` |
| `/api/combos` | DK combos |
| `/api/dk-lines` | DK lines — `?sport=WNBA` |
| `/api/combo-prob` | Combo hit probabilities |
| `/api/pipeline-health` | Deep health diagnostics |

## Key Files

```
/home/workspace/
├── Projects/
│   ├── daily_picks.py          # Core engine — generates all projections
│   ├── consensus_engine.py     # Consensus picks
│   ├── api_tc_unified.py       # Python handler for /api/tc
│   ├── mlb_tc_engine.py        # MLB projections
│   ├── wnba_pipeline_v2.py     # WNBA pipeline
│   ├── worldcup_picks.py       # World Cup picks
│   └── build_pregame_combos.py # Combo builder
├── Daily_Log/
│   ├── last_run.json           # Most recent pipeline run
│   ├── YYYY-MM-DD/
│   │   ├── picks.json          # All picks for that day
│   │   ├── proj_*.json         # Per-game projections
│   │   └── summaries.json      # Graded results
│   └── backtests/              # Historical backtest CSVs
└── sports_betting_dashboard/   # This folder
```

## Environment

Set these in [Settings → Advanced](/?t=settings&s=advanced) → Secrets:

```
ODDS_API_KEY=...            # The Odds API key
SPORTSGAMEODDS_API_KEY=...  # SportsGameOdds API key
SPORTS_DATA_API_KEY=...     # SportsData.io key (NFL)
```

## Dashboard

- Local: http://localhost:8510
- Zo.Space: https://true.zo.space/nba-tc
- API: https://true.zo.space/api/tc?sport=WNBA&away=NY&home=LV
