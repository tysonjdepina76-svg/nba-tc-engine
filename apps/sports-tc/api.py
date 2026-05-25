"""
Sports TC API — FastAPI Server v8.0
===================================
Endpoints for NBA + WNBA Triple Conservative projections.
Uses tc_engine.py v8 — includes both TC Match (player props) and v8 Game Total.

Run:  python api.py
Docs: http://localhost:PORT/docs

Service mode:
    uvicorn sports_tc.api:app --host 0.0.0.0 --port PORT
"""

import sys, os, json, math
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Use the clean v8 tc_engine
sys.path.insert(0, str(BASE_DIR))
from tc_pipeline_clean.tc_engine import (
    project_game, run_backtest, get_team, get_teams,
    NBA_TEAMS, WNBA_TEAMS,
    NBA_BACKTEST, WNBA_BACKTEST,
    Player, Team,
)

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("WARNING: fastapi not installed. Run: pip install fastapi uvicorn pydantic")

# ── App setup ──────────────────────────────────────────────────────
app = FastAPI(
    title="Sports TC v8",
    description="TC Match (player props) + v8 Game Total calibration. Both run independently.",
    version="8.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ── Pydantic models ────────────────────────────────────────────────
class GameRequest(BaseModel):
    home: str
    away: str
    market_total: float
    market_spread: float = 0.0
    series: str = ""
    game_time: str = "TBD"
    bankroll: float = 1000.0
    sport: str = "NBA"

class PlayerProj(BaseModel):
    name: str; pos: str; status: str
    pts: float; tc_pts: float; tc_reb: float; tc_ast: float; tc_3pm: float
    tc_prop_total: float; raw_points_for_total: float

class TeamProj(BaseModel):
    abbr: str; name: str
    players: list[PlayerProj]
    raw_points_total: float; raw_starters_points: float; raw_bench_points: float
    prop_tc_totals: dict; tc_starters_pts: float; bench_tc_pts: float
    injury_notes: list[str]

class GameTotalV8(BaseModel):
    home: dict; away: dict
    v8_combined: float; market_total: float
    gap_vs_market: float; lean: str
    model_type: str; note: str

class TCMatch(BaseModel):
    tc_combined_pts: float; tc_line_pts: float
    tc_edge: float; tc_signal: str
    prop_tc_totals: dict; rule: str

class GameProjResponse(BaseModel):
    meta: dict
    tc_match: TCMatch
    game_total_v8: GameTotalV8
    raw_points: dict; market_total: float
    total_gap_raw_vs_market: float; spread: dict
    players: dict; starters: dict; bench: dict
    injuries: dict; bets: dict

# ── Routes ─────────────────────────────────────────────────────────

@app.get("/", tags=["system"])
def root():
    return {
        "message": "Sports TC v8 — TC Match + v8 Game Total",
        "version": "8.0.0",
        "models": {
            "tc_match": "Player props: PTS/REB/AST/3PM via stat×CONS×factor+GAP",
            "game_total_v8": "Raw pts × star_mult + bench_diff + home_court (separate)",
        },
        "endpoints": ["/health", "/teams", "/backtest", "/project"],
    }

@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "version": "8.0.0",
        "tc_rule": "TC Match = player props only | v8 Game Total = separate calibration",
    }

@app.get("/teams", tags=["rosters"])
def list_teams(sport: str = "NBA"):
    return {abbr: t.name for abbr, t in get_teams(sport).items()}

@app.get("/backtest", tags=["backtest"])
def backtest(sport: str = "NBA"):
    return run_backtest(sport)

@app.post("/project", response_model=GameProjResponse, tags=["projections"])
def project(req: GameRequest):
    try:
        result = project_game(
            req.home, req.away, req.market_total, req.market_spread,
            req.series, req.game_time, req.bankroll, req.sport,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/explain/{sport}/{away_abbr}@{home_abbr}", tags=["explain"])
def explain(
    sport: str, away_abbr: str, home_abbr: str,
    market_total: Optional[float] = Query(None),
):
    """Human-readable explanation of TC Match + v8 Game Total for a game."""
    sport = sport.upper()
    try:
        result = project_game(
            home_abbr.upper(), away_abbr.upper(),
            market_total or 210.0, 0.0,
            series="explain", game_time="TBD",
            sport=sport,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    tc = result["tc_match"]
    v8 = result["game_total_v8"]

    lines = [
        f"SPORTS TC v8 — {away_abbr.upper()} @ {home_abbr.upper()} ({sport})",
        f"{'='*60}",
        f"TC MATCH (Player Props Only)",
        f"  Combined TC PTS: {tc['tc_combined_pts']:.1f}",
        f"  TC Line:         {tc['tc_line_pts']:.1f}",
        f"  TC Edge:         {tc['tc_edge']:+.1f} → {tc['tc_signal']}",
        f"  Rule: {tc['rule']}",
        f"",
        f"v8 GAME TOTAL (Separate from TC Match)",
        f"  {home_abbr.upper()} (home): {v8['home']['v8_total']:.1f}",
        f"    adjustments: {', '.join(v8['home']['adjustments']) or 'none'}",
        f"  {away_abbr.upper()} (away): {v8['away']['v8_total']:.1f}",
        f"    adjustments: {', '.join(v8['away']['adjustments']) or 'none'}",
        f"  Combined:      {v8['v8_combined']:.1f}",
        f"  Market Total:  {v8['market_total']:.1f}",
        f"  Gap:           {v8['gap_vs_market']:+.1f}",
        f"  Lean:          {v8['lean']}",
        f"  Note: {v8['note']}",
    ]
    return {"explanation": "\n".join(lines)}


# ── Run locally ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3456))
    print(f"Starting Sports TC v8 API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)