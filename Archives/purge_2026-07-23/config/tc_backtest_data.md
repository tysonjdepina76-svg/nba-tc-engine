# TC Backtest Data — Reference Numbers (from user's transcripts)

## 12-Agent Picks by Sport
| Sport | Picks | Wins | Win Rate |
|------|------:|-----:|---------:|
| NBA  | 1,267 | 762  | 60.1%    |
| NHL  | 1,148 | 656  | 57.1%    |
| NCAAB| 1,149 | 549  | 47.8%    |
| MLB  |   283 | 109  | 38.5%    |
| **Total** | **3,859** | **2,076** | **53.8%** |

- Platform users: 30
- Bet types: Moneyline, Spread, Totals
- Pick source: 12-agent consensus model

## ML Model Performance (NBA 20 seasons 2003-2023)
- Best Accuracy: 64.1%
- F1 Score: 72.4%
- Algorithms: Logistic Regression, Random Forest, Gradient Boosting
- Feature selection: LASSO, decision tree-based

## CLV Backtest (25 months)
- Return: +216.45% on initial bankroll
- Bets placed: 313,450
- Commission: 2%
- Target: predict odds movement vs. closing odds

## RF Validation
- 5-fold stratified CV
- Test accuracy ~60%+
- Features: rolling averages, usage rates, home/away splits
- Explainability: SHAP

## Sample Player Projections (RF model)
| Player | Stat | Line | Projection | RF_Prob | Pick |
|--------|------|-----:|-----------:|--------:|------|
| J. Embiid | Points | 25.5 | 28.3 | 0.78 | Over |
| S. Curry  | PRA    | 38.5 | 41.9 | 0.74 | Over |
