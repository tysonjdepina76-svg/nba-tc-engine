# TC Pipeline Progress Report — 2026-07-19

## Two Sessions: 12:55 PM + 4:00 PM ET

---

## Morning Session — Pipeline Gaps (6 fixes)

| # | Fix | Status |
|---|-----|--------|
| 1 | Import bug in daily_picks.py line 26 (merged text) | ✓ |
| 2 | Combo API date filter — /api/v1/combos now filters today only | ✓ |
| 3 | Zero-line projections — generate_projections.py no longer fakes book lines | ✓ |
| 4 | Signal propagation — SerpAPI picks carry signal=SERPAPI to DB | ✓ |
| 5 | WC combo defs — 6 types: G+A, S+PS, S+SOT, T+S, T+P, S+T | ✓ |
| 6 | Combos Tab wired to /nba-tc dashboard | ✓ |

---

## Afternoon Session — Dashboard & Visual Polish (4 fixes)

| # | Fix | Status |
|---|-----|--------|
| 1 | /dashboard combos: switched to /api/v1/combos across all 3 leagues, fixed c.label → c.combo_label | ✓ |
| 2 | WC box scores now render on /nba-tc Live Games tab (G, A, SH, SOT, PAS, TKL, YC columns) | ✓ |
| 3 | Combo banner cleanup — compact pills, no glow, muted border | ✓ |
| 4 | Workspace cleanup — removed empty dirs, .bak files, stale node_modules | ✓ |

---

## Current Pipeline State

- **486 picks**: WNBA 210, MLB 212, WC 64 (all SELF_EDGE)
- **618 combos**: WNBA 147, MLB 115, WC 96
- **6,238+ graded picks** in tc_pipeline.db
- **28 API endpoints** live on port 8000
- **Git**: 4 commits pushed today (36ef71f → afbdead)

---

## Active Blocker

⚠️ All external APIs are down — picks run on self-edge only:
- SDIO: 401 (invalid subscription)
- SerpAPI: exhausted
- Odds API: Business tier maxed
- SGO: WNBA not supported

Pipeline infrastructure is solid. Needs working API keys for real market lines.

---

## Dashboard Links

- /nba-tc: https://true.zo.space/nba-tc (4 tabs, combos wired)
- /dashboard: https://true.zo.space/dashboard (combos button working)
- Streamlit: https://tc-streamlit-dashboard-true.zocomputer.io
- API: https://tc-api-true.zocomputer.io

---

## Automation

Daily run at 1:30 PM ET — generate_projections.py → daily_picks.py (wnba/mlb/wc)
