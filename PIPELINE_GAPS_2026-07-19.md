# TC Pipeline Gaps — July 19, 2026

## COMPLETE GAP LIST

### ACTIVE BLOCKERS (Dead Until ~Aug 17)
1. **SerpAPI quota exhausted** — 250/250 daily searches burned. Resets in 29 days. Pipeline was sending every zero-line pick (100+) per run instead of capping at top 8 edge-sorted.
2. **SDIO API key dead** — 401 on all odds endpoints. Key invalid or tier doesn't include odds.
3. **Odds API Business tier maxed** — quota exhausted, 401 on /odds/ + /props/
4. **SGO API WNBA tier missing** — SGO is NBA-only, no WNBA support
5. **All 721 picks are SELF_EDGE** — no real market lines flowing from any API

### FIXES APPLIED TODAY
6. **Combo banner regression** — Inline combo detection banner reappeared in /nba-tc game cards. Removed entirely (redundant with dedicated Combos tab).
7. **Combo API COMBOS button** — /dashboard COMBOS button was dead. Fixed by switching from /api/combos/precomputed to /api/v1/combos.
8. **19 dead API endpoints purged** — Removed obsolete routes from api/main.py. Only 11 live endpoints remain.
9. **COMBO_DEFS deletion bug** — Purging old endpoints accidentally deleted COMBO_DEFS constant. Restored from git.
10. **WC box scores missing** — Live games tab had no WC column definitions. Added WC_COLS and WC rendering blocks.
11. **c.label field mismatch** — Dashboard rendered c.label which doesn't exist on combo API response. Changed to c.combo_label.
12. **Daily limit not enforced in code** — enrich_lines_via_serpapi() sorted zero-line picks but didn't cap at top 8 per run. 250 daily limit existed in serp_odds_scraper.py but not respected by pipeline caller.

### NOT YET FIXED
13. **SerpAPI cap NOT wired to pipeline** — search_odds() checks quota but pipeline's enrich function doesn't sort by edge before calling it. Need: sort picks by abs(edge) descending, only enrich top 8 edge picks per run.
14. **New API key needed** — Fresh Odds API or SDIO key to restore real lines.
15. **WC live stats dashboard** — /api/box-scores live feeds from ESPN but WC may not surface properly in BoxScoreView rendering (WC sport check added but JSON path may differ).
16. **Streamlit dashboard stale** — tc-streamlit-dashboard may be serving old code. Need to restart service after API changes.
17. **Git workspace cleanup incomplete** — .bak files, empty dirs removed but duplicate projection files (CON@PHX.json + CON_at_PHX.json) still in Daily_Log.
18. **daily_picks.py import cleanup** — Line 26-27 imports correct_wc_team and serp_odds_scraper as two lines (fixed from one-line merge bug) but could be cleaner.
