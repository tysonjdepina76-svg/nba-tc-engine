# SPORTS TC — TEMPLATE CORRECTIONS v2.0

## Formula Fix Applied

### OLD (buggy):
```
TC = pts × 0.85 × 0.55   ← applied 0.55 to Q players BEFORE × 0.85
TC = pts × 0.85 × 0      ← double-penalized OUT players
```

### CORRECTED:
```
TC = pts × 0.85 × status_mult
status_mult: ACTIVE=1.0 | Q=0.65 | OUT=0.0
```

**Key fixes:**
1. Apply conservative factor (0.85) first
2. Then apply status multiplier once
3. Q (Questionable) multiplier: 0.55 → 0.65 (WNBA starters play through Q commonly)
4. OUT multiplier: stays 0

---

## Injury Adjustment Rules

| Status | Meaning | TC Treatment |
|--------|---------|-------------|
| ACTIVE | Full minutes | stat × 0.85 × 1.0 |
| Q | Questionable (game-time decision) | stat × 0.85 × 0.65 |
| OUT | Ruled out | stat × 0.85 × 0 = 0 |

---

## Files Updated

- `sports_tc/sports_tc.py` — TC engine core
- `sports_tc/dashboard/app.py` — Streamlit dashboard
- `sports_tc/nba/rosters.py` — NBA rosters + injury data
- `sports_tc/wnba/rosters.py` — WNBA rosters + injury data

---

## Pushed to GitHub

https://github.com/tyson6/sports-tc