# TC Pipeline — Comprehensive Report
### 2026-06-09 01:30 AM ET

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     zo.space routes                         │
│  /nba-tc (dashboard)    /dk-combos (combos page)            │
│  /api/tc (TC engine)    / (home)                            │
├──────────────────────────────────────────────────────────────┤
│         User Services (background processes)                │
│  dk-combos-engine (port 8515) — public HTTP                 │
│  nba-tc-sports-streamlit (port 8507) — private HTTP         │
├──────────────────────────────────────────────────────────────┤
│                   Data Sources                              │
│  ESPN scoreboard/roster API → TC projections                │
│  SportsGameOdds v2 → DK player props + combo lines          │
│  ESPN DraftKings embedded → game totals / ML / spread       │
├──────────────────────────────────────────────────────────────┤
│                   Scheduled Agents                          │
│  8:00 AM ET — Daily TC Refresh (fc811907)                   │
│  9:00 AM ET — TC Daily Pick Log (3d283c4b)                  │
│  2:00 PM ET — Injury Report Refresh (08bf65cd)              │
│  5:00 PM ET — Pre-Tip Report (658fbbbb)                     │
├──────────────────────────────────────────────────────────────┤
│                  Offline Tools                              │
│  daily_picks.py → slate + proj capture                      │
│  dk_combos_engine.py → DK PRA/PR/PA extraction              │
│  tc_math.py → WNBA 40-min normalization                     │
│  health_check.sh → 12-point pipeline probe                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. New Files Created

| File | Purpose | Lines |
|---|---|---|
| `Projects/dk_combos_engine.py` | DK combo lines from SportsGameOdds — standalone HTTP server on port 8515 | 205 |
| `Reports/pipeline_report_2026-06-09.md` | This report | — |
| `Reports/pipeline_integrated_2026-06-08.md` | Previous integration summary | 156 |
| `Reports/pipeline_integration_2026-06-09.md` | Integration pass report | 156 |
| `Reports/combos_diagnostic_2026-06-08.md` | Root cause of "no games" bug | 40 |
| `Scripts/health_check.sh` | CLI pipeline health probe (12-point check + optional rerun) | 60 |
| `SYSTEM_MAP.md` | Master index — architecture, routes, automations, gaps | 258 |
| `Archives/gemini_1227am.md` | Gemini WNBA TC Math prompt (from Google Drive 12:27 AM) | 4 |
| `Archives/INTEGRATION_2026-06-09_obsolete/MANIFEST.md` | Archive manifest with reasoning | 43 |

---

## 3. Modified Files

| File | What Changed |
|---|---|
| **`/api/tc`** (zo.space) | Added `loadSecret()` to self-source keys from `/root/.zo/secrets.env`; wired `mode=live-stats` dispatch; rewrote SGO prop parser for oddID format; fixed marketName/betTypeID filters; added `missing_keys` warning in response |
| **`/nba-tc`** (zo.space) | Updated team defaults to SAS@NYK / CON@NY; added missing-keys warning banner; linked DK combos page |
| **`AGENTS.md`** | Updated to point at SYSTEM_MAP.md and reflect post-integration state |
| `Projects/daily_picks.py` | Already working — used by 9 AM + 2 PM automations |
| `Scripts/refresh_daily_data.sh` | Already working — used by 8 AM automation |
| `/home/workspace/.zo/secrets.env` | Added `SPORTS_DATA_IO_KEY` entry |

---

## 4. Deleted / Archived

| Removal | Why |
|---|---|
| `/combos` page route (zo.space) | Always showed "no games" — replaced by `/dk-combos` |
| `/api/combos` API route (zo.space) | Pregame filter excluded all in-progress games — replaced by DK combos engine |
| 21 orphan scripts → `Archives/INTEGRATION_2026-06-09_obsolete/` | Dead code: old WNBA tuners, streamlit stubs, debug shims, Streamlit dashboard |
| All `Daily_Log/*/combos_*.{md,json}` | Replaced by new offline builder output |

---

## 5. Live Pages / APIs

| Endpoint | Type | Status | Detail |
|---|---|---|---|
| `https://true.zo.space/nba-tc` | page | 🟢 HTTP 200 | TC dashboard: slate, projections, DK lines, live stats |
| `https://true.zo.space/dk-combos` | page | 🟢 HTTP 200 | DK combo lines: PRA/PR/PA columns, real DK odds |
| `https://true.zo.space/` | page | 🟢 HTTP 200 | Homepage (private) |
| `https://true.zo.space/api/tc` | api | 🟢 HTTP 200 | TC engine: 4-tier odds fallback (SGO→ESPN→OddsAPI→WNBA) |
| `https://true.zo.space/api/daily-log` | api | 🟢 HTTP 200 | Daily pick log (backtest data) |
| `https://dk-combos-engine-true.zocomputer.io/combos` | service | 🟢 Running | 46 NBA PRA/PR/PA combos, raw JSON |

---

## 6. Automations (4 daily)

| ID | Time ET | Title | What It Runs |
|---|---|---|---|
| `fc811907` | 8:00 AM | Daily TC Pipeline Status | `refresh_daily_data.sh` + health checks + email |
| `3d283c4b` | 9:00 AM | TC Daily Pick Log | `daily_picks.py NBA WNBA` + email summary |
| `08bf65cd` | 2:00 PM | Injury Report Refresh | Health check + live slate check + `daily_picks.py` + combos builder + email |
| `658fbbbb` | 5:00 PM | NBA/WNBA Pre-Tip Report | `daily_tip_report.py` + `generate_report.py` + email |

---

## 7. Today's Slate (last verified)

| Sport | Matchup | Status | TC Picks | DK Props | Combo Legs |
|---|---|---|---|---|---|
| WNBA | NY@CON | In Progress | 12 | 0 | — |
| WNBA | IND@WSH | In Progress | 12 | 0 | — |
| WNBA | SEA@LV | Scheduled | 18 | 0 (game only) | — |
| NBA | SAS@NYK | In Progress | 30 | 15 SGO props | **46 DK combos** |

---

## 8. Key Fixes Applied

1. **Secrets self-sourced** — `/api/tc` reads `SPORTSGAMEODDS_API_KEY` + `ODDS_API_KEY` from `/root/.zo/secrets.env` on every call (zo.space process doesn't auto-source env)
2. **Live-stats mode wired** — `mode=live-stats` now dispatched in `/api/tc` handler (was dead code → 0 games)
3. **SGO prop parser** — reads `oddID` prefix + `byBookmaker.draftkings.overUnder` for the line (was looking for non-existent `marketID` field → 0 DK props)
4. **SGO market filters** — switched from `o?.marketID` to `marketName`/`betTypeID` (SGO v2 has no `marketID` field → 0 odds)
5. **Slate source** — offline builder now calls `/api/tc?mode=live-stats` instead of `/api/combos?mode=pregame` (the latter excluded in-progress games)

---

## 9. Known Gaps

| Gap | Impact | Fix Path |
|---|---|---|
| **ODDS_API_KEY invalid** | Tier 3 Odds API fallback returns 401 | Replace value in `/root/.zo/secrets.env` with active key from the-odds-api.com |
| **WNBA DK player props = 0** | 42 WNBA picks have no market_line to compare against | 1) Get valid ODDS_API_KEY, OR 2) Upgrade SGO to WNBA tier |
| **DK combo team assignment = "—"** | Combos page shows player name but no team column | Cross-reference ESPN roster in `fetch_event_rosters()` (already scaffolded, missing ESPN→SGO team ID mapping) |
| **SGO rate limiting** | Heavy diagnostic calls trigger 429 (temporary) | Add in-memory 45s cache to `/api/tc` SGO fetches |
| **No /api/health route** | Health endpoint truncated during write, deleted to unblock | Re-create via `write_space_route` with shorter code |

---

## 10. Quick Reference

```bash
# Health check
bash /home/workspace/Scripts/health_check.sh

# Run full pipeline
bash /home/workspace/Scripts/refresh_daily_data.sh

# DK combos (command line)
python3 /home/workspace/Projects/dk_combos_engine.py --sport NBA --away SAS --home NYK

# Test TC math
python3 /home/workspace/Projects/tc_math.py

# Live NBA slate
curl -s 'https://true.zo.space/api/tc?sport=NBA&mode=live-stats' | python3 -m json.tool

# DK combos JSON
curl -s 'https://dk-combos-engine-true.zocomputer.io/combos' | python3 -m json.tool
```
