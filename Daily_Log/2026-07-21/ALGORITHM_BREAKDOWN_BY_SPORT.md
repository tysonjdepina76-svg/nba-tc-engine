# TC Pipeline — Algorithm Breakdown by Sport
Generated: 2026-07-21 7:30 AM ET | Source: live code (not memory)

---

## NAME FIX STATUS
Names now sync from ESPN roster → boxscore. The grading engine cross-references `statsapi.boxscore()` with the ESPN-provided player names from projections. Player name mismatch was the #1 grading blocker — resolved.

---

## 1. MLB — Baseball

### Projection Engine
File: `generate_projections.py` → `build_mlb_player_proj()`

Season baselines (league average per game):
| Stat | Base |
|------|------|
| H (Hits) | 1.00 |
| HR (Home Runs) | 0.12 |
| RBI | 0.55 |
| R (Runs) | 0.55 |
| SB (Stolen Bases) | 0.12 |
| TB (Total Bases) | 1.65 |
| BB (Walks) | 0.40 |
| K (Strikeouts) | 0.85 |
| AVG (Batting Avg) | 0.250 |

Projection formula (seeded per player):
```
projection = base * (0.8 + random() * 0.4)
```
- Random seed: `f"{player_name}{team}2026"` — deterministic per player
- Range: 80% to 120% of league average

### Edge Calculation
File: `tc_math.py` → `sport_over_under_signal()`
```
diff = projection - market_line
edge = abs(diff)                     ← ABSOLUTE edge (not %)
if edge > 8.0: edge = 8.0            ← Max cap
if edge < 0.5: FLAT (no bet)         ← Min threshold
direction = OVER if diff > 0 else UNDER
```

Config: `min_edge=0.5, max_edge=8.0, use_pct=False`

### Pick Generation
File: `daily_picks.py` → `generate_picks()`
```
edge = projection - line
direction = OVER if edge > 0 else UNDER
```
- Line comes from SerpAPI/DK scrape (when available) or defaults to 0.0 (SELF_EDGE)
- With line=0: edge = projection (massive self-edge, not tradeable without real lines)

### Live Enrichment
File: `src/adapters/free_api_aggregator.py`
- `statsapi.league_leader_data()` → batting: HR, SB, R, RBI, BA, OPS, H, SO
- `statsapi.league_leader_data()` → pitching: ERA, K/9, BB/9, WHIP, SO, BB, H/9
- `pybaseball.batting_stats()` / `pitching_stats()` → same fields, cross-validation
- Applied per player: `live_batting_avg`, `live_ops`, `live_hr`, `live_era`, `live_k9`, `live_whip`

### Active Stats
H, HR, RBI, R, SB, TB, BB, K, AVG

---

## 2. WNBA — Women's Basketball

### Projection Engine
File: `gen_wnba_today.py`

Season baselines (league average per game):
| Stat | Base |
|------|------|
| PTS | 12.5 |
| REB | 5.0 |
| AST | 3.0 |
| STL | 1.0 |
| BLK | 0.7 |
| 3PM | 1.2 |
| TO | 1.8 |
| OREB | 1.2 |
| DREB | 3.8 |
| PF | 2.2 |

Projection formula (seeded per player):
```
projection = base * (0.75 + random() * 0.5)
```
- Random seed: `f"{name}{team_abbr}2026wnba"` — deterministic per player
- Range: 75% to 125% of league average
- Players pulled from ESPN team rosters (top 8 per team)

### Edge Calculation
File: `tc_math.py` → `sport_over_under_signal()`
```
diff = projection - market_line
edge = abs(diff)                     ← ABSOLUTE edge
if edge > 15.0: edge = 15.0          ← Max cap
if edge < 0.5: FLAT (no bet)         ← Min threshold
direction = OVER if diff > 0 else UNDER
```

Config: `min_edge=0.5, max_edge=15.0, use_pct=False`

### Live Enrichment
File: `src/adapters/free_api_aggregator.py`
- `nba_api.stats.endpoints.leaguedashplayerstats` (league_id_nullable="10" = WNBA)
- Fields: PTS, REB, AST, STL, BLK, FG_PCT, FG3_PCT, FT_PCT, MIN
- Applied per player: `live_pts`, `live_reb`, `live_ast`, `live_3pct`

### Active Stats
PTS, REB, AST, STL, BLK, 3PM, TO, OREB, DREB, PF
+ Derived: PRA (PTS+REB+AST), PR (PTS+REB), PA (PTS+AST), RA (REB+AST)

---

## 3. WC — World Cup / Soccer

### Projection Engine
File: `generate_projections.py` → `build_wc_player_proj()`

Season baselines (per match):
| Stat | Base |
|------|------|
| Goals | 0.25 |
| Assists | 0.18 |
| Shots | 1.8 |
| Shots on Target | 0.8 |
| Passes | 35 |
| Tackles | 1.5 |
| Yellow Cards | 0.15 |
| Saves | 0 (GK only) |

Projection formula (seeded per player):
```
projection = base * (0.7 + random() * 0.6)
```
- Random seed: `f"{player_name}{team}wc2026"` — deterministic per player
- Range: 70% to 130% of per-match average
- Passes rounded to integer

### Edge Calculation
File: `tc_math.py` → `sport_over_under_signal()`
```
diff = projection - market_line
edge = abs(diff) / market_line       ← PERCENTAGE edge (% of line)
if edge > 0.50: edge = 0.50          ← Max 50% cap
if edge < 0.005: FLAT (no bet)       ← Min 0.5%
direction = OVER if diff > 0 else UNDER
```

Config: `min_edge=0.005, max_edge=0.50, use_pct=True`

### Active Stats
Goals, Assists, Shots, Shots on Target, Passes, Tackles, Yellow Cards, Saves

### ⚠️ Blocked
- Odds API Business tier maxed — no real WC lines
- WC picks are SELF_EDGE only

---

## 4. NFL — Football (PRE-SEASON, INACTIVE)

### Config (ready but not running)
```
Config: min_edge=0.5, max_edge=15.0, use_pct=False (absolute)
```
- `nfl_api_adapter` wired and functional
- No projection generation or pick generation active yet
- Will activate when NFL season starts

---

## 5. NBA — Basketball (OFF-SEASON)

### Config (ready but not running)
```
Config: min_edge=0.5, max_edge=15.0, use_pct=False (absolute)
```
- `nba_api` wired for WNBA stats
- NBA-specific projections not active (off-season)
- Can be repurposed for G-League if needed

---

## 6. NHL — Hockey (OFF-SEASON)

### Config (ready but not running)
```
Config: min_edge=0.2, max_edge=5.0, use_pct=False (absolute)
```
- No active NHL data source wired
- Lowest thresholds — hockey has smaller stat magnitudes

---

## 7. NCAAB / NCAAF (NOT BUILT)

### Config only
```
NCAAB: min_edge=1.0, max_edge=25.0, use_pct=False
NCAAF: min_edge=1.5, max_edge=30.0, use_pct=False
```
- No data sources wired for college sports
- Higher thresholds account for higher variance

---

## 8. UFC / EPL (NOT BUILT)

### Config only
```
UFC:  min_edge=0.01, max_edge=0.50, use_pct=True
EPL:  min_edge=0.005, max_edge=0.50, use_pct=True
```
- Both use percentage-based edge (like soccer)
- No data sources wired

---

## Shared / Cross-Sport Algorithms

### TC Math — Core Signal
File: `tc_math.py` → `over_under_signal()` and `sport_over_under_signal()`

```
if market_line <= 0: INVALID
diff = projection - market_line
if use_pct: edge = abs(diff) / market_line
else:       edge = abs(diff)
if edge > max_edge: edge = max_edge
if edge < min_edge: FLAT
direction = OVER if diff > 0 else UNDER
```

### Consensus Line (Multi-Book)
File: `tc_math.py` → `consensus_line()`
```
Requires ≥3 books
Methods: median (default), mean, sharp, mode
Sharp priority: Pinnacle > Circa > DraftKings > FanDuel > BetMGM > Caesars
```

### Expected Value (Kelly)
File: `tc_math.py` → `calculate_expected_value()`
```
decimal_odds = (odds/100)+1 if odds>0 else (100/abs(odds))+1
implied_prob = 1 / decimal_odds
true_prob = implied_prob + edge  (pct) or implied_prob (absolute)
true_prob = clamp(0.01, true_prob, 0.99)
ev = (true_prob * decimal_odds) - 1
```

### Combo Scoring
File: `tc_math.py` → Combo builder
- Weighted multi-stat combinations
- Cross-stat correlation adjustments
- Requires ≥3 picks, returns top combos by combined edge

---

## Data Source Map per Sport

| Sport | Rosters | Projections | Lines | Live Enrichment | Active |
|-------|---------|-------------|-------|-----------------|--------|
| MLB | ESPN API | Seeded random | SerpAPI (maxed) | statsapi + pybaseball | ✅ |
| WNBA | ESPN API | Seeded random | SerpAPI (maxed) | nba_api (WNBA) | ✅ |
| WC | ESPN API | Seeded random | Odds API (maxed) | None | ✅ |
| NFL | — | Not built | — | nfl_api_adapter | ❌ |
| NBA | ESPN (off-season) | Not built | — | nba_api (dormant) | ❌ |
| NHL | — | Not built | — | — | ❌ |

---

## Edge by Sport (Quick Reference)

| Sport | Edge Type | Min Edge | Max Edge | Formula |
|-------|-----------|----------|----------|---------|
| MLB | Absolute | 0.5 | 8.0 | proj - line |
| WNBA | Absolute | 0.5 | 15.0 | proj - line |
| WC | Percentage | 0.5% | 50% | (proj-line)/line |
| NFL | Absolute | 0.5 | 15.0 | proj - line |
| NBA | Absolute | 0.5 | 15.0 | proj - line |
| NHL | Absolute | 0.2 | 5.0 | proj - line |
| NCAAF | Absolute | 1.5 | 30.0 | proj - line |
| NCAAB | Absolute | 1.0 | 25.0 | proj - line |
