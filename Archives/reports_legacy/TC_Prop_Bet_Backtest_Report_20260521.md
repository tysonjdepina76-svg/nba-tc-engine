# TC Prop Bet Backtest Report

Date: 2026-05-21

## Important Roster Correction

You are right: live scrapes/APIs should not create imperfect historical roster replay. I corrected the backtest workflow rule:

- **Live projections** use live roster/stat/injury APIs.
- **Historical backtests** use the exact ESPN event boxscore/summary for the game ID being tested.
- That means starters, bench, DNPs, minutes, and actual stats are locked to the real game roster, not today’s roster page.

## Saved Market/Prop Backtests

| Test Set | Hits | Total | Hit Rate |
|---|---:|---:|---:|
| market-under props | 10 | 14 | 71.4% |
| TC target props | 40 | 56 | 71.4% |
| All compiled rows including diagnostic target set | 1157 | 1342 | 86.2% |

## Saved Prop Backtests by Game

| Game | Mode | Hits | Total | Hit Rate |
|---|---|---:|---:|---:|
| CLE@NYK ECF G1 | market-under props | 10 | 14 | 71.4% |
| SAS@OKC WCF G1 | TC target props | 21 | 28 | 75.0% |
| SAS@OKC WCF G2 | TC target props | 19 | 28 | 67.9% |

## Saved Prop Backtests by Stat

| Mode | Stat | Hits | Total | Hit Rate |
|---|---|---:|---:|---:|
| market-under props | AST | 1 | 1 | 100.0% |
| market-under props | PTS | 8 | 10 | 80.0% |
| market-under props | REB | 1 | 3 | 33.3% |
| TC target props | 3PM | 11 | 14 | 78.6% |
| TC target props | AST | 10 | 14 | 71.4% |
| TC target props | PTS | 10 | 14 | 71.4% |
| TC target props | REB | 9 | 14 | 64.3% |
| event-roster diagnostic target | 3PM | 210 | 212 | 99.1% |
| event-roster diagnostic target | AST | 141 | 212 | 66.5% |
| event-roster diagnostic target | BLK | 208 | 212 | 98.1% |
| event-roster diagnostic target | PTS | 171 | 212 | 80.7% |
| event-roster diagnostic target | REB | 168 | 212 | 79.2% |
| event-roster diagnostic target | STL | 209 | 212 | 98.6% |

## Event-Roster Diagnostic Backtest

I also created a reusable clean backtest runner: `tc_historical_prop_backtest.py`.

That runner pulls historical rosters from ESPN event summaries, not current roster pages. Current run:

- NBA: 684/798 = 85.7%
- WNBA: 423/474 = 89.2%
- Overall diagnostic target rate: 1107/1272 = 87.0%

## Files

- CSV: `/home/workspace/TC_Prop_Bet_Backtest_Compiled_20260521.csv`
- Event-roster runner: `/home/workspace/tc_historical_prop_backtest.py`
- Event-roster CSV: `/home/workspace/TC_Historical_Prop_Backtest_20260521.csv`
- Event-roster report: `/home/workspace/TC_Historical_Prop_Backtest_Report_20260521.md`

## Next Fix to Integrate in App/API

Add a historical mode endpoint to `/api/tc`, e.g. `/api/tc?event=401871160&sport=NBA&mode=historical`, so any backtest request is forced to exact event rosters and can never fall back to current rosters.
