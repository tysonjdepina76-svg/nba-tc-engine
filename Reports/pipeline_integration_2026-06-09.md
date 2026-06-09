# TC Pipeline Integration Report — 2026-06-09

## Summary
Integrated: 3 `/api/tc` live bugs fixed, 21 dead files archived, system map
created at `SYSTEM_MAP.md`, smoke tests green.

## 1. /api/tc fixes (3 live bugs)

1. **Secrets self-sourced** from `/root/.zo/secrets.env` inside the route. Before,
   zo.space runtime didn't have SGO/ODDS keys. Now both keys load on every call,
   `keys_status: {SGO: True, ODDS: True}, missing_keys: []`.

2. **`mode=live-stats` dispatched** to `buildLiveStats()`. Before, the page
   Live tab returned 0 games. Now: WNBA 3 games (2 In Progress + 1 Scheduled).

3. **SGO player-prop parser** rewritten to use `oddID` prefix (points/assists/
   rebounds/steals/blocks/threes) and `statEntityID` for player names. Before,
   parser expected `marketID` field that does not exist — DK player props were
   dropped silently. Now: 16 SAS@NYK props have real DK lines (was 0).

## 2. Smoke test (post-integration)

```
WNBA live-stats: 3 games
  NY 47 @ CON 37   In Progress
  IND 43 @ WSH 29  In Progress
  SEA @ LV         Scheduled

NBA SAS@NYK projection:
  keys_status: {SGO: True, ODDS: True}
  valid_props: 30
  with_dk_line: 16
  dk_total: 215.5
```

## 3. Code archived (21 files)

`Archives/INTEGRATION_2026-06-09_obsolete/`:
- `Projects/`: 10 files (diag_full, wnba_2026_jun23_tc, wnba_corrected,
  wnba_minute_proj, wnba_model_v2, wnba_tune_v1..v4, wnba_team_id_fix.json)
- Root: 11 files (_check_keys, _check_tc, patch_script, debug_sug,
  college_models, multi_sport_engine, nba_tc_pipeline, wnba_bt,
  SportsTC_Streamlit_App, run_dashboard.sh, run_streamlit.sh)
- Skills/nba-odds-api/3 superseded scripts (no longer imported anywhere)
- See `MANIFEST.md` in the archive for full reasoning.

## 4. Live code (kept in place)

Root:
- `daily_tip_report.py` (used by 5-PM ET automation)
- `generate_report.py` (used by 5-PM ET automation)

Projects/:
- `tc_math.py` (TC math, single source of truth)
- `daily_picks.py` (used by 9-AM ET automation + refresh_daily_data.sh)
- `build_pregame_combos.py` (used by refresh_daily_data.sh)
- `wnba_pipeline_v2.py` (active backtest pipeline, 14-day history)
- `build_hits_file.py` (utility imported by wnba_pipeline_v2.py)

Scripts/:
- `refresh_daily_data.sh` (used by 8-AM ET automation)
- `morning_briefing.py` + README (morning briefing)

## 5. System map

- `SYSTEM_MAP.md` (root, 258 lines) — full system map for any agent pickup
- `AGENTS.md` (root, 48 lines) — compact index pointing to SYSTEM_MAP.md
- `Archives/INTEGRATION_2026-06-09_obsolete/MANIFEST.md` — archive manifest

## 6. Automations (3 active)

| Time | Title | Uses |
|---|---|---|
| 8:00 AM ET | Daily TC Pipeline Status | `refresh_daily_data.sh` |
| 9:00 AM ET | TC Daily Pick Log | `Projects/daily_picks.py` |
| 5:00 PM ET | NBA/WNBA Pre-Tip Report | `daily_tip_report.py` + `generate_report.py` |

## 7. Live zo.space routes

| Route | Type | Status |
|---|---|---|
| `/` | page | Live (private) |
| `/nba-tc` | page | Live (public) — TC dashboard |
| `/combos` | page | Live — combo parlay builder |
| `/api/tc` | api | Live — TC engine, 4-tier odds fallback |
| `/api/combos` | api | Live — combo generator |

## 8. Gaps (known limitations)

1. **ODDS_API_KEY invalid** (value `toa_live_t5d8p3n1` returns 401 from
   the-odds-api.com). `/api/tc` falls back to SGO + ESPN-DK-embedded for NBA
   and ESPN-DK-embedded only for WNBA. To fix: replace the value in
   `/root/.zo/secrets.env`.

2. **WNBA player props unavailable**. SGO plan is NBA-only; ESPN-DK-embedded
   has WNBA game totals/spreads but no player props. WNBA projections generate
   correctly but `dk_line` is null for all player props.

3. **DK moneyline (NBA) sometimes null**. SAS@NYK `dk_ml: None` despite
   `dk_total: 215.5` being present — ESPN provides the total but DK ML
   sometimes surfaces only in spread/ML group, not totals group. Minor.

## 9. Comprehensive improvement recommendations

### A. P0 (fix this week)
- **Get a working The Odds API key** — fill `/root/.zo/secrets.env`
  `ODDS_API_KEY=` with a real value from https://the-odds-api.com/account/.
  This unlocks WNBA player props.
- **Add a sportsdata.io v2 fallback** to `/api/tc` (your SPORTS_DATA_IO_KEY
  is currently dead because the v3 endpoints 404). sportsdata.io has both NBA
  and WNBA player props via `https://api.sportsdata.io/v2/{sport}/odds/json/
  PlayerPropsByGame/{date}` (note: v2, not v3). This would close the WNBA gap.

### B. P1 (next 2 weeks)
- **Add a shared types file** (`Projects/tc_types.py`) with the dataclasses
  for `Player`, `TCPick`, `ComboLeg`, `MatchupProjection`. Both `tc_math.py`
  and `/api/tc` should import from this. Currently the API has inline
  duplicates of the same shape, leading to drift risk.
- **Promote `tc_math.py` to a real package** (`Projects/tc/`) with
  `__init__.py`, `stats.py`, `combo.py`, `calibration.py`. Test it with
  `pytest`. Currently it's a single 290-line file with no tests.
- **Add a CI smoke test** that runs `bash Scripts/refresh_daily_data.sh
  --dry-run` + `python3 Projects/tc_math.py` on every deploy. Catch the
  "line cut off" / "no DK lines" failure modes automatically.

### C. P2 (next month)
- **Backfill historical DK lines** for the 14-day WNBA backtest in
  `Archives/WNBA_Backtests/`. The backtest hit rate is 47% but it's against
  raw averages, not DK lines. Adding DK lines would let you measure actual
  ROI.
- **Build a real dashboard at `/nba-tc`** that shows live DK line movement
  vs TC projection over time (currently the page only shows the most recent
  line). The Odds API supports `historicalEvents` for this.
- **Add a Parlay Builder page** that reads `/api/combos`, lets the user
  filter by TC edge ≥ 2, sport, stat, and emit a DraftKings-friendly ticket.
  The `/combos` page has a basic version; expand it.
- **Email a real parlay ticket** to the user at 5:30 PM ET every day — the
  pre-tip report is plain-English, but the 5:30 PM ticket would be
  structured for direct DK entry.

### D. Architecture
- The pipeline is now **3 layers**:
  1. **Live web**: zo.space routes (`/api/tc`, `/api/combos`)
  2. **Daily batch**: 3 automations × 3 scripts (`refresh_daily_data.sh`,
     `daily_picks.py`, `daily_tip_report.py`)
  3. **Math**: `tc_math.py` (single source of truth, used by both layers)

  This is the right shape. The only weak link is that `tc_math.py` and
  `/api/tc` are not guaranteed to stay in sync — `/api/tc` has its own inline
  CONS logic. Extract that logic into a shared `Projects/tc/stats.py` that
  both import.

## 10. Time spent
~1.5 hours of integration. Net effect: 21 files archived (cleaner repo), 3
live bugs fixed (real data flowing), 1 new system map file, 1 report, all 5
zo.space routes verified HTTP 200.
