# TC Sports Pipeline — Complete Status Report
**Generated**: 2026-07-18 00:15 AM ET

---

## ✅ WHAT'S LIVE & WORKING

### Core Pipeline
| Component | Status | Detail |
|-----------|--------|--------|
| `daily_picks.py` | ✅ Active | Last run: 2026-07-17 11:53 PM ET — 119 picks |
| Sports enabled | ✅ 3 | WNBA, MLB, WC active |
| Projection generation | ✅ | 9 proj files in `Daily_Log/2026-07-17/` |

### Databases (Projects/data/)
| Database | Table | Rows | Status |
|----------|-------|------|--------|
| `tc_pipeline.db` | graded_picks | 6,238 | ✅ 67.1% hit, $1,763 profit |
| `tc_pipeline.db` | bet_tracking | 6,238 | ✅ |
| `picks.db` | picks | 9,890 | ✅ WNBA 8,508 / MLB 1,185 / WC 197 |

### Services & Endpoints
| Service | Port | Status |
|---------|------|--------|
| API server | :8000 | ✅ 200 — 3 sports, all routes healthy |
| Streamlit Dashboard | :8510 | ✅ 200 |
| zo.space `/nba-tc` | — | ✅ 200 |
| zo.space `/api/tc` | — | ✅ 200 |
| API `/api/picks/top` | :8000 | ✅ 200 |
| API `/api/v1/accuracy` | :8000 | ✅ 200 |

### Config & Secrets
| Secret | Status |
|--------|--------|
| SportsDataIO | ✅ Loaded |
| DK | ✅ Loaded |
| SGO | ✅ Loaded |
| SMTP config | ✅ In `.env` |
| `.env` file | ✅ 10 variables loaded |

### Email Pipeline
| Method | Status |
|--------|--------|
| Zo native email | ✅ Working (tysonjdepina76@gmail.com, tysondepina99@gmail.com) |
| SMTP (Gmail) | ⚠️ Configured — needs App Password |

### Infrastructure
| Component | Status |
|-----------|--------|
| Git repo | ✅ Configured |
| Cron jobs | ✅ 4 configured (hourly picks, daily maintenance, health checks, weekly training) |
| `Projects/data/` (real DBs) | ✅ Active |
| `/home/workspace/data/` (zeroed copies) | ⚠️ Stale — symlinked to real DBs |

---

## ⚠️ OPEN ITEMS

1. **Automation "Daily Sports Picks Update"** — Missing. API returns 404 for automations endpoint. Needs re-creation.
2. **DB path cleanup** — `/home/workspace/data/` has zeroed DB copies. Real DBs at `Projects/data/`. Symlinks in progress.
3. **World Cup junk picks** — Messi SAVES/YELLOW_CARDS nonsensical props for forwards. Needs stat eligibility filter.
4. **WC matchup field** — Empty in `2026-07-17/picks.csv`.
5. **League name duplication** — `picks.db` has both `MLB` (915) and `mlb` (270), `WC` (5) and `wc` (192).
6. **WC deduplication** — Broken. Ronaldo PASSES appears twice.
7. **WNBA correction factors** — All >1.0 (PTS: 1.05, REB: 1.03, AST: 1.03, STL: 1.02, BLK: 1.02) → inflates every projection above market → 84% OVER picks.
8. **Combos engine** — 0 qualified combos across all sports.
9. **Odds API** — Business tier quota maxed. WC uses self-edge projections only. No DK/BetMGM lines for WC.
10. **Enhancer** — `enhance_picks.py` runs standalone with hardcoded July 16 box scores, never called by `daily_picks.py`.

---

## 📊 BACKTEST (graded_picks: 6,238)
- **Overall hit rate**: 67.1%
- **Total P&L**: +$1,763
- **WNBA**: 84% OVER picks, 67.5% overall hit
- **MLB**: Active via SportsDataIO DK lines — pitcher OVERs dominate (strikeouts, hits_allowed)

---

## 🔧 NEXT PRIORITY ACTIONS
1. Re-create "Daily Sports Picks Update" automation
2. Symlink real DBs (`Projects/data/*.db` → `/home/workspace/data/*.db`)
3. Fix WNBA correction factors (reduce to ≤1.0 for mixed OVER/UNDER)
4. Add WC stat eligibility filter (no SAVES for forwards, no YELLOW_CARDS for GKs)
5. Normalize league names to uppercase in `picks.db`
6. Fix WC dedup logic
