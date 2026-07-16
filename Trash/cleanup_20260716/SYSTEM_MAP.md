# System Architecture Map

> Last updated: 2026-06-15
> After NBA/NHL gating (June 2026)

## Active Sports
| Sport | Status | TC Engine | Odds Feed |
|-------|--------|-----------|-----------|
| WNBA | ✅ Live | `daily_picks.py` | SGO (DK props) + The Odds API (consensus) |
| MLB | ✅ Live | `mlb_tc_engine.py` | The Odds API |
| World Cup | ✅ Live (FanDuel) | `worldcup_picks.py` | FanDuel player props |
| Soccer | ✅ Live | `soccer_tc_engine.py` | The Odds API (49 books) |
| NBA | 🔒 Gated | `daily_picks.py` | — |
| NHL | 🔒 Gated | `daily_picks.py` | — |

## Data Flow
```
ESPN APIs (rosters, schedules, boxscores)
    │
    ├─→ daily_picks.py ──→ TC projections ──→ Daily_Log/YYYY-MM-DD/proj_SPORT_MATCHUP.json
    │
The Odds API / SGO (DK lines, props, consensus)
    │
    ├─→ consensus_engine.py ──→ multi-book consensus
    ├─→ build_pregame_combos.py ──→ pregame combos
    └─→ dk_combos_engine.py ──→ live DK combo lines (port 8515)
```

## Services
```
┌──────────────────────────────────────────────────────────┐
│  Streamlit Dashboard (8510)                              │
│  ├─ WNBA TC projections, props, combos                   │
│  ├─ MLB TC projections                                  │
│  └─ World Cup + Soccer                                  │
├──────────────────────────────────────────────────────────┤
│  DK Combos Engine (8515)                                 │
│  └─ https://dk-combos-engine-true.zocomputer.io/combos  │
├──────────────────────────────────────────────────────────┤
│  Soccer Combo Engine (8516)                              │
│  └─ http://localhost:8516/combos                         │
└──────────────────────────────────────────────────────────┘
```

## Zo.Space Routes
| Route | Type | Purpose |
|-------|------|---------|
| `/` | Page | Homepage |
| `/nba-tc` | Page | WNBA/World Cup/MLB TC Dashboard |
| `/dk-combos` | Page | DK Combos Dashboard |
| `/worldcup` | Page | World Cup Props |
| `/speaking` | Page | Tyson DePina — Speaking Engagements |
| `/mirror-workbook` | Page | The Mirror Workbook |
| `/api/tc` | API | TC projections (WNBA, MLB, WORLD CUP) |
| `/api/dk-lines` | API | DK lines per sport |
| `/api/combos` | API | Combo generation |
| `/api/combo-prob` | API | Combo probability |
| `/api/pipeline-health` | API | Pipeline health check |
| `/api/daily-log` | API | Daily log access |
| `/api/wnba-boxscores` | API | WNBA boxscore history |
| `/api/worldcup-odds` | API | World Cup odds |
| `/api/worldcup-props` | API | World Cup player props |

## Automations (8 daily)
| Time (ET) | Name | Status |
|-----------|------|--------|
| 1:00 PM | Slate Capture (Pre-Injury) | ✅ Active |
| 1:30 PM | Post-Injury Refresh | ✅ Active |
| 1:00/3:00/5:00/7:00/9:00 PM | World Cup Picks | ✅ Active |
| 5:00 PM | WNBA Pre-Tip Update | ✅ Active |
| 6:30 PM | Final Pre-Tip Capture + Cleanup | ✅ Active |
| 8:30/10:30 PM + 12:30 AM | Boxscore Capture (Halftime + Final) | ✅ Active |
| 4:00 AM | Daily System Maintenance | ✅ Active |
| Mon 9:00 AM | Weekly System Health Check | ✅ Active |

## Key Files
| File | Purpose |
|------|---------|
| `Projects/pipeline_master.py` | Master self-healing daily runner |
| `Projects/daily_picks.py` | Daily slate capture |
| `Projects/dk_combos_engine.py` | DK combo lines (SGO) |
| `Projects/consensus_engine.py` | Multi-book consensus |
| `Projects/tc_dashboard.py` | Streamlit dashboard |
| `Projects/soccer_tc_engine.py` | Soccer TC projections |
| `Projects/mlb_tc_engine.py` | MLB TC projections |
| `Scripts/tc_maintenance.sh` | Daily maintenance script |
| `Scripts/system_cleanup.sh` | System cleanup |

## Secrets
- `SPORTSGAMEODDS_API_KEY` — Primary feed (NBA/WNBA player props)
- `ODDS_API_KEY` — Secondary feed (consensus, soccer, MLB)
- `SPORTS_DATA_API_KEY` — NFL data (SportsData.io)
