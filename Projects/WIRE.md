# TC Pipeline — Wire Map

How all the pieces connect. Read this first when something breaks.

## Daily run (cron 4:00 AM)

```
setup_cron.py
  └─ installs crontab entries:
       4:00 AM  → python3 /home/workspace/Projects/daily_picks.py --date today
       4:30 AM  → python3 /home/workspace/Projects/backup.py
```

## Pick generation flow

```
daily_picks.py
  ├─ argparse --sport {wnba,mlb,wc,all}
  ├─ for each sport: tc_math_hybrid.determine_pick(...)
  │     ├─ uses SPORT_CONFIGS[ sport ] (min_edge, shrinkage, correction_factors)
  │     ├─ reads config/algorithm_weights.json for ensemble weights
  │     ├─ optionally calls sources/wnba_tc_engine.py (full WNBA projection)
  │     └─ returns {direction, edge, prob_over, signal}
  ├─ writes data/picks/<sport>_<YYYY-MM-DD>.{csv,json}
  └─ writes Daily_Log/<YYYY-MM-DD>/proj_<sport>_<matchup>.json
```

## Data sources

| Source | Endpoint | Status | Used by |
|--------|----------|--------|---------|
| ESPN scoreboard | site.api.espn.com/.../scoreboard | ✅ live | daily_picks, sources/player_stats_scraper |
| ESPN summary   | site.api.espn.com/.../summary?event=... | ✅ live | boxscore_saver, run_settlement |
| Odds API       | api.the-odds-api.com/v4 | ⚠️ 401 (quota maxed) | sources/odds_api_client, sources/odds_api_adapter |
| OddsHarvester  | github.com/.../oddsharvester | ❌ disabled | sources/oddsharvester_adapter |
| Snuper         | snuper.com | ❌ disabled | sources/snuper_adapter |
| DK combos      | sportsbook.draftkings.com | ⚠️ paused | dk_combos_engine |

**Workaround for Odds API 401:** fall back to self-edge TC projections
(no DK/BetMGM lines). Documented in `data/picks/*_notes.md`.

## Settlement flow (next morning)

```
run_settlement.py --sport all
  ├─ reads data/picks/<sport>_<date>.{csv,json}
  ├─ reads data/backtest/<sport>/boxscore_<date>.json (from boxscore_saver)
  ├─ grades each pick: hit / miss / push / no_data
  ├─ writes data/picks/settled_<sport>_<date>.json
  └─ appends summary line to logs/daily.log
```

## Dashboard (port 8510)

```
streamlit_app.py
  ├─ reads data/picks/settled_*.json (last 30 days)
  ├─ reads logs/daily.log (summary trends)
  └─ shows hit rate by sport / stat / direction
```

## Health checks (cron 3:00 AM)

```
health_check.py / runtime_health_check.py
  ├─ ping localhost:8510
  ├─ list_automations count
  ├─ check Odds API quota (logs/quota_state.json)
  └─ write logs/health/health_<timestamp>.json
```

## Modules (sources/)

| Module | Purpose |
|--------|---------|
| `tc_math_hybrid.py` | Core math: shrinkage, signals, ensemble |
| `tc_math_wrapper.py` | Shim that prefers TCHybridMath, falls back to TCMath |
| `bayesian_shrinkage.py` | Bayesian pull toward league avg (n_games) |
| `monte_carlo.py` | Sim N games, return mean/std |
| `ensemble_model.py` | Weighted blend of TC + XGBoost + RF + LR |
| `opponent_adjustment.py` | Multiply projection by opponent rank factor |
| `nfl_position_groups.py` | Stat → position map for NFL props |
| `player_stats_scraper.py` | Multi-source player box score pull |
| `wnba_tc_engine.py` | Full WNBA projection model (real) |
| `mlb_tc_engine.py` | MLB projection (uses tc_math_wrapper) |
| `nba_tc_engine.py` | NBA projection (uses tc_math_wrapper) |
| `nhl_tc_engine.py` | NHL projection (uses tc_math_wrapper) |
| `soccer_tc_engine.py` | Soccer/World Cup projection |
| `line_fetcher.py` | Central dispatcher to per-sport fetchers |
| `cache_adapter.py` | JSON disk cache wrapper |
| `espn_odds_fetcher.py` / `espn_odds_adapter.py` | ESPN odds adapter |
| `odds_api_client.py` / `odds_api_adapter.py` | Odds API client |
| `snuper_adapter.py`, `oddsharvester_adapter.py` | Disabled adapters |
| `unified_scraper.py` | Cross-sport scrape entry point |
| `consensus_engine.py` | Multi-source line consensus |
| `tc_dashboard.py` | Streamlit dashboard logic |
| `performance_dashboard.py` | Hit-rate + ROI metrics |

## Top-level scripts

| Script | Purpose |
|--------|---------|
| `daily_picks.py` | Daily pick generator (cron 4 AM) |
| `run_settlement.py` | Grade yesterday's picks (cron 5 AM) |
| `orchestrator.py` | End-to-end pipeline runner |
| `scan.py` | Quick health scan |
| `fix_pipeline.py` | Auto-fix common pipeline issues |
| `streamlit_app.py` | Dashboard entrypoint |
| `health_check.py` | Module-level health probe |
| `runtime_health_check.py` | Live system health probe |
| `setup_cron.py` | Install cron schedule |
| `backup.py` | Copy Daily_Log to timestamped backup |
| `verify_picks.py` | Validate today's picks file exists |
| `generate_todays_picks.py` | Wrapper around daily_picks.py |
| `fix_mlb.py` | One-off MLB fix helper |
| `build_pregame_combos.py` | Build DK pregame parlay combos |
| `dk_combos_engine.py` | DK combos engine |
| `combo_builder.py` | Generic combo builder |
| `seed_test_bets.py` | Seed test data |
| `boxscore_saver.py` | Save ESPN final boxscores |
| `boxscore_backfill.py` | Backfill missing boxscores |
| `wc_tc_engine.py` | World Cup TC engine |
| `wc_tc_math.py` | WC math adjustments |
| `wc_tc_calibrate.py` | WC calibration |

## Data layout

```
data/
├── picks/                    # CSV + JSON of daily picks, settled picks
├── backtest/                 # Final boxscores for backtesting
├── historical/               # Long-term historical stats (DB)
├── bets.json                 # Open positions
└── betting_history.db        # SQLite bet log
```

```
logs/
├── daily.log                 # Settlement summary (TSV, appended)
├── api.log                   # API call log (TSV, appended)
├── cron.log                  # Cron job run log
├── dashboard.log             # Streamlit dashboard log
├── health/                   # Health check JSON snapshots
└── quota_state.json          # Odds API quota tracker
```

```
config/
├── sports.yml                # Per-sport enabled / season / odds_key
├── algorithm_weights.json    # Ensemble weights per sport+stat
├── columns.py                # DataFrame column definitions
└── teams.py                  # Team name normalization
```

## Where to start when something breaks

1. **`logs/api.log`** — first place to check, latest API calls + status
2. **`logs/daily.log`** — see if settlement is actually running
3. **`logs/quota_state.json`** — if Odds API calls are 401'ing
4. **`/health` route on port 8510** — live dashboard
5. **`runtime_health_check.py`** — single-shot diagnostic
6. **`fix_pipeline.py`** — last resort auto-fix
