# TC Math — 6 Mutually Contradictory Formulas Report
**Date**: 2026-07-27  
**Analyzed**: All `over_under_signal` / `sport_over_under_signal` / `sport_prop_signal` across the workspace

---

## Discrepancy 1: Signed vs Absolute Edge

| Function | File | Edge Sign |
|----------|------|-----------|
| `over_under_signal()` | `tc_math.py:48` | **ABSOLUTE** (`abs(diff) / line`) |
| `sport_over_under_signal()` | `tc_math.py:82` | **ABSOLUTE** (`abs(diff) / line`) |
| `sport_prop_signal()` | `tc_math.py:414` | **SIGNED** (`(proj - line) / line`) |
| `sport_prop_signal()` | `sport_prop_signal.py:10` | **SIGNED** (`(proj - line) / line * 100`) |
| `calculate_edge()` | `rules_engine.py:116` | **SIGNED** (`(proj - line) / line`) |
| `sport_over_under_signal()` | `rules_engine.py:122` | **SIGNED** (via calculate_edge) |

**Impact**: Core functions return unsigned magnitude; ported versions return signed. Downstream code consuming both gets inconsistent results.

---

## Discrepancy 2: Edge Return Format (3 Different Units)

| Function | Returns |
|----------|---------|
| `tc_math.over_under_signal` | Raw fraction: `0.05` = 5% |
| `tc_math.sport_over_under_signal` | Raw fraction: `0.05` = 5% |
| `tc_math.sport_prop_signal` | Raw fraction: `0.05` = 5% (signed) |
| `sport_prop_signal.py` | **Percent**: `edge_pct = 5.0` (signed, `* 100` internally, returned as string 'OVER'/'UNDER') |
| `rules_engine.calculate_edge` | Raw fraction: `0.05` = 5% (signed) |
| `rules_engine.sport_over_under_signal` | **Percent**: `round(edge * 100, 2)` = `5.0` |

**Impact**: `db` column stores raw fraction but rules_engine output would store `5.0` instead of `0.05`. 100x discrepancy when mixed.

---

## Discrepancy 3: Edge Capping (Max Edge)

| Function | Cap |
|----------|-----|
| `tc_math.over_under_signal` | Optional `max_edge` param |
| `tc_math.sport_over_under_signal` | `config.max_edge` (per sport: 5-30) |
| `tc_math.sport_prop_signal` | **NONE** — no max_edge, edge can diverge infinitely |
| `sport_prop_signal.py` | **NONE** — no cap |
| `rules_engine` | **NONE** — no cap |

**Impact**: Unbounded edges leak into picks when projection deviates wildly from market line.

---

## Discrepancy 4: min_edge Threshold Comparison (3 Different Methods)

| Function | Comparison |
|----------|-----------|
| `tc_math.over_under_signal` | `edge < min_abs_edge` → FLAT |
| `tc_math.sport_over_under_signal` | `edge < min_edge_val` (sport config) → FLAT |
| `tc_math.sport_prop_signal` | `abs(edge) >= min_edge` → fires; `abs(edge) >= min_edge * 2` → High confidence |
| `sport_prop_signal.py` | `edge_pct >= min_edge * 100` or `edge_pct <= -(min_edge * 100)` — converts threshold to percent |
| `rules_engine.sport_over_under_signal` | `abs(edge) >= min_edge` → fires; `abs(edge) > min_edge * 2` + variance < 0.10 → High |

**Impact**: `sport_prop_signal.py` multiplies threshold by 100x (5% vs 500%), effectively dead — everything is NO_PICK.

---

## Discrepancy 5: Direction Determination Semantics

| Function | OVER condition |
|----------|---------------|
| `tc_math.over_under_signal` | `diff > 0` (strict) |
| `tc_math.sport_over_under_signal` | `diff > 0` (strict) |
| `tc_math.sport_prop_signal` | `edge > 0` → OVER, `edge < 0` → UNDER |
| `sport_prop_signal.py` | `edge_pct >= min_edge * 100` → OVER; also has back-to-back penalty (8%) |
| `rules_engine.sport_over_under_signal` | `edge > 0` → OVER |

**Edge case**: `tc_math` core treats `diff == 0` as FLAT; `sport_prop_signal` functions treat `edge == 0` as NO_PICK (not FLAT). Different sentinel values for "no edge". `sport_prop_signal.py` adds back-to-back penalty and WNBA 40% shrinkage that others don't.

---

## Discrepancy 6: Parameter Signatures (Incompatible)

| Function | Params |
|----------|--------|
| `tc_math.sport_over_under_signal` | `(projection, market_line, sport, min_edge)` — pure math, no player context |
| `tc_math.sport_prop_signal` | `(sport, player, prop, model_proj, book_line, is_preseason, stat_values)` — applies adjustments |
| `sport_prop_signal.py` | `(sport, player, prop, model_proj, book_line, is_preseason, stat_values)` — stat_values is a **list**, not dict |
| `rules_engine.sport_over_under_signal` | `(sport, player, prop, model_proj, book_line, is_preseason, stat_values)` — stat_values is a **Dict** |

**Impact**: Cannot drop-in replace one for another. `stat_values` type mismatch (list vs dict) between `sport_prop_signal.py` and `rules_engine.py`.

---

## Resolution: Canonical Path Forward

Only TWO functions should exist. All callers route through them:

1. **`tc_math.sport_over_under_signal(projection, market_line, sport)`** — Pure math: direction + absolute edge, capped by sport config.
2. **`tc_math.sport_prop_signal(sport, player, prop, model_proj, book_line, is_preseason, stat_values)`** — Full pipeline: adjustments + pure math, returns dict with pick/edge/confidence.

**Deleted duplicates**: `sport_prop_signal.py`, `rules_engine.py` (already purged — these were dead code with zero callers).

---

## Files Analyzed (Pre-Purge)

| File | Size | Status |
|------|------|--------|
| `Projects/tc_math.py` | ~16KB | ✅ CANONICAL — sole source of truth |
| `Projects/sport_prop_signal.py` | ~1.5KB | ❌ PURGED — zero callers, dead code |
| `Projects/rules_engine.py` | ~4KB | ❌ PURGED — zero callers, dead code |
| `Projects/sports_grading_engine.py` | ~15KB | ✅ KEPT — grading, no math conflict |
| `Trash/tc_math_ancient_stub.py` | unknown | Already in Trash |
| `Trash/tc_math_drive_backup.py` | unknown | Already in Trash |
