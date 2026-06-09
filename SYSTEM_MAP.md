# TC Pipeline System Map

> **Read this first** to understand the system. Authoritative index for all live
> code, zo.space routes, automations, and outputs. Last updated 2026-06-09.

---

## 1. At a Glance

The system turns live NBA + WNBA rosters and DraftKings player props into a
**Triple Conservative (TC) projection** for every player, emits a daily combo
report (PRA / PR / PA), and backtests against final box scores. All in three
zo.space routes + two scheduled automations + one offline combo builder.

**Daily loop (in order):**
1. **8:00 AM ET** — `Scripts/refresh_daily_data.sh` runs `daily_picks.py`
   (raw slate capture) then `build_pregame_combos.py` (TC combos).
2. **9:00 AM ET** — second daily-log automation runs `daily_picks.py` again
   and emails a status report.
3. **5:00 PM ET** — pre-tip report automation runs `daily_tip_report.py`
   + `generate_report.py` and emails a plain-English summary.
4. **On-demand** — `/nba-tc` page calls `/api/tc?mode=project` for any
   matchup the user selects.

---

## 2. Code (single source of truth)

| File | Role | Run by |
|---|---|---|
| `Projects/tc_math.py` | **TC math core** — WNBA 40-min norm, PRA/PR/PA builders, edge, win% | imported by `/api/combos` and `build_pregame_combos.py` |
| `Projects/daily_picks.py` | Captures daily slate → `Daily_Log/YYYY-MM-DD/{slate,picks,proj,summary}.{json,csv}` | `Scripts/refresh_daily_data.sh` |
| `Projects/build_pregame_combos.py` | Builds PRA/PR/PA combo legs vs DK lines from `/api/tc` + `/api/combos` | `Scripts/refresh_daily_data.sh` |
| `Scripts/refresh_daily_data.sh` | Daily pipeline runner (DK scrape + combos) | 8 AM ET automation |
| `Scripts/morning_briefing.py` | Standalone morning summary (not in current loop, kept for ad-hoc) | manual |
| `daily_tip_report.py` | Pre-tip MD reports (`/home/workspace/Reports/nba_pre_tip_YYYYMMDD.md`, `wnba_pre_tip_YYYYMMDD.md`) | 5 PM ET automation |
| `generate_report.py` | Plain-English summary generator (consumes pre-tip MDs) | 5 PM ET automation |

**Self-test:** `python3 Projects/tc_math.py` runs NBA + WNBA active/Q/OUT cases.

---

## 3. zo.space routes (live, all publicly accessible except `/`)

| Path | Type | Purpose | Status |
|---|---|---|---|
| `/nba-tc` | page | Live TC dashboard — slate, matchup, projections, ML, total, props | ✅ live |
| `/combos` | page | Auto-combo generator + parlay builder | ✅ live |
| `/` | page | Homepage (Mirror Workbook) | ✅ live, **private** |
| `/api/tc` | api | TC projection engine (NBA + WNBA, 4-tier odds fallback) | ✅ live, 200 |
| `/api/combos` | api | Live combo generator (emits PRA/PR/PA legs) | ✅ live, 200 |

**Public zo.space:** `https://true.zo.space/`

### `/api/tc` modes
- `?sport=NBA&away=SAS&home=NYK` (default) — single-game TC projection
- `?mode=live-stats` — full slate with live game states (In Progress / Scheduled / Final)
- `?mode=diagnostics` — engine + roster diagnostics
- `?diag=1` — shows which API keys loaded (`keys_status`, `missing_keys`)

### `/api/tc` odds fallback chain (in order)
1. **SGO v2** (`SPORTSGAMEODDS_API_KEY`) — best for NBA player props (DK lines)
2. **ESPN DraftKings embedded** — no key needed, NBA only, has game total/ML
3. **The Odds API v4** (`ODDS_API_KEY`) — currently **DEAD** (key invalid)
4. **WNBA historical fallback** — no DK player props, only game lines (SEA@LV)
5. Empty → `dk_line=null, dk_source=null`

### `/api/tc` keys: self-sourced at runtime
- Reads `/root/.zo/secrets.env` on every call (no restart needed)
- No secrets in zo.space runtime env — must come from that file
- `?diag=1` shows what's loaded

---

## 4. Automations (3 active, all daily ET)

| ID | Title | Time (ET) | What it does |
|---|---|---|---|
| `fc811907…` | Daily TC Pipeline Status | 8:00 AM | Runs `refresh_daily_data.sh` + health checks + email |
| `3d283c4b…` | TC Daily Pick Log | 9:00 AM | Runs `daily_picks.py` + email summary |
| `658fbbbb…` | NBA/WNBA Pre-Tip Report | 5:00 PM | Runs `daily_tip_report.py` + `generate_report.py` + email |

All use the same `secrets.env` and `/api/tc` infrastructure. They share work but run separately to catch failures at different times of day.

---

## 5. Outputs

### Daily logs (one folder per day)
```
/home/workspace/Daily_Log/
├── 2026-06-08/
│   ├── slate_NBA.json          # raw ESPN slate
│   ├── slate_WNBA.json
│   ├── picks.csv               # flat backtest table (18 columns)
│   ├── picks.json              # structured picks
│   ├── proj_NBA_SAS_at_NYK.json   # raw /api/tc response
│   ├── proj_WNBA_NY_at_CON.json
│   ├── combos_nba_sas_nyk.md   # combo report (PRA/PR/PA legs)
│   ├── combos_wnba_sea_lv.md
│   ├── combos_summary.json     # all matchups
│   └── dk_scrape_NBA.json
├── 2026-06-07/...
├── 2026-06-06/...
├── last_run.json               # always latest summary
└── refresh_daily_data_YYYYMMDD.log   # pipeline log
```

### Pre-tip reports (one per day per sport)
```
/home/workspace/Reports/
├── nba_pre_tip_YYYYMMDD.md
├── wnba_pre_tip_YYYYMMDD.md
├── pipeline_integrated_YYYY-MM-DD.md   # integration health report
└── wnba_YYYYMMDD.md
```

### Backtest archive
```
/home/workspace/Archives/WNBA_Backtests/      # historical wnba_pipeline_v2 runs
/home/workspace/Archives/wnba_pipeline_*/     # actuals.json + proj.csv + report.md
/home/workspace/Archives/GEMINI_2026-06-08_obsolete/    # previous integration
/home/workspace/Archives/INTEGRATION_2026-06-09_obsolete/   # THIS integration
```

---

## 6. Active vs Obsolete — what's canonical

### ✅ CANONICAL (do not move/rename)
- `Projects/tc_math.py` — TC math
- `Projects/daily_picks.py` — daily log
- `Projects/build_pregame_combos.py` — combo builder
- `Scripts/refresh_daily_data.sh` — daily runner
- `Scripts/morning_briefing.py` + README
- `daily_tip_report.py` + `generate_report.py`
- `/api/tc` + `/api/combos` + `/nba-tc` + `/combos` + `/` zo.space routes
- `AGENTS.md` + `SYSTEM_MAP.md` + this file

### 📦 ARCHIVED (in `Archives/INTEGRATION_2026-06-09_obsolete/`)
**Orphan Projects/** (10 files):
- `diag_full.py` — was a one-shot diagnostic, kept result in this map
- `wnba_2026_jun23_tc.py`, `wnba_corrected.py`, `wnba_minute_proj.py` — pre-`tc_math.py` WNBA experiments
- `wnba_model_v2.py` (52 bytes — stub)
- `wnba_tune_v1.py`..`v4.py` — calibration experiments, output captured in `tc_math.SPORT_PROFILE`
- `wnba_team_id_fix.json` — one-off mapping

**Orphan workspace root/** (11 files):
- `_check_keys.py`, `_check_tc.py`, `patch_script.py`, `debug_sug.py` — dev shims
- `college_models.py`, `multi_sport_engine.py`, `nba_tc_pipeline.py`, `wnba_bt.py` — pre-pipeline experiments
- `SportsTC_Streamlit_App.py` + `run_streamlit.sh` + `run_dashboard.sh` — old Streamlit UI, replaced by `/nba-tc` zo.space page

**Already-archived** (from prior integration):
- `Archives/GEMINI_2026-06-08_obsolete/` — 3 superseded TC engine versions

---

## 7. Known Gaps & Improvement Plan

### G1. **WNBA player props are blind** ⚠️ HIGH PRIORITY
- SGO plan only covers NBA. The Odds API key (`toa_live_t5d8p3n1`) is invalid.
- ESPN has WNBA game lines (SEA@LV showed LV -15.5 / O/U 162.5) but no player props.
- **Today (2026-06-08):** 0 WNBA DK player props. We project 42 WNBA picks but can't compute edges.
- **Fix path:** 1) Get a valid `ODDS_API_KEY` from the-odds-api.com. 2) Or subscribe to SGO WNBA tier. 3) Or scrape DK directly.

### G2. **ODDS_API_KEY invalid** ⚠️ BLOCKER
- File value: `toa_live_t5d8p3n1` → returns `INVALID_KEY`.
- Loaded by `/api/tc` but does nothing useful (Tier 3 always fails).
- **Fix:** log into the-odds-api.com, copy a fresh key, replace in `secrets.env`.

### G3. **No automated WNBA-specific backtest job** (MEDIUM)
- The 5 PM pre-tip job exists but doesn't run `wnba_pipeline_v2.py` against last night's actuals.
- A 4th automation (10 AM ET) running `wnba_pipeline_v2.py` against `yesterday` would close the loop.

### G4. **No alerting on pipeline failure** (MEDIUM)
- Automations email a status report when they succeed. If `refresh_daily_data.sh` errors, the 8 AM email goes out anyway.
- **Fix:** add `set -e` checks + non-zero exit code → failure email subject.

### G5. **Stale `daily_picks.py` (NBA slate `pending` rate is high)** (LOW)
- After the live-stats fix, NBA player props are now resolved (16 of 30 SAS@NYK picks have DK lines). But WNBA slate is still 0/42.
- This is a downstream symptom of G1.

### G6. **No public link for `/combos` page** (LOW)
- Currently private. Could be a paid subscriber link in the future.

### G7. **Project page UI is dense on mobile** (LOW)
- `/nba-tc` works on mobile but the slate table is cramped. Worth a `md:hidden` toggle.

### G8. **`/api/tc` returns ALL rosters on every call** (LOW)
- No caching. For repeated calls, the same 26 player × 6 stat = 156 rows is recomputed. Could add a 60s in-memory cache.

---

## 8. Quick Start — common operations

### Run the full daily pipeline (local)
```bash
bash /home/workspace/Scripts/refresh_daily_data.sh
```

### Build combos for one sport only
```bash
bash /home/workspace/Scripts/refresh_daily_data.sh --sport NBA
```

### Dry-run
```bash
bash /home/workspace/Scripts/refresh_daily_data.sh --dry-run
```

### Test TC math
```bash
python3 /home/workspace/Projects/tc_math.py
```

### Check which keys are loaded by zo.space
```bash
curl -s "https://true.zo.space/api/tc?diag=1" -H "Accept: application/json" | python3 -m json.tool
```

### Get live slate
```bash
curl -s "https://true.zo.space/api/tc?sport=WNBA&mode=live-stats" -H "Accept: application/json" | python3 -m json.tool
```

### Get TC projection for a matchup
```bash
curl -s "https://true.zo.space/api/tc?sport=NBA&away=SAS&home=NYK" -H "Accept: application/json" | python3 -m json.tool
```

### Get combos
```bash
curl -s "https://true.zo.space/api/combos?sport=NBA&away=SAS&home=NYK" -H "Accept: application/json" | python3 -m json.tool
```

---

## 9. Future-Agent Quickstart

1. Read `SYSTEM_MAP.md` (this file) first.
2. Read `AGENTS.md` for project context.
3. To make a code change: edit `Projects/tc_math.py` (math) or `Projects/build_pregame_combos.py` (offline combo) or `Projects/daily_picks.py` (log capture). Use `edit_file_llm` for surgical edits.
4. To change a zo.space route: use `edit_space_route(path, code_edit, edit_instructions)`. Send only the changed sections with `// ... existing code ...` placeholders. NEVER try to read zo.space files with file tools — they don't exist on the filesystem.
5. To change a scheduled automation: use `edit_automation(automation_id, ...)`. The 3 IDs are listed in section 4 above.
6. To check pipeline health: run the Quick Start commands in section 8.
7. To add a new stat type: add a new entry in `tc_math.STAT_CONS` + a new builder in `build_player_combos`. Then update `/api/tc` and `/api/combos` to emit it.

---

## 10. System Status (last verified 2026-06-09 00:20 ET)

- **zo.space routes**: 5 live, 0 errors
- **Automations**: 3 active (next runs: tomorrow 8/9/5 AM ET)
- **API keys loaded by `/api/tc`**: SGO ✅, ODDS_API ❌ invalid
- **DK player props coverage**: NBA ✅ (16/30 picks), WNBA ❌ (0/42)
- **Daily pipeline last run**: 2026-06-08 23:54 UTC — SUCCESS
- **Backtest hit rate (14d WNBA)**: 47% (2882 picks)
- **TC engine version**: 6+ via `/api/tc` (single source of truth)
