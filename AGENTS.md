## Current Status (2026-08-06 23:15 ET) — CALIBRATOR LIVE · 441 MLB PICKS

### 📊 DATABASE (VERIFIED 8/3)
- INDEX-level dedup: `(date, league, player, stat, matchup, direction, source)`
- **All time: 14,897 picks across 20 dates**
- **8/1: 685 picks** — 255 MLB + 430 WNBA
- **8/3: 301 WNBA picks** (0 graded — awaiting boxscores)

### ✅ GRADING — FIXED 8/3
- **regrade_picks.py**: flipped 4,188 of 5,781 picks (comparison was inverted)
- WNBA went from wild swings (10-100%) to realistic 42-56%
- MLB 7/31 went from 7.8% to 49.5%
- Commit applied to picks.db

### 🏀 WNBA MINUTES MODEL — TIERS ADDED 8/3
- `compute_features.py`: `classify_bench_role()` → starter / sixth_man / rotation / deep_bench
- `validate.py`: tier-specific MAE + opponent_pace + blowout_probability + player_age features
- Current MAE: 4.82 overall (target < 4.0) — 60.2% within ±5 min (8/7 run)
- Backfill in progress: 135/210 athletes fetched for 2026 (4,593 player-games); fetch_logs.py --max-calls 45 resumable, ~2 runs left
- 210 athletes in DB, 3,421 walk-forward predictions

### 🔑 API KEYS — ALL WIRED IN SECRETS
| Key | Env Var | Status | Daily Cap |
|-----|---------|--------|-----------|
| SportsDataIO | SPORTSDATAIO_API_KEY | ✅ LIVE — PRIMARY ODDS | 1,000 |
| ESPN | (public) | ✅ LIVE — BOXSCORES | 250 |
| TheOddsAPI Free | THEODDSAPI_FREE | 🚫 BURNED (40/25), resets 8pm ET | 25 |
| TheRundown | THERUNDOWN_API_KEY | ⚠️ 0 MLB, NFL/NBA only | 50 |
| SportsGameOdds | SPORTSGAMEODDS_API_KEY | ✅ LIVE — 200 OK | 1,000 |
| Discovery Labs | SDIO_DISCOVERY_LABS | ❌ 401 — KEY NOT ACTIVE (f573) | 0 |
| SerpAPI | SERPAPI_KEY | 🚫 0 searches left, resets Aug 19 | 3 |

### ✅ SERVICES — 3 UP
- tc-api: https://tc-api-true.zocomputer.io ✅
- tc-streamlit-dashboard: https://tc-streamlit-dashboard-true.zocomputer.io ✅
- tc-streamer: https://tc-streamer-true.zocomputer.io ✅

### 🚀 COMPLETED FIXES
- [x] Grading math flipped — 5,781 picks regraded (8/3)
- [x] Role tiers: classify_bench_role() in compute_features.py (8/3)
- [x] Context features: opponent_pace, blowout_probability, player_age (8/3)
- [x] Odds module fully wired into pipeline (9-file package, multi-provider cascade) (8/1)
- [x] _enrich_from_theoddsapi_free v2 uses odds module instead of inline API calls (8/1)
- [x] Local cap tracking — no burning calls on /me/usage (8/1)
- [x] Symlink bug fixed — _purge_symlinks() (8/1)
- [x] SportsGameOdds verified live (8/3) — key 073d94a... works

### 📁 KEY PATHS
- Pipeline: `/home/workspace/Projects/daily_picks.py`
- Grading: `/home/workspace/Projects/regrade_picks.py`
- Minutes model: `/home/workspace/Projects/wnba_minutes/`
  - Role tiers: `compute_features.py` (classify_bench_role)
  - Validation: `validate.py` (tier-specific + context features)
- Dashboard: `/home/workspace/Projects/tc_dashboard.py`
- Zo Dashboard: https://true.zo.space/nba-tc + https://true.zo.space/live-games
- DB: `/home/workspace/Projects/data/picks.db`
- Daily Log: `/home/workspace/Daily_Log/`
- Odds module: `/home/workspace/Projects/src/odds/`
- Secrets: `/root/.zo/secrets.env`

### 🔑 API CAPS — ACTIVE ENFORCEMENT (8/3 19:45 ET)

Single enforcement point: `src/api_cap_tracker.py` → `cap_check()` called before EVERY external API call.
Daily + hourly + monthly caps. All 3 stale tracker files purged. No more uncapped APIs.

| Module | Daily | Hourly | Monthly | Status |
|--------|-------|--------|---------|--------|
| espn | 250 | 50 | 250 | ✅ LIVE |
| odds_api (SportsDataIO) | 1,000 | 200 | 30,000 | ✅ LIVE |
| sportsdataio | 1,000 | 200 | 30,000 | ✅ REGISTERED |
| sportsgameodds | 1,000 | 200 | 30,000 | ✅ REGISTERED |
| serpapi | 3 | 3 | 100 | ✅ CAPPED (was 0=UNLIMITED) |
| therundown | 50 | 10 | 500 | ✅ CAPPED (was 500) |
| theoddsapi_free | 23 | 8 | 200 | ✅ CAPPED (resets 8pm) |
| sharp_api | 2,500 | 300 | 2,500 | ✅ |
| statsapi_mlb | 500 | 100 | 500 | ✅ |
| free_apis | 100 | 25 | 3,000 | ✅ ADDED |
| roster | 500 | 100 | 15,000 | ✅ ADDED |
| wnba_gen | 200 | 50 | 200 | ✅ |
| espn_odds | 250 | 50 | 250 | ✅ |
| api_fallback | 100 | 25 | 100 | ✅ |

### ✅ FIXES APPLIED 8/4 2:00 AM ET
- [x] Provider cascade reordered: SDIO + SGO enrichment added BEFORE theoddsapi_free
- [x] generate_combos_filtered wrapped in try/except (no more crash-on-combo)
- [x] DEFAULT_LINES killed — hard fail when all market_line <= 0.5
- [x] Result: 0 fake picks for WNBA (all 188 market_lines were 0.5 — correctly skipped)
- [x] Combos REWRITTEN 8/7 — now SINGLE-PLAYER STAT COMBOS (WNBA P+R+A/P+R/P+A, MLB PITCHING+BATTING), NOT cross-player parlays. generate_combos() in daily_picks.py rewritten to group by player.
- [x] Combos table purged 8/7 — stale 2-LEG/FULL-2LEG/FULL-3LEG/SAME-2LEG rows deleted (522 rows); delete-date+league added before insert so no stale rows linger.
### 🎯 COMBOS — SAME-PLAYER STAT COMBOS (NOT PARLAYS) — 8/7
- **Combos = single-player stat combos, NOT cross-player parlays.**
  - WNBA: P+R+A, P+R, P+A from a player's PTS/REB/AST.
  - MLB: PITCHING combo (SO/K) + BATTING combo (H/HR/RBI/R) per player.
- `generate_combos()` in `daily_picks.py` (~line 790) rewritten 8/7: groups all picks by player, sums stat projections/lines, derives edge + majority direction; same-player legs no longer skipped (old logic built cross-player parlays).
- Verified vs real 8/7 DB picks: WNBA 135 combos, MLB 51 combos.

- [x] Reversed-matchup doubling FIXED 8/7 in tc-api (`api/main.py`): `_game_key()` normalizes away_at_home / home_at_away into ONE canonical game. Applied to `/api/picks/by-game-structured` (8 WNBA labels -> 3 games, dedupes exact player+stat+direction, drops empty-player junk rows), `/api/v1/combos`, `/api/picks/top`, `/api/tc-alerts`. All dashboards fed by tc-api now show each game once.
### ✅ COMPLETED FIXES
### 🔄 CASCADE ORDER
1. SportsDataIO (PRIMARY — live odds, player props)
2. TheOddsAPI Free (resets 8pm, h2h/spreads/totals)
4. SportsGameOdds (fallback — LIVE)
5. TheRundown (NFL/NBA only)
6. ESPN (boxscores/grading only)
7. Derived Lines (final fallback: proj - 0.5)

### 🟡 NEEDS ATTENTION
- [ ] P2: Backfill remaining 4 athletes + full 2025 season for WNBA minutes model
- [ ] Discovery Labs key f573 returns 401 — contact Discovery Labs to activate subscription
- [ ] 8/3 WNBA picks need grading once boxscores available
- [ ] TheOddsAPI Free resets at 8pm ET — can then fetch fresh MLB odds

### ✅ FIXED 8/7 — COMBOS SEPARATED FROM PICKS
- [x] Combos show ONLY under the combos tab; each combo card shows projection + line + direction.
- [x] `api/main.py`: `_is_combo_stat()` strips WNBA PRA/PR/PA/P+R+A/P+R/P+A and MLB BATTING/PITCHING/'+' from `/api/picks/by-game-structured`, `/api/picks/top`, `/api/tc-alerts`. Combos endpoints (`/api/v1/combos`) unchanged — carry combined_projection + combined_line + direction.
- [x] Streamlit `tc_dashboard.py`: `load_today_picks` + tab1 filter combo stats.
- [x] Verified live: WNBA top = PTS/REB/AST/3PM/STL only (no PA/PR/PRA). Applies to ALL sport dashboards fed by tc-api incl. NFL (pre-season).
- Combos (WNBA PR/PA/PRA=P+R/A/P+A, MLB BATTING/PITCHING and any '+'-joined stat) are now STRICTLY under the combos tab/section ONLY.
- `api/main.py`: `_is_combo_stat(stat, league)` filters derived combos out of `/api/picks/top`, `/api/picks/by-game-structured`, `/api/tc-alerts`, `/api/v1/combos`. Regular WNBA picks = PTS/REB/AST/3PM/STL/BLK only.
- `tc_dashboard.py` (streamlit): `load_today_picks()` + Tab1 strip the same combo stats from the picks table.
- Combos API returns tc_projection + combined_line + direction under the combos tab.

### 📦 GITHUB SPORTS FREE DATA LAYER — WIRED 8/3
| Sport | Package | Status | Latest Data |
|-------|---------|--------|--------------|
| MLB | statsapi | ✅ LIVE | 8/3: 8 games |
| WNBA | sportypy | ✅ LIVE | 8/3: 3 games |
| NBA | nba_api | ✅ (offseason) | 0 games |
| NFL | nfl_data_py | ✅ LIVE | 272 games (preseason) |
| NHL | nhlpy | ⚠️ API mismatch | 0 games |
| NCAAF | — | ❌ No package | 0 games |
| NCAAB | cbbpy | ⚠️ API mismatch | 0 games |

- Free boxscores + schedules — no API keys, no rate limits
- Backfill script: `src/backfill_github_all_sports.py`
- Integration script: `src/integrate_github_sports.py`
- Cache: `data/github/sports/`
- Grading uses this for actuals comparison
