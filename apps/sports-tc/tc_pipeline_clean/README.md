# TC Pipeline Clean

Clean reusable Sports TC pipeline.

## Critical rule
TC match applies only to individual player props:
- Points
- Rebounds
- Assists
- 3PT shots made

Game/team totals are raw-point context only. Do not apply TC prop math to totals.

## Files
- `tc_engine.py` — single source of truth for NBA/WNBA prop projections and API.
- `nba_tc_streamlit.py` — Streamlit app for full roster 4-stat projections.

## Run
```bash
python tc_engine.py --sport WNBA --game "GS @ NY"
python tc_engine.py --sport NBA --game "SA @ OKC"
uvicorn tc_engine:app --host 0.0.0.0 --port 8001
streamlit run nba_tc_streamlit.py --server.port 8503
```
