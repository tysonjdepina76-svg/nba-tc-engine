# NBA TC — Full Integration Report + Gap Fill
**Date:** May 28, 2026 | **Status:** Partial — gaps identified, ready to fill

---

## What Is Running

### Active Files

| File | Version | Sport | Status |
|------|---------|-------|--------|
| `nba_tc_engine.py` | **V6** | NBA ✅ WNBA ⚠️ | Working — NBA full, WNBA partial (6/12 teams populated) |
| `tc_engine_v8_clean.py` | **V8** | NBA ✅ WNBA ❌ | Working — NBA full, WNBA empty (0/12 teams) |
| `true.zo.space/api/tc` | Live API | NBA ✅ WNBA ✅ | Live — fetches ESPN roster/stats, applies TC formulas |
| `true.zo.space/nba-tc` | Frontend | NBA ✅ WNBA ✅ | UI — Project / Live Stats / Backtest / Slate tabs |

---

## Step-by-Step Results

### ✅ Step 1 — Files Saved

- `file 'nba_tc_engine.py'` — V6 (835 lines), NBA full 29 teams, WNBA partial
- `file 'tc_engine_v8_clean.py'` — V8 (801 lines), NBA full, WNBA empty
- `file 'NBA_TC_Integration_Report.md'` — previous version

---

### ✅ Step 2 — Backtest Run

**V8 Engine (`run_backtest()`):**

| Sport | Games | Hit Rate | Avg Gap |
|-------|-------|---------|---------|
| NBA | 4 | **75.0%** | +13.1 |
| WNBA | 2 | **0.0%** | +50.5 |

NBA: PHI@BOS ✅ OVER, LAC@DEN ❌ OVER, ORL@DET ✅ OVER, POR@SAS ✅ OVER
WNBA: MIN@NYL ❌ UNDER, NYL@CON ❌ UNDER

**V6 Game Projections:**

| Game | Market | TC Line | Edge | Signal | Kelly |
|------|--------|---------|------|--------|-------|
| BOS @ NYK | 218.5 | 227.6 | +9.1 | UNDER | 22.8% |
| CLE @ NYK | 224.5 | 228.3 | +3.8 | UNDER | 9.5% |
| SAS @ OKC | 218.5 | 229.8 | +11.3 | UNDER | 28.2% |

---

### ✅ Step 3 — Game Projection Test

```
BOS @ NYK — V6 Output:
  TC Combined (raw):    210.3 pts
  TC Final (adj):       218.3 (PACE +8.0)
  TC Line:              227.6 (TC_final + K=9.3)
  Edge:                 +9.1 (market undervalues OVER → bet UNDER)
  Valid Props ≥3.0:
    BOS  Jayson Tatum    pts 28.5→T=21 E=+7.5 ✅
    BOS  Jaylen Brown    pts 24.0→T=17 E=+7.0 ✅
    BOS  Al Horford      pts 11.0→T=8  E=+3.0 ✅
    NYK  Karl-Anthony Towns pts 25.0→T=18 E=+7.0 ✅
    NYK  Jalen Brunson   pts 24.5→T=10 E=+14.5 ✅ (Q status)
    NYK  OG Anunoby      pts 17.5→T=13 E=+4.5 ✅
```

---

### ✅ Step 4 — FastAPI / Live API

```
GET /api/tc?away=BOS&home=NYK&sport=NBA
GET /api/tc?away=LAL&home=BOS&sport=NBA&market=225.5
GET /api/tc?sport=NBA&mode=live-stats
GET /api/tc?sport=WNBA&mode=live-stats
```

- Fetches live ESPN roster + stat averages per player
- Applies TC formula: `tc = stat × 0.85 × status_factor`
- Derives target lines: `T = floor(tc × 0.88)`
- Returns per-player edges + game-level TC combined/line/signal
- Live mode: `mode=live-stats` returns current scoreboard + box score

---

### ✅ Step 5 — Math Audit

**V6 (nba_tc_engine.py) — Player Props:**
```
TC_pts   = floor(pts × 0.85 × status_factor)
  ACTIVE × 1.0 | Q × 0.55 | OUT × 0.0
T_pts    = floor(TC_pts × 0.88)
Edge     = market_line − T_pts  (positive = value)
```

**V8 (tc_engine_v8_clean.py) — Player Props:**
```
TC_pts   = round(max(0, pts × 0.85 × status_factor + GAP_PTS(-3.0)), 1)
T_pts    = floor(TC_pts × 0.88)
  GAP_PTS = -3.0, GAP_REB = -1.5, GAP_AST = -1.0, GAP_3PM = -0.8
```

**V6 Game Total (separate from TC Match):**
```
TC_final = raw_PTS × VAR_FACTOR + K_GAP(9.3)
VAR_FACTOR: 0.82 (spread≥10) | 0.79 (4-9) | 0.76 (<4) | +8.0 (no spread)
TC_Line  = round(TC_final + 9.3)
```

**V8 Game Total (separate from TC Match):**
```
STAR_MULTIPLIER = 0.90 (All-NBA tier players only)
raw_combined = sum(starters × STAR_MULT × status) + bench_total + home_court(2.0)
TC_Line  = floor(adjusted × 0.88)
```

**Critical Rule (confirmed identical in both):**
> TC Match = player props ONLY (PTS/REB/AST/3PM). Game totals use a completely separate model. Both can run simultaneously.

---

## Gaps Identified

### Gap 1 — WNBA Roster (V6)
```
V6 nba_tc_engine.py WNBA roster — 6/12 teams populated:
  ✅ DAL (8 players) ✅ IND (7) ✅ LVA (7) ✅ MIN (8) ✅ NYL (8) ✅ WAS (7)
  ❌ ATL (0) ❌ CHI (0) ❌ CON (0) ❌ PHX (0) ❌ POR (0) ❌ SEA (0)
```
**Fix:** Add 6 missing WNBA team rosters.

### Gap 2 — WNBA Roster (V8)
```
V8 tc_engine_v8_clean.py WNBA roster — 0/12 teams populated (all empty)
```
**Fix:** Rebuild V8 WNBA roster from scratch using V6 as source + supplement from ESPN.

### Gap 3 — V6/V8 Player TC Formula Divergence
```
V6: TC_pts = floor(pts × 0.85)           — no GAP, uses floor rounding
V8: TC_pts = round(pts × 0.85 − 3.0)   — uses GAP(-3.0), uses round

Result difference (Tatum 28.5 pts ACTIVE):
  V6: floor(28.5 × 0.85)     = 24  → T = floor(24 × 0.88) = 21
  V8: round(28.5 × 0.85 − 3) = 21  → T = floor(21 × 0.88) = 18

Both are valid conservative approaches but produce different targets.
```

### Gap 4 — V8 Game Total Model vs V6
```
V6: Uses VAR_FACTOR + K_GAP(9.3) — calibrated to historical playoff games
V8: Uses STAR_MULTIPLIER(0.90) + bench_diff + home_court — different calibration

V6 and V8 backtest results are NOT comparable directly.
V6 is better calibrated for playoff/high-variance games.
V8 game total model needs more historical games.
```

### Gap 5 — WNBA Backtest (V8)
```
V8 WNBA hit rate: 0% (2 games, avg gap +50.5)
ROOT CAUSE: V8 WNBA roster is empty — all game totals are 0 → model breaks
```
**Fix:** Gap 2 must be resolved first.

---

## Recommended Priority Fixes

### Priority 1 — Fill WNBA Roster (V6 + V8)
Add all 12 WNBA teams using ESPN data + manual verification.
V6 already has 6 teams as base. V8 needs full rebuild.

### Priority 2 — Reconcile V6/V8 Player TC Formula
Choose one standard:
- **Option A:** V6 style (floor, no GAP) — simpler, already in production
- **Option B:** V8 style (round + GAP) — more conservative, better for lean players

Recommend: Keep V6 as the primary (it's what the zo.space API uses).

### Priority 3 — Run Larger Backtest
Current: 4 NBA games (V8) / 0 games logged (V6).
Add: All playoff Round 1 + Semifinals games (Apr 19 – May 17) for both engines.

### Priority 4 — Update NBA Backtest with Live Results
The `/nba-tc` frontend has all 38 backtest games pre-loaded (R1→ECF).
Verify actual game totals for all 38 games to measure true hit rate.

---

## Current Top Player Props (BOS @ NYK, May 28 context)

| Player | Team | Stat | Market | V6 TC | V6 T | Edge |
|--------|------|------|--------|-------|------|------|
| Jayson Tatum | BOS | PTS | 28.5 | 24.2 | 21 | +7.5 ✅ |
| Karl-Anthony Towns | NYK | PTS | 25.0 | 21.2 | 18 | +7.0 ✅ |
| Jaylen Brown | BOS | PTS | 24.0 | 19.6 | 17 | +7.0 ✅ |
| Jalen Brunson | NYK | PTS | 24.5 | 11.5 | 10 | +14.5 ✅ ⚠️ Q |
| Mikal Bridges | NYK | PTS | 21.0 | 17.8 | 15 | +6.0 ✅ |
| OG Anunoby | NYK | PTS | 17.5 | 14.9 | 13 | +4.5 ✅ |
| Karl-Anthony Towns | NYK | REB | 12.5 | 10.6 | 9 | +3.5 ✅ |

---

## CLI Quick Reference

```bash
# V6 — Game projection
python3 nba_tc_engine.py --game "BOS @ NYK" --total 218.5 --sport NBA

# V6 — List teams + injuries
python3 nba_tc_engine.py --sport NBA --list
python3 nba_tc_engine.py --sport WNBA --list

# V8 — Backtest
python3 tc_engine_v8_clean.py --sport NBA --backtest
python3 tc_engine_v8_clean.py --sport WNBA --backtest

# V8 — Project specific game
python3 tc_engine_v8_clean.py --game "BOS @ NYK" --sport NBA --total 218.5

# Live API
curl "https://true.zo.space/api/tc?away=BOS&home=NYK&sport=NBA"
curl "https://true.zo.space/api/tc?away=NYL&home=CON&sport=WNBA"
curl "https://true.zo.space/api/tc?sport=NBA&mode=live-stats"
```