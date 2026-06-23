# TC Pipeline — Complete Function Map & API Key Directory

> **Scanned 2026-06-23 13:30 ET** — live probe of every key, every endpoint, every service.

---

## 1. API KEY DIRECTORY — What Each Key Does (Live Status)

| # | Key Name | Provider | Length | Plan | Monthly Cost | Status |
|---|----------|----------|--------|------|-------------|--------|
| 1 | `ODDS_API_KEY` | The Odds API | 17 chars | Free | $0 | ✅ LIVE |
| 2 | `SPORTSGAMEOODS_API_KEY` | SportsGameOdds | 32 chars | Paid | $? | ❌ DEAD |
| 3 | `SPORTSDATAIO_API_KEY` | SportsDataIO | 32 chars | Paid | $? | ⚠️ PARTIAL |

---

### KEY #1: `ODDS_API_KEY` — The Odds API (`toa_live...`)

**Base URL:** `https://api.theoddsapi.com`

| Endpoint | Status | What It Gives | Notes |
|----------|--------|---------------|-------|
| `/sports/` | ✅ 200 | List of available sports | Free |
| `/odds/?sport_key=basketball_wnba` | ✅ 200 | WNBA DK/ML/spread game lines | 5 games today, 29KB |
| `/odds/?sport_key=baseball_mlb` | ✅ 200 | MLB DK/ML/spread game lines | 16 games, 113KB |
| `/odds/?sport_key=soccer_fifa_world_cup` | ❌ 403 | — | **"World Cup requires Business plan or higher"** |
| `/props/` (player props) | ❌ NOT ON FREE TIER | — | Requires Business+ plan ($?) |
| `/usage/` (quota check) | ❌ 404 | — | Endpoint doesn't exist on this API |

**Honest assessment:** Free tier = game-level lines ONLY (totals, moneyline, spreads). No player props. No World Cup at all — that's a paywall. 500 req/month free. Currently ~250 used (mid-month estimate).

**What it's actually feeding:** WNBA game totals (used in self-edge LINE calculation), MLB game totals/spreads. Player props come from self-edge fallback or SDIO, NOT from this key.

---

### KEY #2: `SPORTSGAMEOODS_API_KEY` — SportsGameOdds (`073d94a2...`)

**Base URL:** `https://api.sportsgameodds.com/v2`

| Endpoint | Status | What It Gives | Notes |
|----------|--------|---------------|-------|
| `/events?sportID=basketball_wnba` | ❌ 400 | — | "sportID contains invalid value" |
| `/events?sportID=WNBA` | ❌ 400 | — | "sportID contains invalid value" |
| `/events?sportID=basketball_nba` | ❌ 503 | — | NBA off-season (expected) |

**Honest assessment: THIS KEY IS DEAD for all active sports.** It was the primary WNBA player props feed during NBA season. The sportID format may have changed, or the key may have been deactivated. Attempted both `basketball_wnba` and `WNBA` — both return 400.

**Status: DECOMMISSIONED.** The pipeline no longer depends on SGO at all. WNBA player props now come from ESPN embedded DK lines + self-edge fallback.

**What you were paying for:** Nothing currently. If this is a paid key, cancel it.

---

### KEY #3: `SPORTSDATAIO_API_KEY` — SportsDataIO (`4b757b3f...`)

**Base URL:** `https://api.sportsdata.io/v3`

| Endpoint | Status | What It Gives | Notes |
|----------|--------|---------------|-------|
| `/mlb/odds/json/PlayerPropsByDate/YYYY-MM-DD` | ✅ 200 | MLB player props | 1,714 props today across 10 stat types |
| `/mlb/scores/json/Games/YYYY-MM-DD` | ❌ 401 | — | Trial or subscription doesn't cover this endpoint |

**Honest assessment: PARTIAL — props work, scores don't.** But we don't NEED the scores endpoint — ESPN provides those for free. The props endpoint is the valuable one: 1,714 live MLB player props daily with line values from sportsbooks.

**What it feeds:** MLB Layer 2 in `mlb_tc_engine.py`:
- Layer 1: Odds API game lines → ❌ (no player props on free tier)
- **Layer 2: SDIO → ✅ ACTIVE** — 1,714 props, 10 stat types
- Layer 3: Self-edge → ✅ ACTIVE (fallback)

**Stat types returned:** Hits, Total Bases, Runs, RBIs, Home Runs, Strikeouts, Pitching Hits, Pitching Runs Allowed, Pitching Strikeouts, Fantasy Points.

---

### FREE / NO-KEY ENDPOINTS

| Endpoint | Status | What It Gives |
|----------|--------|---------------|
| `https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard` | ✅ 200 | WNBA rosters, schedules, embedded DK lines |
| `https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard` | ✅ 200 | MLB rosters, schedules, embedded DK lines |
| `https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard` | ✅ 200 | World Cup rosters, schedules |
| ESPN gamelogs (per-player) | ✅ 200 | Last-5-game rolling stats for TC math |

---

## 2. PIPELINE FUNCTION MAP — Every Endpoint, Every Connection

```
                         ┌─────────────────────────────────┐
                         │     ESPN APIs (FREE, NO KEY)     │
                         │  • WNBA/MLB/WC scoreboards       │
                         │  • Rosters, schedules            │
                         │  • Embedded DK game lines        │
                         │  • Gamelogs (per-player stats)   │
                         └──────────┬──────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
   ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
   │  daily_picks │        │ mlb_tc_engine│        │worldcup_picks│
   │     .py      │        │     .py      │        │     .py      │
   │              │        │              │        │              │
   │ WNBA + MLB   │        │  MLB ONLY    │        │ WORLD CUP    │
   │ + WC slate   │        │              │        │ FanDuel only │
   └──────┬───────┘        └──────┬───────┘        └──────┬───────┘
          │                       │                       │
          │  ┌────────────────────┤                       │
          │  │  Layer 1: Odds API │                       │
          │  │  (game lines only) │                       │
          │  │  ❌ no player props│                       │
          │  ├────────────────────┤                       │
          │  │  Layer 2: SDIO     │                       │
          │  │  ✅ 1714 props/day │                       │
          │  ├────────────────────┤                       │
          │  │  Layer 3: Self-Edge│                       │
          │  │  LINE = TC × 0.88  │                       │
          │  └────────────────────┘                       │
          │                       │                       │
          ▼                       ▼                       ▼
   ┌──────────────────────────────────────────────────────────┐
   │              consensus_engine.py                         │
   │  Multi-book consensus (DK → FD → BetMGM → Caesars)      │
   │  ODDS_BASE = https://api.theoddsapi.com                  │
   │  Only used for game-level consensus (totals/ML/spread)   │
   └──────────────────────┬───────────────────────────────────┘
                          │
                          ▼
   ┌──────────────────────────────────────────────────────────┐
   │              /api/tc  (zo.space route)                   │
   │  Unified TC projection endpoint                          │
   │  • buildMultiSportProjection() — WNBA, MLB, WORLD CUP   │
   │  • fetchMultiSportDKLines() — game totals                │
   │  • getBestOdds() — 4-tier cascade:                      │
   │      SGO → Odds API → ESPN DK → self-edge               │
   │  • PROP_EDGE_FILTERS (sport-specific thresholds)         │
   └──────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ /nba-tc  │   │ /worldcup│   │/dk-combos│   │ Streamlit│
   │ Dashboard│   │ Dashboard│   │ Dashboard│   │  :8510   │
   │ (React)  │   │ (React)  │   │ (React)  │   │ (Python) │
   └──────────┘   └──────────┘   └──────────┘   └──────────┘
                          │
                          ▼
   ┌──────────────────────────────────────────────────────────┐
   │              Combo Engines (Services)                    │
   │  • dk-combos-engine (:8515) — WNBA combos from SGO      │
   │  • soccer-combos-engine (:8516) — Soccer combos          │
   │  • sdio-lines-service (:8520) — MLB SDIO line cache     │
   └──────────────────────────────────────────────────────────┘
                          │
                          ▼
   ┌──────────────────────────────────────────────────────────┐
   │              Daily_Log/YYYY-MM-DD/                       │
   │  • picks.csv / picks.json — all picks with edges         │
   │  • proj_SPORT_MATCHUP.json — per-game TC projections     │
   │  • slate_*.json — roster + schedule snapshots            │
   │  • combos_*.md — formatted parlay leg reports            │
   │  • pipeline_report.md — daily health summary             │
   └──────────────────────────────────────────────────────────┘
                          │
                          ▼
   ┌──────────────────────────────────────────────────────────┐
   │              Boxscore Capture                            │
   │  • boxscore_saver.py — WNBA halftime + final             │
   │  • soccer_boxscore_capture.py — WC final boxscores       │
   │  Output → boxscore_registry.json / wc_boxscores/         │
   └──────────────────────────────────────────────────────────┘
```

---

## 3. DATA FLOW PER SPORT

### WNBA
```
ESPN scoreboard (rosters + embedded DK lines)
    │
    ├─→ player_gamelogs.py (last 5 games per player)
    │       │
    │       ▼
    │   tc_math.py (TC projection = rolling avg × pace × matchup factor)
    │       │
    │       ▼
    ├─→ daily_picks.py (slate capture, prop generation)
    │       │
    │       ▼
    │   /api/tc (getBestOdds: SGO→Odds API→ESPN DK→self-edge)
    │       │
    │       ▼
    ├─→ Daily_Log/YYYY-MM-DD/proj_WNBA_TEAM_at_TEAM.json
    │       │
    │       ▼
    ├─→ /api/tc valid_props (with edge, line, direction)
    │       │
    │       ▼
    └─→ /nba-tc dashboard + combos (+ boxscore backtest)
```

### MLB
```
ESPN scoreboard (rosters)
    │
    ├─→ player_gamelogs.py (last 5 games per player)
    │       │
    │       ▼
    ├─→ mlb_tc_engine.py (TC projection)
    │       │
    │       ├─→ Layer 1: Odds API game lines (totals only, free tier)
    │       ├─→ Layer 2: SDIO player props (1714 props, 10 stat types) ✅
    │       └─→ Layer 3: Self-edge (LINE = TC × 0.88) ✅
    │       │
    │       ▼
    ├─→ sdio-lines-service (:8520) — cached SDIO feed
    │       │
    │       ▼
    └─→ /api/tc → /nba-tc dashboard
```

### World Cup
```
ESPN scoreboard (fifa.world) — rosters only
    │
    ├─→ worldcup_picks.py (FanDuel player props scraper)
    │       │
    │       ├─→ Tier 0: Disk cache (Daily_Log/worldcup/YYYYMMDD/)
    │       ├─→ Tier 1: Odds API player props → ❌ 403 (needs Business plan)
    │       ├─→ Tier 2: FanDuel scraping → limited coverage
    │       └─→ Tier 3: Self-edge (LINE = TC × 0.88) ✅ (June 20 fix)
    │       │
    │       ▼
    ├─→ /api/worldcup-props + /api/worldcup-odds
    │       │
    │       ▼
    └─→ /worldcup dashboard (9-stat tabs: G, A, SOT, S, COR, TKL, FC, CRD, PAS)
```

---

## 4. HONEST FAILURES — What's Broken and Why

### FAILURE #1: SGO API Key — DEAD
- **What died:** `SPORTSGAMEOODS_API_KEY` — was the primary WNBA/NBA player props feed
- **When:** Sometime between June 16 (NBA Finals end) and June 18
- **Why:** Key format invalid or service changed sportID format. NBA 503 (expected, off-season). WNBA returns 400 for all sportID values tried.
- **Impact:** Pipeline lost its primary DK player props source
- **Mitigation:** ESPN embedded DK game lines + self-edge fallback replaced it
- **Resolution:** TBD. Verify SGO account status or cancel. Self-edge is functional.

### FAILURE #2: Odds API — No Player Props on Free Tier
- **What's missing:** `/props/` endpoint requires Business+ plan
- **Why:** Free tier = 500 req/month of game-level odds only (totals, ML, spread)
- **Impact:** No external player prop verification for WNBA or MLB. All player props are self-edge (LINE = TC × 0.88) — this means we're betting against our own math with no market check.
- **Mitigation:** SDIO provides real MLB player props (key #3). WNBA relies entirely on self-edge.
- **Resolution:** Upgrade Odds API to Business+ tier for player props, OR accept self-edge-only model for WNBA.

### FAILURE #3: Odds API — World Cup 403 Paywall
- **What's blocked:** `soccer_fifa_world_cup` sport key
- **Why:** World Cup requires Business plan or higher ($?/month)
- **Impact:** No DK/FD game lines or player props for World Cup from Odds API
- **Mitigation:** FanDuel scraper (`worldcup_picks.py`) + self-edge fallback + ESPN embedded odds
- **Resolution:** Upgrade Odds API to Business tier, OR build ESPN-scraped WC player props

### FAILURE #4: SDIO — Scores Endpoint 401
- **What's broken:** `/mlb/scores/json/Games/` returns 401
- **Why:** Trial key or subscription tier doesn't cover scores
- **Impact:** NONE — we use ESPN for scores/gamelogs. Props endpoint (the valuable one) works fine.
- **Resolution:** Ignore. Not needed.

### FAILURE #5: No WNBA External Player Props — Fully Self-Edge
- **Why:** SGO dead + Odds API free tier lacks player props
- **What it means:** Every WNBA prop is `LINE = floor(TC × 0.88)`, `EDGE = TC - LINE`. No external market line to validate our projection.
- **Risk:** Self-edge has no market calibration. If TC math is systematically off (e.g., over-estimating minutes for bench players, missing injury news), every pick is wrong in the same direction.
- **Backtest results (June 18):** 57.1% hit rate on 49 WNBA self-edge picks — too small a sample for confidence.
- **Resolution:** Either upgrade Odds API for WNBA player props, find a new WNBA props API, or run larger backtests to validate self-edge calibration.

### FAILURE #6: World Cup No DK Player Props — FanDuel-Only + Self-Edge
- **Why:** Odds API paywall + no SGO + FanDuel scraper partial
- **Impact:** World Cup player props come from FanDuel scraping (limited coverage) + self-edge math. No DK lines at all for WC.
- **Resolution:** Upgrade Odds API to Business tier (covers WC game lines + player props), or build ESPN-scraped WC player props.

### FAILURE #7: Self-Sustaining Loop — The "Fix Same Things" Problem
- **The pattern:** SGO dies → rewrite to use ESPN embedded → ESPN format changes → fix ESPN parser → Odds API URL changes → fix URLs → key expires → cycle repeats
- **Why it keeps happening:** Every external dependency is a single point of failure. When 2+ fail simultaneously (SGO + Odds API props), we fall to self-edge — but self-edge has no external validation.
- **What would fix it:** 
  1. Multiple redundant player props APIs (not just one)
  2. Automated API health monitoring with alerting (exists via `/api/pipeline-health` but no PagerDuty/email alert on failure)
  3. Backtest-driven self-edge calibration (prove self-edge works at scale before relying on it)
  4. Paid Odds API Business plan = one stable source for all 3 sports

---

## 5. SERVICE MAP

| Service | Port | URL | Status | CPU/Mem |
|---------|------|-----|--------|---------|
| `tc-dashboard-streamlit` | 8510 | `https://tc-dashboard-streamlit-true.zocomputer.io` | ✅ Running |
| `dk-combos-engine` | 8515 | `https://dk-combos-engine-true.zocomputer.io/combos` | ✅ Running |
| `soccer-combos-engine` | 8516 | `https://soccer-combos-engine-true.zocomputer.io` | ✅ Running |
| `sdio-lines-service` | 8520 | `https://sdio-lines-service-true.zocomputer.io` | ✅ Running |

---

## 6. AUTOMATION SCHEDULE (ET)

| Time | Name | Frequency | Status |
|------|------|-----------|--------|
| 1:30 PM | Slate + Injury Refresh (WNBA/MLB/WC) | Daily | ✅ Active |
| 6:30 PM | Final Pre-Tip + Combo Generation | Daily | ✅ Active |
| 8:30 PM, 10:30 PM, 12:30 AM | Boxscore Capture (Halftime + Final) | 3x Daily | ✅ Active |
| 2:00 AM | Daily Backtest (WNBA only) | Daily | ✅ Active |
| 4:00 AM | Daily System Maintenance | Daily | ✅ Active |
| Mon 8:00 AM | Weekly 30-Day Backtest Rollup | Weekly | ✅ Active |
| Mon 9:00 AM | Weekly System Health Check | Weekly | ⏸️ Paused |

---

## 7. ZO.SPACE ROUTE MAP

| Route | Type | Visibility | Purpose |
|-------|------|------------|---------|
| `/` | Page | Private | Homepage |
| `/nba-tc` | Page | Private | WNBA/MLB/WC TC Dashboard |
| `/worldcup` | Page | Private | World Cup Props (9 stat tabs) |
| `/dk-combos` | Page | Private | DK Combos Dashboard |
| `/speaking` | Page | Public | Speaking Engagements |
| `/mirror-workbook` | Page | Private | The Mirror Workbook |
| `/api/tc` | API | Public | TC projections (WNBA/MLB/WC) |
| `/api/dk-lines` | API | Public | DK lines per sport |
| `/api/combos` | API | Public | Combo generation |
| `/api/combo-prob` | API | Public | Combo probability |
| `/api/pipeline-health` | API | Public | Health check |
| `/api/daily-log` | API | Public | Daily log access |
| `/api/wnba-boxscores` | API | Public | WNBA boxscore history |
| `/api/worldcup-odds` | API | Public | World Cup odds |
| `/api/worldcup-props` | API | Public | World Cup player props |
| `/api/boxscores` | API | Public | Boxscore data |
| `/api/env-check` | API | Public | Environment check |
| `/api/pipeline-monitor` | API | Public | Pipeline monitor |

---

## 8. QUICK REFERENCE — What To Upgrade / Fix

| Priority | Issue | Action | Cost |
|----------|-------|--------|------|
| 🔴 P0 | SGO key dead — cancel or fix | Check SGO account, update sportID, or cancel | TBD |
| 🟡 P1 | Odds API no player props | Upgrade to Business+ plan | $?/month |
| 🟡 P1 | Odds API World Cup 403 | Upgrade to Business plan | $?/month |
| 🟢 P2 | WNBA fully self-edge | Either: a) run 30-day backtest to validate, or b) get paid player props API | $0 (backtest) or $? (API) |
| 🟢 P2 | SDIO scores endpoint 401 | Ignore — not needed, ESPN provides for free | $0 |
| ⚪ P3 | Self-healing loop fragility | Add PagerDuty/email alerts on `/api/pipeline-health` failures | $0 (built-in) |

---

## 9. KEY FILES REFERENCE

| File | What It Does |
|------|-------------|
| `Projects/pipeline_master.py` | Master daily runner — self-checks, repairs, generates |
| `Projects/daily_picks.py` | Daily slate capture → `Daily_Log/YYYY-MM-DD/` |
| `Projects/consensus_engine.py` | Multi-book consensus (Odds API game lines) |
| `Projects/mlb_tc_engine.py` | MLB TC engine (3-tier: Odds → SDIO → self-edge) |
| `Projects/mlb_sdio_props.py` | SDIO MLB player props fetcher |
| `Projects/worldcup_picks.py` | World Cup FanDuel scraper + self-edge |
| `Projects/soccer_tc_engine.py` | Soccer 9-stat TC projections |
| `Projects/tc_math.py` | TC math core (per-minute, pace, matchup) |
| `Projects/tc_dashboard.py` | Streamlit dashboard (:8510) |
| `Projects/player_gamelogs.py` | Last-5-game rolling averages from ESPN |
| `Projects/boxscore_saver.py` | WNBA halftime + final boxscore capture |
| `Projects/soccer_boxscore_capture.py` | World Cup final boxscore capture |
| `Projects/api_scan.py` | API endpoint health scanner |
| `Projects/api_cache.py` | Unified cache system (2hr TTL) |
| `Projects/api_fallback.py` | Multi-tier API fail-safe manager |
| `Projects/build_pregame_combos.py` | Combo builder (TC × consensus) |
| `Projects/dk_combos_engine.py` | DK combo engine (:8515) |
| `Projects/soccer_combo_engine.py` | Soccer combo engine (:8516) |
| `Projects/pipeline_health.py` | Component health checks |
| `Daily_Log/api_registry.json` | Scanned status of all endpoints |
| `/root/.zo/secrets.env` | API keys (3 keys total) |
| `PIPELINE_MAP.md` | **THIS FILE** — master pipeline map |
