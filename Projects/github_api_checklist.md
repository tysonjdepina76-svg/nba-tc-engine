# GitHub Sports API — Integration Checklist

**Generated: 2026-07-19 19:10 ET**

---

## BEFORE (Current State)

| # | API / Source | Type | Key | Wired? | Data Flow |
|---|---|---|---|---|---|
| 1 | **SerpAPI** | Lines/Odds | `Serp_Api_key` | ✅ Wired | → daily_picks.py → exhausted, 0 results |
| 2 | **Odds API** (`the-odds-api.com`) | Lines/Odds | `THEODDSAPI` | ⚠️ Adapter only | → `odds_api_adapter.py` exists but quota maxed |
| 3 | **SGO** (SportsGameOdds) | Lines/Odds | `SGO_API_KEY` | ❌ Broken ref | → `line_fetcher.py` imports `src.adapters.sgo` which doesn't exist |
| 4 | **MLB-StatsAPI** (`statsapi`) | Stats/Game Data | None (free) | ⚠️ Adapter only | → `mlb_api_adapter.py` exists, NOT called by daily_picks.py |
| 5 | **nba_api** (WNBA LeagueID) | Stats/Game Data | None (free) | ⚠️ Adapter only | → `wnba_api_adapter.py` exists, NOT called by daily_picks.py |
| 6 | **ESPN hidden API** | Stats/Scores | None (free) | ⚠️ Partial | → `wnba_data_fetcher.py` + `world_cup_adapter.py` (minimal) |
| 7 | **BALLDONTLIE** | WNBA Stats + Props | ❌ Not set up | ❌ None | $9.99/mo tier needed for props |
| 8 | **API-Football** (RapidAPI) | WC Stats/xG | ❌ Not set up | ❌ None | 100 req/day free tier |

### Current Line Source Pipeline
```
daily_picks.py
  → generate_projections.py (generates TC projections with line=0)
  → enrich_lines_via_serpapi() → serp_odds_scraper.py → SERPAPI (EXHAUSTED)
  → RESULT: all picks = SELF_EDGE (no real market lines)
```

### Dead References
- `line_fetcher.py`: imports `src.adapters.odds_api` (should be `odds_api_adapter`)
- `line_fetcher.py`: imports `src.adapters.sgo` (file doesn't exist)
- `consensus_engine.py`: references SGO for WNBA (not supported by SGO)

---

## AFTER (Target State)

| # | API / Source | Action | Priority |
|---|---|---|---|
| 1 | **Odds API** | Fix adapter import, wire into daily_picks.py as primary line source | 🔴 HIGH |
| 2 | **SGO** | Create `src/adapters/sgo.py`, wire as MLB/WC fallback | 🔴 HIGH |
| 3 | **MLB-StatsAPI** | Wire `mlb_api_adapter.py` into daily_picks.py for game context/pitching | 🟡 MED |
| 4 | **WNBA nba_api** | Wire `wnba_api_adapter.py` into daily_picks.py for live stats | 🟡 MED |
| 5 | **World Cup ESPN** | Expand `world_cup_adapter.py` with full endpoints | 🟡 MED |
| 6 | **BALLDONTLIE** | Sign up ($9.99/mo), create adapter, wire WNBA props | 🟢 LOW (needs key) |
| 7 | **API-Football** | Sign up (RapidAPI), create adapter, wire WC stats | 🟢 LOW (needs key) |
| 8 | **line_fetcher.py** | Fix broken imports, unify line sources | 🔴 HIGH |
| 9 | **Dead refs** | Remove SGO WNBA references in consensus_engine.py | 🟡 MED |

### Target Line Source Pipeline
```
daily_picks.py
  → generate_projections.py (TC projections)
  → enrich_lines() → tiered fallback:
      1. Odds API (THEODDSAPI key, 500 req/mo cap)
      2. SGO (MLB, WC only — SGO_API_KEY)
      3. BALLDONTLIE (WNBA — when key acquired)
      4. Self-edge (last resort)
  → MLB stats (statsapi) for pitcher vs batter context
  → WNBA stats (nba_api) for live game context
  → WC stats (ESPN + API-Football) for match context
```

---

## Execution Order

### Phase 1 — Fix Broken References (NOW)
- [ ] Fix `line_fetcher.py` imports
- [ ] Create `src/adapters/sgo.py` module
- [ ] Remove dead SGO WNBA references

### Phase 2 — Wire Free APIs (NOW)
- [ ] Wire Odds API into daily_picks.py enrichment
- [ ] Wire MLB statsapi into daily_picks.py
- [ ] Wire WNBA nba_api into daily_picks.py
- [ ] Expand world_cup_adapter.py

### Phase 3 — Dashboard Column Fix (NOW)
- [ ] Align all sport columns with proper borders
- [ ] MLB pitcher vs batter diamond view
- [ ] Set borders for Chromebook/zo.computer workspace

### Phase 4 — Sign Up Required
- [ ] BALLDONTLIE account ($9.99/mo)
- [ ] API-Football (RapidAPI free tier)

---

## API Key Inventory

| Key Name | Exists | Status |
|---|---|---|
| `THEODDSAPI` | ✅ | Quota maxed (Business tier) |
| `SGO_API_KEY` | ✅ | WNBA not supported, MLB/WC only |
| `Serp_Api_key` | ✅ | Exhausted (0 searches remaining) |
| `BALLDONTLIE_API_KEY` | ❌ | Need to sign up |
| `RAPIDAPI_KEY` | ❌ | Need to sign up |
