# TC Pipeline Gap Report — July 19, 2026

## ROOT CAUSE
The pipeline generates **SELF_EDGE fake lines** instead of fetching real market lines.

### Flow:
1. `generate_projections.py` → creates TC projections + FAKE derived lines (5-15% spread)
2. `daily_picks.py` → reads fake lines from projection JSON → writes to picks.db with signal=SELF_EDGE
3. The automation "Daily Sports Picks Update" runs this every day at 1:30 PM ET, OVERWRITING any real data

## GAPS FOUND & FIXED

### GAP 1: Broken SerpAPI import ✅ FIXED
**File:** `daily_picks.py` line 26
**Bug:** `from wc_team_lookup import correct_wc_teamfrom serp_odds_scraper import search_odds`
**Impact:** SerpAPI enrichment never runs. All zero-line picks stay zero-line.
**Fix:** Split into two imports with newline.

### GAP 2: Combo API queries ALL dates ✅ FIXED
**File:** `api/main.py` ~line 726
**Bug:** `_build_combos_from_db()` had no date filter. Mixing 07-18 and 07-19 data.
**Impact:** 84 WNBA players returned (only 21 on today's slate). Old players like Caitlin Clark from yesterday show up.
**Fix:** Added `date = ?` to WHERE clause, uses `datetime.now()`.

### GAP 3: daily_picks.py hardcodes signal=SELF_EDGE 🟡 PARTIAL
**File:** `daily_picks.py` line 459
**Bug:** All picks written with `signal = "SELF_EDGE"` regardless of line source
**Impact:** Can't distinguish real-line picks from fake-line picks
**Fix:** Set signal to "SERPAPI" when enriched, "SDIO" when from SDIO, etc.

### GAP 4: WNBA combos show market_line=0 🟡 NEEDS INVESTIGATION
**File:** `api/main.py` `_build_combos_from_db()`
**Bug:** Summed market_line is 0 for WNBA players (Caitlin Clark, Breanna Stewart)
**Impact:** All WNBA combos show 0 edge_pct
**Cause:** These players are from 2026-07-18 data (yesterday) — now fixed by GAP 2 date filter

### GAP 5: Fake lines in projection files 🟡 ROOT ISSUE
**File:** `generate_projections.py` line 126+
**Bug:** All projections include DERIVED/FAKE lines (5-15% spread from TC projection)
**Impact:** Even when real lines exist, fake lines always overwrite
**Fix:** Either fetch real lines inside generate_projections.py, or have daily_picks.py override with SDIO/SerpAPI lines

### GAP 6: SerpAPI parser doesn't match stat names ⚠️ TODO
**File:** `daily_picks.py` `enrich_lines_via_serpapi()`
**Bug:** Regex uses literal stat name ("PTS") but SerpAPI snippets use full names ("Points")
**Fix:** Add stat synonym mapping (PTS→Points, AST→Assists, REB→Rebounds, etc.)

### GAP 7: /nba-tc dashboard fetches from wrong API ⚠️ TODO
**File:** zo.space route `/nba-tc`
**Bug:** Fetches from `https://zo.computer/api` instead of `https://tc-api-true.zocomputer.io/api/v1`
**Impact:** Combo button shows stale/empty data
**Fix:** Rewrite dashboard to fetch from tc-api endpoints

### GAP 8: Combo button not wired to Streamlit dashboard ⚠️ TODO
**File:** `tc_dashboard.py` (Streamlit)
**Bug:** No combo section in Streamlit dashboard
**Fix:** Add combo table with fetch from `/api/v1/combos`

## LINE SOURCE STATUS
| Source | Status | Tier |
|--------|--------|------|
| SDIO (SportsDataIo) | ❌ 401/404 — Needs paid subscription | Free |
| SGO (SportsGameOdds) | ❌ 429 Rate Limited | Free |
| Odds API | ❌ 401 Quota Exhausted | Business |
| SerpAPI | ✅ Working (after import fix) | Free |
| Self-Edge (fake) | ✅ Always works | N/A |

## REBUILD STEPS
1. Fix daily_picks.py import ✅
2. Fix API date filter ✅  
3. Add stat synonym mapping to SerpAPI parser
4. Fix signal field in daily_picks.py
5. Re-run pipeline with fixes
6. Restart API service at :8000
7. Update /nba-tc zo.space route
8. Wire combos to Streamlit dashboard
9. Git commit + push
