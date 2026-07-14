# Combo Types - Quick Reference

| Combo Type | Formula | Example |
|---|---|---|
| Parlay | All bets must win | NBA ML + NFL Spread |
| Teaser | Adjusted lines | NFL -6.5 becomes -0.5 |
| Pleaser | Adjusted lines (worse odds) | NFL -6.5 becomes -12.5 |
| Round Robin | Combinations of parlays | 3 picks → 3 two-team parlays |
| Same Game Parlay | Correlated bets | Player Over + Team ML |

## Install

```bash
pip install streamlit pandas numpy scikit-learn xgboost plotly redis aiohttp
```

## Secrets (.streamlit/secrets.toml)

```toml
ODDS_API_KEY = "your_api_key_here"
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
EDGE_THRESHOLD = 0.10
CONFIDENCE_MINIMUM = 0.60
KELLY_FRACTION = 0.25
```

## Run

```bash
streamlit run tc_app_complete.py
```
