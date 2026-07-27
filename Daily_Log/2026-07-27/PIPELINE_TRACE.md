# TC Pipeline — Full Technical Trace (2026-07-27)

## 1. ORCHESTRATION TRIGGER

**Entry point:** `python3 daily_picks.py --sport mlb`

**File:** `/home/workspace/Projects/daily_picks.py` (line 1099+, `main()`)

**First schema loaded:** `SPORT_CONFIG` dict at line 72-116 of `daily_picks.py`

```python
SPORT_CONFIG = {
    'mlb': {
        'generator': 'gen_mlb_today.py',
        'recalibrator': 'mlb_recalibration.py',
        'min_edge': 0.05,  # minimum edge to fire a pick
        'stat_blacklist': ['AVG', 'OBP', 'SLG', 'OPS'],
    },
    ...
}
```

**Flow:**
```
main()
  ├── parser.add_argument('--sport', choices=['mlb','wnba','nba','nfl','nhl','all'])
  ├── parser.add_argument('--grade')        ← only if grading
  ├── parser.add_argument('--grade-date')   ← only if grading
  └── if --grade:
        → HistoricalGrader(picks_df, grade_date) → grade_picks()
      else:
        → generate_picks(sport)
          ├── SPORT_CONFIG[sport] loaded
          ├── load_projections(sport)       ← reads Daily_Log/YYYY-MM-DD/proj_MLB_*.json
          ├── enrich (ESPN, SerpAPI, TheRundown, Rosters)
          ├── recalibrate (pre + post)
          └── save to picks.db + last_run.json
```

## 2. DATA INGESTION & SCHEMA ENFORCEMENT

### Step 1: gen_mlb_today.py → Projection JSONs

**File:** `/home/workspace/Projects/gen_mlb_today.py` (491 lines)

```
generate()
  ├── get_todays_games() → statsapi.schedule(date='2026-07-27')
  │     Returns: [{game_id, away_name, home_name, status, game_datetime}]
  │     Source: https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-07-27
  │
  ├── For each scheduled game:
  │     build_projections_for_game(game)
  │       ├── get_team_roster(team_name) → statsapi.roster(team_id) → [player dicts]
  │       ├── For each player (max 40):
  │       │     find_player_id(name) → statsapi.lookup_player() cached
  │       │     get_player_stats(name, pid) → statsapi.player_stat_data(pid, "hitting", "season")
  │       │       Returns: {G, AVG, OBP, SLG, OPS, H, R, RBI, HR, 2B, 3B, BB, SB}
  │       │     For each stat → hash-based self-edge line + tc_math.sport_over_under_signal()
  │       └── Pitcher projections (SO, ERA, BB, H)
  │
  ├── TheRundown enrichment (game_lines):
  │     from therundown_adapter import get_formatted_odds
  │     get_formatted_odds('MLB') → X-TheRundown-Key header
  │       URL: https://therundown.io/api/v2/sports/3/events/2026-07-27
  │       Returns: {events: [{event_id, away_full, home_full, moneyline, spread, totals}]}
  │     Match by away_full/home_full → inject game_lines dict per game
  │
  └── Save: Daily_Log/2026-07-27/proj_MLB_<away>_at_<home>.json (12 files)
            Daily_Log/2026-07-27/proj_MLB_summary.json (master)
```

### Schema: Single Player Projection Entry
```json
{
  "name": "Aaron Judge",
  "player_id": 592450,
  "team": "New York Yankees",
  "venue": "away",
  "games_played": 95,
  "season_stats": { "G": 95, "AVG": 0.310, "H": 112, "HR": 38, ... },
  "projections": {
    "H":   { "projection": 1.15, "line": 1.173, "edge": 0.023, "direction": "UNDER" },
    "HR":  { "projection": 0.42, "line": 0.428, "edge": 0.008, "direction": "UNDER" },
    "RBI": { "projection": 0.78, "line": 0.796, "edge": 0.016, "direction": "UNDER" },
    ...
  }
}
```

### Schema: Game Lines Entry (from TheRundown)
```json
{
  "game_lines": {
    "spread": {
      "New York Yankees": {"DK": {"line": -1.5, "price": 119}, "FD": {...}, "MGM": {...}},
      "Chicago White Sox": {"DK": {"line": 1.5, "price": -142}, "FD": {...}, "MGM": {...}}
    },
    "moneyline": {
      "New York Yankees": {"DK": -148, "FD": -138, "MGM": -150},
      "Chicago White Sox": {"DK": 122, "FD": 118, "MGM": 125}
    },
    "totals": {
      "over":  {"DK": {"line": 8.5, "price": -108}, "FD": {...}, "MGM": {...}},
      "under": {"DK": {"line": 8.5, "price": -113}, "FD": {...}, "MGM": {...}}
    }
  }
}
```

### Step 2: daily_picks.py → load_projections()

**Function:** `load_projections(sport)` at daily_picks.py line ~660

Reads all `Daily_Log/YYYY-MM-DD/proj_MLB_*.json` files, extracts:
- `player`, `team`, `matchup`, `stat`, `projection` (from `stat.projections[stat].projection`)
- `market_line` (from `stat.projections[stat].line`)
- `edge` (from `stat.projections[stat].edge`)
- `direction` (from `stat.projections[stat].direction`)
- `reason` (from explanation_engine)

Flattens into Pandas DataFrame with columns:
```python
['date', 'sport', 'player', 'team', 'opponent', 'stat', 'projection',
 'market_line', 'edge', 'direction', 'matchup', 'period', 'reason']
```

### Step 3: Enrichment Pipeline (daily_picks.py line ~230+)

```python
def generate_picks(sport):
    df = load_projections(sport)
    
    # 1. ESPN context enrichment
    df = enrich_with_espn_context(df)    # Tags players with season/venue context
    
    # 2. SerpAPI web-search enrichment (DEAD — quota maxed)
    df = enrich_with_serpapi(df)         # skip: module missing
    
    # 3. TheRundown market lines
    df = enrich_projections_with_therundown(df, sport)
    #   → maps team names to TheRundown event IDs
    #   → sets market_line from real DK/FD/MGM odds when available
    
    # 4. Roster enrichment
    df = enrich_with_rosters(df)         # Adds position, jersey, depth info
    
    return df
```

## 3. THE FEATURE PULL

Features are computed ON-THE-FLY during projection generation, not from a feature store:

### In gen_mlb_today.py `build_projections_for_game()`:
```python
for stat in ["H", "R", "RBI", "HR", "2B", "3B", "BB", "SB"]:
    raw = (stats[stat] / games) * REGRESSION_FACTOR * venue_bonus
    #       ↑ season total    ↑ games    ↑ 0.95 default   ↑ 0.975 away / 1.025 home
    
    proj_val = round(raw, 2)
    
    # Self-edge line (hash-based pseudo-market)
    hash_val = int(hashlib.md5(f"{name}_{stat}_{game_id}".encode()).hexdigest(), 16)
    line = round(proj_val * 0.98, 3) if hash_val % 2 == 0 else round(proj_val * 1.02, 3)
    
    # Direction via tc_math
    direction, edge = sport_over_under_signal(
        projection=proj_val,
        market_line=line,
        sport="MLB",
        min_edge=0.0
    )
```

### Input features per player:
- **Season stats (rate):** AVG, OBP, SLG, OPS (regressed to mean)
- **Season stats (count):** H, R, RBI, HR, 2B, 3B, BB, SB (divided by G → per-game)
- **Venue:** HOME_BOOST=1.025, AWAY_PENALTY=0.975
- **Regression factor:** 0.95 (shrinks toward 0, conservative)
- **Pitcher stats:** SO, ERA, BB, H (from opposing pitcher's season data)
- **Statcast augmentation** (if pybaseball available): xBA + platoon splits, 30% nudge

## 4. THE HYBRID EXECUTION FORK

### Heuristic Rules Layer

**File:** `/home/workspace/Projects/tc_math.py`

**Function:** `sport_over_under_signal(projection, market_line, sport, min_edge=0.05)`

```python
def sport_over_under_signal(projection, market_line, sport, min_edge=0.05):
    if market_line is None or market_line == 0:
        return "INVALID", 0.0
    
    # Config from SPORT_CONFIGS dict
    config = SPORT_CONFIGS.get(sport, SPORT_CONFIGS['DEFAULT'])
    
    # Edge calculation
    edge = abs(projection - market_line)
    pct_edge = edge / market_line  # percentage edge
    
    # Threshold check
    if pct_edge < min_edge:
        return "FLAT", round(pct_edge, 4)
    
    # Direction
    if projection > market_line:
        return "OVER", round(pct_edge, 4)
    else:
        return "UNDER", round(pct_edge, 4)
```

**SPORT_CONFIGS (in tc_math.py):**
```python
SPORT_CONFIGS = {
    'MLB':  {'min_edge': 0.05, 'direction_cap': 0.60, 'max_projection': 8.0},
    'WNBA': {'min_edge': 0.05, 'direction_cap': 0.60, 'max_projection': 15.0},
    'NBA':  {'min_edge': 0.05, 'direction_cap': 0.60, 'max_projection': 15.0},
    'NFL':  {'min_edge': 0.05, 'direction_cap': 0.60, 'max_projection': 15.0},
    'NHL':  {'min_edge': 0.02, 'direction_cap': 0.60, 'max_projection': 5.0},
}
```

### ML Layer — Statcast Augmentation

**File:** `/home/workspace/Projects/gen_mlb_today.py` (function `_augment_mlb_rate_stat()`)

```python
def _augment_mlb_rate_stat(player_name, pid, stat):
    """
    30% nudge toward blended xBA (Statcast) + platoon split adjustments.
    Guarded by consume_budget('pybaseball').
    """
    if stat not in ('AVG', 'OBP', 'SLG', 'OPS'):
        return None  # Only augments rate stats
    
    # Fetch Statcast expected batting average (xBA)
    xba = pybaseball.statcast_batter(player_name, ...)  # Statcast data
    
    # Blend: 70% season rate stat + 30% xBA
    blended = (season_stat * 0.70) + (xba * 0.30)
    return blended
```

### Merge Function — Recalibration

**File:** `/home/workspace/Projects/mlb_recalibration.py`

**Function:** `calibrate_mlb_picks(df)`

```python
def calibrate_mlb_picks(df):
    """
    1. Drop blacklisted stats: AVG, OBP, SLG, OPS
    2. Apply 60/40 direction cap (no more than 60% one direction)
    3. Apply stat minimums (min games, min projection)
    4. Sort by edge, keep top picks
    """
    # Drop rate stats
    df = df[~df['stat'].isin(['AVG', 'OBP', 'SLG', 'OPS'])]
    
    # Direction cap
    over_mask = df['direction'] == 'OVER'
    under_mask = df['direction'] == 'UNDER'
    max_each = int(len(df) * 0.60)
    
    over_picks = df[over_mask].nlargest(max_each, 'edge')
    under_picks = df[under_mask].nlargest(max_each, 'edge')
    df = pd.concat([over_picks, under_picks])
    
    # Stat minimums
    df = df[df['projection'] >= 0.02]  # skip near-zero projections
    
    return df
```

## 5. THE DECISION GATE

All filtering happens in **daily_picks.py → generate_picks()** and **mlb_recalibration.py**:

### Gate 1: Projection Generation (gen_mlb_today.py)
```python
if games < MIN_GAMES:   # MIN_GAMES = 4 (minimum games played)
    continue             # Skip rookies/DNPs

# Invalid/flat directions replaced with hash-based fallback
if direction in ("INVALID", "FLAT"):
    direction = "OVER" if proj_val > line else "UNDER"
    edge = round(abs(proj_val - line), 3)
```

### Gate 2: Post-generation (daily_picks.py line ~380+)
```python
# Minimum edge check
df = df[df['edge'] >= SPORT_CONFIG[sport]['min_edge']]

# Maximum projection check (prevents absurd outputs)
df = df[df['projection'] <= SPORT_CONFIG[sport].get('max_projection', 99)]

# ESPN context: drop players on IL/not starting
```

### Gate 3: Recalibration (mlb_recalibration.py)
```python
# Drop rate stats (AVG, OBP, SLG, OPS — too noisy for betting)
# Drop if projection < 0.02 (rounding noise)
# Direction cap: 60/40 split enforced
# Take top ~1250 from original 4278 (70% cut)
```

### Gate 4: Signal quality
```python
# Only 5 OVER picks pass through (self-edge default is UNDER-heavy)
# 1,245 UNDER picks — need real market lines from OddsPapi/Paid TheRundown
# to flip the OVER/UNDER balance
```

## 6. THE FINAL WRITE

### Database: `/home/workspace/Projects/data/picks.db` → `picks` table

```sql
CREATE TABLE picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,          -- '2026-07-27'
    league TEXT NOT NULL,        -- 'MLB'
    player TEXT NOT NULL,        -- 'Aaron Judge'
    team TEXT DEFAULT '',        -- 'New York Yankees'
    stat TEXT NOT NULL,          -- 'HR'
    tc_projection REAL DEFAULT 0,  -- 0.42
    market_line REAL DEFAULT 0,    -- 0.428
    edge REAL DEFAULT 0,           -- 0.008
    reason TEXT DEFAULT '',        -- 'Self-edge projection'
    direction TEXT DEFAULT '',     -- 'UNDER'
    matchup TEXT DEFAULT '',       -- 'NYY @ CWS'
    period TEXT DEFAULT 'GAME',
    signal TEXT DEFAULT 'SELF_EDGE',
    created_at NUM DEFAULT datetime('now'),
    actual REAL DEFAULT 0,       -- Filled later by grading
    hit INTEGER DEFAULT 0,       -- Filled later by grading
    profit REAL DEFAULT 0
);
```

### Runtime Log: `/home/workspace/Daily_Log/last_run.json`
```json
{
  "last_run": "2026-07-27T03:16:34.363669-04:00",
  "picks_count": 1250,
  "sports": {"mlb": 1250, "wnba": 0, "nba": 0, "nfl": 0, "nhl": 0}
}
```

### Projection Files: `/home/workspace/Daily_Log/2026-07-27/`
```
proj_MLB_summary.json              ← Master with game_lines
proj_MLB_Seattle_Mariners_at_Texas_Rangers.json
proj_MLB_Baltimore_Orioles_at_Detroit_Tigers.json
...
(12 game files, 368 player projections total)
```

### Combo Picks: Generated by `combo_generator.py`, saved to picks.db `combos` table

## EXECUTION SUMMARY (7/27 MLB)

```
gen_mlb_today.py:      12 games → 368 players → 4278 stat-lines
daily_picks.py enrich:
  - ESPN context:      4236/4278 tagged
  - SerpAPI:           DEAD (skipped)
  - TheRundown:        4272/4278 market_line set
  - Rosters:           3816/4278 enriched
RECAL (pre):           4278 → 2491 (-1787 removed)
RECAL (post):          2491 → 1250 (-1241 removed)
  Direction:           5 OVER / 1245 UNDER
  Combos generated:    25
  Saved:               1250 picks to picks.db
  Game lines:          11/12 games with live DK/FD/MGM spreads
```

## CRITICAL ARCHITECTURE NOTES

1. **TheRundown adapter** (`src/adapters/therundown_adapter.py`):
   - Free tier — `X-TheRundown-Key` header
   - URL: `https://therundown.io/api/v2/sports/3/events/2026-07-27`
   - Returns: moneyline, spread, totals (no player props on free tier)
   - Cached 120s TTL for events, 60s for individual events

2. **OddsPapi adapter** (`src/adapters/oddspapi_adapter.py`):
   - Wrapper around The Odds API v4
   - Requires `ODDSPAPI_API_KEY` env var
   - Player prop endpoint: `/sports/{slug}/events/{id}/odds?markets=player_home_runs`
   - **Current key invalid** — needs paid The Odds API key for player props

3. **Self-edge bottleneck** (line 500-503 of gen_mlb_today.py):
   - Every pick gets a hash-based pseudo-line at ±2% of projection
   - This makes direction = UNDER for ~99.6% of picks
   - Hit rate ceiling: ~38-40% (all-UNDER with no skill)
   - **Fix**: Real market lines via paid Odds API or TheRundown paid tier

4. **Grading engine** (`sports_grading_engine.py`):
   - Function-based: `grade_picks(picks_df, sport, date_str)`
   - Fetches boxscores via statsapi/ESPN
   - Direction-aware: OVER → actual>=projection, UNDER → actual<=projection
   - Known issue: DB column is `tc_projection` but engine expects `projection`
