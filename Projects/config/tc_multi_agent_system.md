# Multi-Agent Betting System

12 specialized AI agents analyze each bet. Consensus + confidence scoring.

## Agent Roster

| # | Agent | Specialization | Data Input |
|---|-------|----------------|------------|
| 1-2 | Momentum Analysts | Recent performance | Win/loss streaks, last 5/10 games |
| 3-4 | Matchup Specialists | Head-to-head | Style comparisons, historical H2H |
| 5-6 | Injury Experts | Availability | Player status, impact ratings |
| 7 | Rest & Travel Analyst | Fatigue | Back-to-back effects, travel distance |
| 8 | Public Betting Analyst | Market sentiment | Betting percentages |
| 9 | Sharp Money Analyst | Line movement | Early vs late money tracking |
| 10 | Historical Trends | Long-term patterns | Seasonal statistical patterns |
| 11 | Statistical Modeler | Advanced metrics | eFG%, pace, net rating, Four Factors |
| 12 | Contextual Analyst | Game context | Weather, motivation, playoff implications |

## Scoring Formulas

### Consensus Score
```
Consensus = (Σ Agent_Weight × Vote_Alignment) / Total_Weight
```

### Confidence Score
```
Confidence = Consensus × (1 - Variance_Among_Agents)
```

### Edge Calculation
```
Edge = Model_Probability - Implied_Probability
Implied_Probability = 1 / Decimal_Odds
```

### Performance Metrics
```
ROI = (Profit - Investment) / Investment + 1
σ   = sqrt(ROI × (Avg_Odds - ROI))
t   = sqrt(n) × (ROI - 1) / σ
```

## Model Calibration Reality Check

| Model | Calibration Error | Result |
|-------|-------------------|--------|
| Claude Opus 4.6 | Overconfident | -11% ROI |
| GPT-5.4 | Overconfident | -13.6% ROI |
| Grok 4.20 | 100% overconfident | Bankrupt |

**Lesson:** Raw model probability needs calibration before sizing. Apply Platt scaling or isotonic regression on historical output. Use edge as a relative ranking tool, not a direct probability.
