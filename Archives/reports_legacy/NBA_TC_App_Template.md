# NBA TC Prop Engine — APP TEMPLATE
**v2.0 | May 3, 2026 | Round 2 Ready**

---

## QUICK START

```bash
# Run the diagnostic
python3 /home/workspace/nba_tc_prop_engine.py

# Run the workflow (generates all Round 2 files)
bash /home/workspace/nba_tc_workflow.sh
```

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                   NBA TC PROP ENGINE                     │
│                      v2.0                               │
├─────────────────────────────────────────────────────────┤
│  DATA LAYER                                              │
│  ├── PlayerStats (pts, reb, ast, 3pt, min, tier)         │
│  ├── TeamRoster (players[], pace, DEF_RTG)               │
│  └── GameContext (series_game, elim, home/away)          │
├─────────────────────────────────────────────────────────┤
│  TC ENGINE                                               │
│  ├── tc_pts(player, min, elim, home) → float             │
│  ├── tc_reb(player, min, elim) → float                   │
│  ├── tc_ast(player, min, elim) → float                   │
│  ├── tc_3pt(player, min, elim) → float                   │
│  └── expected_total(ctx, a_mins, b_mins) → float         │
├─────────────────────────────────────────────────────────┤
│  PICK CARD                                               │
│  ├── add_total(line, side)                              │
│  ├── add_spread(team, line)                             │
│  ├── add_player_prop(player, type, line, min, odds)      │
│  └── best_parlay(min_legs, max_legs, min_conf)          │
├─────────────────────────────────────────────────────────┤
│  DIAGNOSTIC                                              │
│  ├── Error #1-10 analysis                                │
│  ├── Improvement estimate                                │
│  └── Confidence scoring                                  │
└─────────────────────────────────────────────────────────┘
```

---

## KEY FILES

| File | Purpose |
|------|---------|
| `file 'nba_tc_prop_engine.py'` | Core engine — run `python3 nba_tc_prop_engine.py` |
| `file 'NBA_PROP_DIAGNOSTIC.md'` | Root cause analysis of 39.1% → 57%+ plan |
| `file 'NBA_WORKFLOW.md'` | Step-by-step usage guide |
| `file 'nba_tc_workflow.sh'` | Bash runner — generates all game files |
| `file 'OKC_vs_PHX_TC_Complete.md'` | Full TC breakdown with all 4 stat categories |
| `file 'NBA_Round2_TC_Master.md'` | Round 2 overview and pick card summary |

---

## TC FORMULA CARD

```
╔══════════════════════════════════════════════════════════╗
║              TC PROP ENGINE v2.0 FORMULAS               ║
╠══════════════════════════════════════════════════════════╣
║ POINTS                                                  ║
║ TC_PTS = pts × TIER_MULT × (min/36) + star_boost        ║
║          + def_adj + home_adj                            ║
║                                                          ║
║ REBOUNDS                                                ║
║ TC_REB = rebs × (min/36) × 1.05 + pace_adj × 0.5        ║
║                                                          ║
║ ASSISTS                                                 ║
║ TC_AST = asts × (min/36) × 1.02 + (pace-1.00) × 6.0     ║
║                                                          ║
║ 3PT MADE                                                ║
║ TC_3PT = 3pt × (min/36) × 3pt_rate_factor × 0.95        ║
║                                                          ║
║ TIER MULTIPLIERS: Star=0.93 | Starter=0.90              ║
║                    Rotation=0.85 | Bench=0.80           ║
║                                                          ║
║ STAR BOOST: +3.4 pts (from backtest)                   ║
║ PLAYOFF MULT: 1.18 (round 1 avg was +14.7 pts over)     ║
║ PACE: Fast=×1.08 | Neutral=×1.00 | Slow=×0.94          ║
║ ELIMINATION (G6-G7): ×0.92                              ║
║ HOME: +3 pts | ROAD: +4 pts                             ║
╚══════════════════════════════════════════════════════════╝
```

---

## CONFIDENCE THRESHOLDS

| Confidence | Rating | Action |
|------------|--------|--------|
| ≥ 88% | HIGH | ✅ Play |
| 75-87% | MEDIUM | ⚠️ Borderline — evaluate |
| < 75% | LOW | ❌ Skip |

---

## PICK CARD EXAMPLE

```
PICK CARD — OKC Thunder vs LA Lakers | G1 | Pace: 1.08
============================================================
✅ [PROP] SGA OVER 29.5 PTS | Edge: +1.3 | Conf: 84% | -110
✅ [TOTAL] OVER 215.5 | Edge: +21.5 | Conf: 92% | -110
✅ [SPREAD] OKC -13.5 | Edge: +6.5 | Conf: 90% | -110
⚠️ [PROP] LeBron OVER 23.5 | Edge: -0.3 | Conf: 68% | -115
✅ [PROP] Holmgren OVER 22.5 | Edge: +1.5 | Conf: 83% | -110

BEST PARLAY (3 legs, 84% min):
  → SGA OVER 29.5 + OVER 215.5 + OKC -13.5
  → +650 odds | Stake $10 → Payout $75.00
```

---

## COMPETITIVE ADVANTAGES (vs DraftKings/FanDuel)

| Feature | TC Engine v2 | Market |
|---------|-------------|--------|
| Tier-weighted projections | ✅ Stars +3.4 boost | ❌ Generic |
| Pace-adjusted totals | ✅ ±8% fast/slow | ✅ |
| Elimination game filter | ✅ G6-G7 ×0.92 | Partial |
| Defensive rating adjust | ✅ | ✅ |
| Home/road split | ✅ | ✅ |
| 4-category props (P/R/A/3PT) | ✅ | ✅ |
| Diagnostic self-correction | ✅ | ❌ |
| Open-source + customizable | ✅ | ❌ |

---

## DIAGNOSTIC SUMMARY (Round 1)

| Error | Fix | Impact |
|-------|-----|--------|
| E1: Wrong multiplier | 0.90 playoffs / 0.93 stars | Critical |
| E2: Missing REB/AST/3PT | Added tc_reb/tc_ast/tc_3pt | Critical |
| E3: No tier weighting | Tier 1-4 multipliers | High |
| E4: No pace adjust | ±8% for fast/slow series | High |
| E5: No def adjust | DEF_RTG factor | Medium |
| E6: No elim filter | G6-G7 ×0.92 | High |
| E7: Mid-series injuries | Redistribute 30% OUT pts | Medium |
| E8: Sweep overcorrect | -8 if winning by 15+ | Medium |
| E9: No home/road | +3 home, +4 road | Medium |
| E10: Line format | X.5 only | Low |

**Est. improvement: 39.1% → 57-62% hit rate**