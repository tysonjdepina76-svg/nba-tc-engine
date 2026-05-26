# TC Template Comparative Analysis: NBA vs WNBA

**Generated:** May 22, 2026
**NBA file:** `Triple_Conservative_NBA_Template_v6.py`
**WNBA file:** `wnba_tc_live_engine.py`
**WNBA Ledger Input:** DALLAS WINGS @ ATLANTA DREAM projection ledger

---

## 1. TC Formula — Per-Category Math

| Dimension | NBA Template v6 | WNBA Live Engine |
|---|---|---|
| PTS | PTS × 0.85 | PTS × 0.85 |
| REB | not used | REB × 0.80 |
| AST | not used | AST × 0.75 |
| 3PM | not used | 3PM × 0.70 |
| Q multiplier | applied to 0.85 → 0.55 | applied to ALL TC cats → 0.55 |
| OUT multiplier | 0 | 0 |
| Prop categories | single TC_PTS | TC_PTS, TC_REB, TC_AST, TC_3PM |

**Key finding:** NBA uses one TC factor (0.85) for points only. WNBA Live Engine applies
category-specific factors — a materially different formula that multiplies the Conservative
haircut separately per stat line.

## 2. Team Totals — To Match or Not to Match

- **NBA Template:** TC Combined = Σ TC_PTS for all starters + bench TC. Combined TC total
  is compared directly against the O/U Vegas line. Edge is derived and used in picks.

- **WNBA Live Engine (explicit):** `TC match applies ONLY to player props, not team/game
  totals.` Team totals are printed for informational purposes only.

- **WNBA Ledger (your input):** Projects scores of 88.5 ATL / 85.5 DAL but does NOT
  compute a TC-team-total vs O/U comparison. The market line (172.5) is shown but
  no TC edge is calculated against it.

**Verdict:** WNBA Live Engine deliberately avoids TC team-total matching. Your ledger
input also does not do it. NBA Template does it. This is a fundamental architectural
difference — the WNBA workflow treats TC as a player-prop tool only.

## 3. Roster Data Source

| | NBA Template | WNBA Live Engine |
|---|---|---|
| Source type | Hardcoded GAMES dict | Live ESPN APIs |
| Starter data | PTS + status dicts | Player objects (full) |
| Bench data | Single float (total pts) | Full Player objects |
| Injury status | Emoji string (✅/⚠️/❌) | OUT / Q / ACTIVE from ESPN |
| Role assignment | Manual in GAMES dict | Auto-sorted by production_score() |
| athlete_id | not used | fetched from ESPN |
| Live roster fetch | No | Yes — scoreboard → roster → stats |

## 4. USG% and Minute Projections

Your WNBA ledger includes **USG%** and **minutes** per player. The NBA Template
has no USG or minute fields — it uses flat PTS averages only.

The WNBA Live Engine also has no USG field.

USG% × Minutes ÷ 40 ≈ points contribution — this is a more granular projection
method than the NBA template's simple avg PTS × 0.85 approach.

If you want to backtest the WNBA ledger format, the engine would need a USG-aware
projection layer that the NBA template does not have.

## 5. Parlay / Picks Infrastructure

| Feature | NBA Template | WNBA Live Engine |
|---|---|---|
| Leg/ParlayReport class | ✅ full dataclass | ❌ none |
| Odds (American → Decimal) | ✅ | ❌ |
| Payout calculator | ✅ | ❌ |
| Confidence threshold (88%) | ✅ | ❌ |
| Edge thresholds (leg=2, prop=3) | ✅ | ❌ |
| Picks tracker markdown | ✅ | ❌ |
| Backtest history (Round 1) | ✅ | ❌ |
| TC System Summary table | ✅ | ❌ |

**Key finding:** The NBA Template is a full end-to-end betting workflow (projections
→ TC math → leg selection → parlay assembly → payout → backtest record). The WNBA
Live Engine is a **roster projection tool only**. There is no parlay builder, no picks
tracker, no backtest layer in the WNBA engine.

## 6. Status Multiplier Implementation

NBA Template:
```python
STATUS_MULT = {'✅': 0.85, '⚠️': 0.55, '❌': 0.0}
tc_pts = pts * STATUS_MULT[status]
```

WNBA Live Engine:
```python
CONS = {'pts': 0.85, 'reb': 0.80, 'ast': 0.75, 'tpm': 0.70}
Q_FACTOR = 0.55
def _factor(self):
    if self.status == 'OUT': return 0.0
    if self.status == 'Q':    return 0.55
    return 1.0
def tc(self):
    f = self._factor()
    return {
        'PTS': round(self.pts * CONS['pts'] * f, 1),  # 0.85 × 0.55 = 0.4675 if Q
        'REB': round(self.reb * CONS['reb'] * f, 1),
        'AST': round(self.ast * CONS['ast'] * f, 1),
        '3PM': round(self.tpm * CONS['tpm'] * f, 1),
    }
```

**Math difference:** NBA applies Q as a flat 0.55 to TC_PTS. WNBA applies Q as
0.55 × per-category factor — so Questionable PTS becomes 0.85 × 0.55 = 0.4675
(≈ 47% of avg) vs NBA's 55% of TC points.

## 7. Backtest Layer

NBA Template includes:
- Round 1 OKC vs PHX game-by-game recap
- TC projected totals vs actual outcomes
- Picks tracker with win/loss record

WNBA Live Engine: Backtest files remain the 'validation layer, not the roster
source' — meaning there IS a backtest layer but it's treated as external reference,
not baked into the live output.

## 8. What the WNBA Ledger Adds (That Neither Engine Has)

Your projection ledger (DAL @ ATL) introduces:

| Feature | NBA Template | WNBA Live Eng | Your Ledger |
|---|---|---|---|
| Minute projections | ❌ | ❌ | ✅ |
| USG% per player | ❌ | ❌ | ✅ |
| Bench rotation tiers (CORE/ROTATION/GARBAGE) | ❌ | ❌ | ✅ |
| Team rebound totals | ❌ | ❌ | ✅ |
| Team assist totals | ❌ | ❌ | ✅ |
| Individual assist projections | ❌ | only TC_AST | ✅ |
| Individual rebound projections | ❌ | only TC_REB | ✅ |

## 9. Gap Summary — What Would Need to Be Built

To unify both workflows, the gaps are:

| # | Gap | Affects |
|---|---|---|
| G1 | WNBA needs parlay/picks infrastructure | WNBA Live Engine |
| G2 | WNBA has no O/U TC edge calculation | WNBA Live Engine |
| G3 | NBA template has no REB/AST/3PM TC factors | NBA Template |
| G4 | Neither has USG% × minute projection layer | Both |
| G5 | WNBA engine has no picks tracker or backtest log | WNBA Live Engine |
| G6 | Q multiplier: NBA 0.55 applied post-TC; WNBA 0.55 × per-category factor | Both |
| G7 | NBA bench is a single float; WNBA bench is full Player objects | Both |

## 10. Recommended Unification Path

1. **Extend NBA Template** to add REB × 0.80, AST × 0.75, 3PM × 0.70 per WNBA engine
2. **Port ParlayReport + Picks Tracker** into WNBA workflow
3. **Add USG/minute layer** as an optional input mode to both engines
4. **Standardize Q math** — use NBA's simpler approach (0.55 × TC factor) across both
5. **Add backtest log** to WNBA engine matching NBA template's Round 1 structure
6. **Keep team-total TC matching optional** — WNBA mode suppresses it by design