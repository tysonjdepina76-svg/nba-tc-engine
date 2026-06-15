# Archive Manifest — Pipeline Integration (2026-06-09)

## What changed
Integration pass over the live TC pipeline:

1. **`/api/tc` (zo.space)** — self-sources API keys from `/root/.zo/secrets.env`
   (was: keys missing in zo.space runtime → all DK lines blank); dispatched
   `mode=live-stats` (was: dead code → 0 games on Live tab); rewrote SGO
   player-prop parser to use `oddID` prefix + `byBookmaker.draftkings.overUnder`
   (was: looking for non-existent `marketID` field → 0 DK props).

2. **`/nba-tc` (zo.space page)** — updated team defaults to today's actual
   slate (SAS@NYK, CON/NY); added missing-keys warning banner.

3. **Daily pipeline (`refresh_daily_data.sh`)** — end-to-end run verified:
   1 NBA slate (30 picks, 16 with DK lines) + 3 WNBA slates (42 picks) +
   105 NBA combo legs + 66 WNBA combo legs produced in 7 seconds.

## What was archived (and why)

### `/home/workspace/Projects/` — orphan files
These are NOT referenced by any automation or by `tc_math.py` /
`build_pregame_combos.py`. Their math is already inlined into `tc_math.py` or
superseded by the `/api/tc` zo.space route.

| File | Reason | Replaced by |
|------|--------|-------------|
| `Projects/diag_full.py` | One-off diagnostic that hit `/api/tc?mode=live-stats` | (no replacement needed — was just a debug tool) |
| `Projects/wnba_2026_jun23_tc.py` | Date-specific (Jun 23) WNBA projection script, last touched Jun 2 | `Projects/tc_math.py` (sport-aware, no date hardcode) |
| `Projects/wnba_corrected.py` | Earlier WNBA correction, math now in `tc_math.py` | `Projects/tc_math.py` |
| `Projects/wnba_minute_proj.py` | Minute projection (Q-minutes calculation), not wired | `/api/tc` does this inline (status_factor in tc_math) |
| `Projects/wnba_model_v2.py` | 52-byte stub (just an import re-export) | nothing — dead stub |
| `Projects/wnba_tune_v1.py` … `v4.py` | Sequential tuning drafts from Jun 8 | `Projects/tc_math.py` (final calibration from v4 retained) |
| `Projects/wnba_team_id_fix.json` | 230-byte WNBA team-ID mapping; no longer used | `/api/tc` uses ESPN's own abbreviation table |

### `/home/workspace/` root — orphan files
These are old engine/UI files. The active pipeline lives in `Projects/`,
`Scripts/`, the zo.space routes (`/api/tc`, `/api/combos`, `/nba-tc`,
`/combos`), and `Archives/WNBA_Backtests/`.

| File | Reason |
|------|--------|
| `_check_keys.py`, `_check_tc.py`, `patch_script.py`, `debug_sug.py` | One-off debug scripts (1