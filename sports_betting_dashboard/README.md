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
├── picks.py                 → Projects/daily_picks.py (symlink)
├── dashboard.py             → Projects/tc_dashboard.py (symlink)
├── scan.sh                  # Health scan — check every subsystem
├── fix_pipeline.py          # Auto-repair broken states (+ API budget monitor)
├── setup.sh                 # One-time install
├── .env                     # API keys (gitignored — use Zo Secrets)
├── README.md                # This file
├── data/
│   ├── picks/
│   │   ├── today_picks.csv  # Synced daily from Daily_Log/YYYY-MM-DD/picks.csv
│   │   └── historical.csv   # Backtest archive (from backtests/)
│   ├── events/              # Live events by sport (WNBA, MLB, World Cup)
│   ├── odds/                # Live odds snapshots
│   ├── props/               # Live player props
│   ├── historical/          # Historical backtest data
│   ├── sports/              # Sport definitions
│   └── account/
│       └── status.json      # API call budget tracking
├── logs/
│   ├── daily.log            # Daily routine summary
│   ├── api.log              # API call log
│   └── scan_YYYYMMDD.txt    # Daily scan reports
├── models/
│   └── algorithm_weights.json  # Ensemble weights per sport
└── scripts/
    ├── daily.sh             # Daily runner — picks + sync + scan
    ├── status.sh            # Quick status overview
    ├── generate.sh          # Generate picks for today
    ├── start.sh             # Start Streamlit
    ├── stop.sh              # Stop services
    └── odds_api_scraper.py  # Odds API scraper (NBA off-season aware)
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

## API Call Budget

The free Odds API tier allows ~500 calls/month (~12/day). Budget is tracked in `data/account/status.json`:

```json
{
  "daily_calls": { "used": 0, "limit": 12, "reset": "2026-06-27" },
  "monthly_calls": { "used": 0, "limit": 500, "reset": "2026-07-01" }
}
```

**Automations respect this budget**: the 1:30 PM slate run is the PRIMARY consumer. The 6:30 PM run uses cache first. If budget >80% used, heavy calls are deferred to next reset.

## Off-Season Handling

- **NBA**: Off-season as of June 2026 — `basketball_nba.json` purged from events, SGO blocks with HTTP 503
- **NHL**: Off-season — skipped entirely
- **Active**: WNBA, MLB, World Cup (2026)

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
