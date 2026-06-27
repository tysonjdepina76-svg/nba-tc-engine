# Game & Injury Report Timing — All Sports

> Generated 2026-06-27 · All times Eastern (ET)

## Summary Table

| Sport | Earliest Game | Latest Game | Initial Injury Report | Final/Game-Day Updates | Lineups Lock |
|-------|--------------|-------------|----------------------|----------------------|--------------|
| **WNBA** | 2:00 PM ET | 10:00 PM ET | 5 PM local day before | Every 15 min on game day from midnight | ~30 min before tip |
| **MLB** | 1:00 PM ET | 10:00 PM ET | Starting pitchers 1-2 days before | Lineups ~2-3h before first pitch | ~1h before first pitch |
| **World Cup** | 1:00 PM ET | 10:00 PM ET | Squad list pre-tournament only | Lineups 75 min before kickoff | 75 min before kickoff |

---

## WNBA Injury Report Rules (2026 Season)

- **Initial Report**: Teams must submit by 5 PM **local time** the day before the game
- **Game-Day Updates**: Begin at midnight, updated every **15 minutes** until tipoff
- **New 2026 System**: Real-time injury/illness reports generated automatically
- **Enforcement**: Teams face fines for late/vague reporting (see Fever/Caitlin Clark incident)
- **Source**: WNBA.com official injury report + league office memos

### What This Means for Automation
| Time (ET) | Action |
|-----------|--------|
| 10:00 AM | Check overnight injury report updates for today's games |
| 1:30 PM | Refresh — covers the 2 PM game (TOR @ PHX type) |
| 5:00 PM | Final check before evening games |
| 7:00 PM | Pre-game check for 8 PM/9 PM games |

---

## MLB Lineup Timing

- **Starting Pitchers**: Typically announced 1-2 days before (check MLB.com probable pitchers)
- **Batting Lineups**: Released ~2-3 hours before first pitch
- **Injury/Roster Moves**: Reported to MLB transaction wire (no formal daily report like WNBA)
- **Late Scratches**: Can happen any time before first pitch

### What This Means for Automation
| Time (ET) | Action |
|-----------|--------|
| 10:00 AM | Lineups for 1 PM games start appearing |
| 3:00 PM | Lineups for 4 PM games |
| 5:00 PM | Lineups for 7 PM games |
| 8:00 PM | Lineups for 10 PM west coast games |

---

## World Cup Lineup Timing (FIFA Standard)

- **Lineup Release**: Exactly **75 minutes before kickoff** — FIFA-mandated, globally enforced
- **No Daily Injury Reports**: Only squad lists submitted pre-tournament
- **In- Tournament Injuries**: Reported by team medical staff, no formal daily system

### June 27, 2026 World Cup Schedule (from ESPN API)

| Match | Kickoff (UTC) | Kickoff (ET) | Lineups Drop (ET) |
|-------|--------------|-------------|-------------------|
| GHA @ CRO | 21:00 | **5:00 PM** | 3:45 PM |
| ENG @ PAN | 21:00 | **5:00 PM** | 3:45 PM |
| POR @ COL | 23:30 | **7:30 PM** | 6:15 PM |
| UZB @ COD | 23:30 | **7:30 PM** | 6:15 PM |
| AUT @ ALG | 02:00 (Jun 28) | **10:00 PM** | 8:45 PM |
| ARG @ JOR | 02:00 (Jun 28) | **10:00 PM** | 8:45 PM |

> Group stage final matchdays: **all 6 games in a group kick off simultaneously**. June 24-27 are the final group matchdays.

---

## Optimal Automation Schedule

```
06:00 AM — MORNING HEALTH CHECK + SLATE REFRESH
├── Run scan.sh (full health diagnostic)
├── Fetch today's slates (ESPN API — 1 call per sport)
├── Check cache freshness, rotate stale cache
├── Verify API budget: calls remaining, keys active
├── If ANY check fails → email BOTH tysondepina99@gmail.com AND tysonjdepina76@gmail.com
└── Write health report to sports_betting_dashboard/logs/scan_YYYYMMDD.txt

11:00 AM — MLB EARLY SLATE + WNBA INJURY REFRESH
├── Health check FIRST (scan.sh --quick)
├── MLB lineups for 1 PM games appearing
├── WNBA game-day injury updates streaming (midnight+)
├── Fetch DK odds for afternoon games
├── Cache all API responses with 6h TTL
└── Email if DK lines missing for any game

1:30 PM — PRIMARY SLATE + INJURY (EXISTING — KEEP)
├── Health check FIRST
├── Full slate pull for WNBA, MLB, World Cup
├── Injury/roster refresh for all sports
├── Generate projections for 2 PM+ games
├── Cache all responses
└── Email slate summary

4:00 PM — WORLD CUP PRE-GAME + EVENING MLB
├── Health check FIRST
├── World Cup lineups drop (75 min before 5 PM kickoffs)
├── Evening MLB lineups (7 PM games)
├── WNBA evening game injury checks
├── Generate projections, save picks
└── Email pre-game summary

6:30 PM — FINAL PRE-TIP LOCK (EXISTING — KEEP)
├── Health check FIRST
├── Final projections for all remaining games
├── Build combos/parlays
├── All World Cup games locked
├── WNBA 8 PM/9 PM games final check
└── Email final picks + combos

8:30 PM — BOXSCORE HALFTIME (EXISTING)
10:30 PM — BOXSCORE FINAL WAVE 1
12:30 AM — BOXSCORE FINAL WAVE 2

2:00 AM — DAILY BACKTEST (EXISTING)
4:00 AM — SYSTEM MAINTENANCE (EXISTING)
```

---

## Cache Strategy

| Data Type | TTL | Stored At | Refresh Trigger |
|-----------|-----|-----------|----------------|
| Slates (schedule) | 6 hours | `Daily_Log/cache/slates/` | After 2 AM, before 11 AM |
| DK Odds | 4 hours | `Daily_Log/cache/odds/` | On injury update, or every 4h |
| Projections | 2 hours | `Daily_Log/cache/proj/` | On new odds or roster change |
| Injury Reports | 1 hour | `Daily_Log/cache/injuries/` | Every scan run |
| Lineups | Until game start | `Daily_Log/cache/lineups/` | New lineup posted |

### Manual Call Flow (Cache-First)
When you manually call for projections:
1. Check cache TTL → if fresh, return cached
2. If stale, check API budget → if OK, pull fresh
3. If budget exceeded, return stale cache with warning
4. All calls logged to `api_registry.json`
