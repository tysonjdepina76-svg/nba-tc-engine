# Sports TC — Triple Conservative Betting Engine

**Version:** 8.0 (Clean Integrated)
**Updated:** 2026-05-25

---

## Two Independent Models

This system runs **two completely separate models** that can be used simultaneously:

### Model 1: TC Match (Player Props)
**What it answers:** *"Should I bet this player's over/under on PTS/REB/AST/3PM?"*

```
TC_PTS = pts × 0.85 × status_factor + GAP_PTS
TC_REB = reb × 0.80 × status_factor + GAP_REB
TC_AST = ast × 0.75 × status_factor + GAP_AST
TC_3PM = tpm × 0.70 × status_factor + GAP_3PM

status_factor: ACTIVE×1.0 | Q×0.55 | OUT×0.0
Edge = TC_stat − market_prop_line
Signal = OVER if edge > 1.0 | UNDER if edge < -1.0 | NO EDGE otherwise
```

**TC Match does NOT apply to game totals, team totals, spread, or ML.**

---

### Model 2: v8 Game Total Calibration (Separate from TC Match)
**What it answers:** *"Is the game total line too high or too low?"*

```
v8_team_total = Σ(raw_pts × star_mult × status_factor) + home_court + bench_diff

Where:
  raw_pts = pts × status_factor (no TC factor)
  star_mult = All-NBA first team → 0.90 | second team → 0.87 | role players → 1.0
  home_court = +2 pts for home team
  bench_diff = +4 pts if team bench avg > 15 PPG above opponent over series
  lean = UNDER if gap < -5 | OVER if gap > 5 | NO EDGE otherwise
```

**v8 uses raw point projections with star/bench/home adjustments — it does NOT use TC Match.**

---

## Quick Start

```bash
# Run a projection
python tc_pipeline_clean/tc_engine.py --game "SAS @ OKC" --total 218.5 --spread -2.5

# Run backtest
python tc_pipeline_clean/tc_engine.py --sport NBA --backtest

# List teams
python tc_pipeline_clean/tc_engine.py --list-teams

# Run Streamlit dashboard
streamlit run tc_pipeline_clean/nba_tc_streamlit.py

# Run FastAPI server
uvicorn tc_pipeline_clean.tc_engine:app --host 0.0.0.0 --port 8001
```

---

## File Structure

```
tc-workspace/apps/sports-tc/
├── tc_pipeline_clean/
│   ├── tc_engine.py          ← Main engine (TC Match + v8 Game Total)
│   ├── nba_tc_streamlit.py  ← Streamlit dashboard (NBA + WNBA)
│   ├── archive/
│   │   └── v8_pre_integration/
│   │       └── tc_engine_v3_pre_v8.py  ← Pre-v8 engine (TC Match only)
├── master_tc.py             ← Legacy master engine (v4, pre-v8)
├── api.py                   ← FastAPI server (v4, pre-v8)
├── app.py                   ← Flask dashboard (v7, pre-v8)
├── scripts/                 ← Individual game scripts (various versions)
└── roster_backup/           ← Archived rosters
```

---

## Key Roster Files

| File | Sport | Status |
|------|-------|--------|
| `master_tc.py` NBA rosters | NBA | Current |
| `master_tc.py` WNBA rosters | WNBA | Current |
| `WNBA_TC_Rosters_Clean.md` | WNBA | Full reference |

---

## API Endpoints

```
GET  /                  — Root info
GET  /health            — Status check
GET  /teams             — List all teams
GET  /backtest          — Run backtest suite
POST /project           — Project a game (body: GameRequest)
```

---

## Architecture Decision: Why Two Models

The TC engine was designed as a **player prop floor model**. It answers prop questions well. It was never designed to answer game total questions — using TC PTS sums as a game total gives gaps of 60-80 pts in backtests.

v8 adds a **separate** game total calibration that starts from raw point projections and layers in:
- All-NBA star differential (top players project more stably)
- Series bench differential (playoff-specific edge signal)
- Home court advantage

Both models run independently and output to the same dashboard. The user sees two signals: **TC Prop Edge** and **v8 Game Total Lean**.
