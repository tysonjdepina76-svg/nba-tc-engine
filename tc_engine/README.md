# TC Engine — Triple Conservative Sports Betting Pipeline

**Production-grade sports analytics and edge detection platform.**

## Architecture

```
tc_engine/
├── engine/          # Core intelligence — picks, ML, arbitrage, backtest
├── stagger/         # FastAPI REST API + scheduler
├── dashboard/       # Streamlit UI with SHAP/PDP explainability
├── tests/           # 47-test suite, all passing
├── models/          # Trained .pkl model artifacts
├── plots/           # Generated SHAP/PDP/ICE HTML plots
├── migrations/      # Alembic Postgres schema migrations
└── .github/         # CI/CD — test on PR, deploy on main
```

## Pipeline Flow

1. **Data Ingestion** — TheOddsAPI + SportRadar via `engine/daily_picks.py`
2. **Intelligence Layer** — `PredictiveEngine` (hybrid ML+rule) + `HistoricalTracker` (H2H/form/rest) + `MLPredictor` (Random Forest with Platt calibration)
3. **Arbitrage Detection** — `ArbitrageFinder` scans cross-book lines for +EV opportunities
4. **Delivery** — FastAPI (`stagger/main.py`) + Streamlit dashboard (`dashboard/tc_dashboard.py`)
5. **Explainability** — SHAP summaries, PDP, ICE plots via `engine/generate_explainability_plots.py`

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run tests
PYTHONPATH=. pytest tests/ -v

# Start API
uvicorn stagger.main:app --host 0.0.0.0 --port 8000 --reload

# Start dashboard
streamlit run dashboard/tc_dashboard.py --server.port 8510

# Generate picks
python engine/daily_picks.py --sport all
```

## Docker

```bash
docker-compose up -d
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API health + version |
| GET | `/api/v1/system/health` | Full system health check |
| GET | `/api/picks/top?limit=20` | Top +EV picks |
| GET | `/api/accuracy-data` | Graded pick hit rates by sport |
| GET | `/api/system-data` | System metrics + live games |
| GET | `/api/live-dashboard?sport=all` | Live game scores + player stats |
| GET | `/api/tc-alerts` | TC edge alerts |
| GET | `/api/injuries?sport=all` | Injury report |
| GET | `/api/v1/lines/{sport}` | Current lines per sport |
| GET | `/api/projection/{sport}?player=X` | Single player projection |

## Supported Sports

- **MLB** — via SportsDataIO DK lines
- **WNBA** — via TheOddsAPI + ESPN injury scraping
- **World Cup** — self-edge TC projections (Odds API Business quota maxed)

## Tests

```bash
PYTHONPATH=. pytest tests/ -v --cov=engine --cov=stagger
# 47 tests, all passing
```

## License

Proprietary — TC Engine. All rights reserved.
