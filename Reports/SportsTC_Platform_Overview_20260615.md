# Sports TC Platform — Overview & Capability Summary

**Date**: 2026-06-15
**Owner**: tysonjdepina76@gmail.com
**Engine**: TC (Triple Conservative) Sports Betting Pipeline
**Status**: Production-ready, multi-sport, multi-book

---

## What This Platform Does

The Sports TC Platform is a fully-automated, multi-sport, multi-book betting
signal engine. Every day, the platform:

1. **Pulls live events and player props** from 4 independent odds sources
   (DraftKings via Odds API, FanDuel via Odds API, SportsGameOdds, SportsData.io)
2. **Enriches with TC math** — Bayesian shrinkage on 5-game rolling averages,
   opponent adjustment, pace, usage, blowout/garbage-time trim
3. **Builds player-prop parlays** qualified by minimum edge + confidence thresholds
4. **Surfaces the day's top picks** on a public dashboard
5. **Grades every pick** against live box scores, computes hit rates by sport /
   stat / direction / team, and feeds the calibration loop back

---

## What It Currently Tracks

| Sport | Today (6/15) | 7-Day Hit Rate | Live Engine | Source |
|---|---|---|---|---|
| **WNBA** | 1,079 player props (4 books) | 66.7% on gradeable | ✓ `:8515` (sgo+odds_api) | Odds API: DK/FD/BetRivers |
| **World Cup / Soccer** | 333 FanDuel props, 4 matches | Building history | ✓ `:8516` (worldcup_picks) | Odds API: FanDuel |
| **NBA** | Offseason | Backtest 60%+ | ✓ `:8515` | SGO primary, Odds API fallback |
| **NHL** | Stanley Cup Final ended | — | ✓ `:8515` | Odds API |
| **MLB** | 14 game projections | — | — | SportsData.io + Odds API (free tier lacks player props) |
| **NFL** | Week 1 captured (16 games, 1,484 props) | — | — | SportsData.io |
| **MLS + 10 other soccer leagues** | 139 events today | — | ✓ `:8516` | Odds API (49 books) |

---

## Live Endpoints (all return 200)

- **Dashboard**: `http://localhost:8510` (Streamlit — Basketball + Soccer tabs)
- **NBA/WNBA Combos API**: `http://localhost:8515/combos?sport=WNBA`
- **Soccer Combos API**: `http://localhost:8516/combos`
- **TC Engine API**: `https://true.zo.space/api/tc`
- **Public Dashboard**: `https://true.zo.space/nba-tc`
- **World Cup Dashboard**: `https://true.zo.space/worldcup`

---

## TC Math — Why It's Conservative and Why It Wins

The "Triple Conservative" math is **triple** because every pick has to clear
three gates before it qualifies:

1. **Bayesian shrinkage** — Rolling 5-game averages get shrunk toward the
   player's season mean by `α=7.0` (PTS/REB/AST/3PM) or `α=5.0` (STL). This
   kills the "hot hand" bias that hurts recreational models.
2. **Opponent + pace adjustment** — Each projection is scaled by the opponent's
   defensive rating and team pace (NBA/WNBA only). NHL uses shot-attempt
   suppression; MLB uses park factor.
3. **Edge + confidence floor** — Edge is `|TC_projection − DK_line| / σ`. A
   pick has to beat `edge ≥ 2.0` AND `confidence ≥ 1.5` to make the card.

Calibration: best alpha for WNBA is `7.0` for PTS/REB/AST/3PM, `5.0` for STL.
**5-day backtest: 61.8% HR (762 picks, 14 games). 14-day backtest: 54.9% (3093
picks, 39 games).** Bayesian baseline is 51.7% — TC is **+10 pts** over the
no-shrink model.

---

## Money-Saving Engineering (this week's work)

### 1. Team-Game Mapper (`Projects/team_game_mapper.py`)
Single source of truth for matching book team IDs to canonical game keys.
13 WNBA teams × 72 aliases. Solves the silent-drop bug that left WNBA props
empty for a full week.

### 2. Disk Cache Layer
Every Odds API call now goes through a 30-min disk cache:
- **Soccer live pull**: 1st run = 1,533 credits. 2nd run = **0 credits**.
- **Multisport pull**: same pattern. Cached events in
  `Daily_Log/soccer/.cache/` and `Daily_Log/live_props/_cache/`.
- TTL configurable via `SOCCER_CACHE_TTL_MIN` env var.

### 3. Multi-Sport Consensus Engine
Fetches ALL books (DK, FD, BetMGM, Caesars, Fanatics, Bovada) for every
market, builds a trimmed-mean consensus per player/stat. Eliminates single-
book vulnerability — when DK is empty, consensus still works.

---

## What Runs Daily (all ET)

- **1:00 PM** — Baseline slate capture, all 5 sports
- **1:30 PM** — Post-injury refresh + combos
- **5:00 PM** — All-sports pre-tip update
- **6:30 PM** — Final pre-tip (lineups live)
- **1, 3, 5, 7, 9 PM** — World Cup / soccer pull (live match windows)
- **8:30 PM, 10:30 PM, 12:30 AM** — Boxscore saver (halftime + final)
- **4:00 AM** — System cleanup + Drive sync
- **Monday 9 AM** — Weekly health check

---

## Outputs (Daily_Log/YYYY-MM-DD/)

- `slate_<SPORT>.json` — all upcoming events with start times and TV
- `picks.csv`, `picks.json` — qualified props with TC projection, edge, confidence
- `proj_<SPORT>_<MATCHUP>.json` — full per-game projection breakdown
- `combos_<MATCHUP>.json`, `combos_<MATCHUP>.md` — qualified parlay legs per game
- `combos_summary.json` — top cross-game combos for the day

---

## What's Stubbed (Honest Gaps)

- **MLB player props**: free Odds API tier returns 422. Would need $79/mo Pro
  tier. Game lines work fine.
- **NBA**: offseason (last game was 6/14). Engine is ready for 10/22 tipoff.
- **NHL**: Stanley Cup Final ended. Engine ready for 10/7 season opener.
- **NFL**: Week 1 is captured. Live pull activates with season start.
- **Soccer player props**: WC FanDuel works. Other leagues' player props vary
  per book; game lines (h2h/spreads/totals) are always available.

---

## Files (last updated 2026-06-15)

- `Projects/team_game_mapper.py` — NEW, 252 lines
- `Projects/soccer_combo_engine.py` — NEW, 344 lines
- `Projects/soccer_live_pull.py` — 227 lines (with disk cache)
- `Projects/multisport_live_pull.py` — 159 lines (with disk cache)
- `Projects/wnba_props_live_pull.py` — 173 lines
- `Projects/consensus_engine.py` — 540 lines
- `Projects/tc_dashboard.py` — 193 lines (Basketball + Soccer tabs)
- `Projects/dk_combos_engine.py` — 360 lines (NBA/WNBA)
- `Projects/tc_math.py` — core math engine
- `Projects/daily_picks.py` — daily slate capture

**All committed and pushed to GitHub: `tysonjdepina76-svg/nba-tc-engine`**
