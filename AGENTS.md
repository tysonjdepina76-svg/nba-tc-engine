# Workspace Index — true.zo.computer

## Current Status (2026-07-02 ~4:00 PM ET) — World Cup Lineup Lock ✅
- **World Cup**: 11 games projected (3,564 player projections), all self-edge — Odds API 401 quota maxed, no DK/BetMGM lines
- **WC Top Picks**: Argentina ML 80%, Brazil ML 79%, Switzerland ML 73%, Colombia ML 73%, Spain ML 67%
- **WC Totals**: Croatia@Portugal OVER 2.5 (3.15 exp), England@Mexico OVER 2.5 (3.12), Austria@Spain OVER 2.5 (3.05), Belgium@USA OVER 2.5 (2.99), Norway@Brazil OVER 2.5 (2.94)
- **WNBA evening**: 3 games on schedule (ATL@WSH 7:30, DAL@CON 8:00, SEA@PHX 10:00 PM ET) — no late scratches detected from 1:30 PM cache
- **MLB evening**: CIN@MIL (in progress 6-2), MIA@COL (in progress 3-3), 6 more pending (CHW@CLE 6:40 PM through SD@LAD 10:10 PM)
- **Cache**: manifest written (`Daily_Log/cache_manifest.json`), 16 entries, WC TTL=2h, MLB TTL=3h
- **API budget**: 0 paid calls this run (within 3 max)
- **Email sent**: Both tysondepina99 + tysonjdepina76
- **Next**: 6:30 PM Final Pre-Tip + Combo Lock

## Current Status (2026-07-02 ~6:30 PM ET) — FINAL LOCK ✅
- **Picks**: 455 across 9 games (3 WNBA, 449 MLB, 0 World Cup picks) — 19 total games projected, 3 completed skipped
- **WNBA**: 6 picks (PTS/REB OVERS, self-edge), 0 combos — DK player props not posted (expected: DK posts WNBA 30-60 min before tip)
- **MLB**: 449 picks across 6 evening games — pitcher OVERS dominate top edges (hits_allowed, strikeouts)
- **World Cup**: 11 games projected, 0 picks — all self-edge, Odds API 401 (Business tier quota maxed)
- **Combos**: 0 across all sports (- no DK player lines available)
- **Top Edge**: Nathan Eovaldi (TEX@DET) hits_allowed OVER 0.5 → proj 9.3, edge +8.8
- **Top 5 MLB edges**: Eovaldi +8.8, Davis Martin +8.0 (CHW@CLE), Roki Sasaki +7.0 (SD@LAD), Bryce Miller +6.1 (LAA@SEA), Stephen Kolek +5.6 (TB@KC)
- **Top WNBA**: Amy Okonkwo (WSH) PTS+3.0/REB+3.0, Costanza Verona (DAL) PTS+2.2 ⚠️ OUT, Sydney Taylor (PHX) PTS+2.2, Paige Bueckers (DAL) PTS+2.0, Dominique Malonga (CON) PTS+2.0
- **🚨 Costanza Verona (DAL)**: Flagged OUT at 1:30 PM, still appears in picks — skip this wager
- **WNBA injuries**: Brionna Jones (ATL) OUT, Aaliyah Nye (ATL) OUT, Alanna Smith (DAL) Questionable (Concussion), PHX: Brochant/Mack/Whitcomb OUT
- **API budget**: 5 calls today, 5 remaining (10/day soft limit)
- **Health**: 5 secrets ✅, Dashboard :8510 ✅, DK Combos Engine :8515 ⚠️ 404, Soccer Combo Engine :8516 ⚠️ 404
- **Games upcoming**: WSH@ATL 7:30, DAL@CON 8:00, SEA@PHX 10:00; MLB: CHW@CLE ~7:10, STL@ATL ~7:20, DET@TEX ~8:05, TB@KC ~8:10, LAA@SEA ~9:40, SD@LAD ~10:10
- **Email sent**: Both tysondepina99@ + tysonjdepina76@
- **Next**: Boxscore captures (halftime ~8:30 PM, final ~10:30 PM)

## Current Status (2026-07-02 ~1:30 PM ET) — PRIMARY Slate Run ✅
- **Picks**: 708 across 23 games (3 WNBA, 9 MLB, 11 World Cup) — all slates refreshed
- **WNBA**: 3 games (ATL@WSH 7:30 PM, DAL@CON 8:00 PM, SEA@PHX 10:00 PM), 6 picks — PTS/REB OVERS all self-edge (no DK player props yet), 0 combos
- **MLB**: 9 games (PIT@PHI in progress since 12:35 PM, 8 evening), 702 picks — top edges all pitcher hits_allowed/strikeouts OVERS (Nathan Eovaldi +8.8, Davis Martin +8.0, Michael Lorenzen +7.8)
- **World Cup**: 11 games, 0 picks ⚠️ — Odds API 401 on all /odds/ calls (Business tier quota maxed, expected). Self-edge TC projections generated for all 11 games (Austria@Spain, Croatia@Portugal, Algeria@Switzerland, Egypt@Australia, Cape Verde@Argentina, Ghana@Colombia, Morocco@Canada, France@Paraguay, Norway@Brazil, England@Mexico, Belgium@USA)
- **soccer_game_picks.csv bug**: Each WC game overwrites the file — only Belgium@USA survives in final output
- **Health**: 5 secrets loaded, dashboard :8510 alive, DK Combos Engine :8515 404, Soccer Combo Engine :8516 404
- **WNBA injuries**: Heavy — Brionna Jones (ATL) OUT, Aaliyah Nye (ATL) OUT, Amoore/Citron (WSH) Questionable, Alanna Smith (DAL) Questionable (Concussion), Ezi Magbegor (SEA) Probable, 3 PHX players OUT (Brochant, Mack, Whitcomb)
- **API calls**: 5 this run (3 SGO slates + 2 consensus), api_call_budget.json reset for July 2
- **Email sent**: Both tysondepina99 + tysonjdepina76
- **Next**: 6:30 PM Final Pre-Tip + Combo Lock

## Current Status (2026-07-02 ~1:00 PM ET) — /nba-tc LiveStatsPanel Case-Insensitive Fix ✅

- **Bug**: `/api/tc?mode=live-stats` returns `actual` keys lowercase (pts/reb/ast/tpm/stl/blk for WNBA; h/hr/rbi/r/sb/avg for MLB), but config used uppercase keys → live tab cells were blank even when data was present
- **Fix pushed** (`/nba-tc` LiveStatsPanel `<tr>`):
  - 8-level fallback chain: `tc_K → actual.tc_K → K → actual.K → tc_k → actual.tc_k → k → actual.k → '-'`
  - Both upper and lower case covered regardless of config casing
  - Verified via `get_space_route` — full route re-read shows updated markup with `<td className="px-2 py-1 font-medium">` for name column
- **MLB config** (`MLB_STAT_CONFIG`): stays lowercase (h/hr/rbi/r/sb/avg with tc_h/tc_hr/tc_rbi/tc_r/tc_sb/tc_avg field paths) — no change needed
- **WNBA live tab empty until 7:30 PM ET** — confirmed `mode=live_stats` returns `"players":[]` for all 3 games (WSH@ATL 7:30, DAL@CON 8:00, SEA@PHX 10:00 PM ET), status=Scheduled, clock=0.0
- **7/2 WNBA cache populated**: proj_WNBA_{ATL_at_WSH, DAL_at_CON, SEA_at_PHX}.json — 12/15/13 players per game, all with PTS/REB/AST/3PM/STL/BLK projections
- **Space errors**: get_space_errors.count = 0 after sync
- **Next**: Verify MLB live tab renders real numbers; WNBA live tab will populate at tip-off

## Current Status (2026-07-01 ~11:30 PM ET) — /nba-tc + Registry Sync ✅
- **Runtime error stopped firing**: get_space_errors.count = 0 after ErrorBoundary + registry-first guard patch. Cached server_log entries are pre-fix (from 00:09 and 00:15 UTC), not new
- **Sports registry synced**: Python (`/home/workspace/Projects/sports_registry.py`) and frontend (`/nba-tc REGISTRY`) now agree — MLB = BOOK_LINES, WNBA = TC_ENGINE, NHL = COMING_SOON

## Current Status (2026-07-01 ~8:00 PM ET) — /nba-tc MLB Crash Fixed ✅
- **/nba-tc MLB render bug fixed**: MLB API returns `mode: "live"` (not "dk-only") with null `tc_combined/tc_line`; MLB players lack `p.symbols` array. Page now guards with `result.away && result.home`, null coalesces metrics, and uses sport-aware `cfg.symbol` fallback in StatLeaders topSymbol.
- **Fix date**: 2026-07-01 ~8:00 PM ET

## Current Status (2026-07-01 ~4:00 PM ET) — World Cup Lineup Lock ✅
- **World Cup**: 12 games projected (self-edge only), 324 player projections, 0 picks ⚠️ — Odds API 401 quota exhausted. All projections use TC self-edge engine (no DK/BetMGM lines)
- **Today's WC games**: BEL@SEN 4PM ET (60% Belgium, 2.99 xG OVER 2.5), USA@BIH 8PM ET (58% USA, 2.82 xG OVER 2.5), ENG@COD noon (completed)
- **WNBA**: 3 games cached from 1:30 PM — ATL@WSH (7:30), DAL@CON (8:00), SEA@PHX (10:00). No late scratches. DK props not yet posted
- **MLB**: 14 games cached from 1:33 PM, 10 evening games upcoming
- **Health**: 5 secrets loaded, dashboard :8510 alive, DK Combos Engine :8515 404, Soccer Combo Engine :8516 404
- **API calls**: 1 SGO this run, ~5 total today — well under budget. Odds API 0 calls (quota maxed)
- **Cache**: 29 entries in cache_manifest.json — WC TTL=2h, MLB TTL=3h, WNBA TTL=5h
- **⚠️ picks.csv overwritten by WC-only run** — MLB/WNBA proj files intact for 6:30 PM rebuild
- **Email sent**: Both tysondepina99 + tysonjdepina76
- **Next**: 6:30 PM Final Pre-Tip + Combo Lock

## Current Status (2026-07-01 ~1:30 PM ET) — PRIMARY Slate Run ✅
- **Picks**: 1,115 across 20 games (3 WNBA, 14 MLB, 3 World Cup) — all slates refreshed
- **WNBA**: 3 games (ATL@WSH 7:30 PM, DAL@CON 8:00 PM, SEA@PHX 10:00 PM — all Jul 2), 6 picks — PTS/REB OVERS (Amy Okonkwo PTS+3.0, REB+3.0; Costanza Verona PTS+2.2; Sydney Taylor PTS+2.2; Paige Bueckers PTS+2.0; Dominique Malonga PTS+2.0), 0 combos (no DK player props yet)
- **MLB**: 14 games (CHW@BAL 12:35 PM in-progress, TEX@CLE 1:10 PM in-progress, DET@NYY 1:35 PM upcoming), 1,109 picks, 765 non-zero edge — top edges all pitcher hits_allowed OVERS (MacKenzie Gore +5.2, Joey Cantillo +4.0, Zac Gallen +4.0)
- **World Cup**: 3 games (COD@ENG, SEN@BEL, BIH@USA), 0 picks ⚠️ — all 3 returned "No data" (3rd consecutive run with 0 WC picks)
- **Health**: 5 secrets loaded, dashboard :8510 alive, DK Combos Engine :8515 404, Soccer Combo Engine :8516 404
- **WNBA injury**: Heavy — Costanza Verona (DAL) OUT but still in our picks 🚨; Brionna Jones (ATL) OUT; Ezi Magbegor (SEA) OUT; Jordan Horston (SEA) OUT; A'ja Wilson (LV) OUT; Caitlin Clark (IND) OUT; Satou Sabally (NY) OUT. 43 total injuries logged to cache.
- **API calls**: 4 this run (3 SGO slates + 1 consensus), api_registry.json + api_call_budget.json + cache_manifest.json updated
- **Top edge**: MacKenzie Gore (TEX@CLE) hits_allowed OVER 2.5 → proj 7.7, edge +5.2
- **Email sent**: Both tysondepina99 + tysonjdepina76
- **Next**: 6:30 PM Final Pre-Tip + Combo Lock

## Current Status (2026-06-30 ~1:30 PM ET) — PRIMARY Slate Run ✅
- **Picks**: 1,178 across 19 games (3 WNBA, 1,175 MLB, 0 World Cup) — all slates refreshed
- **WNBA**: 1 game (LV@NY — Commissioner's Cup Final, 7:00 PM ET), 3 picks — PTS OVERS (A'ja Wilson +2.5, Chennedy Carter +2.5, Satou Sabally +2.0), 0 combos (no DK player props yet — expected at 1:30 PM)
- **MLB**: 15 games (CHW@BAL first pitch 6:35 PM ET), 1,175 picks, 805 with non-zero edge — top edges all pitcher UNDERs on fringe SPs (Noah Cameron -4.4, Brandon Sproat -3.7, Brandon Pfaadt -3.6)
- **World Cup**: 3 games, 0 picks ⚠️ — all 3 games (NOR@CIV, SWE@FRA, ECU@MEX) returned "No data" (missing projection data for international teams)
- **Health**: 5 secrets loaded, dashboard :8510 alive, DK Combos Engine :8515 404 (non-critical), Soccer Combo Engine :8516 404
- **WNBA injury**: LV@NY CLEAN — both teams at full strength for Cup Final. Jovana Nogic (PHX) OUT season.
- **API calls**: 4 this run (3 SGO slates + 1 consensus), api_registry.json + api_call_budget.json + cache_manifest.json updated
- **Top edge**: Noah Cameron (KC) hits_allowed UNDER 5.7 → proj 1.3, edge -4.4
- **Email sent**: Both tysondepina99 + tysonjdepina76
- **Next**: 6:30 PM Final Pre-Tip + Combo Lock

## Current Status (2026-06-30 ~1:00 AM ET) — NFL Adjustments + Metrics LIVE ✅

### Sport Images Status
- WNBA ✅ 3 cards + 1 roundup (verified at 23:07 UTC)
- SOCCER ⏳ Ready — auto-runs when World Cup matches feed picks
- NBA ⏳ Ready — auto-runs on/off-season slate
- NFL ✅ **Stats wired via sport_config.py (NEW)** — auto-runs when preseason/regular season matches feed picks (Aug 6+)
- MLB ⏳ Ready — auto-runs when matches feed picks
- NHL ⏳ Ready — auto-runs when matches feed picks

### NFL Stats + Adjustments (wired 2026-06-30)
- `sport_config.py` — added 11 NFL StatProfiles (pass_yds, rush_yds, rec_yds, pass_td, rush_td, rec_td, receptions, ints, sacks, completions, attempts)
- `NFL_ADJUSTMENTS` dict with 5 multipliers: injury, pace (fast/medium/slow), defense (elite/good/avg/poor), home_away (home/away/neutral), team_total (high/medium/low + scaling_factor 0.015)
- `apply_nfl_adjustments(base_proj, injury, pace, defense, home_away, team_total)` — multiplies all factors, returns adjusted projection
- Verified Mahomes 300 pass_yds @ KC home + good def + fast pace + team_total 50.5 → adjusted 365.19 yds

### Industry-Standard Metrics (wired 2026-06-30)
- `src/domain/metrics.py` — 13 functions covering NBA/WNBA (PER, WS, Four Factors, TS%), NFL (DVOA, OffRtg/DefRtg), MLB (wRC+, FIP), SOCCER (xG), NHL (Corsi, PDO), plus Elo class, consensus_line(), sharp_money()
- Sport-aware dashboard panel via `Projects/tc_dashboard.py:render_metrics(sport, matchup)` — shows PER/WS/TS% for NBA/WNBA, wRC+/FIP for MLB, xG/xGA for soccer, OffRtg/DefRtg for NFL, Corsi/PDO for NHL
- All sports: Team Elo + Consensus Line + Sharp Money panels

### Fantasy Images Pipeline (wired 2026-06-29)
- `Projects/fantasy_images.py` — generates per-player cards + sport roundups
- Wired into `Projects/daily_picks.py` lines 784-794 (tail step after picks + combos)
- Outputs: `reports/images/{SPORT}_{Player_Name}_{YYYYMMDD_HHMMSS}.png` + `{SPORT}_roundup_*.png`
- Verified: WNBA roundup + Satou Sabally/A'ja Wilson/etc cards generated this run

### Backtest Coverage (2026-06-30)
- WNBA: 1,415 picks graded (48.8% hit rate, all OVER — TC design)
- WC 6/29: 282 graded (55.0% hit rate after 14-day boxscore pull)
- Pull commands: `python3 Projects/wc_boxscore_backtest.py --dates 20260618-20260630` + `python3 Projects/wnba_backtest_full.py`
- Reports saved to `/home/workspace/Reports/{wc,wnba}_backtest_*_20260630.csv`

### Task Status
1. OddsAPI auto-enable 📅 July 1, 2026
2. NFL preseason wiring 📅 Aug 6, 2026
3. Backtest ⏳ Resumes July 2, 2026 (after OddsAPI activates)

## Current Status (2026-06-29 ~6:30 PM ET) — FINAL LOCK ✅
- **Picks**: 1,482 across 16 games (3 WNBA, 1,038 MLB, 441 World Cup) — all projections refreshed
- **WNBA**: LV@NY — 3 picks (PTS OVERS), 0 combos (no DK player props — expected, DK posts WNBA props late)
- **MLB**: 13 games all upcoming — top edges all UNDER on fringe SP strikeouts/hits_allowed (Tyler Alexander -11.3 K best edge)
- **World Cup**: PAR@GER finished 1-1 (EOR), JPN@BRA finished 1-2 (FT), MAR@NED 9PM ET upcoming — 12 combos (4 per match, fouls OVER props, all self-edge ~-0.024)
- **Combos**: 12 total (all WC), 0 WNBA (no DK lines), 0 MLB (no qualified multi-leg) — build_pregame_combos.py errored (too many values to unpack), inline combo builder in daily_picks.py worked
- **Health**: Secrets ✅, Dashboard :8510 ✅, DK Combos Engine :8515 ⚠️ 404, Soccer Combo Engine :8516 ⚠️ 404
- **API budget**: Cache file stale (June 27) — shows 2 calls/day, needs refresh
- **⚠️ picks.csv overwritten by WC-only run at 4PM** — MLB/WNBA fully rebuilt this run, no data loss
- **Email sent**: Both tysondepina99 + tysonjdepina76
- **Next**: Boxscore captures (halftime 8:30 PM, final 10:30 PM), backtest at 2AM

## Current Status (2026-06-29 ~4:00 PM ET) — World Cup Lineup Lock ✅
- **WC Lineups CONFIRMED**: PAR@GER (4:30 PM), MAR@NED (9:00 PM), JPN@BRA completed (1-0)
- **WC picks**: 441 (230 PAR@GER + 211 MAR@NED), 8 combos — self-edge engine (no DK props on free tier)
- **WC top edge**: GER players PASSES OVER 35 → proj 39.2, edge +4.2 (all 11 German starters above the line)
- **WNBA**: LV@NY 7PM — no DK props yet (expected closer to tip), cached from 1:30 PM
- **MLB**: 13 evening games cached (proj files intact from 1:30 PM), first pitch 4:35 PM (CHW@BAL)
- **API calls**: 1 SGO this run, ~5 total today — well under budget
- **Cache**: manifest.json updated, WC TTL=2h, MLB TTL=3h
- **⚠️ picks.csv overwritten by WC-only run** — MLB/WNBA picks lost from 1:30 PM; proj files intact for 6:30 PM run to rebuild
- **Health**: 5 secrets loaded, dashboard :8510 alive
- **Emails sent**: Both tysondepina99 + tysonjdepina76
- **Next**: 6:30 PM Final Pre-Tip + Combo Lock

## Current Status (2026-06-29 ~1:30 PM ET) — PRIMARY Slate Run ✅
- **Pipeline**: 17 games (1 WNBA, 13 MLB, 3 WC), 1,717 picks — all slates refreshed
- **WNBA**: 1 game (LV@NY), 3 picks — PTS OVERS (A'ja Wilson +2.5, Chennedy Carter +2.5, Satou Sabally +2.0), no DK props yet (tips tomorrow 7PM)
- **MLB**: 13 games (CHW@BAL first pitch 6:35 PM), 1,065 picks — pitcher unders dominate top edges (Tyler Alexander -11.3 K)
- **WC**: 3 games (JPN@BRA in progress 1-0, PAR@GER 4:30 PM, MAR@NED 9:00 PM), 649 picks self-edge, 667 proj entries
- **Health**: 5 secrets loaded, dashboard :8510 alive, DK Combos Engine :8515 404 (non-critical), api_registry.json created
- **WNBA injury**: Minimal — ESPN API no injuries, WNBA.com 404. Manual check recommended before lock.
- **API calls**: 4 this run (3 SGO slates + 1 Odds API), cache_manifest.json updated
- **Top edge**: Tyler Alexander (TEX@CLE) strikeouts UNDER 11.5 → proj 0.3, edge -11.3

## Key Paths

### Core Engine
| Path | Purpose |
|------|---------|
| `Projects/daily_picks.py` | Main engine — WNBA uses dedicated TC engine (wnba_tc_engine.py) with ESPN Core API season stats + TC math instead of raw roster only |
| `Projects/tc_dashboard.py` | Streamlit dashboard on :8510 — **SPORTS TC — Multi-Sport Analytics** (NBA/MLB/WNBA/SOCCER/NFL/NHL). Has sport-aware `render_metrics()` panel |
| `Projects/consensus_engine.py` | Consensus picks — Odds API + SGO |
| `Projects/api_tc_unified.py` | Zo.space TC API — WNBA/MLB/WC with ESPN DK lines fallback |
| `Projects/build_pregame_combos.py` | DK combo builder (tightened: WC filter to fouls+shots+yellow+red, force UNDER if edge_pct ≤ 0.05) |
| `sport_config.py` | Sport configs + NFL stats + `NFL_ADJUSTMENTS` 5-multiplier system + `apply_nfl_adjustments()`. **2026-06-30 — Sport Show stat menus wired**: MLB added `avg`/`ops`/`era`, NHL added `plus_minus`/`hits`/`pim`, SOCCER added `yellow_cards`/`red_cards`. NFL INT was already `pass_int`. NBA/WNBA PTS/REB/AST unchanged. Reference: `Documents/Sport_Shows_Stat_Menus.md` |

### Industry-Standard Metrics (2026-06-30)
| Path | Purpose |
|------|---------|
| `src/domain/metrics.py` | 13 metrics: per, win_shares, Elo class, consensus_line, sharp_money, dvoa, four_factors, ts_pct, offensive_rating, defensive_rating, xg, corsi, pdo |
| `src/domain/examples.py` | Runner that prints example values for all 13 metrics |

### Secrets
| Path | Content |
|------|---------|
| `/root/.zo/secrets.env` | ODDS_API_KEY, SPORTSGAMEODDS_API_KEY, SPORTSDATAIO_API_KEY, SPORTS_DATA_API_KEY |

### Dashboard & Monitoring
| Path | Purpose |
|------|---------|
| `sports_betting_dashboard/` | Structured dashboard folder |
| `sports_betting_dashboard/scan.sh` | Health scan |

### Data — Live Output
| Path | Purpose |
|------|---------|
| `Daily_Log/last_run.json` | Latest pipeline run summary |
| `Daily_Log/YYYY-MM-DD/picks.json` | Full picks with metadata |
| `Daily_Log/YYYY-MM-DD/proj_MLB_*.json` | Per-game MLB projections |
| `Daily_Log/YYYY-MM-DD/proj_WNBA_*.json` | Per-game WNBA projections |
| `Daily_Log/YYYY-MM-DD/proj_NFL_*.json` | Per-game NFL projections (Aug 6+) |
| `Daily_Log/YYYY-MM-DD/slate_*.json` | Raw slate responses |
| `Daily_Log/worldcup/YYYYMMDD/props.json` | World Cup props |
| `Daily_Log/worldcup/YYYYMMDD/picks.csv` | World Cup picks |

### Backtests
| Path | Purpose |
|------|---------|
| `Projects/wc_boxscore_backtest.py` | Pull + parse WC boxscores (14-day range) |
| `Projects/wc_backtest_recent.py` | WC hit-rate grader (crash-hardened, 100-row batching, edge>0.05 threshold) |
| `Projects/wnba_backtest_full.py` | Full WNBA backtest across all `proj_WNBA_*.json` files |
| `Reports/wc_player_stats_YYYYMMDD.csv` | WC player boxscores |
| `Reports/wc_matches_YYYYMMDD.csv` | WC match boxscores |
| `Reports/wnba_backtest_full_YYYYMMDD.csv` | Full WNBA backtest grading (1415 rows) |
| `Reports/wnba_backtest_direction_YYYYMMDD.csv` | WNBA direction split (all OVER — TC design) |

### Zo.Space Routes
| Route | Handler |
|-------|---------|
| `/` | Homepage |
| `/worldcup` | World Cup props dashboard — 12 matches, stat leaders per category |
| `/dk-combos` | DK combo lines + TC-qualified picks — NBA/WNBA/MLB |
| `/api/tc` | TC projections — `?sport=WNBA&away=ATL&home=GS` |
| `/api/dk-lines` | Multi-book DK lines (SGO → ESPN → Odds API tiered) |
| `/api/worldcup-props` | World Cup player props + edges |
| `/api/pipeline-health` | Full diagnostic with API keys, connectivity, data integrity |
| `/api/combo-prob` | Game-by-game combo hit probabilities |
| `/api/daily-log` | Daily picks from Daily_Log |
| `/api/combos` | TC-qualified player props |
| `/api/wnba-boxscores` | WNBA minutes leaders + closing lineups |
| `/api/env-check` | Secrets/environment check |
| `/api/backtest` | Historical hit-rate data |

### Services
| Service | Port | Status |
|---------|------|--------|
| Streamlit Dashboard | :8510 | Running |
| Zo.Space (Hono/Bun) | :3099 | Running |
| DK Combos Engine (external) | dk-combos-engine-true.zocomputer.io | Running |

## Pipeline Routine (All Times ET — Health Check Precedes Every Run)

| Time | Description |
|------|-------------|
| 1:30 PM ET | Slate refresh + injury scan + DK lines pull |
| 6:30 PM ET | Final projections + combo generation |
| 8:30/10:30 PM ET | Boxscore captures (halftime/final) |
| 2:00 AM ET | Daily backtest |
| 4:00 AM ET | System cleanup |

## Key Rules
- NBA and NHL are OFF-SEASON — skip entirely
- SGO V2 API: DEFAULT PAGE SIZE IS NOW 10 — all calls MUST include `limit=100` (applied: pipeline_master, dk_combos_engine, build_pregame_combos, api_scan)
- WNBA DK player props appear closer to game time (30-60 min before tip)
- ESPN DK odds (totals/spreads/ML) are time-sensitive — available during daytime, absent late night
- SGO key (SPORTSGAMEODDS_API_KEY) is rate-limited — ESPN fallback handles DK lines
- All API keys stored in /root/.zo/secrets.env — loaded by daily_picks.py and pipeline_master.py
- World Cup picks use self-edge engine (no FD/DK player props on free tier)
- Health checks use `pipeline_master.py --quick --dry-run` (lightweight, no external API calls) — NOT scan.sh
- Odds API Business trial: toa_live_t5d8p3n1 — auto-reverts to Pro July 26, 2026
- Always update this file after pipeline changes
- Trash directory: `Trash/obsolete_purge_20260627/` contains purged NBA/archive/dead code
- TC projection logic always picks OVER when tc > line (UNDER-pick design in NBA/WNBA is intentional, not a bug — backtest is direction-aware)
