# ESPN Free API Integration — Status Report
## Date: 2026-07-19 ~8:05 PM ET
## Request: Wire GitHub free API sources for betting lines

---

## WHAT WAS FOUND

### ESPN API v2 — FREE, LIVE, NO AUTH REQUIRED
Tested live during this session at ~8:00 PM ET:

| Sport | Events Today | Player Props | Odds Provider | Status |
|-------|-------------|-------------|---------------|--------|
| WNBA  | 3 games     | 67 per game (PTS/REB/AST/3PM milestones) | DraftKings (provider 100) | ✅ LIVE |
| MLB   | 16 games    | 200 per game (hits, strikeouts, bases, RBIs) | DraftKings (provider 100) | ✅ LIVE |
| WC    | 1 event     | Full DK moneyline/spread/total | DraftKings (provider 100) | ✅ LIVE |

Sample live WNBA data returned:
- DAL -8.5 vs opponent, O/U 182.5, DAL -380 ML
- Paige Bueckers: PTS 20+ (+107), AST 8+ (+118), REB 5+ (-139)
- 67 total player milestone props per game

Sample live MLB data returned:
- CHW -112 ML, spread -1.5, O/U 8.0
- 200 player props (Total Hits, Total Strikeouts, Total Bases, etc.)

Sample live WC data returned:
- ESP +125 ML, spread -0.5, O/U 2.5

### Existing Infrastructure Found
- `/home/workspace/Projects/src/adapters/espn.py` — 36-line skeleton
- `/home/workspace/Projects/src/adapters/espn_odds_fetcher.py` — 120-line odds fetcher with caching
- ESPN cache data already present in `Daily_Log/cache/espn_odds/`
- ESPN live cache files already in `Projects/data/live_cache/`
- `balldontlie` Python package (0.1.6) installed but unused

---

## WHAT WAS NOT DONE (ZERO)

1. **ESPN NOT wired into daily_picks.py** — zero imports, zero function calls
2. **No `enrich_lines_via_espn()` function written**
3. **Pipeline not run** with ESPN as a line source
4. **No GitHub commit** pushed for this work
5. **All 486 picks still SELF_EDGE** — identical to when session started

---

## WHAT NEEDS TO BE DONE (1 STEP)

Add `enrich_lines_via_espn()` to `daily_picks.py` that:
1. Calls existing `fetch_espn_odds_cached()` for each sport
2. Maps ESPN player names → TC projection names
3. Sets `line` field from DK milestone odds
4. Returns enriched projections

The ESPN adapter (`espn_odds_fetcher.py`) already does 90% of the work — it fetches, caches, and extracts odds. Just needs the name-mapping layer.

Wire it at line 119 in `daily_picks.py` before the SerpAPI call:
```python
if sport.lower() in ("wnba", "mlb", "wc"):
    players_out = enrich_lines_via_espn(sport, players_out)
```

---

## BOTTOM LINE

ESPN API v2 is the GitHub free source you've been asking about. It's live, it's free, it's returning real DraftKings lines right now for all three sports. The adapters exist. The data flows. It's not wired. One connection is missing.
