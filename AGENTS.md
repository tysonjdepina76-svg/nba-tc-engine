# Workspace Index — true.zo.computer

## Current Status (2026-06-29 ~7:20 PM ET) — Fantasy Images LIVE ✅

### Sport Images Status
- WNBA ✅ 3 cards + 1 roundup (verified at 23:07 UTC)
- SOCCER ⏳ Ready — auto-runs when World Cup matches feed picks
- NBA ⏳ Ready — auto-runs on/off-season slate
- NFL ⏳ Ready — auto-runs when preseason/regular season matches feed picks (Aug 6+)
- MLB ⏳ Ready — auto-runs when matches feed picks
- NHL ⏳ Ready — auto-runs when matches feed picks

### Fantasy Images Pipeline (wired 2026-06-29)
- `Projects/fantasy_images.py` — generates per-player cards + sport roundups
- Wired into `Projects/daily_picks.py` lines 784-794 (tail step after picks + combos)
- Outputs: `reports/images/{SPORT}_{Player_Name}_{YYYYMMDD_HHMMSS}.png` + `{SPORT}_roundup_*.png`
- Verified: WNBA roundup + Satou Sabally/A'ja Wilson/etc cards generated this run

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
| `Projects/tc_dashboard.py` | Streamlit dashboard on :8510 |
| `Projects/consensus_engine.py` | Consensus picks — Odds API + SGO |
| `Projects/api_tc_unified.py` | Zo.space TC API — WNBA/MLB/WC with ESPN DK lines fallback |
| `Projects/build_pregame_combos.py` | DK combo builder |

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
| `Daily_Log/YYYY-MM-DD/slate_*.json` | Raw slate responses |
| `Daily_Log/worldcup/YYYYMMDD/props.json` | World Cup props |
| `Daily_Log/worldcup/YYYYMMDD/picks.csv` | World Cup picks |

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
