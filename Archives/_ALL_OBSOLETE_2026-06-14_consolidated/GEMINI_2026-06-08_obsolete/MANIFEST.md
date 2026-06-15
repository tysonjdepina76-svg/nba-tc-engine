# Archive Manifest — Gemini TC Pipeline Integration (2026-06-08)

## What changed
Three Google Docs from `tysonjdepina99@gmail.com` (titled "Gemini code, fill in gaps and enhance") were merged into the live TC pipeline:

1. **Live Combos Generator (WNBA TC Math)** — added per-player PRA/PR/PA combo
   projection module (`/home/workspace/Projects/tc_math.py`) + WNBA-specific
   40-min normalization. Wired into the live `/api/combos` zo.space API route
   and the `/combos` page. All combos now include three stat combos per player
   (PRA / PR / PA) with TC projection, line, edge vs DK market, and conservative
   win%.

2. **8 AM Cron Job** — gVisor (our sandbox) does not have a `cron` daemon, so
   the traditional crontab approach was replaced with a Zo scheduled agent
   (see "Live demo" section of the user-facing report). The agent runs the
   `refresh_daily_data.sh` shell script every morning at 08:00 EDT, emails a
   summary to the user, and verifies the live API is still up.

3. **Pregame Combos Parlay Builder** — refactored the builder component to
   follow the TC template: now emits PRA / PR / PA combo cards (not just single
   props), added a "+ Add Combos" drop button that filters to combo-only cards,
   added a COMBO leg chip in the UI (purple "✦" badge), and wired everything to
   the same TC Math module so the report and the live UI share one source of
   truth.

## What was archived (and why)

| File | Reason | Replaced by |
|------|--------|-------------|
| `tc-workspace/scripts/nba_tc_engine_v2.py` | v2 of offline TC engine, superseded by `/api/tc` zo.space route + `tc_engine.py` (v6+) | `tc-workspace/scripts/tc_engine.py` (v6+, single source of truth) |
| `tc-workspace/scripts/nba_tc_engine_v3.py` | v3, also superseded | same as above |
| `tc-workspace/scripts/wnba_tc_engine.py` | Standalone WNBA engine with duplicated math. The WNBA logic is now inlined into `tc_engine.py` and applied via sport-specific W_FACTOR + the new `tc_math.py` module | `tc_math.py` (WNBA-specific 40-min normalization + per-player PRA/PR/PA) |

## What was NOT changed (and why)

- **`/api/tc`** — already has WNBA-specific TOTAL_GAP calibration, BAYES_ALPHA
  shrinkage tuned on 14 days of WNBA backtests, and a 4-tier odds source
  fallback (SGO → ESPN DK → The Odds API → WNBA historical fallback). The
  Gemini prompt didn't ask for changes here, so it's preserved as-is.
- **`/nba-tc`** — TC Dashboard already calls `/api/tc` correctly. No changes
  needed; the new combo math flows through the existing API automatically.
- **`/api/daily-log`** — used for picking history. Out of scope of the three
  prompts; left untouched.

## What's NEW (not in any prior archive)

- `Projects/tc_math.py` — the WNBA-specific PRA/PR/PA combo module (272 lines)
- `Scripts/refresh_daily_data.sh` — daily pipeline runner (replaces the
  8 AM cron requirement from Gemini Prompt 2)
- `Projects/build_pregame_combos.py` — REWRITTEN to consume `tc_math.py` and
  emit per-player PRA/PR/PA combo reports for both NBA and WNBA
- `Archives/GEMINI_2026-06-08_obsolete/` — this manifest + 3 superseded files
- zo.space route `/api/combos` — extended with `buildPlayerCombos()`,
  `bestComboLegs()`, `fetchDKComboProps()`, and a "Combos 2/3/4-leg" emission
  block in the main handler
- zo.space page `/combos` — added a COMBO leg chip, a "+ Add Combos" filter
  button (purple), and `useMemo` filtering logic

## Live registration status

| System | Status | URL / Location |
|--------|--------|----------------|
| `/api/combos` | ✅ Live (200, 0 errors) | https://true.zo.space/api/combos |
| `/combos` page | ✅ Live (200) | https://true.zo.space/combos |
| `/api/tc` | ✅ Live (200, 0 errors) | https://true.zo.space/api/tc |
| `/nba-tc` page | ✅ Live (200) | https://true.zo.space/nba-tc |
| Daily pipeline shell script | ✅ Working | /home/workspace/Scripts/refresh_daily_data.sh |
| 8 AM EDT automation | ✅ Registered | Next run: tomorrow 08:00 EDT |
| Python TC Math module | ✅ Tested | /home/workspace/Projects/tc_math.py |
| WNBA 40-min normalization | ✅ Live in /api/combos | flagged on every combo leg source string |

## Verified
- All 4 zo.space pages return HTTP 200
- All 3 API routes return HTTP 200 with valid JSON
- 0 errors in `get_space_errors`
- `python3 Projects/tc_math.py` passes its self-test (NBA + WNBA, ACTIVE/Q/OUT)
- `bash Scripts/refresh_daily_data.sh` runs end-to-end without errors
- `python3 Projects/build_pregame_combos.py` generates 105 combo legs for
  SAS@NYK in NBA (35 players × 3 combo types)
- 8 AM agent created and confirmed scheduled
