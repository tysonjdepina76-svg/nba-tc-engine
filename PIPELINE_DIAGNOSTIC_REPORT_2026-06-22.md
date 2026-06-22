# 🩺 TC Pipeline — Comprehensive Diagnostic + Fix Report
> **Date:** 2026-06-22 17:10 ET  
> **Status:** DEGRADED → PARTIALLY RESTORED  
> **Games:** 20 (12 DK LIVE, 4 NO DK, 4 completed)  
> **Picks:** 846 (self-edge, no verified market lines)  

---

## ROOT CAUSE — URL FORMAT CHANGE

The Odds API (`api.theoddsapi.com`) changed its URL format. **Every file was broken**:
- Old: `/{sport_key}/odds` → 404
- New: `/odds/?sport_key={sport_key}&apiKey={key}&regions=us`

Additionally, the secrets file was being read but keys were **never assigned to variables** — the `for k,v in` loop read the values and threw them away.

---

## FILES FIXED TODAY

| # | File | What Was Broke | Fix Applied |
|---|------|---------------|-------------|
| 1 | `consensus_engine.py` | Secrets loaded but never assigned to ODDS_KEY/SGO_KEY | Fixed assignment: `if k == "ODDS_API_KEY": ODDS_KEY = v` |
| 2 | `consensus_engine.py` | 4 URL constructions: `/{sport}/odds`, `/{sport}/events/{id}/odds` | All 4 fixed to `/odds/?sport_key=...` |
| 3 | `consensus_engine.py` | Response format changed: `{books: [{book, market, outcomes}]}` | Added `_normalize_odds_response()` to convert to old format |
| 4 | `consensus_engine.py` | MLB_TEAM_MAP only had 1 team (ARI) | Added all 30 MLB teams |
| 5 | `/api/tc` | `ODDS_BASE = "https://api.the-odds-api.com"` (wrong domain + dead key) | `ODDS_BASE = "https://api.theoddsapi.com"` |
| 6 | `/api/tc` | `ODDS_SPORT` missing MLB key | Added `MLB: "baseball_mlb"` |
| 7 | `/api/tc` | `fetchMultiBookOdds()` used wrong URL path | Rewritten for `/odds/?sport_key=...` with new `ev.books[]` format |
| 8 | `/api/tc` | `fetchMultiSportDKLines()` used wrong URL path + response format | Rewritten for correct `/odds/` endpoint |
| 9 | `api_scan.py` | Empty loop `for key, label in [("key", "label")]` — never called probes | Fixed: loads ODDS_KEY from secrets, probes `/sports/` and `/odds/` with correct params |
| 10 | `api_scan.py` | No URL passed to Odds probes | Fixed: uses `ODDS_BASE + "/sports/"` and `ODDS_BASE + "/odds/"` |
| 11 | `/api/pipeline-health` | Odds API test used dead `/v4/sports/basketball_wnba/odds/` URL | Fixed: uses `/odds/?sport_key=basketball_wnba&apiKey=...` |
| 12 | `/api/pipeline-health` | Wrong param name: `sport=wnba` | Fixed: `sport_key=basketball_wnba` |

---

## CURRENT STATE — WHAT'S WORKING ✅

| Component | Before Fixes | After Fixes |
|-----------|-------------|-------------|
| WNBA game totals | ❌ NO MARKET | ✅ DK total via Odds API + ESPN embedded |
| WNBA spread/ML | ❌ No data | ✅ Via Odds API multi-book |
| MLB game totals | ❌ NO DK LINES | ✅ 11/16 games DK LIVE |
| MLB spread/ML | ❌ No data | ✅ Via Odds API 14-book consensus |
| DK Combos (8515) | ⚠️ 404 | ✅ Running |
| Soccer Combos (8516) | ⚠️ 404 | ✅ Running, 3 combos |
| Streamlit (8510) | — | ✅ Running |
| ESPN rost