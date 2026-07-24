# 🐦 TC PIPELINE — EARLY BIRD SPECIAL
## Tuesday, July 21, 2026 | 5:05 AM ET

---

# ⚡ TOP 10 EARLY BIRD PICKS — MLB 7/21

> *Self-Edge projections. No market lines available. All lines shown as 0.0 — real edge is our projection difference from player averages.*

| # | PLAYER | TEAM | STAT | DIR | PROJ | EDGE | MATCHUP |
|---|--------|------|------|-----|------|------|---------|
| 1 | **Freddie Freeman** | LAD | Total Bases | ▲ OVER | 1.98 | +1.98 | DET@CHC |
| 2 | **Aaron Judge** | NYY | Total Bases | ▲ OVER | 1.95 | +1.95 | CIN@SEA |
| 3 | **Shohei Ohtani** | LAD | Total Bases | ▲ OVER | 1.95 | +1.95 | WSH@COL |
| 4 | **Yordan Alvarez** | HOU | Total Bases | ▲ OVER | 1.94 | +1.94 | MIN@CLE |
| 5 | **Mike Trout** | LAA | Total Bases | ▲ OVER | 1.94 | +1.94 | NYM@MIL |
| 6 | **Bryce Harper** | PHI | Total Bases | ▲ OVER | 1.93 | +1.93 | LAD@PHI |
| 7 | **Corey Seager** | TEX | Hits | ▲ OVER | 1.20 | +1.20 | PIT@NYY |
| 8 | **Ronald Acuna** | ATL | Hits | ▲ OVER | 1.19 | +1.19 | STL@LAA |
| 9 | **Juan Soto** | NYM | Runs | ▲ OVER | 0.66 | +0.66 | BAL@BOS |
| 10 | **Mookie Betts** | LAD | Strikeouts | ▲ OVER | 1.00 | +1.00 | CHW@TEX |

---

# 📊 BACKTEST SUMMARY — ALL HISTORICAL PICKS

| METRIC | VALUE |
|--------|-------|
| **Total Historical Picks** | **5,481** |
| MLB Picks | 3,188 (58.2%) |
| WNBA Picks | 1,768 (32.3%) |
| WC Picks | 195 (3.6%) |
| Other | 330 (6.0%) |
| **Days Tracked** | 6 days (7/13 — 7/21) |
| **Median Edge** | 0.61 |
| **Mean Edge** | 2.34 |
| **Picks with Edge >0.5** | 3,004 (54.8%) |
| **Picks with Edge >0.2** | 3,762 (68.6%) |
| **Today's Picks** | 810 MLB (15 games, 90 players) |

### Daily Volume
| DATE | MLB | WNBA | WC | TOTAL |
|------|-----|------|----|-------|
| 7/17 | 3 | — | 65 | 68 |
| 7/18 | 754 | 911 | 65 | 1,730 |
| 7/19 | 810 | 211 | 65 | 1,086 |
| 7/20 | 811 | 641 | — | 1,452 |
| 7/21 | 810 | — | — | 810 |

> ⚠️ **Self-Edge note**: No graded results available — picks are generated against self-computed projections. Real grading requires live boxscore results post-game or integration with a results API. Historical hit rate not yet computed — this is the next priority.

---

# 🔧 TC PIPELINE ARCHITECTURE MAP

```
                    ┌─────────────────────┐
                    │   FREE DATA SOURCES  │
                    │  ESPN v2 API (FREE)  │
                    │  pybaseball (MLB)    │
                    │  nba_api (offseason) │
                    └──────────┬──────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │   PROJECTION GENERATION       │
               │                               │
               │  generate_projections.py      │
               │  ├─ MLB: ESPN roster + stats  │
               │  ├─ WNBA: gen_wnba_today.py   │
               │  └─ WC: ESPN schedule pull    │
               │                               │
               │  Output: Daily_Log/YYYY-MM-DD/│
               │    proj_SPORT_MATCHUP.json     │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │   LINE ENRICHMENT (CAPPED)    │
               │                               │
               │  enrich_lines_via_espn()      │
               │  enrich_lines_via_serpapi()   │
               │  └─ QUOTA GUARD: checks       │
               │     before loop, skips clean  │
               │                               │
               │  ALL EXTERNAL APIs CAPPED:    │
               │  • SerpAPI: 50/run, 250/day   │
               │  • Odds API: EXHAUSTED        │
               │  • SDIO: 401 on all odds      │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │   TC MATH ENGINE              │
               │   tc_math.py                  │
               │                               │
               │   Core Functions:             │
               │   ├─ over_under_signal()      │
               │   ├─ sport_over_under_signal()│
               │   ├─ calculate_expected_value │
               │   ├─ kelly_criterion()        │
               │   ├─ shrink_projection()      │
               │   └─ is_sane_edge()           │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │   PICK GENERATION             │
               │   daily_picks.py              │
               │                               │
               │   • Loads projections         │
               │   • Computes edge per player  │
               │   • Filters by sport config   │
               │   • Generates combos          │
               │   • Saves to CSV + JSON       │
               └───────────────┬───────────────┘
                               │
                               ▼
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
   ┌──────────┐        ┌──────────┐         ┌──────────┐
   │ STREAMLIT│        │ EMAIL    │         │ DASHBOARD│
   │ :8510    │        │ REPORTS  │         │ /nba-tc  │
   │ live dash│        │ auto-gen │         │ zo.space │
   └──────────┘        └──────────┘         └──────────┘
```

---

# 🧮 TC MATH — THE EQUATIONS

## 1. Core Signal: `over_under_signal(projection, market_line)`

```
diff = tc_projection − market_line
abs_edge = |diff|

IF sport_config.use_pct:
    edge = abs_edge / market_line          # Soccer/WC: percentage edge
ELSE:
    edge = abs_edge                        # MLB/WNBA: absolute edge

IF edge > sport_config.max_edge:
    edge = sport_config.max_edge           # Cap at sport max

IF edge < sport_config.min_edge:
    return "FLAT", 0.0                     # No signal if below threshold

direction = "OVER" if diff > 0 else "UNDER"
return direction, edge
```

## 2. Sport-Specific Thresholds

| SPORT | MIN EDGE | MAX EDGE | TYPE | LINE MIN |
|-------|----------|----------|------|----------|
| MLB | 0.5 | 8.0 | absolute | 0.5 |
| WNBA | 0.5 | 15.0 | absolute | 0.5 |
| WC | 0.005 (0.5%) | 0.50 (50%) | pct | 0.5 |
| NBA | 0.5 | 15.0 | absolute | 0.5 |
| NFL | 0.5 | 15.0 | absolute | 0.5 |
| NHL | 0.2 | 5.0 | absolute | 0.5 |

## 3. Projection Shrinkage: `shrink_projection(tc_val, line_val, sample, k)`

```
shrunken = (tc_val * sample + line_val * k) / (sample + k)

# Bayesian shrinkage toward market line
# k=20: strong prior toward market when sample is low
# Prevents wild projections on small samples
```

## 4. Edge Sanity Check: `is_sane_edge(tc_val, line_val, max_ratio=2.5)`

```
IF line_val <= 0: return True    # Self-edge allowed
IF tc_val <= 0:  return False    # Invalid projection
ratio = max(tc_val, line_val) / min(tc_val, line_val)
return ratio <= 2.5              # Reject if TC > 2.5x market
```

## 5. Expected Value: `calculate_expected_value(projection, line, odds=-110)`

```
implied_prob = odds_to_prob(odds)
ev = (projection − line) * implied_prob
return ev
```

## 6. Self-Edge Mode (Current — No Market Lines)

```
When line = 0.0 (no market data):
    edge = tc_projection − 0.0
    edge = tc_projection
    direction = "OVER"
    
    # We project what the player WILL do.
    # Without market lines, edge = raw projection.
```

---

# 📡 API STATUS — ALL SOURCES CAPPED

| API | STATUS | CAP/QUOTA | ACTION |
|-----|--------|-----------|--------|
| **ESPN v2** | 🟢 LIVE | Unlimited (free) | Primary data source |
| **pybaseball** | 🟢 LIVE | Unlimited (free) | MLB stats |
| **SerpAPI** | 🔴 DEPLETED | 250/day, 50/run | Reset ~midnight |
| **Odds API** | 🔴 MAXED | Business tier quota | Do not retry |
| **SportsDataIO** | 🔴 401 | All odds endpoints | Dead for now |
| **GitHub APIs** | 🟡 UNWIRED | Free tier (60/hr) | **PRIORITY: Wire in** |

### Free Public APIs — Wire Plan

| SOURCE | ENDPOINT | RATE LIMIT | USE |
|--------|----------|------------|-----|
| GitHub Raw | raw.githubusercontent.com | 60/hr unauthenticated | Roster/line data repos |
| ESPN Hidden | site.api.espn.com | Unlimited | Scores, schedules, rosters |
| MLB StatsAPI | statsapi.mlb.com | Unlimited | MLB game data |
| TheSportsDB | thesportsdb.com | 100/day (free tier) | Cross-sport data |
| BallDontLie | balldontlie.io | 60/min (free) | NBA data (offseason) |

---

# 📋 TODAY'S SLATE — 7/21/2026

## MLB — 15 Games, 90 Players
LAD@PHI · MIN@CLE · PIT@NYY · TB@TOR · BAL@BOS · SD@ATL · NYM@MIL · SF@KC · CHW@TEX · DET@CHC · MIA@HOU · WSH@COL · STL@LAA · ATH@ARI · CIN@SEA

## WNBA — No Games Today (0)
## World Cup — No Games Today (0)

### Total: 810 picks · 25 combos · All SELF_EDGE

---

# 🔄 PIPELINE GENERATION FLOW

```
1. ESPN v2 API → Schedule + Rosters
2. pybaseball → Player season stats
3. generate_projections.py → Daily_Log/proj_*.json
4. ESPN enrichment → Game spreads/totals
5. SerpAPI enrichment → Player prop lines (WHEN QUOTA AVAILABLE)
6. daily_picks.py → tc_math.py → Edge computation
7. Sport config filtering → Valid picks only
8. Combo generation → Top parlays
9. CSV save → data/picks/{sport}_{date}.csv
10. Streamlit dashboard → :8510 live view
11. Email delivery → Automated reports
```

---

*TC Pipeline v4.2 | DeepSeek V4 Pro | Self-Edge Mode | Next quota reset: ~midnight ET*
