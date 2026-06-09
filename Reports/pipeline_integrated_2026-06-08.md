# TC Pipeline Integrated Report — 2026-06-08

## Health Check ✅ All green
- **SGO API key** loaded from `/root/.zo/secrets.env` by `/api/tc` runtime (was False before)
- **ODDS API key** loaded (tier 3 enabled, key is invalid — see Gap #2)
- **ESPN DraftKings embedded** fallback working (game total/ML/spread for NBA + WNBA)
- **Live-stats mode** wired (WNBA: 3 games, 2 In Progress; NBA: 1 game Scheduled)
- **DK player props** flowing: 16 of 30 NBA picks have real DK lines (SGO v2 oddID parser)

## Today's Slate (real run via `bash Scripts/refresh_daily_data.sh`)

| Sport | Matchup | TC Picks | DK Lines | Combo Legs | Signal |
|---|---|---|---|---|---|
| NBA | SAS@NYK | 30 | 16 | 105 | OVER |
| WNBA | NY@CON | 12 | 0 | 0 | NO MARKET |
| WNBA | IND@WSH | 12 | 0 | 0 | NO MARKET |
| WNBA | SEA@LV | 18 | 0 (game only) | 66 | UNDER |

**Top NBA edge** (DK line vs TC): De'Aaron Fox PTS OVER 14.5, TC 17.9, **+3.4 edge**.

## Pipeline Stack
```
refresh_daily_data.sh (8 AM ET automation)
  ├── step 1: daily_picks.py NBA → dk_scrape_NBA.json (30 picks, 16 with DK)
  ├── step 1: daily_picks.py WNBA → dk_scrape_WNBA.json (42 picks, 0 with DK)
  └── step 2: build_pregame_combos.py → combos_*.md + combos_*.json (171 legs)
       (uses tc_math.py for PRA/PR/PA + 40-min WNBA normalization)
```

## Gaps (with fix path)
1. **WNBA player props empty** — SGO v2 subscription is NBA-only. Options:
   - Add WNBA to SGO plan (~$30/mo add-on)
   - Get a working The Odds API key (current value `toa_live_t5d8p3n1` returns INVALID_KEY)
2. **ODDS_API_KEY invalid** — stored key doesn't match account. User needs to log into the-odds-api.com, copy the live key, and update `/root/.zo/secrets.env`.
3. **5 PM automation script** (`daily_tip_report.py` + `generate_report.py`) works but uses a different report format than the 8 AM one. Could merge into one canonical pregame report.

## Automations (all active)
| ID | Time (ET) | Title | Next Run |
|---|---|---|---|
| fc811907 | 8:00 AM | Daily TC Pipeline Status | 2026-06-09 08:00 |
| 3d283c4b | 9:00 AM | TC Daily Pick Log for NBA & WNBA | 2026-06-09 09:00 |
| 658fbbbb | 5:00 PM | NBA/WNBA Pre-Tip Report | 2026-06-09 17:00 |

## zo.space Live Routes
- https://true.zo.space/nba-tc — TC dashboard (defaults to today's first slate game, missing-keys banner, live tab)
- https://true.zo.space/api/tc — TC engine (4-tier odds fallback: SGO → ESPN DK → Odds API → WNBA game-only)
- https://true.zo.space/api/combos — auto combo generator (7 combos for SEA@LV today)

## Files written today
- `/home/workspace/Daily_Log/2026-06-08/` — 17 files (slate, proj, combos, dk_scrape, picks)
- `/home/workspace/Daily_Log/refresh_daily_data_20260608.log` — full run log
- `/home/workspace/Daily_Log/last_run.json` — latest summary
- `/home/workspace/Reports/pipeline_integrated_2026-06-08.md` — this report
