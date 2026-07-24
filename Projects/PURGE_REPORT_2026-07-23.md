# Projects/ Purge Report — 2026-07-23

## Summary

| Metric | Before | After |
|--------|--------|-------|
| Total files | ~160+ | 67 |
| Python files | ~91 | 37 |
| Subdirectories | 20 | 3 |
| Disk space (Projects/) | ~140MB | ~5MB |
| Archived size | — | 129MB |

## Archive Location

`/home/workspace/Archives/purge_2026-07-23/`

## What Was Purged

### 1. Scraper Directories (moved to archive)
- `espn_scraper/` — old ESPN scraper with .git history
- `oddsScraper/` — 80MB+ CSV history files (NBA/MLB/NHL prop data 2020-2023) + geckodriver
- `DKscraPy/` — stale DraftKings scraper

### 2. Stale Python Files (80 files moved to archive)
- **Duplicates:** `gen_wnba_proj.py`, `generate_wnba_pregame.py`, `generate_wnba_projections.py` (kept: `gen_wnba_today.py` + `generate_projections.py`)
- **Legacy engines:** `tc_math_hybrid.py`, `true_signals_engine.py`, `build_self_edge_combos.py`, `dk_combos_engine.py`
- **Stale scrapers:** `espn_odds_scraper.py`, `sportsbook_scraper.py`, `odds_scraper_base.py`
- **One-offs:** `build_investor_deck.py`, `run_backtest.py`, `run_backtest_0719.py`, `comprehensive_backtest_scan.py`
- **Replaced modules:** `api_cache.py`, `api_call_manager.py`, `api_fallback.py` (replaced by `src/api_cap_tracker.py`)
- **Dead integrations:** `serp_api_tracker.py` (SerpAPI maxed), `github_line_sources.py`, `enrich_from_github_sources.py`
- **Old utilities:** `db_writer.py`, `boxscore_saver.py`, `market_catalog.py`, `sports_registry.py`, `team_game_mapper.py`
- **Stale reporting:** `generate_email_report.py`, `grade_daily_picks.py`, `populate_graded.py`
- **World Cup remnants:** `wc_team_lookup.py`, `wc_country_codes.json`, World Cup adapter
- **Symlink stubs:** `line_fetcher.py`, `fantasy_combo_generator.py` (broken symlinks)
- **And:** `apply_recalibration.py`, `build_pregame_combos.py`, `espn_enrichment.py`, `fantasy_images.py`, `runtime_health_check.py`, `wnba_combo_stats.py`, `pipeline_output.json`, `repair_report.json`, `algorithm_weights.json`, `health_status.json`

### 3. Stale Subdirectories (moved to archive)
- `stagger/` — old node server
- `pipeline/` — backtest scripts
- `scripts/` — old shell scripts
- `cron/` — old cron definitions
- `config/` — stale configs
- `tests/` — stale test files
- `sizing/` — broken symlinks
- `backtesting/` — broken symlinks
- `utils/` — old capped utils
- `automations/` — empty directory
- All `__pycache__/` (recursive)

### 4. Large Data Cleanup
- `data/api_cache/` — old API cache files (~1MB)
- `data/cache/` — old cached responses
- `data/tc_pipeline.db` — old database (1.1MB)
- `data/odds/` — stale odds CSV

## What Survived — Active Pipeline

### Core Pipeline (root)
| File | Purpose |
|------|---------|
| `daily_picks.py` | Daily orchestrator — all sports, cap-aware |
| `generate_projections.py` | TC Math projection engine |
| `gen_wnba_today.py` | WNBA daily generator |
| `backfill_projections.py` | Historical backfill tool |
| `tc_math.py` | Core TC Math engine |
| `tc_sports_dashboard.py` | Main Streamlit dashboard (port :8510) |
| `real_time_streamer.py` | Live data feed (port :8001) |
| `combo_generator.py` | Parlay combo builder |
| `clean_picks.py` | Data quality maintenance |

### Utilities (root)
| File | Purpose |
|------|---------|
| `mlb_team_lookup.py` | MLB team name resolution |
| `wnba_team_lookup.py` | WNBA team name resolution |

### API Layer (`api/`)
| File | Purpose |
|------|---------|
| `main.py` | FastAPI (port :8000) — /health, /picks, /combos, /alerts |
| `live_boxscore.py` | ESPN box score fetcher with cap enforcement |
| `docs.py` | API documentation |
| `picks_endpoint.py` | Picks endpoint helper |
| `site_boxscore.py` | Site-specific box scores |
| `routes/` | Route definitions |

### Source Layer (`src/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `api_cap_tracker.py` | API call cap enforcement |
| `core_math_engine.py` | Core math calculations |
| `daily_pipeline_health.py` | Pipeline health monitor |
| `enhancer.py` | Model enhancer |
| `explanation_engine.py` | Rationale generator |
| `measure.py` | Performance measurement |
| `monitoring.py` | Pipeline monitoring |
| `roster_loader.py` | Player roster loader |
| `tc_math.py` | TC math utilities |

### Adapters (`src/adapters/`)
23 API/source adapters:
- `espn.py`, `espn_enricher.py`, `espn_odds_fetcher.py`
- `free_api_aggregator.py`
- `sdio_adapter.py`, `odds_api_adapter.py`
- `nba_api_adapter.py`, `wnba_api_adapter.py`
- `mlb_api_adapter.py`, `mlb_book_fetcher.py`, `mlb_pipeline.py`
- `nfl_api_adapter.py`, `world_cup_adapter.py`
- `cache_adapter.py`, `live_grader.py`, `live_grading.py`
- `schedule_fetcher.py`, `sgo.py`
- `wnba_data_fetcher.py`, `line_fetcher.py`, `fantasy_combo_generator.py`

### Config & Infra
- `config/weight_applicator.py` — model weight config
- `src/fetchers/` — early lines, smart fetcher
- `src/pipelines/mlb_integration.py`
- `src/scheduler/priority_scheduler.py`

### Data (`data/`)
- `picks.db` — SQLite picks database (84 picks, 65KB)
- `betting_history.db` — historical bets
- `bets.json` — bet configuration
- `picks/` — picks CSVs by date
- `picks_2026-07-18.csv` — recent picks export
- `picks_report_2026-07-18.md` — recent report

### Infrastructure Files
- `.env.template`, `.gitignore`, `Dockerfile`, `docker-compose.yml`
- `requirements.txt`, `tc-sports-cron`
- `ARCHITECTURE_BLUEPRINT.md`, `README.md`, `gaps.md`
- `api_research.md`, `github_api_checklist.md`
- `deploy.sh`, `setup.sh`, `maintenance.sh`
- `check_quota.sh`, `verify_all.sh`

## Preserved Externals (not in Projects/)
Rosters remain at `/home/workspace/data/rosters/`:
- `mlb_rosters.json` — 30 teams, ~780 players
- `wnba_rosters.json` — 15 teams, 12-player rosters
- `nba_rosters.json`, `nfl_rosters.json`

Daily logs remain at `/home/workspace/Daily_Log/`.

## Cleanup Summary
- **3 scraper directories** → archived
- **~80 Python files** → archived (duplicates, stubs, one-offs, replaced modules)
- **9 stale subdirectories** → archived
- **All `__pycache__`** → deleted
- **Broken symlinks** → deleted
- **Empty directories** → removed
- **0 active pipeline files touched**
- **0 data files lost**

All archived files available at: `/home/workspace/Archives/purge_2026-07-23/` (129MB)
Everything there can be fully restored with `cp -r`.
