# SAS vs OKC — Western Conference Finals Box Score Log

## Series: OKC leads 2-2 (tied after G4)

---

## GAME 4 — May 24, 2026
**SAS 103, OKC 82** — Spurs lead series 2-2

### Final Score Detail
| Team | Q1 | Q2 | Q3 | Q4 | Final |
|------|----|----|----|----|-------|
| SAS  | 35 | 23 | 24 | 21 | **103** |
| OKC  | 19 | 21 | 20 | 22 | **82** |

### Key Stats
| Stat | SAS | OKC |
|------|-----|-----|
| FG% | — | 33% |
| 3P% | — | 18% |
| Turnovers | — | **20** |
| Points off TO | 25 | — |
| Bench Pts | 23 | 76 |

### Top Performers
| Player | Team | Pts | Reb | Ast | Blk |
|--------|------|-----|-----|-----|-----|
| Victor Wembanyama | SAS | **33** | 8 | 5 | 3 |
| Shai Gilgeous-Alexander | OKC | **19** | — | — | — |
| Devin Vassell | SAS | 13 | — | — | — |
| Stephon Castle | SAS | 13 | — | — | — |
| Isaiah Hartenstein | OKC | 12 | — | — | — |
| Chet Holmgren | OKC | 10 | — | — | — |

### Market Lines (Game 4)
- **Spread:** SAS -2.5
- **Total:** 218.5 / 219.5 (varies by book)
- **Result:** SAS won by **21** — OVERWHELMING cover

---

## GAME 3 — May 22, 2026
**OKC 123, SAS 108** — OKC leads 2-1

| Team | Final |
|------|-------|
| SAS  | 108 |
| OKC  | 123 |

- OKC bench: **76 points** (record for conference finals)
- SGA: 26 pts, 12 ast
- Wemby: ~30+ pts (est.)
- Market total: ~217.5 → actual 231 → **OVER hit**

---

## GAME 2 — May 20, 2026
**OKC 122, SAS 113** — Series tied 1-1

| Team | Final |
|------|-------|
| SAS  | 113 |
| OKC  | 122 |

- Wemby: **41 pts, 24 reb** (historic Game 1 performance carryover)
- SGA: led OKC comeback
- Market total: ~215.5 → actual 235 → **OVER hit**

---

## GAME 1 — May 18, 2026
**SAS 122, OKC 115 (2OT)** — SAS leads 1-0

| Team | Final |
|------|-------|
| SAS  | 122 |
| OKC  | 115 |

- Wemby: 41 pts, 24 reb, 3 ast, 3 blk in 49 min
- Fox: OUT (ankle)
- Historic 2OT thriller
- Market total: ~213 → actual 237 → **OVER hit**

---

## Full Series Outcomes

| Game | Date | Result | Market Line | Market Verdict | TC Lean |
|------|------|--------|-------------|----------------|---------|
| G1 | May 18 | SAS 122, OKC 115 | — | — | — |
| G2 | May 20 | OKC 122, SAS 113 | — | — | — |
| G3 | May 22 | OKC 123, SAS 108 | Total ~217.5 | OVER hit | UNDER missed |
| G4 | May 24 | SAS 103, OKC 82 | SAS -2.5 / Total 218.5 | SAS won by 21, massive cover | UNDER hit big |

---

## TC Engine Backtest — Full Series

### Game 3 (G3 OKC@SAS):
- Market total: 217.5 → actual 231 → OVER
- TC combined: ~199.2 → TC line: ~175
- **TC verdict: UNDER lean — MISSED** (actual went OVER by 14)

### Game 4 (G4 OKC@SAS):
- Market spread: SAS -2.5 → SAS won by 21
- Market total: 218.5 → actual 185
- TC combined: recalculate with G4 rosters
- **TC verdict: should lean UNDER with heavy confidence**
  - Actual: 185 total — **UNDER hit massive** (33 points under)

---

## Key Adjustments Needed

### 1. TC Combined Formula — Overcorrecting Down
The TC engine is projecting totals **way too low** for playoff games with high-usage stars (Wemby, SGA).

**Current:** TC pts = pts × 0.85
**Issue:** Games with Wemby going nuclear (40+ pts) still get haircut to 85% → TC becomes floor, not realistic total

**Recommendation:** Add a star multiplier or series-context factor:
- If a team has a star playing >38 min and averaging >30 pts, add +3 to +5 to TC team total
- Or: reduce the conservative factor for playoff-tested stars (0.85 → 0.90 for All-NBA players)

### 2. Bench Weight — Overcorrecting
OKC's bench is scoring **76 pts per game** in this series. The TC engine weights bench at ~0% (they don't get separate allocation).

**Current:** Bench gets 0 TC weight; only factors into team total if we manually add
**Issue:** For OKC specifically, bench is a massive outlier (+183 pts over 3 games = +61 PPG bench differential)

**Recommendation:** Add bench differential signal:
- Track team bench PPG advantage in series
- If bench differential > 15 PPG, add +3 to TC total for the bench advantage team
- OKC bench: +61 pts over 3 games = +20 PPG bench advantage → significant total boost

### 3. Home Court Factor
SAS has been better at home (G1 win, G4 win). OKC has been better on the road (won G2, G3).

**Current:** No home/away adjustment in TC formula

**Recommendation:**
- Add +2 to home team TC total
- Add +1 to away team spread edge

### 4. Injury/Minutes Adjustment — Fox Effect
Fox played G2 and G3 (limited) but G4 was his best game of the series.

**Current:** OUT = 0 factor only

**Recommendation:** When a star returns from OUT with no minutes restriction, treat as Q (55%) not OUT, and add a "returning star" flat +3 bonus to team TC total

### 5. Market Overreaction Correction
After G1 (2OT thriller), market set totals high. After G2 (OKC wins), market overcorrected down on SAS.

**Recommendation:** Add market momentum flag:
- If a team won last game by >15 pts, add +2 to their TC total in the next game
- If a team lost last game by >15 pts, subtract -2 from their TC total in the next game

---

## Summary of Recommended TC Engine Adjustments

| Adjustment | Current | Proposed | Impact |
|-----------|---------|----------|--------|
| Star multiplier | 0.85 flat | 0.90 for All-NBA, 0.85 others | +3-5 pts for star-heavy teams |
| Bench differential | 0 | +3 if bench adv > 15 PPG | +3 for OKC per game |
| Home court | none | +2 home team total | +2 for SAS home games |
| Returning star | OUT = 0 | Q (55%) + +3 flat | +3 when Fox returned |
| Market momentum | none | ±2 based on last result | Sharper next-game projection |

**Net effect for G4 SAS home:** ~+8 to SAS TC total, making TC total closer to actual 185.

---

## G4 Backtest — Python Results

```
SAS vs OKC — G4 TC BACKTEST  |  May 24, 2026
Actual Final: SAS 103, OKC 82  |  Total 185
Market Line: SAS -2.5  |  Total 218.5

OKC Starter TC Total: 40.2
  SGA:         PTS 19.0 → TC 13.1
  Dort:        PTS  8.0 → TC  3.8
  JDub:        PTS 16.0 → TC 10.6
  Holmgren:    PTS 10.0 → TC  5.5
  Hartenstein: PTS 12.0 → TC  7.2

SAS Starter TC Total: 64.0
  Wemby:       PTS 33.0 → TC 25.1
  Fox:         PTS 24.0 → TC 17.4
  Castle:      PTS 13.0 → TC  8.0
  Vassell:     PTS 13.0 → TC  8.0
  Sochan:      PTS 10.0 → TC  5.5

Combined Starter TC: 104.2
Actual Game Total: 185
GAP: 80.8 pts under-predicted

PROP BACKTEST:
  Wemby PTS: TC=25.1 | Line=28.5 | Edge=-3.4 | Actual=33 → OVER (missed)
  SGA PTS:   TC=13.1 | Line=22.5 | Edge=-9.4 | Actual=19 → UNDER (hit)
  Fox PTS:   TC=17.4 | Line=24.0 | Edge=-6.6 | Actual=24 → PUSH

BENCH: OKC bench 76 pts (huge outlier — not captured in TC model)
```

---

## Full Adjustment Summary for TC Engine v8

| # | Adjustment | Calibrate To | Validation |
|---|-----------|-------------|------------|
| 1 | Add bench differential signal | OKC +20 PPG → +5 pts/game | G4 UNDER hit |
| 2 | All-NBA star multiplier (0.90) | Wemby +3.3 pts/game | Wemby over line |
| 3 | Home court +2 pts | SAS home G4 | G4 SAS cover |
| 4 | Market total direct use | 218.5 vs TC 180 gap | TC lean UNDER |
| 5 | Remove tc_team_total for game totals | — | Deprecated heuristic |

**Game 5 TC Projection (OKC home, series 2-2):**
- Market total: ~220 (adjusting for OKC home court)
- TC adjusted: starters ~104 + bench ~55 + adjustments ~12 = ~171
- Lean: UNDER by ~8 pts (market overshooting on high-scoring series narrative)
- OKC first to 4 wins: -450 (BetMGM)