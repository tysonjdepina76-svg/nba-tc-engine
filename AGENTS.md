# Workspace Index — true.zo.computer

## Current Status (2026-07-19 ~8:40 AM ET) — INVESTOR READY ✅

### Today's Data (ALL TEAMS VERIFIED)
- **picks.db**: 486 unique picks (MLB: 212, WNBA: 210, WC: 64) — ZERO duplicates
- **combos**: 522 precomputed combos (407 WNBA + 115 MLB); WC has no combo defs (soccer stats≠PRA)
- **tc_pipeline.db**: 6,238+ graded picks
- **last_run.json**: MLB=212, WNBA=210, WC=64

### Team Mapping Fix (2026-07-19) — CRITICAL ✅
- **MLB**: 150-player map in `mlb_team_lookup.py` — fixes garbage team assignments (Yordan→HOU not CHW, Mookie→LAD not CHW, etc.)
- **WNBA**: 40+ player map in `wnba_team_lookup.py` — Kelsey Plum→LA (not LV), Jewell Loyd→LV
- **WC**: 40-player national team map in `wc_team_lookup.py` — Kane→ENG (not ARG), Musiala→GER (not ARG), Vini→BRA (not ESP)
- **WNBA projections**: Hardcoded fallback in `generate_wnba_projections.py` when ESPN+combo DB return 0 players

### Live Dashboards (all verified 200 OK)
- **Zo.space /nba-tc**: https://true.zo.space/nba-tc
- **Zo.space /dashboard**: https://true.zo.space/dashboard
- **Streamlit**: https://tc-streamlit-dashboard-true.zocomputer.io (port 8510)
- **API**: https://tc-api-true.zocomputer.io (:8000, 28 endpoints)
- **Combo API**: https://tc-api-true.zocomputer.io/api/v1/combos (522 combos)

### Filing System
- **Cron**: 1:15 AM ET (projections) · 1:20 AM ET (picks: wnba/mlb/wc) · 1:23 AM ET (alerts)
- **Services**: tc-api (:8000) ✅ · tc-streamlit-dashboard (:8510) ✅

### Key Paths
- **Picks engine**: Projects/daily_picks.py
- **Team lookups**: Projects/mlb_team_lookup.py · Projects/wnba_team_lookup.py · Projects/wc_team_lookup.py
- **Projection generators**: Projects/generate_projections.py (MLB+WC) · Projects/generate_wnba_projections.py (WNBA)
- **API**: Projects/api/main.py (port 8000, 28 routes)
- **Streamlit dashboard**: tc_engine/dashboard/tc_dashboard.py
- **Data**: Daily_Log/YYYY-MM-DD/ · Projects/data/ (picks.db + tc_pipeline.db)
- **Combo builder**: Projects/build_pregame_combos.py (reads picks.db, writes combos_daily.json)

### Known Gaps
- **Odds API Business tier quota maxed** — WC has 24/192 self-edge picks; MLB and WNBA lines are 100% real from SDIO
- **NBA/NHL off-season** — pipeline handles this (NBA and NHL are NOT passed to daily_picks.py)
- **SerpAPI wired as fallback** — `enrich_lines_via_serpapi()` called from `load_projections()` for WNBA/WC when line==0; searches via SerpAPI for real player prop odds
- **WC combo defs populated** — 6 combo types: G+A, S+PS, S+SOT, T+S, T+P, S+T
- **WNBA ESPN roster fetch often returns 0** — hardcoded star fallback in generate_wnba_projections.py covers this

### ⚠️ CONTACT TRUTH
- ONLY phone: 508-840-0794 (SMS +15088400794)
- 508-639-4473 is DEAD — never use
- Email: tysonjdepina76@gmail.com / tysondepina99@gmail.com
