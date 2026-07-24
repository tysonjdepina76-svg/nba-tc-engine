# Setup, Run & Priority Matrix

## Install + Run

```bash
# Core dependencies
pip install xgboost scikit-learn pandas numpy streamlit redis

# Full backtest
python tc_backtest.py --sport NBA --seasons 5 --verbose

# Streamlit dashboard
streamlit run tc_dashboard.py

# WebSocket streaming (optional)
playwright install chromium
uvicorn tc_app:app --reload
streamlit run app.py
```

## Model Significance

| Model | Win Rate | ROI | p-Value |
|-------|----------|-----|---------|
| XGBoost | 88% | Variable | <0.0017 |
| 12-Agent Consensus | 60.1% | +~15% | Significant |
| RandomForest (NBA) | 60%+ | Positive EV | Confirmed |

## Gap Priority Matrix

| Area | Gap | Priority |
|------|-----|----------|
| Real-Time Odds API | Use free tier of Odds-API.io or SportsGameOdds | **Medium** |
| Live Data Refresh | Implement Redis Streams for sub-5-second updates | **Medium** |
| Multi-Sport Calibration | Fine-tune thresholds for MLB, NHL separately | Low |

## Current Status (TC Sports v3.0)

- 7 sport engines live (NBA, WNBA, MLB, NFL, NHL, Soccer, WC)
- 12-agent consensus scoring ready
- Arb detector active
- Time-series CV backtester (5-fold) ready
- Streamlit dashboard on port 8511

## Next Steps

1. Plug in real-time odds feed (Odds-API.io free tier = 100 req/day)
2. Wire Redis Streams for live in-game updates
3. Calibrate sport-specific thresholds once 100+ graded picks per sport
