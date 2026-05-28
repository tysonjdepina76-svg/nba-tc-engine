# NBA TC Engine — Triple Conservative Betting System

## What Is This?
A data-driven NBA/WNBA betting engine that applies a **Triple Conservative (TC)** multiplier to player stats to generate conservative projections, then compares them against market lines to find edge.

## Quick Start

### Python Engine
```bash
# Project a game
python nba_tc_engine.py --game "BOS @ NYK" --total 218.5 --json

# List all teams + injuries
python nba_tc_engine.py --list --sport NBA

# Backtest from CSV
cat games.csv | python nba_tc_engine.py --backtest
```

### Streamlit GUI
```bash
streamlit run nba_tc_streamlit.py --server.port 8501
```

### Live Web UI
Visit: `https://true.zo.space/nba-tc`

## The TC Formula

| Status | Multiplier |
|--------|-----------|
| Active player | stat × 0.85 |
| Questionable (Q) | stat × 0.85 × 0.55 |
| Out (OUT) | 0 |

**Betting Target (T)** = floor(TC × 0.88)

**Edge** = market_line − T  (positive = player exceeds line = value bet)

**Game TC Line** = raw_combined_TC × variance_factor + 9.3

## Architecture
- `nba_tc_engine.py` — Python engine, rosters, backtest engine
- `/api/tc` — Live TypeScript API (ESPN data)
- `/nba-tc` — React web UI
- `nba_tc_streamlit.py` — Local Python GUI
