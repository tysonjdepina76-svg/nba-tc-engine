# TC Pipeline — End-to-End Technical Trace
**Date**: 2026-07-27 | **Time**: 3:16 AM ET | **Picks Generated**: 1,250 MLB

---

## 1. ORCHESTRATION TRIGGER

**Executable**: `python3 /home/workspace/Projects/daily_picks.py --sport mlb`

**Entry point** (line ~1100): `if __name__ == "__main__": main()`

`main()` at line ~890 parses args via argparse:
```python
parser.add_argument("--sport", choices=["mlb","wnba","nba","nfl","nhl","all"])
```

**First schema file loaded**: `data/picks.db` (SQLite) — accessed via `load_projections(sport)` which reads the `picks` table schema:
```
id, date, league, player, team, stat, tc_projection, market_line, edge,
reason, direction, matchup, period, signal, created_at, actual, hit, profit
```

Sport status check: `SPORT_STATUS = {"MLB": "LIVE", "WNBA": "LIVE", ...}` at line ~60.

---

## 2. DATA INGESTION & SCHEMA

### 2a. Projection Loading (`load_projections()`, line ~950)
Reads JSON files from `Daily_Log/2026-07-27/proj_MLB_*.json`:

```python
# For each game file (12 games, 368 players):
proj = json.load(f)  # {"game_id": ..., "players": [...], "game_lines": {...}}
for p in proj["players"]:
    for stat, vals in p["projections"].items():  # e.g. "HR": {"projection": 0.12, "line": 0.118, "edge": 0.002, "direction": "OVER"}
```

**Schema enforcement**: Each stat's dict must have `projection`, `line`, `edge`, `direction`.
The pipeline loads `tc_projection = vals["projection"]` and `market_line = vals["line"]`.

### 2b. TheRundown Game Lines (`gen_mlb_today.py`, line ~474)
After building player projections, each game JSON is enriched:
```python
from therundown_adapter import get_formatted_odds
rundown = get_formatted_odds('MLB')
# Matches away/home names to TheRundown events
game_entry['game_lines'] = {
    'spread': ev['spread'],      # {team: {DK: {line, price}, FD: ..., MGM: ...}}
    'moneyline': ev['moneyline'], # {team: {DK: price, FD: price, MGM: price}}
    'totals': ev['totals'],       # {over: {DK: {line, price}}, under: {DK: {line, price}}}
}
```
**API**: `GET https://therundown.io/api/v2/events?sport_id=3&date=2026-07-27`  
**Auth**: `X-TheRundown-Key` header  
**Daily cap**: 9999 (uncapped in crash_guard)

---

## 3. FEATURE PULL

### 3a. Season Stats (gen_mlb_today.py, `get_player_stats()`, line ~390)
```python
stats = statsapi.player_stat_data(player_id, group="hitting", type="season")
```
Cached per-player in `data/cache/pid_*.json` with `_fetch_date` key.

**Stats pulled**: G, AVG, OBP, SLG, OPS, H, R, RBI, HR, 2B, 3B, BB, SB

### 3b. ESPN Context Enrichment (daily_picks.py, `enrich_with_espn()`, line ~1040)
```python
from src.enhancer import enrich_projections_with_espn
# Tags each stat-line with: ESPN player_id, team_abbr, position, season_avg, vs_opponent
```

### 3c. Roster Enrichment (daily_picks.py, `enrich_with_rosters()`, line ~1060)
```python
from src.roster_loader import RosterLoader
loader = RosterLoader("mlb")  # loads data/rosters/mlb_rosters.json
# Adds: team_id, position, jersey_number, status
```

### 3d. Pybaseball Statcast (gen_mlb_today.py, `apply_mlb_augmentation()`, line ~450)
```python
from pybaseball import statcast_batter
# Gets xBA, launch_angle, barrel_rate for last 30 days
# Applies 30% nudge toward Statcast-expected values
# Budget-guarded: consume_budget("pybaseball", 1)
```

---

## 4. HYBRID EXECUTION FORK

### 4a. Heuristic Rule Engine: `tc_math.py`
**File**: `Projects/tc_math.py`  
**Key function**: `sport_over_under_signal()` at line ~180
```python
def sport_over_under_signal(projection, market_line, sport, min_edge=0.0):
    # Step 1: Compute raw edge = (projection - market_line) / market_line
    # Step 2: Check against sport-specific config (SPORT_CONFIGS):
    #   MLB: min_edge=0.5, max=8.0
    #   WNBA: min_edge=0.5, max=15.0
    #   NFL: min_edge=0.5, max=15.0
    # Step 3: Apply directional logic:
    #   if edge > 0: return "OVER", edge
    #   if edge < 0: return "UNDER", abs(edge)
    # Step 4: Cap edge at sport max
    return direction, pct_edge
```

### 4b. Hash-Based Self-Edge Lines (gen_mlb_today.py, line ~440)
Before tc_math, each player/stat combination gets a synthetic market line:
```python
key = f"{name}_{stat}_{game_id}"
hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
line = round(proj_val * 0.98, 3) if hash_val % 2 == 0 else round(proj_val * 1.02, 3)
```
This creates a 2% spread around the projection — self-edge only until real player props arrive.

### 4c. ML Model (NOT YET WIRED)
The `tc_math_hybrid.py` file exists with `HybridPredictor` class but is not called in the pipeline.
Heuristic-only (self-edge + tc_math) for now.

---

## 5. DECISION GATE — RECALIBRATION

### 5a. Pre-Recalibration: `mlb_recalibration.py`, `calibrate_mlb_picks()`
```python
# Input: 4,278 stat-lines with projections, lines, edges
# Filters applied:
#   - Drop AVG, OBP, SLG, OPS (rate stats → not prop-friendly)
#   - Direction diversity: ensure mix of OVER/UNDER
#   - Blacklist: 0 players, Boosted: 0 players
# Output: 2,491 picks  (1,787 removed)
```

### 5b. Post-Recalibration: second pass
```python
# Further filters: edge thresholding, stat dropout priority
# Final output: 1,250 picks (1,241 removed)
# Direction split: 5 OVER / 1,245 UNDER (all self-edge = UNDER bias)
```

### 5c. Combo Generation
```python
from combo_generator import generate_combos
# Creates parlay combos from top-edge picks
# Output: 25 combos for mlb
```

---

## 6. FINAL WRITE

### 6a. SQLite Database: `data/picks.db`
```sql
INSERT INTO picks (date, league, player, team, stat, tc_projection, market_line, edge,
                   reason, direction, matchup, period, signal)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

**Key output fields**:
| Field | Source | Example |
|-------|--------|---------|
| `tc_projection` | season_avg × regression × venue | 0.85 |
| `market_line` | TheRundown or hash-self-edge | 0.83 |
| `edge` | `tc_math.sport_over_under_signal()` | 0.024 |
| `direction` | OVER or UNDER | UNDER |
| `signal` | SELF_EDGE or THERUNDOWN | SELF_EDGE |

### 6b. JSON Archive: `Daily_Log/2026-07-27/`
```
proj_MLB_summary.json  → 12 games, 368 players, game_lines per game
proj_MLB_*_at_*.json   → per-game detail with spread/ML/totals
last_run.json           → timestamp + count
```

### 6c. Game Lines Schema (per game in proj JSONs):
```json
{
  "game_lines": {
    "spread": {"Seattle Mariners": {"DK": {"line": -1.5, "price": 121}, "FD": {...}}},
    "moneyline": {"Seattle Mariners": {"DK": -145, "FD": -134, "MGM": -140}},
    "totals": {"over": {"DK": {"line": 8.0, "price": -102}}, "under": {...}},
    "event_id": "4e0e6cc8e348c23a45abd24a76706c3a"
  }
}
```

---

## 7. EXECUTION FLOW SUMMARY

```
daily_picks.py --sport mlb
├── load_projections("mlb")
│   ├── Read Daily_Log/2026-07-27/proj_MLB_*.json (12 files)
│   └── Build DataFrame with 4,278 rows (368 players × 12 stats)
├── enrich_with_espn()         → tags 4,236 rows with ESPN context
├── enrich_projections_with_therundown() → sets market_line on 4,272 rows
├── enrich_with_free_apis()    → statsapi + pybaseball (0 cached)
├── enrich_with_rosters()      → team_id, position, status (3,816 enriched)
├── calibrate_mlb_picks(pre)   → 4,278 → 2,491 (drop rate stats, directional filter)
├── calibrate_mlb_picks(post)  → 2,491 → 1,250 (edge thresholding)
├── generate_combos()          → 25 parlay combos
├── save_to_db()               → INSERT 1,250 rows into picks.db
├── save_to_csv()              → data/picks/mlb_2026-07-27.csv
└── update last_run.json       → timestamp + metrics
```

**Total API calls**: ~390 (368 statsapi player_stat_data + 12 TheRundown events + 1 schedule + 10 ESPN)  
**Runtime**: ~90 seconds (with warm caches)  
**Self-edge limitation**: All projections use 2% hash-based lines → UNDER bias → 5/1,245 split
