# TC Sports App

Multi-sport analytics pipeline for MLB, WNBA, World Cup, NFL, NHL, NCAA.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export ODDS_API_KEY=your_toa_live_key

# 3. Run dashboard
streamlit run tc_dashboard.py

# 4. Run daily picks (cron job)
python daily_picks.py --sport all
```

## Sanity Checks

```bash
python -c "from src.domain.entities import REGISTRY; print('✅ Registry loaded')"
python -c "from src.adapters.odds_api_adapter import OddsAPIAdapter; print('✅ Odds API adapter loaded')"
```

## Project Structure

```
tc-sports-app/
├── tc_dashboard.py          # Main Streamlit app
├── daily_picks.py           # Measurement / cron job
├── requirements.txt
├── README.md
├── src/
│   ├── domain/
│   │   └── entities.py      # SportConfig + Registry
│   └── adapters/
│       ├── odds_api_adapter.py
│       ├── cache_adapter.py
│       └── fantasy_combo_generator.py
├── logs/
│   └── app.log
└── data/
    └── cache/               # Auto-created
```

## Cron

```bash
# Every hour at minute 13, 26, 39, 52
13,26,39,52 * * * * cd /home/workdir/artifacts/tc-sports-app && python daily_picks.py --sport all >> logs/cron.log 2>&1
```
