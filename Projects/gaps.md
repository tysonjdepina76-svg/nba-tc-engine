# TC Pipeline Gaps — Full Truth (2026-07-19)

## WHAT WE HAVE (11 live endpoints)
- Root + Docs (GET /)
- System data (GET /system-data)
- Projections (GET /api/v1/projections?league=wnba|mlb|wc)
- Picks (GET /api/v1/picks?league=wnba|mlb|wc)
- Combos (GET /api/v1/combos?league=wnba|mlb|wc&min_edge=0)
- Live games (GET /api/v1/live)
- Boxscore (GET /api/v1/boxscore?league=wnba|mlb|wc&game_id=X)
- Accuracy (GET /api/v1/accuracy)
- Pregame combos (GET /api/v1/combos?mode=pregame)
- Combo detail (GET /api/v1/combos/{id})
- Health (GET /health)

## EXTERNAL DATA SOURCES — LIVE vs DEAD

### LIVE (working)
1. MLB StatsAPI (statsapi + pybaseball) — free, no key — live game data, boxscores, statcast
2. nba_api for WNBA — free, no key — scoreboard, boxscores, rosters
3. ESPN scrapers — free — schedules, scores, rosters
4. The Odds API (THEODDSAPI env) — BUSINESS TIER QUOTA MAXED — returns 401 until reset

### CAPPED (stay capped)
5. Serp_Api_key — capped at 50 req/run, 250/day — search_odds() for enrichment

### DEAD (purge references)
6. SDIO_API_KEY — 401 on all odds endpoints, invalid subscription
7. SGO_API_KEY — NBA-only tier, no WNBA support

## APIs WE NEED TO WIRE (NOT YET INTEGRATED)

### A. Balldontlie WNBA ($9.99/mo after 48hr free trial) — PRIORITY
- wnba.balldontlie.io — betting odds, player props, game stats, advanced stats
- Endpoints: /odds, /player_props, /stats, /games, /players, /teams
- WHY: Replaces dead SDIO + quota-maxed Odds API for WNBA lines
- Status: NOT WIRED — needs API key (free trial available)

### B. API-Football (RapidAPI) — World Cup stats
- 100 free requests/day
- Endpoints: fixtures, lineups, stats, in-play data, xG, shot maps
- WHY: World Cup context (possession, xG, shots) for model inputs
- Status: NOT WIRED — needs RapidAPI key

### C. Balldontlie MLB ($9.99/mo after 48hr free trial) — SECONDARY
- mlb.balldontlie.io — same company, betting odds, player props for MLB
- WHY: Backup for MLB odds when Odds API quota maxes
- Status: NOT WIRED — same API key as WNBA

### D. FIFA Balldontlie — TERTIARY
- fifa.balldontlie.io — World Cup group stage data
- Status: NOT WIRED

## DASHBOARD GAPS

### /nba-tc (https://true.zo.space/nba-tc)
7. ✅ Live games tab — WC columns wired
8. ✅ Combos tab — wired to /api/v1/combos
9. ⚠️ Picks tab — rendering but all SELF_EDGE (no real lines)
10. ⚠️ MLB pitching matchup panel — NOT BUILT
11. ⚠️ Column alignment — columns stuffed/unbordered on Chromebook

### /dashboard (https://true.zo.space/dashboard)
12. ✅ 5 buttons (WNBA,MLB,WC,Combos,System)
13. ✅ Combos button — wired to /api/v1/combos
14. ⚠️ Column alignment — same border/alignment issue
15. ⚠️ Live game cards — need professional borders

### Streamlit (https://tc-streamlit-dashboard-true.zocomputer.io)
16. ⚠️ Needs same combos integration
17. ⚠️ Column alignment + borders
18. ⚠️ Clutter cleanup

## CODE CLEANUP NEEDED
19. Dead adapters referencing SDIO/SGO — remove or comment
20. Duplicate boxscore files — 4 boxscore*.py in api/
21. Empty dirs and stale .bak files — already partially cleaned
22. Old Zo.space routes — audit for unused endpoints
23. nba_api_adapter.py — NBA off-season, disconnect
24. nfl_api_adapter.py — NFL off-season, disconnect

## PIPELINE HEALTH
25. picks.csv — append mode working, picks accumulate
26. picks.db — all picks marked SELF_EDGE until real lines return
27. tc_pipeline.db — graded picks table exists, used for accuracy
28. SerpAPI cap — installed at 50/run, 250/day
29. SerpAPI search — returns 0 results (key exhausted or query issue)
30. Combos — 126 WNBA, ~115 MLB, ~96 WC

## ACTION PLAN (in order)
1. Wire Balldontlie WNBA adapter → free trial key → real props/odds
2. Wire API-Football → RapidAPI key → WC stats
3. Build MLB pitcher vs batter panel → live diamond visualization
4. Add borders/alignment CSS to all 3 dashboards (Chromebook-friendly)
5. Clean dead SDIO/SGO references from adapters
6. Consolidate 4 boxscore files into 1
7. Disconnect nba/nfl adapters (off-season)
8. Push to GitHub + Google Drive
