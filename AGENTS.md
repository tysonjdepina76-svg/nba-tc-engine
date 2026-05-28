# AGENTS.md — NBA TC Project Workspace

## Overview
Single-source-of-truth workspace for the **NBA Triple Conservative (TC) Betting System**.

### Core Components

#### 1. Python TC Engine (`nba_tc_engine.py`)
- **Path:** `/home/workspace/nba_tc_engine.py`
- **Purpose:** Offline batch projections, backtest engine, hardcoded rosters for all 30 NBA teams + 12 WNBA teams
- **Version:** v6.0 (~836 lines)
- **Key classes:** `Player`, `Team`, `Game`, `BacktestEngine`
- **CLI usage:**
  ```bash
  python nba_tc_engine.py --game "BOS @ NYK" --total 218.5 --json
  python nba_tc_engine.py --list --sport NBA
  python nba_tc_engine.py --backtest < games.csv
  ```

#### 2. Zo Space API (`/api/tc`)
- **Path:** Zo Space route `/api/tc`
- **Type:** TypeScript/Hono API route (public)
- **Purpose:** Live game projections via ESPN live roster + stat APIs
- **Live mode:** `GET /api/tc?away=BOS&home=NYK&sport=NBA`
- **Live stats:** `GET /api/tc?sport=NBA&mode=live-stats`
- **Historical:** `GET /api/tc?sport=NBA&mode=historical&event=<ESPN_EVENT_ID>`
- **前端:** React page at `/nba-tc` calls this API

#### 3. Zo Space UI (`/nba-tc`)
- **Path:** Zo Space route `/nba-tc`
- **Type:** React/TypeScript page (private, auth required)
- **Tabs:** Project · Live Stats · Backtest · Slate
- **Dependencies:** Calls `/api/tc` for all data

#### 4. Streamlit App (`nba_tc_streamlit.py`)
- **Path:** `/home/workspace/nba_tc_streamlit.py`
- **Purpose:** Local Python GUI — runs Python engine directly + calls `/api/tc` as fallback
- **Run:** `streamlit run nba_tc_streamlit.py --server.port 8501`

#### 5. Google Drive Sync Folder
- **Folder:** `NBA_TC_System/`
- **Contains:** `nba_tc_engine.py`, `nba_tc_streamlit.py`, `AGENTS.md`, `README.md`
- **Account:** `tysondepina99@gmail.com`

## Workflow

### Development Loop
1. Edit `nba_tc_engine.py` (Python engine changes)
2. Edit `nba_tc_streamlit.py` (Streamlit UI changes)
3. Run backtest locally: `python nba_tc_engine.py --backtest < test.csv`
4. Test via Streamlit: `streamlit run nba_tc_streamlit.py`
5. Sync to GitHub + Google Drive
6. Zo Space auto-serves `/api/tc` and `/nba-tc`

### Publishing Flow
- **Zo Space:** Changes to `/api/tc` or `/nba-tc` go live immediately via space tools
- **GitHub:** Push workspace files to `nba-tc-engine` repo
- **Google Drive:** Upload versioned copies to `NBA_TC_System/` folder

## Rosters
- NBA: 30 teams, full rosters hardcoded in `nba_tc_engine.py`
- WNBA: 12 teams (NYL, IND, WAS, LVA, MIN, DAL fully populated; CON, SEA, PHX, CHI, ATL, POR empty)
- Injuries: status field supports `ACTIVE`, `Q` (questionable), `OUT`

## Formulas (source of truth)
```
Player TC   = stat × 0.85 (ACTIVE) | × 0.85 × 0.55 (Q) | × 0 (OUT)
Player T    = floor(TC × 0.88)   # betting target
Edge        = market_line − TC_target  (positive = value)
Game TC_Final = raw_PTS × VAR_FACTOR + K_GAP(9.3)
  VAR_FACTOR: HIGH=0.82 (spread≥10) | MID=0.79 (4-9) | LOW=0.76 (<4)
Signal      = UNDER when TC_Line > market_total | OVER when TC_Line < market_total
```

## Key Files
| File | Purpose |
|------|---------|
| `nba_tc_engine.py` | Python engine (primary) |
| `nba_tc_engine.v6.py` | Versioned backup |
| `nba_tc_streamlit.py` | Streamlit GUI |
| `AGENTS.md` | This file |
| `README.md` | Public-facing docs |
| `TC_Hit_Rate_Report.md` | Historical model performance |
| `NBA_TC_Complete_Integration_Report.md` | Integration audit |
