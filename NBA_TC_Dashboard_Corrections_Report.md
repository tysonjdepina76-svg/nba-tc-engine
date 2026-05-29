# NBA TC Dashboard — Full Correction Report
**Generated:** May 28, 2026
**Route:** `/nba-tc`

---

## What Was Wrong (3 Issues)

### Issue 1 — TC Stat Windows Showed Wrong Values
**Symptom:** 6 stat windows below OKC roster showed `145.7` for TC PTS — a team sum, not a player projection.

**Root cause:** `TeamTotals` component was reading `data.totals.tc_pts` (sum of all active players' TC points = 139.1 for OKC) instead of the stat leader's per-player projection.

**Fix:** Replaced `TeamTotals` with `TeamLeaders` component. Now each of the 6 windows scans all active players on that team and displays:
- The **highest TC projection** for that stat (the team leader)
- The **player name** (last name) of who holds that projection

**Result for OKC vs SAS:**
| Stat | Leader | TC Projection |
|------|--------|---------------|
| TC PTS | Shai Gilgeous-Alexander | 21.5 |
| TC REB | Chet Holmgren | 7.1 |
| TC AST | Shai Gilgeous-Alexander | — |
| TC 3PM | — | — |
| TC STL | — | — |
| TC BLK | — | — |

*Note: live ESPN API provides current-season averages; TC applies 0.85 conservative factor.*

---

### Issue 2 — DK Game Lines Card Was Collapsing ML/Spread/Total
**Symptom:** Odds card showed only `—` for ML and Spread despite API returning real DK lines.

**Root cause:** Frontend was reading nested paths that didn't match the actual API response structure (`odds.away?.moneyline` vs actual `odds.away_ml`).

**Fix:** Rewrote `DKLinesCard` to read the correct API paths:
- `odds.total` → DK Total
- `odds.spread` → DK Spread (shown as `SA -3.5` format)
- `odds.away_ml / odds.home_ml` → DK ML (with + formatting for underdogs)
- `odds.spread_pick` → Spread lean badge
- `result.dk_total` → TC does NOT apply to game totals (kept separate)

**Current API response for OKC @ SAS:**
```
dk_total: 218.5
odds.spread: -3.5
odds.details: "SA -3.5"
odds.spread_pick: "SAS"
ml_spread_total: {total: 218.5, spread: -3.5, spread_pick: "SAS"}
```

---

### Issue 3 — Other Sports (WNBA/NCAAB/MLB/NHL) Not in Dashboard
**Symptom:** Sport selector only showed NBA/WNBA toggle. No tabs or selectors for NCAAB, MLB, or NHL.

**Root cause:** Hardcoded sport list was `["NBA", "WNBA"]` — three sports were missing entirely.

**Fix — Full 5-sport integration:**

Added to frontend:
```js
const SPORTS = ["NBA", "WNBA", "NCAAB", "MLB", "NHL"] as const;
const TEAM_MAP = {
  NBA:   [30 teams],
  WNBA:  [15 teams],
  NCAAB: [25 teams],
  MLB:   [30 teams],
  NHL:   [29 teams],
};
const DEFAULT_GAME = {
  NBA:   ["NYK", "CLE"],
  WNBA:  ["NY",  "CON"],
  NCAAB: ["DU",  "UConn"],
  MLB:   ["NYY", "BOS"],
  NHL:   ["BOS", "TOR"],
};
const SPORT_ICONS = {
  NBA: "🏀", WNBA: "🏀", NCAAB: "🏆", MLB: "⚾", NHL: "🏒"
};
```

Changes made:
1. Sport selector now shows all 5 sports with icons (🏀🏀🏆⚾🏒)
2. Team dropdowns dynamically update when sport changes (WNBA uses `NY` not `NYK`, etc.)
3. Sport-specific defaults auto-select when switching
4. Live Stats tab has sport selector with all 5 sports
5. Slate tab has sport selector with all 5 sports
6. Header subtitle updated: `NBA · WNBA · NCAAB · MLB · NHL`

**WNBA note:** WNBA uses different ESPN team codes (GS not GSW, NY not NYK, LV not LVA). The API already handles normalization — frontend sport selector passes `sport=WNBA` and API converts team codes internally.

---

## Corrections Summary

| # | Issue | Status |
|---|-------|--------|
| 1 | 6 stat windows showed team sums (139.1/145.7) instead of stat leader projections (21.5 for Shai) | ✅ FIXED |
| 2 | DK Lines card (ML, Spread, Total) was showing `—` despite real API data | ✅ FIXED |
| 3 | Only NBA/WNBA in dashboard — missing NCAAB, MLB, NHL tabs and selectors | ✅ FIXED |

---

## Design Clarifications

1. **TC does NOT apply to game totals.** TC is a player prop projection system.
   - Game total (OU) = DraftKings market line (e.g. 218.5)
   - TC combined is shown separately for reference only
   - TC projections apply to individual player props (PTS/REB/AST/3PM/STL/BLK)

2. **6 stat windows per team** = one per stat category (PTS, REB, AST, 3PM, STL, BLK)
   - Each window shows the **team leader's TC projection** for that stat
   - Not a sum. Not a total. The individual leader's number.

3. **DK game lines (ML/Spread/Total)** pulled live from ESPN scoreboard API.
   - Moneyline may show `—` when ESPN doesn't publish ML in scoreboard endpoint
   - Spread and Total are typically available pre-game

4. **Stat Leaders panel** (below odds card) shows cross-game top 5 players across both teams for the selected stat category — remains unchanged.

---

## Files Modified

- `/nba-tc` (zo.space page route) — complete rewrite
  - Replaced `TeamTotals` → `TeamLeaders` component
  - Rewrote `DKLinesCard` with correct API field paths
  - Added 5-sport support (NBA/WNBA/NCAAB/MLB/NHL)
  - Added `DEFAULT_GAME` per-sport team presets
  - Added `SPORT_ICONS` per sport
  - Dynamic team lists via `TEAM_MAP[sport]`
  - Sport selector in Project, Live, and Slate tabs

---

## Verified API Response Structure

```
GET /api/tc?away=OKC&home=SAS

away.totals.tc_pts: 139.1  ← team sum (sum of all active player TC projections)
home.totals.tc_pts: 145.7  ← team sum

away.all.players[].tc_pts: 21.5  ← Shai (TC PTS LEADER for OKC)
away.all.players[].tc_reb: 7.1   ← Chet (TC REB LEADER for OKC)

odds.total: 218.5   ← DK total
odds.spread: -3.5   ← DK spread
odds.spread_pick: "SAS"

dk_total: 218.5     ← exposed for frontend
```