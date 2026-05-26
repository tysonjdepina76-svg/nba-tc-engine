# TC Backtest Hit Rate Report — Current Live API

Date: 2026-05-21

Backtest method: current `https://true.zo.space/api/tc` live roster/stat workflow was run against stored NBA and WNBA backtest fixtures with known market totals and actual final totals.

## Summary

| League | Games | Settled | Wins | Losses | Pushes | Hit Rate |
|---|---:|---:|---:|---:|---:|---:|
| NBA | 9 | 9 | 5 | 4 | 0 | 55.6% |
| WNBA | 11 | 11 | 6 | 5 | 0 | 54.5% |
| TOTAL | 20 | 20 | 11 | 9 | 0 | 55.0% |

## NBA Game-by-Game

| Date | Game | Market | Actual | TC Combined | Edge | Signal | Result |
|---|---|---:|---:|---:|---:|---|---|
| May 3, 2026 | ORL@DET R1 G7 | 208.5 | 210 | 237.0 | -32.0 | UNDER | LOSS |
| May 3, 2026 | BOS@PHI R1 G7 | 215.5 | 209 | 248.3 | -30.7 | UNDER | WIN |
| May 3, 2026 | CLE@TOR R1 G7 | 218.5 | 245 | 246.3 | -37.7 | UNDER | LOSS |
| May 3, 2026 | HOU@LAL R1 G7 | 218.0 | 190 | 224.4 | -79.6 | UNDER | WIN |
| May 2, 2026 | MIN@DEN R1 G7 | 222.5 | 208 | 253.1 | -39.9 | UNDER | WIN |
| May 6, 2026 | NYK@PHI S1 G1 | 213.5 | 210 | 287.8 | -11.2 | UNDER | WIN |
| May 6, 2026 | SAS@MIN S1 G1 | 215.5 | 228 | 262.9 | -32.1 | UNDER | LOSS |
| May 8, 2026 | CLE@DET S1 G3 | 211.5 | 204 | 279.5 | -11.5 | UNDER | WIN |
| May 8, 2026 | LAL@OKC S1 G3 | 210.5 | 226 | 255.1 | -41.9 | UNDER | LOSS |

## WNBA Game-by-Game

| Date | Game | Market | Actual | TC Combined | Edge | Signal | Result |
|---|---|---:|---:|---:|---:|---|---|
| 2025-10-10 | LV@NY FINALS G1 | 160.5 | 161 | 173.4 | -56.6 | UNDER | LOSS |
| 2025-10-12 | LV@NY FINALS G2 | 158.5 | 157 | 173.4 | -56.6 | UNDER | WIN |
| 2025-10-15 | NY@LV FINALS G3 | 163.5 | 161 | 173.4 | -56.6 | UNDER | WIN |
| 2025-10-17 | NY@LV FINALS G4 | 172.5 | 176 | 173.4 | -56.6 | UNDER | LOSS |
| 2025-10-20 | LV@NY FINALS G5 | 169.5 | 170 | 173.4 | -56.6 | UNDER | LOSS |
| 2025-10-23 | NY@LV FINALS G6 | 164.5 | 163 | 173.4 | -56.6 | UNDER | WIN |
| 2024-10-10 | NY@LV FINALS G1 | 170.5 | 179 | 173.4 | -56.6 | UNDER | LOSS |
| 2024-10-13 | NY@LV FINALS G2 | 162.5 | 162 | 173.4 | -56.6 | UNDER | WIN |
| 2024-10-16 | LV@NY FINALS G3 | 171.5 | 173 | 173.4 | -56.6 | UNDER | LOSS |
| 2024-10-20 | LV@NY FINALS G4 | 157.5 | 157 | 173.4 | -56.6 | UNDER | WIN |
| 2024-10-24 | NY@LV FINALS G5 | 155.5 | 154 | 173.4 | -56.6 | UNDER | WIN |

## Read This Before Using the Number

- This is a current-roster/API backtest, not a perfect historical roster replay.
- ESPN live roster data is used now, so old WNBA Finals rows and past NBA playoff rows can be affected by roster changes.
- Treat this as a system-health hit-rate check after the live API cleanup, not as a final betting model grade.
