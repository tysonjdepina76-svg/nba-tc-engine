# TC Pipeline — Full Data Breakdown by Sport and Source

**Generated:** 2026-07-21 06:25 AM ET
**Status:** Live data audit from actual code

---

## MLB DATA SOURCES

### 1. ESPN Free API (espn_enricher.py, espn.py)
- **What we get:** Schedule, game summaries, team rosters, final scores
- **What we DON'T get:** Player props, betting lines, advanced stats
- **Cost:** Free, no key
- **Status:** WORKING ✓

### 2. MLB-StatsAPI → via `statsapi` Python package (free_api_aggregator.py)
- **What we get (per player, current season):**
  - Hitters: AVG, HR, RBI, OPS, SLG, OBP
  - Pitchers: ERA, WHIP, SO, W
- **How:** `statsapi.league_leader_data()` with stat groups
- **Cost:** Free, no auth
- **Status:** WORKING ✓ — wired into daily_picks.py via `get_live_stats()`

### 3. PyBaseball (free_api_aggregator.py)
- **What we get (per player, current season):**
  - Batting: `pybaseball.batting_stats(2026, qual=50)`
  - Pitching: `pybaseball.pitching_stats(2026, qual=30)`
- **Overlap with statsapi:** Same data, different source — cross-validation
- **Cost:** Free, no auth
- **Status:** WORKING ✓

### 4. Fangraphs (tc_math.py line 90)
- **What we WANT:** Advanced stats (wOBA, xFIP, WAR, park factors)
- **What we GET:** HTTP 403 — IP blocked, no API key
- **Cost:** Free tier
- **Status:** BLOCKED ✗ — to fix: export stats from browser manually or use proxy

### 5. SerpAPI (serp_odds_scraper.py)
- **What we get:** Live DraftKings player prop lines (scraped from Google results)
- **Specific stats scraped:** Points, Rebounds, Assists, Threes (WNBA); Hits, HRs, RBIs, Ks (MLB)
- **Cap:** 50 searches/run, 250/day
- **Status:** QUOTA MAXED ✗ — resets ~8/1
- **No lines = Self-edge until reset**

### 6. Odds API (src/adapters/odds_api_adapter.py)
- **What we get (when working):** Real-time odds across DraftKings, BetMGM, FanDuel
- **Status:** DEAD ✗ — Business tier quota maxed (401)
- **Dependent on:** Gap 5

---

## WNBA DATA SOURCES

### 1. ESPN Free API
- **What we get:** Schedule, game summaries, team info
- **What we DON'T:** Player props, lines
- **Status:** WORKING ✓

### 2. NBA_API (free_api_aggregator.py) — WNBA via LeagueID="10"
- **What we get (per player, current season):**
  - nba_api.stats.endpoints.leaguedashplayerstats → PTS, REB, AST, FG%, 3P%, FT%, STL, BLK, MIN
  - nba_api.stats.endpoints.scoreboardv2 → live scoreboard (wnba_api_adapter.py)
  - boxscoreadvancedv2 → per-game player breakdowns
- **Cost:** Free, no auth
- **Status:** WORKING ✓

### 3. SerpAPI (serp_odds_scraper.py)
- **What we get:** DraftKings WNBA player prop lines
- **Specific props:** Points, Rebounds, Assists, 3-Pointers Made, Steals, Blocks
- **Status:** QUOTA MAXED ✗

---

## WORLD CUP DATA SOURCES

### 1. ESPN Free API
- **What we get:** Match schedule, team info, match summaries
- **Status:** WORKING ✓
- **Today:** 0 matches

### 2. No Free Soccer Stats API
- **Problem:** No equivalent to statsapi/pybaseball for soccer
- **No live player stats for World Cup** from free sources

### 3. SerpAPI (serp_odds_scraper.py)
- **What we get:** Soccer player prop lines
- **Status:** QUOTA MAXED ✗

---

## GITHUB SOURCES (github_line_sources.py)

### 1. NBA-TC-Engine (repo)
- **What:** Historical picks + results, backtest baselines, reference math
- **Status:** WORKING ✓

### 2. Other sport-data repos
- **What:** Community-maintained line histories, reference models
- **Status:** Read-only access

---

## SUMMARY: WHAT GIVES US REAL LINES

| Source | Type | Cost | Status |
|--------|------|------|--------|
| SerpAPI | Scraped DraftKings lines | Monthly quota ($50 tier) | MAXED ✗ |
| Odds API | API-direct odds | Business tier | DEAD ✗ |
| ESPN | Game data only | Free | WORKING |
| statsapi | MLB stats (NO LINES) | Free | WORKING |
| pybaseball | MLB stats (NO LINES) | Free | WORKING |
| nba_api | WNBA stats (NO LINES) | Free | WORKING |
| Fangraphs | Advanced MLB stats | Free | BLOCKED (403) |

**Bottom line:** Free APIs give us stats/projections. Real lines require SerpAPI or Odds API. Both dead → self-edge only.
