# Workspace Index — true.zo.computer

## Current Status (2026-07-21 6:10 AM ET) — HEALTHY

### Today's Pipeline
- **810 picks**: MLB 810 (15 games), WNBA 0, WC 0
- **25 combos**: MLB 25
- **Signal**: All SELF_EDGE — SerpAPI key depleted (no real market lines)
- **Free API aggregator WIRED**: statsapi + nba_api + pybaseball live in daily_picks.py

### FIXES APPLIED (2026-07-21)
1. **Free API aggregator wired** — `src/adapters/free_api_aggregator.py` integrated into `daily_picks.py` import chain. `health_check()` and `get_live_stats()` imported. Runs every pipeline execution.
2. **GitHub sources fully wired** — `enrich_from_github_sources.py` + `github_line_sources.py` imported in `daily_picks.py`. Pipelines now enrich with live game-specific stats (not just season leaders). Source report runs every execution.
3. **Combos banner removed** — `/nba-tc` dashboard combos tab deleted
4. **Gap list generated** — `Daily_Log/2026-07-21/GAP_LIST.md` — 9 gaps with explanations
5. **Pushed to GitHub** — tysonjdepina76-svg/nba-tc-engine master branch updated.

### ⚠️ Known Gaps (see GAP_LIST.md for full details)
- SerpAPI: monthly quota maxed. Resets ~8/1.
- Odds API: Business tier quota maxed
- SDIO: dead key
- Fangraphs: 403 IP-blocked (statsapi still works)
- WNBA: 0 games today
- ESPN: game lines only, no player props (free tier)
- WC: 0 matches
- Email: SMTP not configured (Gmail OAuth works for manual)
- WC odds: depends on gap 2

### Active Automations (all zo:deepseek/deepseek-v4-pro)
- MLB Morning (9 AM), WNBA+WC (11 AM), Combo Refresh (1:30 PM), Evening Summary (6 PM)

### Infrastructure
- Streamlit: :8510 (UP) | API: :8000 (UP) | /nba-tc + /dashboard (UP)
- Proj files: Daily_Log/2026-07-21/proj_*.json · Picks: data/picks/*.csv

### Key Paths
- Picks: Projects/daily_picks.py | Projections: Projects/generate_projections.py
- WNBA gen: Projects/gen_wnba_today.py
- Free APIs: Projects/src/adapters/free_api_aggregator.py
- Quota: Daily_Log/serpapi_quota.json
- Gap list: Daily_Log/2026-07-21/GAP_LIST.md

### ⚠️ CONTACT TRUTH
- ONLY phone: 508-840-0794 (SMS +15088400794). 508-639-4473 is DEAD.
- Email: tysonjdepina76@gmail.com / tysondepina99@gmail.com
