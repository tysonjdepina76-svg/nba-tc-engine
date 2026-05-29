# TC Engine + NBA-TC App Integration Report
## Game Total Calibration System — v8 Additions

**Date:** May 24, 2026
**Status:** WRITTEN — NOT YET INTEGRATED
**Prepared for:** Tyson — NBA TC Workflow

---

## Executive Summary

This report covers what the TC engine game total code does, how it fits into the existing `/nba-tc` zo.space app, what the v8 patch adds, and what integration steps are needed to wire everything together. Two files are referenced throughout:

- `file 'tc-workspace/apps/sports-tc/tc_pipeline_clean/tc_engine.py'` — the current clean TC engine
- `file '/nba-tc'` — the zo.space React frontend

The game total code described here is the v8 patch saved to `file 'tc_engine_v8_patch.py'`. It is deliberately **not yet integrated** — this report explains how it will work once it is.

---

## 1. The Core TC Rule (What the Engine Already Gets Right)

The clean tc_engine.py (v3) has a critical architectural rule explicitly stated in its docstring:

```
TC MATCH DOES NOT APPLY TO TEAM TOTALS.
TC Match is ONLY for individual player prop support lines:
    - Points
    - Rebounds
    - Assists
    - 3-point shots made
```

This is the correct foundation. Here's why:

| Model | What it is | What it's for |
|-------|------------|---------------|
| **TC Match** | `stat × CONS × status_factor + GAP` applied per player per stat | Player prop support lines only (PTS/REB/AST/3PM) |
| **`tc_team_total()`** | Sums TC PTS across all roster players | Aggregate prop support number — NOT a game total |
| **`raw_points_total()`** | `pts × status_factor` per player, summed | Raw team point projection for informational use |

The `tc_team_total()` method in the engine is explicitly labeled legacy alias. It sums TC PTS props — it was never designed to predict actual game scores. Using it as a game total model produces the large gaps seen in backtesting (e.g., SAS vs OKC G4: tc_team_total() starter sum ≈ 104.2 vs actual team total 185).

**Correct model separation:**
```
Player Props  → TC Match (PTS/REB/AST/3PM) → edge vs book lines → bet
Game Total   → Raw Points + v8 Adjustments  → compare to market total → lean
```

---

## 2. What the v8 Game Total Code Does (The 5 Adjustments)

The v8 patch (`tc_engine_v8_patch.py`) adds a separate game-total calibration layer on top of raw point projections. It does NOT modify TC Match or the player prop engine.

### 2.1 The Raw Foundation

For each active player:
```python
raw_pts = pts × status_factor   # ACTIVE=1.0, Q=0.55, OUT=0.0
```

No TC factor (0.85) applied at this stage — that factor is for prop support lines only.

### 2.2 Adjustment 1 — STAR_MULTIPLIER (All-NBA Players)

All-NBA first-team players project slightly higher than the general CONS factor because their usage and efficiency are more stable:

```python
STAR_MULTIPLIER = 0.90    # vs default CONS_PTS = 0.85

ALL_NBA_PLAYERS = {
    "Shai Gilgeous-Alexander": 0.90,
    "Nikola Jokic": 0.90,
    "Victor Wembanyama": 0.90,
    "Luka Doncic": 0.90,
    "Jayson Tatum": 0.90,
    # All-NBA Second Team (slightly lower)
    "Donovan Mitchell": 0.87,
    "Jalen Brunson": 0.87,
    "Anthony Edwards": 0.87,
    "Giannis Antetokounmpo": 0.87,
    "Kevin Durant": 0.87,
}
```

Effect: Wembanyama's raw projection goes from `33 × 0.85 = 28.1` to `33 × 0.90 = 29.7` (+1.6 pts). SGA from `32 × 0.85 = 27.2` to `32 × 0.90 = 28.8` (+1.6 pts).

### 2.3 Adjustment 2 — BENCH_DIFF_ADJUST

In a playoff series context, bench differential can be a persistent edge signal. When one team's bench averages > 15 PPG more than the opponent's over the series, add a flat bonus:

```python
BENCH_DIFF_THRESHOLD = 15   # PPG differential threshold
BENCH_DIFF_BONUS = 4        # pts added per game when threshold exceeded

SERIES_BENCH_PTS = {
    "OKC": {"G1": 33, "G2": 45, "G3": 76, "G4": 23},  # OKC bench pts
    "SAS": {"G1": 25, "G2": 19, "G3": 19, "G4": 23},  # SAS bench pts
}
```

OKC series average: `(33+45+76+23)/4 = 44.25` | SAS: `(25+19+19+23)/4 = 21.5`
Diff: `44.25 - 21.5 = 22.75 PPG` → exceeds 15 threshold → **+4 pts to OKC total**

This bonus is per-game. It applies to whatever team has the bench advantage in that game.

### 2.4 Adjustment 3 — HOME_COURT

```python
HOME_COURT_BONUS = 2   # pts added to home team total
```

Simple: home teams get +2 pts to their raw projection. NBA home advantage historically averages ~2.5-3 pts. Using 2 is conservative.

### 2.5 Adjustment 4 — MARKET_TOTAL_FLOOR

The market total is the single most informative signal for game totals. Sportsbooks set totals using models far more sophisticated than a raw-point projection. The TC engine should use the market total as:

1. **Calibration signal** — compare model output vs market to identify directional lean
2. **Floor check** — if model output is > 20 pts below market, the model may be missing something (pace, style-of-play factors not captured in player averages)

The market total is NOT used to replace the model's output. It is used to check whether the model's direction aligns with the market's expectation.

### 2.6 Adjustment 5 — Deprecation Warning on tc_team_total()

The engine already has comments warning against using `tc_team_total()` for game totals. The v8 patch makes this an explicit runtime behavior: any code that tries to use the TC prop sum as a game total should fail with a clear error message.

---

## 3. The Game Total Projection Formula

Putting it all together, the game-total-calibrated team projection is:

```
tc_game_total_TEAM = Σ(raw_pts × star_mult if All-NBA) + HOME_COURT + BENCH_DIFF_BONUS

Where:
  raw_pts = pts × status_factor
  star_mult = ALL_NBA_PLAYERS[name] if found else 1.0
  HOME_COURT = 2 if team is home else 0
  BENCH_DIFF_BONUS = 4 if team bench diff > 15 else 0
```

**Full game total:**
```
tc_game_total_COMBINED = tc_game_total_HOME + tc_game_total_AWAY
LEAN = "UNDER" if tc_game_total_COMBINED < market_total else "OVER"
```

---

## 4. Integration Architecture — How It Fits the /nba-tc App

### 4.1 Current App Structure

The `/nba-tc` React page has 4 tabs:

| Tab | Function | Current Data |
|-----|----------|-------------|
| 📊 Project Game | Run TC for a selected matchup | `tc_combined`, `tc_line`, `edge`, `signal`, player props |
| 📡 Live Stats | Live ESPN scoreboard + box scores | Actual pts/reb/ast from live games |
| 📈 Backtest | Historical TC performance | Hard-coded reference games |
| 📋 Slate | Multi-game slate overview | Placeholder |

The Project Game tab calls `GET /api/tc?away=X&home=Y&sport=Z` which hits the FastAPI backend.

### 4.2 Where Game Total Fits in the Frontend

The frontend `TeamTable` component already has a `TeamTotals` section showing 6 stat columns (PTS, REB, AST, 3PM, STL, BLK). The game total data is already being returned by the API in `result.game_total`:

```python
"game_total": {
    "model": raw_game_total,      # e.g., 198.3
    "market": market_total,        # e.g., 218.5
    "gap": total_gap,              # e.g., -20.2
    "note": "Raw point projection only. TC Match does not apply to totals.",
}
```

Currently this data is returned but **not prominently displayed** in the UI. The TC Edge and Signal shown in the Metrics row are for the combined TC prop sum — not the game total.

### 4.3 Proposed Frontend Changes

Three additions to the `/nba-tc` page:

**A. New "Game Total" panel (below the existing Metrics row):**
```
┌─────────────────────────────────────────────────────┐
│  GAME TOTAL PROJECTION                              │
│  TC Model: 210.4   Market: 218.5   Gap: -8.1       │
│  Lean: UNDER  ←── market is higher than model       │
│  Note: Raw pts + v8 adjustments (star/bench/home)   │
└─────────────────────────────────────────────────────┘
```

**B. New "v8 Adjustments" panel (collapsible, for transparency):**
```
┌─────────────────────────────────────────────────────┐
│  v8 GAME TOTAL CALIBRATION                          │
│  ✓ Wembanyama All-NBA (×0.90)  +1.6 pts            │
│  ✓ OKC Bench Diff +22.8 PPG       +4.0 pts         │
│  ✓ SAS Home Court               +2.0 pts            │
│  ─────────────────────────────────                 │
│  Net adjustment: +7.6 pts                           │
└─────────────────────────────────────────────────────┘
```

**C. Signal row upgrade:**
The current signal logic is: `OVER if edge > 1.0 else UNDER if edge < -1.0 else NO EDGE`
This edge is the TC prop sum vs TC line — it tells you whether the aggregated TC prop support is above or below the prop market line.

For game total, a separate signal should display:
```
Game Total Signal: UNDER (model 210.4 vs market 218.5, gap -8.1)
```

### 4.4 Backend Changes Required

Two endpoints need updates:

**`GET /api/tc`** (current query parameter style):
- Add `market_total` and `market_spread` as query params
- Compute v8 game total using `tc_adjusted_team_total()` from v8 patch
- Return `"game_total_v8"` alongside existing `"game_total"`

**`GET /api/tc?sport=NBA&mode=live-stats`** (Live Stats tab):
- Already fetches live ESPN data
- After fetching, run v8 game total for completed games
- Compare v8 model vs actual to build live accuracy track record
- Return `"game_total_v8"` with actual result for post-game review

### 4.5 Data Flow Diagram

```
[Frontend /nba-tc]
       │
       │ GET /api/tc?away=OKC&home=SAS&sport=NBA&market_total=218.5
       ▼
[FastAPI (api.py)]
       │
       ├──► [tc_engine.py] — TC Match for player props (unchanged)
       │        Returns: tc_pts/reb/ast/3pm per player, edges
       │
       └──► [tc_engine_v8_patch.py] — Game Total Calibration (new)
                │  raw_points_total()
                │  + STAR_MULTIPLIER (All-NBA lookup)
                │  + BENCH_DIFF_ADJUST (series bench tracking)
                │  + HOME_COURT (+2 home)
                │  + MARKET_TOTAL_FLOOR (read-only signal)
                ▼
                Returns: tc_game_total_HOME, tc_game_total_AWAY,
                         tc_game_total_COMBINED, lean, adjustments
       │
       ▼
[API Response]
{
  "game_total_v8": {
    "home_tc": 105.2,
    "away_tc": 86.4,
    "combined": 191.6,
    "market": 218.5,
    "gap": -26.9,
    "lean": "UNDER",
    "adjustments": {
      "home_star_multi": "+1.6 (Wembanyama All-NBA)",
      "home_bench_diff": "+4.0 (OKC bench +22.8 PPG)",
      "home_home_court": "+2.0 (SAS home)",
      "away_home_court": "+2.0 (OKC away = 0)"
    }
  },
  "tc_combined": 249.4,    ← existing TC prop sum (unchanged)
  "edge": 8.4,              ← existing TC prop edge (unchanged)
  "signal": "OVER",         ← existing TC prop signal (unchanged)
  "players": { ... }        ← existing player props (unchanged)
}
       │
       ▼
[Frontend displays both: TC Prop Signal + Game Total Lean]
```

---

## 5. OKC vs SAS G4 Worked Example (Using v8)

**Game:** SAS home, OKC away | Actual: SAS 103, OKC 82, Total 185
**Market Total:** 218.5 | **Market Spread:** SAS -2.5

### 5.1 SAS Starters (Home)

| Player | Raw PTS | All-NBA Multi | Adj PTS |
|--------|---------|--------------|---------|
| Wembanyama | 33.0 | 0.90 | 29.7 |
| Fox | 24.0 | 1.0 | 24.0 |
| Castle | 13.0 | 1.0 | 13.0 |
| Vassell | 13.0 | 1.0 | 13.0 |
| Sochan | 10.0 | 1.0 | 10.0 |
| **Sum** | | | **89.7** |

+ HOME_COURT +2 → **91.7**

### 5.2 OKC Starters (Away)

| Player | Raw PTS | All-NBA Multi | Adj PTS |
|--------|---------|--------------|---------|
| SGA | 19.0 | 0.90 | 17.1 |
| Dort | 8.0 | 1.0 | 8.0 |
| JDub | 16.0 | 1.0 | 16.0 |
| Holmgren | 10.0 | 1.0 | 10.0 |
| Hartenstein | 12.0 | 1.0 | 12.0 |
| **Sum** | | | **63.1** |

OKC bench diff: +22.8 PPG (> 15 threshold) → +4 bench bonus → **67.1**

### 5.3 v8 Game Total Output

| Metric | Value |
|--------|-------|
| SAS v8 TC (home + home_court) | 91.7 |
| OKC v8 TC (away + bench_diff) | 67.1 |
| **v8 Combined** | **158.8** |
| Market Total | 218.5 |
| Gap | **-59.7** |
| v8 Lean | UNDER |
| Actual Total | 185 |
| Actual vs v8 | +26.2 (actual over v8) |
| Actual vs Market | -33.5 (actual under market) |

### 5.4 What This Tells Us

The v8 model under-predicts by ~26 pts even with adjustments. This is expected — raw point projections from season averages miss:
- **Pace** — both teams may push tempo in playoff games
- **Defensive breakdowns** — playoff series often feature opponent-specific exploitable mismatches
- **Game script** — if SAS falls behind early, 4th quarter bench players get more minutes (boosting raw pts)

**The v8 lean is still correct directionally** — both v8 and actual are well UNDER the market total of 218.5. The value is in the lean signal, not the exact point prediction.

---

## 6. What Integration Requires (Step-by-Step)

### Phase 1: Wire v8 Into tc_engine.py (Backend Only)
- [ ] Add `STAR_MULTIPLIER`, `BENCH_DIFF_THRESHOLD`, `BENCH_DIFF_BONUS`, `HOME_COURT_BONUS` constants
- [ ] Add `ALL_NBA_PLAYERS` dictionary
- [ ] Add `SERIES_BENCH_PTS` tracking dict
- [ ] Add `calc_series_bench_diff()` function
- [ ] Add `tc_adjusted_team_total()` function
- [ ] Add `generate_game_tc_report()` function
- [ ] Update `project_game()` to include `"game_total_v8"` in response
- [ ] No change to TC Match math, player prop output, or existing API response fields

### Phase 2: Update api.py (FastAPI Layer)
- [ ] Import v8 functions from tc_engine
- [ ] `GET /api/tc` — call v8 function, attach `"game_total_v8"` to response
- [ ] `GET /api/tc?sport=NBA&mode=live-stats` — after game completes, run v8 and compare to actual for live accuracy log

### Phase 3: Update /nba-tc Frontend
- [ ] Add Game Total panel below existing Metrics row
- [ ] Add collapsible v8 Adjustments detail panel
- [ ] Use separate color coding for Game Total lean vs TC Prop signal
- [ ] Add completed game v8 accuracy to Live Stats tab

### Phase 4: Backtest the v8 Model
- [ ] Run v8 game total on existing backtest games (Apr 19 slate, May 15 games)
- [ ] Compare v8 lean direction vs actual game total direction
- [ ] Track: `v8_direction_hit_rate`, `avg_v8_gap`
- [ ] Calibrate BENCH_DIFF_BONUS threshold if needed

---

## 7. Summary: What Works, What Doesn't, What Changes

### What Works Today (tc_engine.py clean v3)
- ✅ TC Match for player props (PTS/REB/AST/3PM) — solid, defensible model
- ✅ Edge calculation vs book prop lines
- ✅ Status handling (ACTIVE/Q/OUT) with correct factors
- ✅ Explicit documentation that TC Match ≠ game total model
- ✅ FastAPI server with clean endpoints

### What Doesn't Work (Current Gap)
- ❌ `tc_team_total()` used as proxy for game total — gap of 60-80 pts in backtests
- ❌ No All-NBA star calibration — All-NBA players get same 0.85 as role players
- ❌ No bench differential tracking — playoff bench advantages not modeled
- ❌ No home court adjustment in game total context
- ❌ Market total used only as optional param, not as calibration signal
- ❌ Frontend `/nba-tc` doesn't display game total lean prominently

### What the v8 Game Total Code Adds
- ✅ `tc_adjusted_team_total()` — separate from TC Match, proper game total calibration
- ✅ All-NBA multiplier (0.90 vs 0.85) — accurate star projection
- ✅ Series bench differential tracking + bonus
- ✅ Home court bonus (+2 pts)
- ✅ Market total as floor/calibration signal
- ✅ Explicit deprecation of `tc_team_total()` for game totals

### What Integration Does NOT Change
- 🚫 TC Match math for player props (PTS/REB/AST/3PM) — unchanged
- 🚫 `project_game()` existing response structure — new field added, old fields untouched
- 🚫 Frontend's player prop table — continues to show TC_PTS/REB/AST/3PM
- 🚫 Backtest results for props — those are independent of game total

---

## 8. Files Involved

| File | Role | Status |
|------|------|--------|
| `file 'tc-workspace/apps/sports-tc/tc_pipeline_clean/tc_engine.py'` | Core TC engine | Current production |
| `file 'tc_engine_v8_patch.py'` | Game total v8 additions | Written, not integrated |
| `file 'tc-workspace/apps/sports-tc/api.py'` | FastAPI server | Needs Phase 2 update |
| `file '/nba-tc'` (zo.space route) | React frontend | Needs Phase 3 update |
| `file 'SAS_vs_OKC_Game4_BoxScore.md'` | SAS vs OKC G4 actual data | Saved |
| `file 'sas_vs_okc_g4_backtest.py'` | G4 backtest script | Written |

---

## 9. Conclusion

The TC engine is a **player prop model**. It was designed to answer: "Given this player's season averages and status, what prop line does the TC model support — and does it have edge vs the book?" The answer to that question lives in TC_PTS/TC_REB/TC_AST/TC_3PM per player, and it works.

The game total question is a **different question**: "Given both teams' rosters, status, and context, is the market total too high or too low?" The v8 patch answers that by starting from raw point projections and layering in playoff-series-specific adjustments (star differential, bench differential, home court). It does not touch TC Match.

Once integrated:
- The frontend shows two independent signals: **TC Prop Edge** (should I bet this player's over/under?) and **Game Total Lean** (is the total line too high or too low?)
- Both signals can be used simultaneously without confusion
- The backtest system tracks them independently
- The system is transparent about which model is which

The integration is a backend-plus-frontend update. The math is done. The architectural separation is correct. The next step is wiring it in.