# BACKTEST TRUTH — July 24, 2026

## What's Real vs. What Was Claimed

| What AGENTS.md Said | Reality |
|---|---|
| "67.2% hit rate across 6,238 graded picks" | 3,094 in `graded_picks` are junk imports. Only 84 WNBA picks properly graded: **60.7% (51/84)** |
| "45 roster files" | 4 files (mlb, wnba, nba, nfl) |
| "generate_projections.py" | Archived — was a random.uniform() stub |
| "roster_loader.py" | Did not exist. Rebuilt today from .pyc bytecode |
| "7/23 Pipeline: 0 picks" | Correct — no WNBA games, no MLB lines |

## Properly Graded Picks: WNBA 7/19

**84 picks. 51 hits. 33 misses. 60.7% hit rate. All UNDER.**

| Stat | Total | Hits | Rate |
|------|-------|------|------|
| PTS | 21 | 14 | 66.7% |
| P+R | 21 | 14 | 66.7% |
| P+A | 21 | 12 | 57.1% |
| P+R+A | 21 | 11 | 52.4% |

### By Player
| Player | H/M | Rate |
|--------|-----|------|
| Cheyenne Parker | 4/4 | 100% |
| Diamond DeShields | 4/4 | 100% |
| Brionna Jones | 4/4 | 100% |
| Diana Taurasi | 4/4 | 100% |
| Marina Mabrey | 4/4 | 100% |
| Kelsey Plum | 4/4 | 100% |
| Lexie Brown | 4/4 | 100% |
| Natasha Howard | 4/4 | 100% |
| Satou Sabally | 4/4 | 100% |
| Skylar Diggins-Smith | 4/4 | 100% |
| Teaira McCowan | 4/4 | 100% |
| Rhyne Howard | 3/4 | 75% |
| Alyssa Thomas | 2/4 | 50% |
| Jordin Canada | 2/4 | 50% |
| Allisha Gray | 0/4 | 0% |
| Brittney Griner | 0/4 | 0% |
| DeWanna Bonner | 0/4 | 0% |
| Kahleah Copper | 0/4 | 0% |
| Arike Ogunbowale | 0/4 | 0% |
| Azura Stevens | 0/4 | 0% |
| Dearica Hamby | 0/4 | 0% |

## Junk Data: graded_picks Table

- 3,094 total rows imported from 5 CSVs
- 842 (27.2%) have line=0 — these are raw projections, not picks
- 24 "wins" are ALL Mookie Betts with line=0, fake
- 3,070 pending (hit=0) — these were never actually graded against boxscores
- Only 84 WNBA picks from 7/19 in the `picks` table are real

## Pipeline Status

| Sport | Status |
|-------|--------|
| WNBA | ✅ Working (self-edge via gen_wnba_today.py) — no games 7/23-7/24 |
| MLB | ❌ Broken — no odds source (Odds API Business tier maxed) |
| NFL | ⏸️ Off-season |
| WC | ⏸️ Ended July 2026 |

## What Was Fixed Today

1. **roster_loader.py rebuilt** — loads 4 roster JSONs, lookup, enrich_pick, enrich_player
2. **Rosters wired into daily_picks.py** via `enrich_via_rosters()` — position, team, jersey data flows to all picks
3. **API endpoints fixed** — /health, /picks, /stats, /combos, /backtest all return valid data
4. **AGENTS.md updated** — actual roster count, actual hit rate, actual pipeline status
5. **Backtest grading** — 84 WNBA picks from 7/19 graded against ESPN boxscores

## Recommendations

1. **Purge graded_picks** — drop and reimport only from properly graded CSVs
2. **Get Odds API Business un-maxed** — MLB can't generate picks without live lines
3. **Run WNBA when games resume** — self-edge works, 60.7% is solid for UNDER-only
4. **Remove WC references** — World Cup ended, sports registry still lists it
5. **Delete duplicate adapters** — src/adapters/ has 4 ESPN fetchers, 3 odds fetchers

## Live URLs

- API Health: https://tc-api-true.zocomputer.io/health
- Dashboard: https://tc-streamlit-dashboard-true.zocomputer.io
- Zo Dashboard: https://true.zo.space/nba-tc

---
Generated: 2026-07-24 01:50 UTC
