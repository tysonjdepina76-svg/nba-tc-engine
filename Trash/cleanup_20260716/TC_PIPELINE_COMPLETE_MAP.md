# TC Sports Pipeline — Complete Map (2026-07-16 2PM ET)

## PROJECTS — 4 LAYERS

### 1. Production Core: `Projects/`
| File | Status | Purpose |
|---|---|---|
| `orchestrator.py` | ⚠️ NOT RUN TODAY | End-to-end daily workflow (projections → picks → log) |
| `pipeline_master.py` | ⚠️ NOT RUN TODAY | Self-healing daily runner |
| `daily_picks.py` | ✅ Running but 0 picks | Needs proj_*.json files from orchestrator |
| `sources/` (62 files) | ✅ Present | WNBA/MLB/WC/NBA/NCAA TC engines, fetchers, live scrapers |
| `.env` | ✅ CAPPED | All API keys intentionally empty |

### 2. Dashboard & API: `sports_betting_dashboard/`
| Service | Status | Port |
|---|---|---|
| Streamlit dashboard | ✅ UP | :8510 |
| FastAPI picks API | ❌ DOWN | :8000 (no process running) |
| DK Combos Engine | ❌ DOWN | :8515 |
| Soccer Combo Engine | ❌ DOWN | :8516 |
| MLB Cross Dashboard | ❌ DOWN | paused |

### 3. Docker/ML Stack: `tc-sports-app/`
| Service | Status |
|---|---|
| docker-compose.yml | ❌ DOCKER NOT RUNNING |
| Postgres | ❌ OFFLINE |
| Redis | ❌ OFFLINE |
| ML training pipeline | ❌ OFFLINE |

### 4. Enhanced Pipeline (NOT YET DEPLOYED): `tc_engine_deployment/`
| File | Purpose |
|---|---|
| `final_gap_closer.py` | Orchestrator — creates all engine files |
| `push_ready_deploy.py` | Generates full tc-sports-app scaffold |
| `bookmaker_blueprint.py` | Bayesian opening lines + risk engine + live adjustment |
| `engine/api_server.py` | FastAPI + endpoints |
| `engine/live_engine.py` | Real-time truth engine |
| `engine/train_with_shap.py` | XGBoost + SHAP |
| `engine/backtest.py` | ML vs heuristic comparison |
| `engine/models.py` | SQLAlchemy models |
| `engine/telegram_bot.py` | Telegram alerts |
| `engine/ml_dashboard.py` | Streamlit ML monitoring |
| `scripts/export_training_data.py` | DB → CSV export |
| `migrations/` | Alembic (adds features + actual_value) |
| `docker-compose.yml` | 6-service stack (Postgres, API, engine, stagger, telegram, dashboard) |

### 5. Zo.Space Routes
| Route | Status |
|---|---|
| `/` (homepage) | ✅ Live |
| `/nba-tc` (slate dashboard) | ✅ Live |
| `/api/tc` (projections API) | ✅ Live |

## 5 GAPS — ROOT CAUSES

1. **No projections for 7/16** → `orchestrator.py` or `pipeline_master.py` didn't run. Without `proj_WNBA_*.json` / `proj_MLB_*.json`, daily_picks has nothing to grade.

2. **FastAPI :8000 down** → No process running. Dashboard makes API calls to localhost:8000 that fail.

3. **Docker not running** → tc-sports-app's docker-compose stack (Postgres, Redis, ML pipeline) is offline.

4. **DK Combos :8515 + Soccer :8516 down** → Processes not running. Odds API quota maxed anyway.

5. **Enhanced pipeline isolated** → All 23 files in `tc_engine_deployment/` but not wired into the production pipeline.

## ACTION PLAN (ordered)

1. Run `orchestrator.py` to generate today's projection files
2. Run `daily_picks.py --sport wnba && --sport mlb` with projections present
3. Start FastAPI on :8000 (or integrate enhanced api_server.py)
4. Integrate enhanced engine into production pipeline
5. Launch Docker stack (Postgres + ML)
6. Wire live scrape enhancements
