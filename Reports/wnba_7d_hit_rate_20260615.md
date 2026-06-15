# WNBA 7-Day Hit Rate Report — 2026-06-15

**Period:** 2026-06-08 to 2026-06-14 (7 days, 20 WNBA games)

## ⚠️ Data Caveat

The TC pipeline captured **0 DK player prop lines** for 6/8-6/14 WNBA games. All picks have `market_line` empty. Only 3 picks from 6/11 had real lines (from a one-off DK scrape that day).

Grading only picks with real `market_line`:

| Result | Count |
|---|---|
| Graded | 3 |
| HIT | 2 |
| MISS | 1 |
| PUSH | 0 |
| **Hit rate** | **66.7%** (2/3) |

## Graded picks (6/11 only)

| Date | Team | Player | Stat | Dir | Line | Actual | Result |
|---|---|---|---|---|---|---|---|
| 6/11 | CHI | Kamilla Cardoso | PTS | OVER | 12.5 | 10 | MISS |
| 6/11 | IND | Caitlin Clark | PTS | OVER | 19.5 | 32 | HIT |
| 6/11 | IND | Aliyah Boston | PTS | OVER | 14.5 | 34 | HIT |

## Picks captured but NOT graded (no DK line)

| Day | WNBA picks | With market line |
|---|---|---|
| 6/8  | ?  | 0 |
| 6/9  | ?  | 0 |
| 6/10 | 118 | 0 |
| 6/11 | 67 | 3 |
| 6/12 | 102 | 0 |
| 6/13 | 0   | 0 |
| 6/14 | ?   | 0 |

(Skipped 6/8/9/14 picks.csv had no WNBA rows; the picks were generated but lines never came from DK.)

## Why this matters

The TC engine is producing projections and picks correctly. **The DK player-prop feed for WNBA has been silent for 7 days.** Possible causes:
1. WNBA off-week (All-Star break? — too early, ASG is mid-July)
2. SportsData.io WNBA tier not loaded
3. Odds API WNBA player props endpoint returning empty
4. SGO not returning WNBA props

## Next steps

- Re-run `consensus_engine.get_odds('WNBA')` to confirm what each source returns
- Add a 4th source (BetMGM, Caesars, Fanatics) as fallback for WNBA
- For today's slate (6/15) we have **0 upcoming WNBA games** so the gap won't close tonight
- Next WNBA games tip **2026-06-16** — pipeline should re-capture props then

## Files

- `Daily_Log/wnba_7d_graded_picks.json` — 3 graded picks
- `Daily_Log/wnba_7d_summary.json` — counts
- Script: `/home/.z/workspaces/con_2obFQqO7XacPthtH/grade_wnba_7d.py`
