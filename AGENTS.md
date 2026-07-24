# Workspace Index — true.zo.computer

## Current Status (2026-07-24) — VERIFIED + CORRECTED

### BACKTEST TRUTH
- **84 WNBA picks from 7/19 properly graded**: 51 hits, 33 misses = 60.7% hit rate
- **3,094 graded_picks rows are junk** — imported from CSVs that were mostly line=0 projections (no real market lines). 842 zero-line entries, 24 fake "wins" (Mookie Betts line=0 auto-graded hit). Only the picks table has real data.
- **+$1,759 profit claim**: Unverified — based on the junk data.

### ROSTERS — WIRED (2026-07-24)
- **Roster loader**: `src/roster_loader.py` — rebuilt from .pyc bytecode. Loads 4 JSON files (783 MLB, 208 WNBA, 545 NBA). Provides `enrich_player()`, `enrich_pick()`, `resolve_team_name()`.
- **Wired into daily_picks.py** via `enrich_via_rosters()` — position, team_name, jersey, player_id added to all picks going forward.
- **Roster files**: `data/rosters/{mlb,wnba,nba,nfl}_rosters.json` — 4 files, NOT 45. Combined indexes per sport.

### DASHBOARD — FIXED & LIVE
1. **WC fully purged** from SPORTS, sportColor, sportEmoji, STAT_LABELS, stat key, combos league selector, combos fetch
2. **Combos tab reachable** — "combos" in activeTab union, 🔥 COMBOS button in nav, /api/picks/combos endpoint wired
3. **Live box-score view** — BoxScoreView uses boxScores only, removed dead liveGames/LiveGame refs, removed broken live-dashboard fetch
4. **Stat keys completed**:
   - WNBA: PTS, REB, AST, STL, BLK, 3PM, FG%, FT%, DREB, OREB, TO, PRA
   - MLB: H, R, RBI, HR, AVG, OBP, SLG, OPS, 2B, 3B, SB, BB
5. **display_stats → boxscore handshake** — `live_boxscore.py` WNBA parser (L251) and MLB parser (L284) set display_stats = display dict
6. **Live-dashboard fallback** at `/api/live-dashboard` uses fetch_all_boxscores (L146), returns valid JSON

### API — VERIFIED (2026-07-24)
- /health ✅ | /picks ✅ | /stats ✅ | /combos ✅ | /backtest ✅ | /backtest/report ✅

### API CAP ENFORCEMENT — INSTALLED
- `live_boxscore.py` `_get()` function capped via `cap_check("site.api.espn.com")` — all ESPN boxscore calls throttled
- `main.py` `fetch_live_boxscores()` capped via `cap_check("site.api.espn.com")` — dashboard endpoint throttled
- Cap tracker: `Projects/src/api_cap_tracker.py` — logs warnings for unregistered callers, passes through

### 🔴 AUTOMATIONS — ALL PAUSED
- MLB Morning (9 AM), WNBA Morning (11 AM), Combo Refresh (1:30 PM), Evening Summary (6 PM), Daily Sports Picks Update
- Reason: Manual maintenance window — no automated runs until pipeline is fully verified

### ⚠️ KNOWN GAPS
- SerpAPI: monthly quota maxed (~8/1 reset)
- Odds API: Business tier quota maxed — MLB dead without it
- SDIO: dead key
- Fangraphs: 403 IP-blocked (statsapi still works)
- ESPN: game lines only, no player props (free tier)
- Email: SMTP not configured — using send_email_to_user() tool

### PIPELINE HEALTH
- WNBA: Working (self-edge via gen_wnba_today.py) but no games 7/23-7/24
- MLB: Broken — all projection lines are 0 (no live odds source)
- NFL: Off-season
- WC: Ended July 2026

### PERSONA
- **TC Pipeline Engineer** (d5301f09) — active.

### INFRASTRUCTURE
- Streamlit: :8510 (UP) | API: :8000 (UP)
- /nba-tc: https://true.zo.space/nba-tc (public, live)
- /dashboard: https://true.zo.space/dashboard (public, live)
- tc-api: https://tc-api-true.zocomputer.io (UP, clean restart)

### KEY PATHS
- Picks: `Projects/daily_picks.py` | WNBA Projections: `Projects/gen_wnba_today.py`
- Backfill: `Projects/backfill_projections.py`
- Box scores: `Projects/api/live_boxscore.py` | API: `Projects/api/main.py`
- Free APIs: `Projects/src/adapters/free_api_aggregator.py`
- Roster loader: `Projects/src/roster_loader.py` (rebuilt 7/24) | Cap tracker: `Projects/src/api_cap_tracker.py`
- Rosters: `data/rosters/{mlb,wnba,nba,nfl}_rosters.json` (4 files)
- Health: `Projects/src/daily_pipeline_health.py`
- Station: `Daily_Log/{date}/proj_*.json` · Picks DB: `Projects/data/picks.db`
- Backtest Archives: `Archives/backtests/` (21 tarballs, 499 files)

### ⚠️ CONTACT TRUTH
- ONLY phone: 508-840-0794 (SMS +15088400794). 508-639-4473 is DEAD.
- Email: tysonjdepina76@gmail.com / tysondepina99@gmail.com

### SELF-EDGE BACKTEST (2026-07-24) — FIXED
- **generate_projections.py is DEAD** — random.uniform(), IDENTICAL 13.5 PTS for all 21 WNBA players. ARCHIVED.
- **Real engine**: `tc_math.py → over_under_signal(test="selfedge")` driven by `gen_wnba_today.py` per-player projections
- **7/19 backtest**: 84 WNBA picks graded. **60.7% hit rate** (51/84). All UNDER direction.
- **Best stat by hit rate**: PTS 66.7%, P+R 66.7% | Worst: P+A 57.1%, P+R+A 52.4%
- **Best players**: 100% — Cheyenne Parker, Diamond DeShields, Brionna Jones, Diana Taurasi, Marina Mabrey, Kelsey Plum, Lexie Brown, Natasha Howard, Satou Sabally, Skylar Diggins-Smith, Teaira McCowan
- **Worst players**: 0% — Allisha Gray, Brittney Griner, DeWanna Bonner, Kahleah Copper, Arike Ogunbowale, Azura Stevens, Dearica Hamby
- **Full report**: `reports/BACKTEST_TRUTH_20260724.md`