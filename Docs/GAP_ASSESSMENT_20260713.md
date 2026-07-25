# TC Pipeline Gap Assessment — 2026-07-13

**Status: 6/7 critical gaps remain. Pipeline runs but coverage is ~25%.**

## What Works ✅
- MLB grading: **64.3% hit rate** (2,664 H / 1,482 M, 4,146 graded)
- Health check, docs generator, end-to-end pipeline
- Backfill, grading, daily picks generation

## What Doesn't Work ❌

| Gap | Sport | Impact | Root Cause |
|---|---|---|---|
| **G1: WNBA boxscores** | WNBA | 2,341/2,343 pending (99.9%) | WNBA final/ has only 7 dates — missing 2026-06-13/16/17/18/19/20/22/23/24/25/26 |
| **G2: World Cup boxscores** | WC | 3,241/3,241 pending (100%) | wc_boxscores has 35 files; pick matchups are country codes, not in TEAM_ABBREV |
| **G3: MLB pick matchups** | MLB | 5,238/9,384 pending (56%) | 21 unique matchups (ARI@SD, ATH@DET, etc.) — abbrevs not in TEAM_ABBREV |
| **G4: 2026-07-11/12/13 picks** | All | 2,476 rows | 3 most recent days have no boxscore backfill yet |
| **G5: 1,324 "?" league rows** | Mixed | 8% of data | Picks missing league/team field — fix at write time |
| **G6: 3 dates with 0 picks** | — | 2026-06-29/30, 07-01/05 | Pipeline not run those days — historical gap |

## Specific Missing Abbrevs (G3)
ARI, ATH, LAA, SD, DET, SF, HOU, WSH, MIA, MIL, MIN, PHI, PIT, COL, LAD, STL, KC, BAL, TB, SEA, TEX

## Specific Missing Matchups (G1)
CHI@CON, CHI@DAL, CHI@PHX, DAL@CON, DAL@SEA, GS@TOR, IND@LA, IND@LV, IND@PHX, LA@ATL, LV@PHX, LV@POR, MIN@GS, NY@TOR, PHX@IND, PHX@MIN, SEA@ATL, SEA@PHX, SEA@WSH, TOR@ATL

## Top 3 Fixes (Priority Order)
1. **Backfill 2026-07-11/12/13 boxscores** (G4) — needed for today's report
2. **Add 21 missing MLB abbrevs to TEAM_ABBREV** (G3) — quick fix, unlocks 5,238 picks
3. **Build WNBA scraper runner for 2026-06-13 thru 2026-06-26** (G1) — needed for WNBA coverage
