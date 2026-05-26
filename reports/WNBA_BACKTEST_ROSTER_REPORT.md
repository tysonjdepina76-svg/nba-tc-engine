# WNBA Backtest Roster Report

**Generated:** 2026-05-22 20:44:44

## Summary

- Canonical teams checked: **15**
- Teams exported: **15**
- Team files patched with default injury notes: **15**
- Errors: **0**

## Team Readiness

| Code | Team | Starters | Bench | Total Players | Injury Notes | Duplicates | Status |
|---|---|---:|---:|---:|---:|---|---|
| ATL | Atlanta Dream | 5 | 8 | 13 | 1 | None | READY |
| CHI | Chicago Sky | 5 | 9 | 14 | 1 | None | READY |
| CON | Connecticut Sun | 5 | 9 | 14 | 1 | None | READY |
| DAL | Dallas Wings | 5 | 9 | 14 | 1 | None | READY |
| GSV | Golden State Valkyries | 5 | 10 | 15 | 1 | None | READY |
| IND | Indiana Fever | 5 | 8 | 13 | 1 | None | READY |
| LVA | Las Vegas Aces | 5 | 7 | 12 | 1 | None | READY |
| LAS | Los Angeles Sparks | 5 | 9 | 14 | 1 | None | READY |
| MIN | Minnesota Lynx | 5 | 9 | 14 | 1 | None | READY |
| NYL | New York Liberty | 5 | 10 | 15 | 1 | None | READY |
| PHX | Phoenix Mercury | 5 | 9 | 14 | 1 | None | READY |
| POR | Portland Fire | 5 | 8 | 13 | 1 | None | READY |
| SEA | Seattle Storm | 5 | 9 | 14 | 1 | None | READY |
| TOR | Toronto Tempo | 5 | 9 | 14 | 1 | None | READY |
| WAS | Washington Mystics | 5 | 9 | 14 | 1 | None | READY |

## Files Created

- `wnba_rosters/WNBA_BACKTEST_ROSTERS.json` — JSON export for backtesting engine
- `wnba_rosters/WNBA_BACKTEST_ROSTERS.py` — Python dict export for backtesting engine
- `WNBA_BACKTEST_ROSTER_REPORT.md` — this report

## Injury Note Standard

> No injuries listed in May 22, 2026 live scrape; treat all rostered players as ACTIVE until pregame report updates.

## Patched Files

- `WNBA_ATL_Dream.py`
- `WNBA_CHI_Sky.py`
- `WNBA_CON_Sun.py`
- `WNBA_DAL_Wings.py`
- `WNBA_GSV_Valkyries.py`
- `WNBA_IND_Fever.py`
- `WNBA_LVA_Aces.py`
- `WNBA_LAS_Sparks.py`
- `WNBA_MIN_Lynx.py`
- `WNBA_NYL_Liberty.py`
- `WNBA_PHX_Mercury.py`
- `WNBA_POR_Fire.py`
- `WNBA_SEA_Storm.py`
- `WNBA_TOR_Tempo.py`
- `WNBA_WAS_Mystics.py`

## Backtesting Engine Contract

Each team now exposes:

```python
STARTERS = [Player(...), ...]  # exactly 5
BENCH = [Player(...), ...]
INJURY_NOTES = [...]
```

The export files normalize every player into: `name`, `pos`, `ht`, `ppg`, `rpg`, `apg`, `tpm`, `status`.