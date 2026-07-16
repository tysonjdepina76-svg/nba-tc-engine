# TC Sports App

Full-stack +EV betting pipeline powered by Triple Conservative math engine, TheOddsAPI line fetching, and DeepSeek reasoning enhancement.

## Structure

```
tc-sports-app/
├── tc_dashboard.py          # Streamlit investor dashboard (:8510)
├── daily_picks.py           # Pick generation CLI (--sport wnba|mlb|wc|all)
├── runtime_health_check.py  # System health validation
├── src/
│   ├── core_math_engine.py  # TC edge calculator
│   ├── adapters/
│   │   ├── line_fetcher.py      # TheOddsAPI integration
│   │   ├── deepseek_enhancer.py # DeepSeek reasoning
│   │   ├── fantasy_images.py    # Team logos (re-exports from domain)
│   │   ├── oddsapi/             # Per-sport Odds API adapters
│   │   ├── sportsdataio/        # SportsDataIO adapters
│   │   └── sportsgameodds/      # SportsGameOdds adapters
│   ├── domain/
│   │   ├── projection_service.py # Unified projection engine
│   │   ├── combo_optimizer.py    # Multi-leg combo builder
│   │   ├── roster_manager.py     # Roster scraping + validation
│   │   ├── fantasy_images.py     # Team logo + player image generator
│   │   └── entities.py           # Core domain objects
│   ├── api/
│   │   └── app.py                # FastAPI server
│   ├── services/                 # Event triggers, parlay builder
│   ├── monitoring/               # API budget, odds monitor
│   └── utils/
│       └── logging.py            # Centralized logging
├── data/
│   ├── picks/                    # Daily pick CSVs
│   └── cache/                    # Odds API response cache
├── logs/                         # Runtime logs
├── backups/                      # Database backups
├── docs/                         # Documentation
├── models/                       # ML model files
└── tests/                        # Test suite
```

## Quick Start

```bash
pip install -r requirements.txt
python runtime_health_check.py
docker compose up -d
```

Dashboard: http://localhost:8510

## API Endpoints

- `GET /api/picks/top` — Top-ranked picks
- `GET /api/stats/dashboard` — Performance dashboard
- `GET /api/stats/recap` — Yesterday's graded recap
- `GET /projections/{sport}` — Raw projections

## Environment Variables

| Variable          | Description                |
|-------------------|----------------------------|
| `THEODDSAPI`      | TheOddsAPI key             |
| `DEEPSEEK_API_KEY`| DeepSeek API key           |
| `SGO_API_KEY`     | SportsGameOdds API key     |
| `DB_HOST`         | PostgreSQL host            |
| `DB_NAME`         | PostgreSQL database name   |
| `DB_USER`         | PostgreSQL user            |
| `DB_PASSWORD`     | PostgreSQL password        |
