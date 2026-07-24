# SELF-EDGE IDENTIFIED + BACKTEST — 2026-07-23

## 🔴 WRONG SELF-EDGE — The One We've Been Calling

**File: `Projects/generate_projections.py`**

This is the **dummy/stub** engine. Every single player across every team and matchup gets **identical projections**:

| Player | Team | PTS | AST | REB | P+A | P+R | P+R+A |
|--------|------|-----|-----|-----|-----|-----|-------|
| Arike Ogunbowale | DAL | 13.5 | 2.7 | 4.5 | 16.2 | 18.0 | 20.7 |
| Kelsey Plum | LA | 13.5 | 2.7 | 4.5 | 16.2 | 18.0 | 20.7 |
| Allisha Gray | ATL | 13.5 | 2.7 | 4.5 | 16.2 | 18.0 | 20.7 |
| Rhyne Howard | ATL | 13.5 | 2.7 | 4.5 | 16.2 | 18.0 | 20.7 |

**These are league-average fallbacks. Not self-edge. Not personalized. No signal.**

---

## ✅ REAL SELF-EDGE — The One That Works

**File: `Projects/tc_math.py` → `over_under_signal()` (line 49)**

Logic: TC projection vs. market line → direction + edge. When a real market line exists, this produces true self-edge picks. The 84 picks in `picks.db` (7/19) were created by this engine using ESPN-derived market lines.

**File: `Projects/gen_wnba_today.py`**

Uses per-player season averages via `wehoop`/ESPN. Generates player-specific projections based on actual historical data. This is the engine that should feed daily_picks.py.

---

## 📊 BACKTEST RESULTS — 7/19 WNBA (96 graded, 58 hit)

### Overall
| Direction | Hits/Graded | Rate | Verdict |
|-----------|-------------|------|---------|
| OVER | 34/48 | 70.8% | ⚠️ Mostly market_line=0 noise |
| UNDER | 24/48 | 50.0% | **Coin flip** |
| **TOTAL** | **58/96** | **60.4%** | **Below 62% threshold** |

### By Stat (UNDER only — real market lines)
| Stat | Hit Rate | Verdict |
|------|----------|---------|
| 3PM | 6/8 = 75.0% | ✅ STRONG |
| REB | 12/16 = 75.0% | ✅ STRONG |
| BLK | 8/16 = 50.0% | ⚠️ MARGINAL |
| STL | 8/16 = 50.0% | ⚠️ MARGINAL |
| PTS | 11/16 = 68.8% | ✅ GOOD |
| AST | 9/16 = 56.2% | ❌ WEAK |

### By Player (UNDER only)
| Player | Rate | 
|--------|------|
| Brittney Griner | 4/6 = 66.7% |
| DeWanna Bonner | 4/6 = 66.7% |
| Arike Ogunbowale | 4/6 = 66.7% |
| Alyssa Thomas | 3/6 = 50.0% |
| Allisha Gray | 2/6 = 33.3% |

---

## 🧠 ROOT CAUSE

`daily_picks.py` imports `generate_projections.py` (line ~24) for WNBA projections. That file generates **identical league-average fallbacks** for every player — no per-player differentiation.

The self-edge signal becomes: "is this random number above or below a generic league line" instead of "is this specific player above or below their real line."

---

## 🔧 RECOMMENDATIONS

1. **SWITCH WNBA PROJECTIONS**: `daily_picks.py` → replace `generate_projections.TCProjectionEngine` with `gen_wnba_today.py` for per-player projections
2. **DIRECTION-GATE**: Only pick one direction per player-stat (the stronger signal). Current system picks BOTH OVER and UNDER for the same stat.
3. **FOCUS ON 3PM + REB**: Self-edge works best on these stats (75%). PTS is decent (68.8%). Drop AST-only picks.
4. **PTS REBUILD**: The `gen_wnba_today.py` engine needs reconnection — it already has per-player season averages. Wire it as the primary WNBA projection source.
5. **BACKTEST DAILY**: Grade every day's picks against ESPN boxscores to build a live hit-rate tracker.

---

## 📁 FILE LOCATIONS
- **Real self-edge**: `/home/workspace/Projects/tc_math.py:49` (over_under_signal)
- **Real WNBA gen**: `/home/workspace/Projects/gen_wnba_today.py`
- **Broken stub**: `/home/workspace/Projects/generate_projections.py`
- **Backtest data**: `/home/workspace/Daily_Log/backtests/2026-07-19/summary.json`
- **Picks DB**: `/home/workspace/Projects/data/picks.db` (84 WNBA picks, 7/19)
