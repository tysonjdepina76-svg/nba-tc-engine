# Workspace Index — true.zo.computer

## Current Status (2026-07-19 ~12:55 PM ET) — PIPELINE GAPS FIXED

### Today's Data
- **picks.db**: 486 picks (WNBA: 210, MLB: 212, WC: 64) — SELF_EDGE signal (external APIs down)
- **combos**: API returns date-filtered combos; ~147 WNBA, 115 MLB, 96 WC
- **tc_pipeline.db**: 6,238+ graded picks
- **last_run.json**: MLB=212, WNBA=210, WC=64

### Gaps Fixed (2026-07-19 12:55 PM)
1. **Import bug** — `daily_picks.py` line 26 had merged `correct_wc_teamfrom serp_odds_scraper` (fixed)
2. **Combo API date filter** — `/api/v1/combos` now filters by today's date (was returning mixed dates)
3. **Zero-line projections** — `generate_projections.py` no longer generates fake book lines (line=0 across sports, letting SerpAPI enrich with real lines)
4. **Signal propagation** — SerpAPI-enriched picks now carry `signal=SERPAPI` through to DB
5. **WC combo defs** — 6 combo types: G+A, S+PS, S+SOT, T+S, T+P, S+T
6. **Combo Tab wired** — /nba-tc dashboard has "🔥 Combos" tab fetching from API

### ⚠️ ACTIVE BLOCKER: External APIs Down
- **SDIO** (SportsDataIo key): 401/404 on all odds endpoints — key invalid or tier doesn't include odds. WNBA get 401 "invalid subscription", MLB get 401, WC endpoint was producing 404.
- **SerpAPI**: queries return 0 results — SerpAPI key may be exhausted or search params need tuning
- **Odds API**: Business tier quota maxed (known)
- **SGO API**: Does NOT support WNBA (NBA-only tier)
- **RESULT**: All 486 picks are self-edge (no real market lines). Pipeline infrastructure is correct — needs working API keys to populate.

### Infrastructure (working)
- **Zo.space /nba-tc**: https://true.zo.space/nba-tc (combos tab wired, 4 tabs)
- **Zo.space /dashboard**: https://true.zo.space/dashboard
- **Streamlit**: https://tc-streamlit-dashboard-true.zocomputer.io (port 8510)
- **API**: https://tc-api-true.zocomputer.io (:8000, 28 endpoints)
- **Combo API**: https://tc-api-true.zocomputer.io/api/v1/combos?league=mlb

### Key Paths
- **Picks engine**: Projects/daily_picks.py (line 26 import fixed, line 111 split)
- **SerpAPI enrichment**: Projects/daily_picks.py → enrich_lines_via_serpapi() — calls Projects/serp_odds_scraper.py
- **Projection generators**: Projects/generate_projections.py (now produces line=0 across all sports)
- **API**: Projects/api/main.py (port 8000, combo date filter at line 725)
- **Streamlit dashboard**: tc_engine/dashboard/tc_dashboard.py (port 8510)
- **Data**: Daily_Log/YYYY-MM-DD/ · Projects/data/ (picks.db + tc_pipeline.db)
- **Combo builder**: Projects/build_pregame_combos.py

### Automation
- **Daily Sports Picks Update**: Runs 1:30 PM ET — `generate_projections.py --sport all` then `daily_picks.py --sport wnba/mlb/wc`

### ⚠️ CONTACT TRUTH
- ONLY phone: 508-840-0794 (SMS +15088400794)
- 508-639-4473 is DEAD — never use
- Email: tysonjdepina76@gmail.com / tysondepina99@gmail.com
