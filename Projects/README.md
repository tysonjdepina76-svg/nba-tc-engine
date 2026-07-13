# TC Sports App

Multi-sport projection + betting edge pipeline. WNBA, MLB, World Cup live + projected props with TC engine.

## Status (2026-07-13)

- 47/52 manifest files present on disk
- Health check: 3/7 OK, 1 error (wnba_tc_engine module missing), 3 off-season
- Streamlit dashboard on port 8510
- API keys: currently UNCAPPED

## Structure

```
Projects/
├── config/                  # Sport stat configs + team abbreviations
├── sources/                 # Data fetchers, TC engines, scrapers
│   ├── utils/               # cache, logging, monitor, bet_tracker, redis_cache
│   └── scrapers/            # baseball/basketball references, soccer fbref
├── dashboard/               # Streamlit UI
│   └── components/          # tables, charts, advanced_charts
├── pipeline/                # daily_picks.py
├── tests/                   # test_gaps.py
├── api/                     # FastAPI (main.py missing)
├── database/                # schema.sql (missing)
├── scripts/                 # deploy.sh, health_check.sh, backup.sh
├── data/                    # local JSON/SQLite state
└── logs/                    # daily logs
```

## Run

```bash
# Health check
python3 runtime_health_check.py

# Streamlit dashboard
streamlit run dashboard/tc_dashboard.py --server.port 8510

# Generate daily picks (per-sport)
python3 pipeline/daily_picks.py --sport WNBA
python3 pipeline/daily_picks.py --sport MLB
python3 pipeline/daily_picks.py --sport WORLD_CUP

# Tests
python3 -m pytest tests/ -v
```

## Sports

- **WNBA** — TC engine (project_game stub until wnba_tc_engine.py is provided)
- **MLB** — Book lines + live summary
- **World Cup / Soccer** — Book lines + fbref roster + live summary
- **NHL / NCAA** — engines present, off-season / unofficial
- **NBA / NFL** — disabled (off-season)

## See also

- `MISSING_FILES_TODO.md` — list of 13 files not yet on disk
