# TC Betting Math — Full Reference

## Break-Even Win Rate (Vigorish Math)

| Bet Type | Wager | Win | Loss | Break-Even Win Rate |
|----------|-------|-----|------|---------------------|
| Standard (-110) | $110 | $100 profit | $110 loss | **52.38%** |

## Odds Conversion

| Expression | Formula | Example |
|------------|---------|---------|
| American → Decimal (positive) | 1 + (odds/100) | +165 → 2.65 |
| American → Decimal (negative) | 1 + (100/odds) | -190 → 1.526 |
| Decimal → Implied Probability | 1 ÷ decimal odds | 2.65 → 37.7% / 1.526 → 65.5% |
| The Vigorish | Sum of implied probabilities - 1 | 37.7% + 65.5% = 103.2% → 3.2% vig |

## Edge Calculation

```
Edge = Model_Predicted_Probability - Implied_Probability
```

A positive edge means the bet has value. To be profitable long-term, edge must exceed the bookmaker margin (vig).

## Bookmaker Margins by Market

| Market Type | Typical Total Percentage | Bookmaker Margin |
|-------------|--------------------------|------------------|
| 2-way outcomes (e.g., NBA) | ~108% | 8% |
| 3-way outcomes (e.g., Soccer) | ~112% | 12% |
| Exact scores | Up to 140-150% | 40-50% |

## Arbitrage Trigger

```
1/odds_A + 1/odds_B < 1
```

If this is true across books, a guaranteed arb exists.

## TC Math vs Truth Performance

| Metric | TC Math | Truth Performance |
|--------|---------|-------------------|
| Accuracy | Must beat 52.38% | 88% classification |
| Calibration | Must match reality | Good alignment |
| Statistical Significance | p < 0.05 | ✅ p < 0.0017 |

## Key Takeaway

- The 52.38% break-even is the floor — anything below loses money
- TC's 88% binary classifier crushes it
- Edge = Model Prob − Implied Prob. If positive, bet. If negative, pass
- 3-way markets (soccer) have higher vig (12%) — need bigger edge to profit
- Arbitrage opportunities are rare but risk-free when they appear
