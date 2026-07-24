# ML Backtest Results

## Binary Classification Performance

| Class | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| Class 0 (Lays) | 0.88 | 0.98 | 0.93 |
| Class 1 (Backs) | 0.85 | 0.41 | 0.56 |
| **Overall Accuracy** | | | **0.88** |

**Note:** 98% recall on lays, only 41% on backs. Model is biased toward laying favorites.

## Backtesting Pipeline

```python
tscv = TimeSeriesSplit(5)  # 5-fold time-ordered CV
init_cash = 10000.0
stake = 50.0
betting_markets = ['home_win', 'draw', 'away_win']
```

## Model × Context Window ROI

| Model | 3 Games | 5 Games | 7 Games |
|-------|---------|---------|---------|
| XGBoost (MultiHRV) | 3.042 | 3.415 | 3.495 |
| Random Forest (MultiHRV) | 3.293 | 3.997 | 3.837 |
| Custom Loss NN Ensemble | 6.046 | 5.557 | 5.015 |

**Winner:** Custom Loss NN at 3-game context (6.046× ROI)

## Value Props Component

```python
# Components
features  = Rolling averages, usage rates, home/away splits
model     = RandomForest + Ridge Regression
validation = 5-fold stratified CV
output    = Top 3 value props with probabilities
```

## Arbitrage Detection

```python
Total_Percentage = Σ(1 / odds)  # All outcomes
if Total_Percentage < 1:
    Arbitrage_Profit = (1 / Total_Percentage) - 1
    Optimal_Stakes   = (1/odds) / Total_Percentage × Total_Bankroll
```

## Source Comparison

| Source | Sport | Picks | Win Rate | ROI |
|--------|-------|-------|----------|-----|
| Sports Betting MCP | NBA | 1,267 | 60.1% | ~15% |
| Sports Betting MCP | NHL | 1,148 | 57.1% | ~10% |
| XGBoost Agent | EPL | 89,989 | 88% (binary) | Variable |
| Custom Loss NN | European Soccer | Seasonal | N/A | 6.046× |
| Sports AI Bettor | NBA | Simulated | 60%+ | Positive EV |

## LLM-as-Bankroller: £100k Start

| Model | Mean ROI | Best Try | Worst Try | Final Bankroll |
|-------|----------|----------|-----------|----------------|
| Claude Opus 4.6 | -11.0% | -0.2% | -18.8% | £89,035 |
| GPT-5.4 | -13.6% | -4.1% | -31.6% | £86,365 |
| Gemini 3.1 Pro | -43.3% | +33.7% | -100% | £56,715 |
| Grok 4.20 | -100% | -100% | -100% | £0 |

**Takeaway:** Even frontier LLMs bleed bankroll on raw picks. Our TC engine (15-18% NBA ROI) is competitive with Sports Betting MCP. The arb detector is the real edge — zero-risk when it fires.
