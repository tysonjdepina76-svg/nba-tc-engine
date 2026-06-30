# SPORTS TC — System Overview

> Single source of truth. If `AGENTS.md` and this file disagree, this file wins.

---

## Architecture

```
ESPN  ─┐
SGO   ─┼─► Adapters ─► Gates ─► Engine ─► Daily_Log ─► Dashboard
OddsAPI┘                                                 │
                                                       Combos / Cards / Reports
```

| Layer        | Path                                          | Purpose                                                                 |
|--------------|-----------------------------------------------|-------------------------------------------------------------------------|
| Domain       | `tc-sports-app/src/domain/`                   | Pure entities (Sport, Player, Projection), sport config, image gen      |
| Adapters     | `tc-sports-app/src/adapters/`                 | ESPN, SGO, OddsAPI, DK — normalize external feeds                       |
| Gates        | `tc-sports-app/src/gates/`                    | Validation gates (blowout, injury, sharp-money)                         |
| Engine       | `Projects/*.py` (mlb_tc_engine, soccer_tc_engine, …) | Per-sport projection engines                                     |
| Pipeline     | `Projects/daily_picks.py`                     | Orchestrator — runs all enabled engines, writes `Daily_Log/YYYY-MM-DD/` |
| Dashboard    | `Projects/tc_dashboard.py` (Streamlit :8510)  | Multi-sport UI — rosters, lines, projections, cards, parlays            |
| Monitoring   | `Projects/tc_dashboard.py` + service logs     | Health pills, last-update timestamp, slate summary                      |

---

## Data Flow

1. **Fetch** — Adapters pull ESPN scoreboard, SGO injuries/lines, OddsAPI markets.
2. **Gate** — Each event checked against sport-specific gates (starters locked? line moved >X?).
3. **Project** — Per-sport engine produces `Player + Projection` pairs.
4. **Log** — `daily_picks.py` writes to `Daily_Log/YYYY-MM-DD/`:
   - `picks.csv` — consolidated today (sport, player, stat, line, direction, edge, proj)
   - `proj_{SPORT}_{AWAY}_at_{HOME}.json` — full roster + per-player TC math
   - `combos_{sport}_{away}_{home}.json` — cached consensus parlays (fallback for 429s)
5. **Archive** — Next-day cron moves old `Daily_Log/` dirs into `data/historical/{sport}/{season}/{YYYY-MM-DD}/`.
6. **Backtest** — Historical CSVs land in `data/backtest/{sport}_{season}_*.csv` per sport+season.
7. **UI** — Streamlit reads latest `Daily_Log` and historical pivots on demand.

---

## Health Checks

| Check           | Command / Signal                          | Healthy when…                            |
|-----------------|-------------------------------------------|-----------------------------------------|
| Dashboard up    | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8510` | `200`                            |
| Pipeline ran    | `ls -t Daily_Log/ | head -1`              | today's dir present with `picks.csv`    |
| Picks non-empty | `wc -l Daily_Log/$(date +%F)/picks.csv`   | `≥ 1` row beyond header                  |
| Engines loaded  | `python3 -c "import daily_picks"`         | imports without error                   |
| Service logs    | `tail -n 50 /dev/shm/*.log`               | no `ERROR` / `Traceback` in last 50     |

---

## Sport Sources

| Sport    | ESPN Path                  | Source Type    | Reason                                |
|----------|----------------------------|----------------|---------------------------------------|
| NBA      | `basketball/nba`           | TC Math        | Stable, starter-locked math model     |
| WNBA     | `basketball/wnba`          | TC Math        | Same engine as NBA                    |
| NFL      | `football/nfl`             | TC Math        | Preseason mode until Aug 6            |
| MLB      | `baseball/mlb`             | Bookmaker      | Markets more efficient than math      |
| SOCCER   | `soccer/World Cup`         | Bookmaker      | Markets + live stats                   |
| NHL      | `hockey/nhl`               | Bookmaker      | Off-season Jun–Sep                    |
| BOXING   | (OddsAPI only)             | OddsAPI        | No ESPN feed; cards via OddsAPI       |
| MMA      | (OddsAPI only)             | OddsAPI        | No ESPN feed; cards via OddsAPI       |

> Rule locked 2026-06-22: NBA/WNBA/NFL = TC Math. Everything else = Bookmaker lines. Don't switch without explicit user directive.

---

## Scheduled Events

| Date        | Event                                                |
|-------------|------------------------------------------------------|
| Jul 2       | OddsAPI free-tier auto-disables — confirm fallback   |
| Aug 6       | NFL preseason scheduler activates                    |
| Daily 1:30p | TC slate + injury + health check (automation)        |
| Daily 6:30p | Final pre-tip + combo lock (automation)              |
| Daily 11:00p| Boxscore capture — halftime + final                  |

---

## Data Layout

```
/home/workspace/
├── AGENTS.md                  # Workspace routing index (human-quick)
├── SYSTEM.md                  # ← this file — single source of truth
├── Daily_Log/                 # Today + recent (rotated after 7d)
│   └── YYYY-MM-DD/
│       ├── picks.csv
│       ├── proj_{SPORT}_{AWAY}_at_{HOME}.json
│       └── combos_{sport}_{away}_{home}.json
├── data/                      # Organized historical
│   ├── historical/
│   │   ├── nba/2025-26/YYYY-MM-DD/…
│   │   ├── wnba/2025/YYYY-MM-DD/…
│   │   ├── nfl/2025/YYYY-MM-DD/…
│   │   ├── mlb/2025/YYYY-MM-DD/…
│   │   └── soccer/2026/YYYY-MM-DD/…
│   └── backtest/
│       ├── nba_2025-26_*.csv
│       ├── wnba_2025_*.csv
│       ├── soccer_2026_*.csv
│       └── {season}/          # Empty skeleton for future seasons
├── Projects/                  # Python pipeline (engines, daily_picks, dashboard)
├── tc-sports-app/             # Domain layer (entities, sport_config, image gen)
├── reports/images/            # Generated PNG cards / roundups / fight cards
└── cache/                     # Runtime cache (combo fallbacks, logos)
```

---

## Dashboard

- **URL:** http://localhost:8510
- **Title:** 🏆 SPORTS TC — Multi-Sport Analytics
- **Tabs:** 📋 Roster + TC · 📈 Lines · 🎯 Projections · 🎴 Cards · 📊 Parlay Builder · 🔥 Live Combos
- **Conditional tabs:**
  - SOCCER → ⚽ Soccer Stats (player G/A/SH/SOT + team Poss/Corners/SoT)
  - BOXING/MMA → 🥊 Fight Card (head-to-head poster, odds, method/round props)
- **Status pill:** Sport-aware live clock (Top 7 / 78' / Q2 3:45 / R5 2:10)

---

## Operational Rules

1. **No silent regressions.** If you touch a pipeline file, re-run `daily_picks.py` to confirm picks still emit.
2. **Cache fallbacks are mandatory.** Every consensus call wrapped in `_fetch_consensus_with_cache()`; on 429, read cached combo JSON.
3. **Sport-config wins over ad-hoc.** When extending a sport, edit `tc-sports-app/src/domain/sport_config.py`, not the dashboard.
4. **Boxing/MMA are OddsAPI-only.** Until ESPN coverage lands, do not scrape them from `site.api.espn.com`.
5. **Backtest files are immutable.** Once written to `data/backtest/`, never overwrite — append `_v2` if logic changes.

---

## Last Verified

- **System.md:** 2026-06-30 (Tyson — initial)
- **Dashboard:** http://localhost:8510 — live
- **Picks:** `Daily_Log/2026-06-30/picks.csv` (refreshed daily 1:30p / 6:30p ET)