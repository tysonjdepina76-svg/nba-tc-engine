# TC Pipeline — Complete Status Report
**Generated**: 2026-07-18 00:35 ET

---

## ✅ What's Running (Live & Healthy)

| Component | Status | Details |
|-----------|--------|---------|
| **tc-api (:8000)** | ✅ LIVE | 3 sports enabled, health check 200 |
| **Streamlit Dashboard (:8510)** | ✅ LIVE | Returns HTML, all tabs functional |
| **zo.space /nba-tc** | ✅ LIVE | 4 tabs — Live, Picks, Accuracy, Injuries |
| **zo.space /api/tc** | ✅ LIVE | Projections + TC API |
| **Daily Automation** | ✅ ACTIVE | 1:30 PM ET daily — email delivery |
| **Email (Zo native)** | ✅ Working | SMTP .env not configured, Zo native email works |

---

## 📊 Databases

| Database | Size | Records |
|----------|------|---------|
| `picks.db` | 2.2 MB | **9,890 picks** |
| `tc_pipeline.db` | 1.1 MB | **6,238 graded** + **6,238 bet_tracking** |

### picks.db Breakdown
| League | Count |
|--------|-------|
| WNBA | 8,508 |
| MLB | 915 |
| mlb (lowercase) | 270 |
| wc (lowercase) | 192 |
| WC | 5 |
| **Total** | **9,890** |

⚠️ **League name duplication**: `MLB` vs `mlb`, `WC` vs `wc` — needs normalization.

### tc_pipeline.db Accuracy
| Sport | Graded | Hit Rate | Avg Edge |
|-------|--------|----------|----------|
| WNBA | 6,230 | 67.1% | +691.6% |
| MLB | 3 | 100.0% | +470.0% |
| WC | 5 | 100.0% | +628.0% |
| **Total** | **6,238** | **67.1%** | — |

---

## 📅 Last Run

- **Date**: 2026-07-17 11:53 PM ET
- **Picks generated**: 119 (in Daily_Log/2026-07-17/picks.csv)
- **Projection files**: 13 files in Daily_Log/2026-07-17/

### Projection File Status (7/17)
| Sport | Files | Status |
|-------|-------|--------|
| WNBA | 5 files | ⚠️ Nearly empty (19-43 bytes) — no real projections |
| MLB | 2 files | ✅ 11-12 KB |
| WC | 2 files | ✅ 14-15 KB |

⚠️ **WNBA projections are duds** — files contain only timestamp, zero player data. This means no WNBA picks can be generated until projection generation is fixed.

---

## 🔌 Services

| Service | Port | Status |
|---------|------|--------|
| **tc-api** | 8000 | ✅ ENABLED — healthy |
| **Streamlit Dashboard** | 8510 | ✅ Running (not a managed service) |
| **sdio-lines-service** | 8520 | ❌ DISABLED since 7/10/2026 |

---

## 🔑 API Keys / Secrets

| Key | Status |
|-----|--------|
| SGO_API_KEY | ✅ Set |
| ODDS_API_KEY | ❌ Not set (Odds API quota maxed on Business tier) |
| SPORTS_DATA_API_KEY | ✅ Set (in sdio service env) |
| DEEPSEEK_API_KEY | ❌ Not set — running via Vercel provider |
| SMTP vars | ❌ Not set — using Zo native email |

---

## ⚠️ Known Issues

1. **WNBA projection generation broken** — 7/17 WNBA proj files are 19-43 bytes (empty)
2. **League name duplication** — picks.db has `MLB`/`mlb`, `WC`/`wc` — needs normalization
3. **sdio-lines-service disabled** since July 10
4. **Odds API quota maxed** — no DK/BetMGM lines for WC, all self-edge
5. **No DeepSeek API key** — you're on Vercel provider, not direct DeepSeek
6. **SMTP not configured** — email works through Zo native, not SMTP

---

## 📋 What You Have vs. What's Missing

### ✅ COMPLETE
- TC picks pipeline (daily_picks.py)
- SQLite persistence (picks.db + tc_pipeline.db)
- Grading/backtesting (6,238 graded)
- Live dashboard (:8510)
- zo.space routes (/nba-tc, /api/tc)
- API (:8000) — health, picks, accuracy endpoints
- Daily automation (1:30 PM ET)
- Email delivery (Zo native)
- MLB projections (StatsAPI)
- WC projections (self-edge)

### ❌ MISSING / BROKEN
- WNBA projection generation (files empty since 7/17)
- League name normalization (MLB/mlb duplication)
- SMTP email pipeline (not configured)
- sdio-lines-service (disabled)
- DeepSeek direct API key (using Vercel provider instead)
- Odds API key (quota maxed on Business tier)
- Real DK/BetMGM lines for WC (self-edge only)

---

## 🚀 Quick Wins (If You Want to Fix)

1. **Fix WNBA projections**: Run `generate_projections.py --sport wnba` with ET date
2. **Normalize league names**: One-line fix in daily_picks.py to uppercase all leagues
3. **Re-enable sdio-lines**: `update_user_service` to set enabled=true
4. **Add DeepSeek key**: Add `DEEPSEEK_API_KEY` to Settings → Advanced → Secrets
