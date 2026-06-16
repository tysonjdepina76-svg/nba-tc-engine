# 🌍 WORLD CUP 5-DAY BACKTEST — API Key Scan + Results

*Generated: 2026-06-16 ~00:30 ET*

---

## 🔑 API Key Scan

| API | Key Name | Status | Tier | Player Props? |
|-----|----------|--------|------|---------------|
| The Odds API | `ODDS_API_KEY` in secrets.env | ✅ Active | $30/mo | ❌ Historical; ✅ Live only |
| SGO | `SPORTSGAMEODDS_API_KEY` in secrets.env | ✅ Key exists | Paid | ⚠️ Not loaded in env; WC unsupported |
| Odds (alt) | `Theoddsapi` in env | ✅ Active | $30/mo | Same key |
| ESPN | Public API | ✅ Free | N/A | N/A (stats not odds) |

## 📊 5-Day Data Coverage

| Date | Odds API Snapshots | Matches Played | Completed | DK Player Props |
|------|-------------------|----------------|-----------|-----------------|
| 2026-06-12 | 71 events | 4 matches listed | 4 | ❌ |
| 2026-06-13 | 69 events | 4 matches listed | 4 | ❌ |
| 2026-06-14 | 67 events | 4 matches listed | 4 | ❌ |
| 2026-06-15 | 62 events | 4 matches listed | 4 | ❌ |
| 2026-06-16 | 58 events | 2 matches listed | 2 | ❌ |

## 🎯 Game-Level Backtest (H2H / ML)

Using **closing lines** from the last available Odds API snapshot before kickoff.

| Match | Score | Total | Winner | DK Home | DK Draw | DK Away | Result | Payout |
|-------|-------|-------|--------|---------|---------|---------|--------|--------|
| Spain vs Cape Verde | 0-0 | 0 | Draw | -1100 | 1100 | 2200 | ⚠️ | Draw @ +1100 |
| Belgium vs Egypt | 1-1 | 2 | Draw | -165 | 290 | 450 | ⚠️ | Draw @ +290 |
| Saudi Arabia vs Uruguay | 1-1 | 2 | Draw | 1600 | -320 | 300 | ⚠️ | Draw @ -320 |
| Iran vs New Zealand | 1-2 | 3 | New Zealand | -125 | 255 | 390 | ✅ | NZL @ +390 |

### Implied Probabilities vs Actual

| Match | Home Implied | Draw Implied | Away Implied | Actual |
|-------|-------------|-------------|-------------|--------|
| Spain vs Cape Verde | 91.7% | 8.3% | 4.3% | Draw (8.3% event) |
| Belgium vs Egypt | 62.3% | 25.6% | 18.2% | Draw (25.6% event) |
| Saudi Arabia vs Uruguay | 5.9% | 76.2% | 25.0% | Draw (76.2% event) |
| Iran vs New Zealand | 55.6% | 28.2% | 20.4% | Away (20.4% event) |

**Note**: 3 of 4 matches were draws — an unusually high draw rate. NZL win at +390 was the only profitable straight bet.

## ⚠️ Key Issues Found

1. **No DK player props for soccer** — Odds API historical endpoint returns HTTP 422 for player props on soccer. Only game-level (H2H/spreads/totals) available. Live endpoint has player props but they must be captured pre-match.
2. **Generic player names** — Soccer picks use `Qatar_GK_1` etc. instead of real player names. No player-level backtest possible without real names.
3. **All PASS signals** — Every soccer player pick has `signal=PASS` meaning no edge was found at the edge thresholds. Zero actual picks were placed.
4. **SGO API key not loaded** — `SPORTSGAMEODDS_API_KEY` exists in `/root/.zo/secrets.env` but is NOT loaded into env vars. SGO also does not support World Cup (FIFA) — only UEFA Champions League.
5. **World Cup not in SGO league list** — SGO supports: MLB, MLS, NCAAF, NHL, NBA, NCAAB, NFL, UEFA_CHAMPIONS_LEAGUE. No FIFA World Cup.
6. **worldcup_picks.py output dir mismatch** — Writes to `Daily_Log/worldcup/YYYY-MM-DD/` but pipeline reads from `Daily_Log/YYYY-MM-DD/`.

## 📈 Pipeline Status (5 days)

| Day | Odds Pulled | Picks Generated | Matches Played | Backtest Possible |
|-----|------------|-----------------|----------------|-------------------|
| Jun 12 | ✅ 71 events | ❌ No soccer picks | 0 | ❌ No matches |
| Jun 13 | ✅ 69 events | ✅ 19,585 rows | 0 | ❌ No matches |
| Jun 14 | ✅ 67 events | ❌ No soccer picks | 0 | ❌ No matches |
| Jun 15 | ✅ 62 events | ✅ 18,793 rows | 4 | ⚠️ Game-level only |
| Jun 16 | ✅ 58 events | ❌ Not yet | 0 (today) | ❌ Not settled |

**Total: 5/5 days odds pulled. 2/5 days picks generated. 4 matches completed.**

## 🔜 Recommendations

1. **Fix API key loading** — Add `SPORTSGAMEODDS_API_KEY` to pipeline env loader (though SGO may not have WC)
2. **Get real player names** — Scrape ESPN rosters for World Cup teams with actual player names
3. **Enable player props** — Odds API live endpoint has player props; capture pre-match for future backtests
4. **Set edge thresholds** — Current `PASS` on everything means thresholds are too strict for soccer (WNBA is tuned for basketball)
5. **Fix output dir mismatch** — Align `worldcup_picks.py` output with pipeline expectations
