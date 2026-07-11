# FINAL REPORT — 2026-07-11

## ✅ SYSTEM CHECKLIST

### 1. Pipeline Run
- **Command**: `python run.py --all-sports --show-positions --settle`
- **Status**: ✅ PASS
- **Settlement 7/10**: 0 pending (cleared)
- **Pipeline iter**: WNBA → MLB → WORLD_CUP all ran

### 2. Picks Generated
- **WNBA**: 750 picks
- **MLB**: 3,953 picks
- **WORLD_CUP**: 162 player picks + 3 game picks
- **Total**: 4,865 player picks + 3 game picks
- **Files**: `Daily_Log/2026-07-11/picks.csv`, `soccer_player_picks.csv`, `soccer_game_picks.csv`

### 3. Projections
- **MLB**: 16 matchups
- **WNBA**: 2 matchups
- **WORLD_CUP**: 3 matchups (England@Norway, Spain@France, Switzerland@Argentina)
- **Location**: `Daily_Log/2026-07-11/proj_*.json`

### 4. Dashboard
- **URL**: http://localhost:8510
- **Health**: 200 OK (`/_stcore/health` → "ok")
- **Status**: LIVE

### 5. Models
- **Path**: `/home/workspace/Projects/models/`
- **Status**: ⚠️ EMPTY (no trained .pkl files)

### 6. Historical Data
- **Path**: `/home/workspace/data/historical/`
- **Coverage**: mlb, nba, soccer, wnba (all by 2025)

### 7. Backtests
- **Scripts**: backtest_30day.py, backtest_pipeline.py, multi_sport_backtest.py
- **MLB Backtest**: 0.579 / 0.594 (avg 0.587 acc, 11.2% ROI)
- **Status**: scripts present, ready to run

### 8. Settlement DB
- **Path**: `/home/workspace/Projects/betting_history.db`
- **Size**: 20K (active)

---

## ⚠️ OPEN GAPS

### Gap 1: Models dir empty
- **Issue**: `/Projects/models/` exists but has 0 trained model files
- **Impact**: ml-based features not available, only TC math
- **Fix**: need a `train_model.py` to populate

### Gap 2: Odds API quota exhausted
- **Issue**: 401 on `/odds/` and `/props/` endpoints (Business tier maxed)
- **Impact**: no DK/BetMGM lines for WORLD_CUP
- **Workaround**: self-edge TC projections in use, noted in WC report

### Gap 3: Combos = 0 qualified
- **Issue**: "Combos: 0 total qualified across 0 games"
- **Impact**: no multi-leg parlay combos today
- **Likely cause**: WC games not in combiner sport set

### Gap 4: Fantasy cards
- **Issue**: "10 generated — None"
- **Status**: cosmetic

### Gap 5: Debug noise
- `DEBUG: wc_games count = 0, sports = set()` printed
- Indicates WC game list empty after filter

---

## 🔒 CLOSED TODAY
- ✅ WNBA pipeline added to run.py
- ✅ MLB OVER/UNDER signals (mlb_over_under_signal)
- ✅ WC self-edge isolated from MLB
- ✅ Sport stat config keys normalized
- ✅ LiveStatsPanel un-nested map bug fixed
- ✅ Picks visible on dashboard API
- ✅ Settlement 7/10 cleared (no pending)
- ✅ Dashboard live on :8510

## NEXT STEPS (your call)
1. **Train models** — build `train_model.py` and run across mlb/wnba/soccer historical
2. **Combo builder** — debug why 0 games fed to dk_combos
3. **Odds API upgrade** — out of scope today (quota)
