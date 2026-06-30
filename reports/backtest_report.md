# Multi-Sport Backtest Report — 2026-06-30

## Overall (all sports)

- Picks evaluated: 311
- Graded: 199
- Hit rate: 13.6%
- Avg edge: 0.85
- ROI (at -110): -87.5%
- Profit (on $19900 wagered): $-17418.43

## By Sport

| Sport | Picks | Graded | HIT | MISS | PUSH | Hit Rate | Avg Edge | ROI | Profit |
|---|---|---|---|---|---|---|---|---|---|
| WNBA | 45 | 33 | 21 | 12 | 0 | 63.6% | 1.08 | -41.5% | $-1369.89 |
| SOCCER | 180 | 166 | 6 | 160 | 14 | 3.6% | n/a | -96.7% | $-16048.54 |
| MLB | 86 | 0 | 0 | 0 | 0 | n/a | 0.73 | n/a | $0.0 |
| ALL | 311 | 199 | 27 | 172 | 14 | 13.6% | 0.85 | -87.5% | $-17418.43 |

## Source Coverage

| Source | Picks | Graded | Hit Rate |
|---|---|---|---|
| WNBA — 2026-06-13 (39 graded) | 45 | 33 | 63.6% |
| World Cup — 2026-06-15 (180 graded) | 180 | 166 | 3.6% |
| MLB SF@ATL — 2026-06-18 (39 picks, all PENDING) | 86 | 0 | n/a |

## Methodology

- ROI assumes -110 odds: HIT pays +$91.91, MISS loses $100, PUSH returns stake
- Hit rate = HIT / (HIT + MISS); PUSH and ungraded picks excluded
- Avg edge = mean of `edge` columns from source CSVs (TC projection minus market line)

## Limitations

- Only WNBA 6/13 + World Cup 6/15 + MLB SF@ATL have actuals. NBA/MOST MLB picks lack boxscore coverage.
- WNBA result column uses H/M/P (not HIT/MISS); PUSH discarded from hit-rate calc.
- World Cup 3.6% hit rate likely reflects wrong `direction` field (column overloaded); recheck before betting.
- ROI assumes flat $100/pick with no line-shopping or limit awareness.
