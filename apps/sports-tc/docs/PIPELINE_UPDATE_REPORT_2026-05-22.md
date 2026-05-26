# Sports TC Pipeline Update Report — 2026-05-22

## Executive Summary
Integrated the NBA/WNBA TC template differences into a cleaner v5 workflow pipeline. The key fix is architectural: **team totals and game totals are now generated separately as raw projections only**, while **TC remains restricted to player prop floors** for PTS, REB, AST, and 3PM.

This prevents the earlier confusion where TC combined values were treated like game totals.

---

## Files Added / Updated

| File | Status | Purpose |
|---|---|---|
| `tc_pipeline.py` | Added | New unified pipeline for NBA + WNBA reports, raw totals, player prop TC floors, prop watchlists, and backtest seed logs. |
| `app.py` | Updated | Dashboard now calls `tc_pipeline.py` instead of the older Streamlit/legacy report path. |
| `reports/*.md` | Added | Saved human-readable game reports. |
| `data/*.json` | Added | Saved structured game data for backtesting. |
| `data/backtest_seed_log.csv` | Added/updated | Running seed log for future actual-result comparisons. |
| `reports/PIPELINE_DIAGNOSTICS.md` | Added | Diagnostic results from the current pipeline. |

---

## Implemented Enhancements

### 1. TC Is Now Player-Prop Only
TC applies to:
- PTS × 0.85
- REB × 0.80
- AST × 0.75
- 3PM × 0.70
- Questionable: TC result × 0.55
- OUT: 0

TC does **not** apply to:
- team point totals
- full game totals
- market O/U totals
- spread calculations

### 2. Team Totals Are Separate Raw Projection Totals
Each team now gets raw totals only:
- raw team points
- raw team rebounds
- raw team assists
- raw team 3PM

These are not labeled as TC totals and are not used for TC betting signals.

### 3. Game Totals Are Separate Raw Projection Totals
The report now prints:
- away raw team points
- home raw team points
- raw game points total
- raw game rebounds total
- raw game assists total
- raw game 3PM total
- market total, if provided
- market spread, if provided

No TC game-total edge is generated.

### 4. Starters + Bench + Injury Notes Are Backtest-Ready
The WNBA source JSON already has:
- `starters`
- `bench`
- `injury_notes`
- `backtest_ready`

The new pipeline carries that structure into reports and JSON exports.

### 5. Prop Candidate Watchlist Added
The pipeline generates candidate watchlists by comparing raw projection to TC floor.

These are **not automatic picks**. They are the short list to compare against sportsbook lines.

Example logic:
- Paige Bueckers raw points 20.8 → TC floor 17.7 → target 17+
- Angel Reese raw rebounds 12.7 → TC floor 10.2 → target 10+

### 6. Backtest Seed Logging
When run with `--save`, the system writes:
- Markdown report
- JSON structured data
- CSV row in `data/backtest_seed_log.csv`

This gives you future comparison against actual box scores.

---

## Diagnostics Result

All diagnostics passed:

| Check | Result |
|---|---:|
| WNBA backtest roster JSON exists | PASS |
| WNBA teams loaded | PASS |
| Every WNBA team has starters | PASS |
| Every WNBA team has bench | PASS |
| Every WNBA team has injury notes | PASS |
| Build WNBA DAL @ ATL | PASS |
| No TC total fields in game dict | PASS |
| Prop candidates generated | PASS |
| Build NBA NYK @ PHI | PASS |

---

## Confirmed Working Commands

```bash
cd /home/workspace/sports-tc
python3 tc_pipeline.py --diagnostics
python3 tc_pipeline.py --sport WNBA --game "DAL @ ATL" --total 172.5 --spread -5.5 --save
python3 tc_pipeline.py --sport NBA --game "NYK @ PHI" --save
```

Dashboard command path:

```bash
python3 /home/workspace/sports-tc/app.py
```

---

## Current Known Limitations

1. Some WNBA roster averages remain as 0.0 where live scrape did not provide reliable stat averages.
2. The pipeline is intentionally not auto-betting or calling picks without sportsbook player-prop lines.
3. Team/game totals are informational raw projections only.
4. Old `sports_tc.py` still contains legacy TC game-total logic. New clean workflow should use `tc_pipeline.py`.

---

## Recommendation

Use `tc_pipeline.py` as the clean source of truth going forward.

Keep `sports_tc.py` as legacy/reference until fully retired.
