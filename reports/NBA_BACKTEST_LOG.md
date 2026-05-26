# NBA TC BACKTEST RESULTS — May 8, 2026

**TC System: TC = PTS × 0.85 | Line = PTS × 0.88 | Edge = TC − Line | Q = ×0.55 | OUT = 0**

---

## Current Playoff Series Standing

| Series | Status | Games |
|--------|--------|-------|
| **East Semifinals** | | |
| CLE vs DET | **DET leads 2-0** | May 7: DET 107 @ CLE 97 (Final) |
| NY vs PHI | **NY leads 2-0** | May 6: NY 108 @ PHI 102 (Final) |
| **West Semifinals** | | |
| OKC vs LAL | **OKC leads 1-0** | May 7: OKC in progress (Period 3) |
| MIN vs SA | **Series tied 1-1** | May 6: SA 133 @ MIN 95; May 4: SA 102 @ MIN 104 |

---

## Round 1 Recap (Complete)

| Date | Game | Final Score | Series Result |
|------|------|-------------|--------------|
| May 1 | TOR @ CLE 110-112 | CLE wins G6, series tied 3-3 | CLE wins G7 114-102 |
| May 1 | HOU @ LAL | LAL wins series 4-2 | LAL 98-78 (G6 Final) |
| May 1 | ORL @ DET | Series tied 3-3 | DET wins G7 93-79 |
| May 2 | BOS @ PHI | PHI wins series 4-3 | PHI 109-100 (G7 Final) |
| May 3 | CLE @ TOR | **CLE wins series 4-3** | CLE 114-102 (G7 Final) |
| May 3 | DET @ ORL | **DET wins series 4-3** | DET 116-94 (G7 Final) |
| May 4 | SA @ MIN | MIN leads 1-0 | MIN 104-102 |
| May 4 | NY @ PHI | NY leads 1-0 | NY 137-98 |
| May 5 | OKC @ LAL | OKC leads 1-0 | OKC 108-90 |
| May 5 | DET @ CLE | DET leads 1-0 | DET 111-101 |
| May 6 | SA @ MIN | **Series tied 1-1** | SA 133-95 |
| May 6 | NY @ PHI | NY leads 2-0 | NY 108-102 |
| May 7 | DET @ CLE | DET leads 2-0 | DET 107-97 |
| May 7 | OKC @ LAL | OKC leads 1-0 | OKC 61 @ LAL 63 (in progress) |

---

## TC Backtest Log

| # | Date | Game | TC Combined | Actual | Diff | Result |
|---|------|------|-------------|--------|------|--------|
| 1 | May 2 | MIN@DEN G7 | 204.3 | 208 | +3.7 | UNDER ✅ |
| 2 | May 3 | DET@ORL G7 | — | 210 | — | OUT (roster gap) |
| 3 | May 3 | PHI@BOS G7 | 184.0 | 209 | +25.0 | UNDER ✅ |
| 4 | May 6 | MIN@SA G1 | — | 228 | — | OUT (roster gap) |
| 5 | May 6 | PHI@NY G1 | — | 210 | — | OUT (roster gap) |

**Note:** Games 2, 4, 5 showed TC=0 due to incomplete roster maps in FALLBACK_STATS. Live scrape confirmed actual scores. These are excluded from the win rate until rosters are filled.

---

## What Needs Fixing

1. **FALLBACK_STATS incomplete** for: DET, ORL, SA, NY, PHI
2. **Live scrape returning null team names** — ESPN API game data format issue for past dates
3. **Box score API returns 404** for past game IDs

## Next Steps

- [ ] Fill in DET/ORL/SA/NY/PHI roster data in FALLBACK_STATS
- [ ] Re-run backtest for games 2, 4, 5 once rosters are complete
- [ ] Verify OKC@LAL result when game completes
- [ ] Update GAME_CARDS for tonight's games: DET@CLE, OKC@LAL
