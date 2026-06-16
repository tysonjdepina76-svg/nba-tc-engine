# NBA TC Prop Engine — WORKFLOW DOCUMENTATION
**Version 2.0 | May 3, 2026 | Backtest: 46 games → Target: 57-62% hit rate**

---

## WHAT THIS SYSTEM DOES

Generates sports-betting-grade NBA player prop projections (points, rebounds, assists, 3PT made) for any game, using the Triple Conservative (TC) mathematical framework — corrected with 10 critical diagnostic fixes from round 1 backtest data.

---

## PIPELINE OVERVIEW

```
DATA INPUTS          PROCESSING              OUTPUTS
───────────          ──────────              ──────
Player stats  ────→  TC Prop Engine  ────→  Pick Card (Markdown)
Season averages      10-error diagnosis      Team Totals
Round 1 data         Tier weighting         Player Props (P/R/A/3PT)
Injury report        Pace/def adjustments   Parlay Builder
                     Confidence scoring     Diagnostic Report
```

---

## STEP-BY-STEP WORKFLOW

### STEP 1 — REGISTER TEAMS & PLAYERS

```python
from nba_tc_prop_engine import NBATCPropApp, PlayerStats, TeamRoster

app = NBATCPropApp()

# Register OKC Thunder
okc = TeamRoster(name="OKC Thunder", avg_pace=101.2, avg_DEF_RTG=106.4)
okc.players = [
    PlayerStats("Shai Gilgeous-Alexander","PG",30.3,5.8,7.0,1.8,36,1,injury="ACTIVE"),
    PlayerStats("Chet Holmgren","C",24.0,7.8,2.1,2.4,32,1,injury="ACTIVE"),
    PlayerStats("Ajay Mitchell","SG",22.5,4.2,4.8,2.1,34,1,injury="ACTIVE"),
    PlayerStats("Isaiah Hartenstein","C",17.8,9.4,3.9,0.8,28,2,injury="ACTIVE"),
    PlayerStats("Luguentz Dort","SF",8.4,3.2,1.8,1.6,26,2,injury="ACTIVE"),
    PlayerStats("Alex Caruso","PG",14.2,4.1,5.2,2.3,24,2,injury="ACTIVE"),
    PlayerStats("Cason Wallace","SG",10.3,2.8,2.4,1.9,20,3,injury="ACTIVE"),
    PlayerStats("Aaron Wiggins","SF",9.6,3.4,1.6,1.4,16,3,injury="ACTIVE"),
]
app.register_team(okc)

# Register Los Angeles Lakers
lal = TeamRoster(name="LA Lakers", avg_pace=99.8, avg_DEF_RTG=110.2)
lal.players = [
    PlayerStats("LeBron James","SF",23.2,7.2,8.3,1.8,38,1,injury="ACTIVE"),
    PlayerStats("Austin Reaves","SG",15.0,4.2,5.1,2.0,34,2,injury="ACTIVE"),
    PlayerStats("Rui Hachimura","PF",12.6,4.8,1.2,1.2,30,2,injury="ACTIVE"),
    PlayerStats("Dorian Finney-Smith","SF",8.4,3.6,1.8,1.4,28,3,injury="ACTIVE"),
    PlayerStats("Deandre Ayton","C",16.2,11.2,1.8,0.4,32,2,injury="ACTIVE"),
    PlayerStats("Marcus Smart","PG",9.2,3.4,4.2,1.2,24,3,injury="ACTIVE"),
]
app.register_team(lal)
```

### STEP 2 — BUILD GAME CONTEXT

```python
ctx = app.build_game("OKC Thunder", "LA Lakers",
                     series_game=1,
                     a_is_home=True)  # OKC home
```

### STEP 3 — SET EXPECTED MINUTES (per player)

```python
# OKC minutes (from round 1 actuals)
okc_mins = {
    "Shai Gilgeous-Alexander": 38,
    "Chet Holmgren": 34,
    "Ajay Mitchell": 35,
    "Isaiah Hartenstein": 29,
    "Luguentz Dort": 27,
    "Alex Caruso": 26,
    "Cason Wallace": 22,
    "Aaron Wiggins": 18,
}

# LAL minutes (from round 1 actuals, Luka OUT)
lal_mins = {
    "LeBron James": 38,
    "Austin Reaves": 34,
    "Rui Hachimura": 30,
    "Dorian Finney-Smith": 28,
    "Deandre Ayton": 32,
    "Marcus Smart": 24,
}
```

### STEP 4 — RUN FULL REPORT

```python
app.run_full_report(ctx, okc_mins, lal_mins)
```

**Output:**
- Team total TC (raw + adjusted)
- Starting 5 TC per team
- Bench TC per team
- Top 8 player projections (PTS, REB, AST, 3PT) per team
- Pick card with legs, edges, confidence ratings
- Best parlay suggestion with payout

### STEP 5 — GENERATE PICK CARD FILE

```python
card = PickCard(ctx, okc_mins, lal_mins)
card.add_total(232.5, "OVER")
card.add_spread("OKC Thunder", -13.5)

# Add player props
for p in okc.top_8_by_min()[:4]:
    card.add_player_prop(p, "PTS", round(p.pts_avg * 0.90), okc_mins[p.name])
    card.add_player_prop(p, "REB", round(p.rebs_avg * 0.90), okc_mins[p.name])
    card.add_player_prop(p, "AST", round(p.asts_avg * 0.90), okc_mins[p.name])

for p in lal.top_8_by_min()[:4]:
    card.add_player_prop(p, "PTS", round(p.pts_avg * 0.90), lal_mins[p.name])
    card.add_player_prop(p, "REB", round(p.rebs_avg * 0.90), lal_mins[p.name])
    card.add_player_prop(p, "AST", round(p.asts_avg * 0.90), lal_mins[p.name])

card.print_card()
```

---

## FILE STRUCTURE

```
/home/workspace/
├── nba_tc_prop_engine.py          ← Core engine (all logic)
├── NBA_PROP_DIAGNOSTIC.md         ← Root cause analysis (10 errors)
├── NBA_WORKFLOW.md                ← This file (how to use)
├── NBA_Round2_TC_Master.md        ← Round 2 overview + picks
├── nba_tc_workflow.sh             ← Shell runner (bash)
└── game_files/
    ├── LAL_vs_OKC_TC_Game1.md     ← Lakers @ Thunder G1
    ├── SAS_vs_MIN_TC_Game1.md      ← Spurs @ Wolves G1
    ├── NYK_vs_PHI_TC_Game1.md      ← Knicks @ 76ers G1
    └── OKC_PHX_Historic.md        ← OKC vs PHX backtest data
```

---

## KEY FORMULAS (CORRECTED)

### Player TC Points
```
TC_PTS = pts_avg × TIER_MULT × (game_min / 36) + star_boost + def_adj + home_adj

TIER_MULT:  Star=0.93 | Starter=0.90 | Rotation=0.85 | Bench=0.80
star_boost: +3.4 pts (Tier 1 players only — from backtest error analysis)
def_adj:    (opp_DEF_RTG - 112) × 0.04
home_adj:   +3.0 (home) | +4.0 (road)
```

### Player TC Rebounds
```
TC_REB = rebs_avg × (game_min / 36) × 1.05 + pace_adj × 0.5
```

### Player TC Assists
```
TC_AST = asts_avg × (game_min / 36) × 1.02 + (pace_factor - 1.00) × 6.0
```

### Player TC 3PT Made
```
TC_3PT = 3pt_avg × (game_min / 36) × (3pt_rate_factor) × 0.95
```

### Team Total
```
BASE_TC = Σ TC_PTS_i  (all active players)
PACE_ADJ = BASE_TC × (pace_factor - 1.00)
EXPECTED_TOTAL = (BASE_TC + PACE_ADJ) × 1.18
```

### Edge
```
EDGE = EXPECTED_TOTAL - LINE
OVER if EDGE ≥ +8 | UNDER if EDGE ≤ -5 | SKIP otherwise
```

### Confidence
```
CONFIDENCE = min(0.95, 0.50 + |EDGE| / min_edge_threshold)
HIGH: ≥ 88% | MEDIUM: 75-87% | LOW: < 75% → SKIP
```

---

## SPREADSHEET/EV CALCULATION

```python
def ev(stake: float, odds: float, confidence: float) -> float:
    """Expected value of a bet."""
    prob_win = confidence
    prob_lose = 1 - prob_win
    if odds > 0:
        payout = stake * (1 + odds / 100)
    else:
        payout = stake * (1 + 100 / abs(odds))
    return prob_win * payout - prob_lose * stake

# Only bet if EV > 0
# Only bet if confidence ≥ 88% AND edge ≥ 3 pts (props) / edge ≥ 5 pts (totals)
```

---

## LIVE UPDATE PROTOCOL

After each game:

1. **Pull actual stats** from box score
2. **Compare vs TC projections** for each player
3. **Log error** in backtest tracker
4. **Update minutes** if rotation changed (injury, bench emergence)
5. **Re-run TC engine** for next game with corrected inputs

```python
# Post-game update example
actual = {
    "SGA": {"pts": 33, "rebs": 6, "asts": 7, "3pt": 2, "min": 38},
    "Holmgren": {"pts": 24, "rebs": 9, "asts": 2, "3pt": 1, "min": 34},
}
# Log error: SGA TC 30.3 vs actual 33 → error = -2.7 (TC underestimated)
# Use new error to adjust next game projection
```

---

## COMPARISON: TC Engine vs Market Leaders

| Feature | TC Engine v2 | DraftKings | FanDuel | VSiN |
|---------|-------------|------------|---------|------|
| Points props | ✅ | ✅ | ✅ | ✅ |
| Rebound props | ✅ (new) | ✅ | ✅ | ✅ |
| Assist props | ✅ (new) | ✅ | ✅ | ✅ |
| 3PT props | ✅ (new) | ✅ | ✅ | ✅ |
| Combo props | 🔜 v3 | ✅ | ✅ | ✅ |
| Pace adjustment | ✅ (new) | ✅ | ✅ | ✅ |
| Def rating adjust | ✅ (new) | ✅ | ✅ | ✅ |
| Tier weighting | ✅ (new) | ✅ | ✅ | ✅ |
| Elimination filter | ✅ (new) | partial | partial | ✅ |
| Same-game parlays | 🔜 v3 | ✅ | ✅ | ✅ |
| Live odds | 🔜 v3 | ✅ | ✅ | ✅ |

---

## ROUND 2 FILES PRODUCED

| File | What's Inside |
|------|--------------|
| `file 'NBA_Round2_TC_Master.md'` | Full Round 2 schedule + overview |
| `file 'NBA_PROP_DIAGNOSTIC.md'` | 10-error diagnosis + fixes |
| `file 'nba_tc_prop_engine.py'` | Runable Python engine |
| `file 'NBA_WORKFLOW.md'` | This document |
| `file 'LAL_vs_OKC_TC_Game1.md'` | Lakers @ Thunder G1 full analysis |
| `file 'SAS_vs_MIN_TC_Game1.md'` | Spurs @ Wolves G1 full analysis |
| `file 'NYK_vs_PHI_TC_Game1.md'` | Knicks @ 76ers G1 full analysis |

---

## NEXT PHASE (v3.0)

1. **Combo props** (P+R+A, P+R, R+A) — match DraftKings SGP
2. **Same-game parlay builder** — auto-generate SGP combinations
3. **Live odds integration** — pull real lines from API
4. **Bankroll tracker** — log every bet, calculate ROI
5. **Round 2 backtest** — validate fixes against new data
