# TC SYSTEM BLUEPRINT + FULL BACKTEST → COPY/PASTE
## Generated: 2026-07-21 · 4,148 Graded Picks Analyzed

---

# BACKTEST RESULTS (4,148 GRADED PICKS)

## OVERALL: 64.25% HIT RATE

## BY DIRECTION
| Direction | N     | Hits  | Misses | Hit Rate |
|-----------|-------|-------|--------|----------|
| UNDER     | 2,881 | 2,144 | 737    | 74.4%    |
| OVER      | 1,267 | 521   | 746    | 41.1%    |

## BY EDGE BUCKET (The Edge Curve)
| Edge     | N     | Hits  | Misses | Hit Rate |
|----------|-------|-------|--------|----------|
| <0.5     | 2,149 | 1,239 | 910    | 57.6%    |
| 0.5-1    | 1,193 | 752   | 441    | 63.0%    |
| 1-2      | 441   | 341   | 100    | 77.3%    |
| 2-3      | 277   | 249   | 28     | 89.9%    |
| 3-5      | 62    | 58    | 4      | 93.5%    |
| 5+       | 26    | 26    | 0      | 100.0%   |

## BY STAT
| Stat         | N     | Hits  | Misses | Hit Rate |
|--------------|-------|-------|--------|----------|
| total_bases  | 1,018 | 719   | 299    | 70.6%    |
| hits         | 991   | 632   | 359    | 63.8%    |
| rbi          | 977   | 607   | 370    | 62.1%    |
| runs         | 977   | 577   | 400    | 59.1%    |
| strikeouts   | 48    | 41    | 7      | 85.4%    |
| hr           | 30    | 24    | 6      | 80.0%    |
| hits_allowed | 58    | 39    | 19     | 67.2%    |
| earned_runs  | 47    | 25    | 22     | 53.2%    |

## TOP 10 MATCHUPS
| Matchup  | N   | Rate |
|----------|-----|------|
| SEA@PIT  | 119 | 79.0% |
| COL@MIN  | 120 | 74.2% |
| CHC@NYM  | 167 | 73.0% |
| LAD@MIN  | 121 | 71.1% |
| CHW@CLE  | 118 | 71.2% |
| LAD@SD   | 120 | 70.0% |
| KC@MIA   | 105 | 67.6% |
| ATL@PIT  | 120 | 65.0% |
| SD@LAD   | 171 | 64.3% |
| DET@MIN  | 109 | 64.2% |

## TOP 10 TEAMS
| Team | N   | Rate |
|------|-----|------|
| NYM  | 186 | 71.0% |
| CLE  | 175 | 70.3% |
| COL  | 187 | 69.0% |
| MIN  | 221 | 67.9% |
| KC   | 168 | 67.3% |
| LAD  | 194 | 67.0% |
| SD   | 150 | 66.7% |
| TOR  | 186 | 64.0% |
| BAL  | 215 | 63.3% |
| MIL  | 200 | 62.5% |

---

# WNBA TC HYBRID MODEL v3 · FEATURE WEIGHTS

| Feature                | Weight | Category  |
|------------------------|--------|-----------|
| Diff                   | 0.13   | Combos    |
| True Combos            | 0.13   | Combos    |
| Minutes Consistency    | 0.10   | Minutes   |
| Defensive Rating Adv   | 0.08   | Defense   |
| Continuity Diff        | 0.07   | Scheme    |
| H2H Home Win PCT       | 0.06   | Matchups  |
| Basketball IQ Diff     | 0.05   | Assists   |
| Opp FG Advantage       | 0.03   | Defense   |

Total weight: 0.65 (35% reserved for projections base)

---

# PIPELINE ARCHITECTURE MAP

## FLOW
```
ESPN v2 API (free, unlimited)
        │
        ▼
┌──────────────────────────┐
│  generate_projections.py │  ← pybaseball (free)
│  gen_wnba_today.py       │  ← ESPN rosters
│  backfill_projections.py │  ← ESPN boxscores
└──────────┬───────────────┘
           │ proj_SPORT_YYYY-MM-DD.json
           ▼
┌──────────────────────────┐
│  daily_picks.py          │
│  ├─ load_projections()   │
│  ├─ enrich_lines_via_serpapi()  ← SerpAPI (depleted)
│  ├─ tc_math.py functions │
│  └─ generate_picks()     │
└──────────┬───────────────┘
           │ picks.csv
           ▼
┌──────────────────────────────────────┐
│  OUTPUTS                             │
│  ├─ data/picks/mlb_YYYY-MM-DD.csv    │
│  ├─ data/picks/today_picks.csv       │
│  ├─ SQLite: data/picks.db            │
│  └─ Daily_Log/last_run.json          │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  DELIVERY                            │
│  ├─ Streamlit Dashboard :8510        │
│  ├─ FastAPI :8000                    │
│  ├─ /nba-tc route (zo.space)         │
│  ├─ /dashboard route (zo.space)      │
│  └─ Email via Automations            │
└──────────────────────────────────────┘
```

---

# TC MATH EQUATIONS

## Core Edge Formula
```
edge = |tc_projection − market_line|

IF line == 0 (self-edge):
    edge = tc_projection  (raw projection becomes edge)
```

## Signal Determination (over_under_signal)
```python
def over_under_signal(projection, actual_line, min_abs_edge=0.05, max_edge=None):
    if projection <= 0 or actual_line <= 0:
        return None  # FLAT — no pick
    
    diff = projection - actual_line
    abs_diff = abs(diff)
    
    if abs_diff < min_abs_edge:
        return None  # FLAT — edge below threshold
    
    if max_edge is not None and abs_diff > max_edge:
        abs_diff = max_edge  # CAP edge
    
    if diff > 0:
        return "OVER"
    else:
        return "UNDER"
```

## Sport-Specific Thresholds
```python
SPORT_CONFIGS = {
    "MLB":  SportConfig(min_edge=0.05, use_pct=False, max_edge=8.0,  min_market_line=0.5),
    "WNBA": SportConfig(min_edge=0.05, use_pct=False, max_edge=15.0, min_market_line=0.5),
    "WC":   SportConfig(min_edge=0.05, use_pct=True,  max_edge=0.15, min_market_line=0.01),
}

# WC uses PERCENTAGE edge: |diff| / line
# MLB caps at 8.0 absolute edge
# WNBA caps at 15.0 absolute edge
```

## TC Shrinkage (Bayesian)
```
shrunk = (tc_projection × n + market_line × prior_weight) / (n + prior_weight)
```
Where n = sample size of TC data, prior_weight = 20 (shrinkage constant)

## WNBA TC Hybrid Score
```
hybrid_score = Σ(feature_i × weight_i) for all 8 features
             + base_projection × 0.35
```
Direction: OVER if hybrid_score > market_line, UNDER if below
Confidence: proportional to |hybrid_score - market_line|

---

# API STATUS + CAPS

| API            | Status            | Cost | Cap         |
|----------------|-------------------|------|-------------|
| ESPN v2        | ACTIVE/UNLIMITED  | FREE | ∞           |
| pybaseball     | ACTIVE            | FREE | ∞           |
| SerpAPI        | DEPLETED          | $    | reset midnight |
| Odds API       | MAXED (401)       | $    | Business tier full |
| SportsDataIO   | DEAD (401)        | $    | expired     |
| GitHub APIs    | NOT WIRED         | FREE | TBD         |
| statsapi (MLB) | NOT WIRED         | FREE | TBD         |
| nba_api        | NOT WIRED         | FREE | TBD         |
| balldontlie    | NOT WIRED         | FREE | TBD         |

## Priority to Wire
1. GitHub free sports data APIs
2. statsapi (MLB live)
3. nba_api (NBA + WNBA stats)
4. balldontlie (basketball reference)

---

# AUTOMATIONS (all zo:deepseek/deepseek-v4-pro)
| Name                        | Time      |
|-----------------------------|-----------|
| Daily Sports Picks Update   | Morning   |
| MLB Morning Line Pull       | 9:00 AM   |
| WNBA and WC Projections     | 11:00 AM  |
| Evening Sports Refresh      | 6:00 PM   |

---

# TODAY (2026-07-21) EARLY BIRD TOP 10

| Rank | Player          | Team | Stat | Matchup  | Proj | Edge  | Dir  |
|------|-----------------|------|------|----------|------|-------|------|
| 1    | Freddie Freeman | LAD  | TB   | LAD@PHI  | 1.86 | 1.86  | OVER |
| 2    | Aaron Judge     | TB   | TB   | TOR@BOS  | 1.94 | 1.94  | OVER |
| 3    | Shohei Ohtani   | LAD  | TB   | LAD@PHI  | 1.82 | 1.82  | OVER |
| 4    | Yordan Alvarez  | HOU  | TB   | HOU@TEX  | 1.87 | 1.87  | OVER |
| 5    | Mike Trout      | LAA  | TB   | LAA@OAK  | 1.82 | 1.82  | OVER |
| 6    | Bryce Harper    | PHI  | TB   | LAD@PHI  | 1.87 | 1.87  | OVER |
| 7    | Corey Seager    | TEX  | TB   | HOU@TEX  | 1.82 | 1.82  | OVER |
| 8    | Ronald Acuna    | ATL  | TB   | ATL@CIN  | 1.89 | 1.89  | OVER |
| 9    | Juan Soto       | NYY  | TB   | NYY@DET  | 1.82 | 1.82  | OVER |
| 10   | Mookie Betts    | LAD  | TB   | LAD@PHI  | 1.82 | 1.82  | OVER |

All SELF_EDGE — no market lines available (SerpAPI depleted)
Stat bias: UNDER picks dominate (74.4% historical hit rate on UNDER vs 41.1% OVER)
NOTE: Total Bases picks hit at 70.6% historically — our best stat category
All today's top picks are OVER direction — proceed with caution vs historical UNDER bias

---

# KEY FOLDERS
```
/home/workspace/
├── Projects/
│   ├── daily_picks.py          ← MAIN PICK GENERATOR
│   ├── generate_projections.py ← MLB proj from ESPN + pybaseball
│   ├── gen_wnba_today.py       ← WNBA proj from ESPN
│   ├── backfill_projections.py ← Historical boxscore proj
│   └── tc_math.py              ← CORE MATH ENGINE
├── data/picks/                 ← ALL PICK CSVs
├── Daily_Log/                  ← Projections, backtests, graded picks
├── Backtest_Reports/           ← Backtest result reports
└── Reports/                    ← Generated analysis reports
```
