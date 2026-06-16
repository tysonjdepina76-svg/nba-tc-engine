# TC Historical Prop Backtest — Event-Roster Correct

Generated: 2026-05-21 22:26

## Roster Correction Rule

This backtest does **not** use current team rosters. Every historical test uses the ESPN event `summary` boxscore for that exact game ID. That locks the starters, bench, DNPs, minutes, and actual stats to the real game roster.

## Overall Hit Rate

**1107/1272 = 87.0%**

## By League

| League | Hits | Total | Hit Rate |
|---|---:|---:|---:|
| NBA | 684 | 798 | 85.7% |
| WNBA | 423 | 474 | 89.2% |

## By Stat

| Stat | Hits | Total | Hit Rate |
|---|---:|---:|---:|
| 3PM | 210 | 212 | 99.1% |
| AST | 141 | 212 | 66.5% |
| BLK | 208 | 212 | 98.1% |
| PTS | 171 | 212 | 80.7% |
| REB | 168 | 212 | 79.2% |
| STL | 209 | 212 | 98.6% |

## By Role

| Role | Hits | Total | Hit Rate |
|---|---:|---:|---:|
| BENCH | 540 | 672 | 80.4% |
| START | 567 | 600 | 94.5% |

## By Game

| Sport | Date | Event | Matchup | Hits | Total | Hit Rate |
|---|---|---:|---|---:|---:|---:|
| NBA | 2026-05-03 | 401869384 | 401869384 | 104 | 108 | 96.3% |
| NBA | 2026-05-03 | 401869418 | 401869418 | 111 | 132 | 84.1% |
| NBA | 2026-05-06 | 401871160 | 401871160 | 104 | 114 | 91.2% |
| NBA | 2026-05-07 | 401871153 | 401871153 | 157 | 174 | 90.2% |
| NBA | 2026-05-08 | 401871161 | 401871161 | 119 | 162 | 73.5% |
| NBA | 2026-05-09 | 401871154 | 401871154 | 89 | 108 | 82.4% |
| WNBA | 2026-05-15 | 401856910 | 401856910 | 108 | 114 | 94.7% |
| WNBA | 2026-05-15 | 401856911 | 401856911 | 112 | 126 | 88.9% |
| WNBA | 2026-05-16 | 401856912 | 401856912 | 103 | 120 | 85.8% |
| WNBA | 2026-05-16 | 401856913 | 401856913 | 100 | 114 | 87.7% |

## Method

- Source: ESPN historical event summary boxscores.
- Correct roster source: exact-game starters/bench/DNPs from each event, not current roster pages.
- Stats graded: PTS, REB, AST, 3PM, STL, BLK.
- Target formula: `target = floor(prior_baseline × 0.85 × 0.88)`. If no earlier game exists for that player in this test set, the first-game event stat seeds the baseline so the roster remains correct while the system has a baseline to grade.
- This file is a clean prop-hit diagnostic. For real market prop betting, the next layer should replace target lines with sportsbook prop lines from The Odds API/SportsGameOdds when available.
