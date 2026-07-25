# TC Sports Intelligence

**Version:** 6.0.0
**Generated:** 2026-07-13T20:07:52.199287

## Overview
- 24 documented components
- 0 API endpoints
- Sports: MLB, WNBA, WC, NBA, NFL, NHL

## Quick Start
```bash
python3 /home/workspace/Projects/daily_picks.py --sport wnba
python3 /home/workspace/Projects/daily_picks.py --sport mlb
streamlit run /home/workspace/Projects/dashboard.py --server.port 8510
```

## Components
- **AlertSystem** (`alert_system.py`) — (no docstring)
- **FallbackManager** (`api_fallback.py`) — Manages multi-tier API fallback with caching and quota awareness.
- **C** (`backtest_30day.py`) — (no docstring)
- **BacktestResult** (`backtest_all_sports.py`) — One (sport, strategy) summary row — wins, losses, hit rate, ROI, drawdown.
- **HistoricalBacktest** (`backtest_all_sports.py`) — Multi-sport, multi-strategy historical backtester.
- **DKCombo** (`dk_combos_engine.py`) — (no docstring)
- **Handler** (`dk_combos_engine.py`) — (no docstring)
- **MLBPlayer** (`mlb_tc_engine.py`) — (no docstring)
- **NBATCEngine** (`nba_tc_engine.py`) — (no docstring)
- **NHLTCEngine** (`nhl_tc_engine.py`) — (no docstring)
- **OddsScraperBase** (`odds_scraper_base.py`) — (no docstring)
- **PlayerStatsScraper** (`player_stats_scraper.py`) — Multi-source player stats scraper with cascading fallback.
- **SoccerComboLeg** (`soccer_combo_engine.py`) — (no docstring)
- **SoccerCombo** (`soccer_combo_engine.py`) — (no docstring)
- **Handler** (`soccer_combo_engine.py`) — (no docstring)
- **DataSource** (`sports_registry.py`) — (no docstring)
- **SportConfig** (`sports_registry.py`) — (no docstring)
- **SportsRegistry** (`sports_registry.py`) — (no docstring)
- **SystemMaintenance** (`system_maintenance.py`) — (no docstring)
- **SportConfig** (`tc_math.py`) — Sport-specific configuration for edge calculation
