# Workspace Index — true.zo.computer

## Current Status (2026-06-29 ~6:20 AM ET) — World Cup refreshed ✅
- **Pipeline**: WNBA 0 upcoming, MLB 0 upcoming (both done for day), WC 3 upcoming (JPN@BRA, PAR@GER, MAR@NED)
- **WC refresh**: worldcup_picks.py ran successfully — 158 players, 649 props, self-edge (Odds API 401 — Business trial expired/paused)
- **WC outputs**: `Daily_Log/worldcup/20260629/{matches,props,picks}.json` + 12 TC combos via soccer_combo_engine
- **Daily picks**: 3 WC games, 649 picks, 12 combos qualified — all `WC PROPS LIVE (self-edge)`
- **DK lines gap**: No DK/FD player props available (free tier) — picks use self-edge engine
- **Health**: All checks pass — dashboard :8510 alive, last_run 6:20 AM ET

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
