# Sports Prop TC Workflow Pipeline

## Single source of truth

Use:

```bash
python tc-workspace/scripts/tc_engine.py
```

This engine now covers NBA + WNBA and enforces the core rule:

> TC Match applies only to individual player props: PTS, REB, AST, and 3PM. Team/game totals are not TC Match.

## Generate projections

NBA:

```bash
python tc-workspace/scripts/tc_engine.py --sport NBA --game "PHI @ BOS" --total 208.5 --spread -11.5
```

WNBA:

```bash
python tc-workspace/scripts/tc_engine.py --sport WNBA --game "MIN @ DAL" --total 168.5 --spread -3.5
```

## Backtest saved prop projections

Projection CSVs should preserve this schema:

```csv
date,league,game_id,team,player,stat,tc,target,pick,actual,result,source
```

Run:

```bash
python tc-workspace/scripts/tc_engine.py \
  --backtest-props path/to/projections.csv \
  --boxscores live_sports_scrape \
  --out tc-workspace/reports/prop_backtest_report.md
```

## Backtest rules

- DNP/MISSING players are not counted as losses.
- Ungradable rows are separated.
- Hit rate is calculated only from rows with a matched box-score stat and valid OVER/UNDER pick.
- By-stat hit rates are calculated for PTS, REB, AST, and 3PM.

## Leader symbols

| Symbol | Meaning |
|---|---|
| ♛ | Points leader |
| ◆ | Rebounds leader |
| ✚ | Assists leader |
| ● | 3PM leader |
| ▣ | Blocks leader |
| ✦ | Steals leader |

## Output locations

- Reports: `tc-workspace/reports/`
- Engine: `tc-workspace/scripts/tc_engine.py`
- Final box scores: `live_sports_scrape/`

## Quality checks

```bash
python -m py_compile tc-workspace/scripts/tc_engine.py
python tc-workspace/scripts/tc_engine.py --backtest
python tc-workspace/scripts/tc_engine.py --sport WNBA --game "MIN @ DAL"
```
