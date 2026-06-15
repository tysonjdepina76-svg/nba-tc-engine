"""
NBA TC Engine v8.1 — FastAPI Server
Serves CLE @ DET Game 7 projections + all game endpoints
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

import sys, os
sys.path.insert(0, '/home/workspace')

from nba_tc_engine_v8 import (
    game_line, tc_starters, tc_starters_breakdown,
    starters, generate_props, analyze_prop,
    PLAYOFF_MULT, LINE_FACTOR, TC_W, INJ,
    TEAM_CITIES, BACKTEST_GAMES, TEAM_ROSTERS
)

app = FastAPI(title="NBA TC Engine v8.1", version="8.1")

# ── Pydantic models ──────────────────────────────────────────────────────────

class PlayerTC(BaseModel):
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str
    tier: int
    tc_pts: float
    tc_reb: float
    tc_ast: float
    tc_3pm: float

class GameProjection(BaseModel):
    matchup: str
    away: str
    home: str
    series: str
    game_time: str
    market_total: Optional[float]
    tc_line: float
    edge: float
    signal: str
    raw_combined: float
    tc_final: float
    away_tc: float
    home_tc: float
    cle_starters: List[PlayerTC]
    det_starters: List[PlayerTC]
    cle_bench: List[PlayerTC]
    det_bench: List[PlayerTC]
    formula: str

# ── Helpers ───────────────────────────────────────────────────────────────────

def player_tc(p) -> PlayerTC:
    """Convert raw P tuple to PlayerTC with TC calcs."""
    return PlayerTC(
        name=p.name, pos=p.pos, ht=p.ht,
        pts=p.pts, reb=p.reb, ast=p.ast, tpm=p.tpm,
        status=p.status, tier=p.tier,
        tc_pts=round(p.pts * TC_W['pts'], 1),
        tc_reb=round(p.reb * TC_W['reb'], 1),
        tc_ast=round(p.ast * TC_W['ast'], 1),
        tc_3pm=round(p.tpm * TC_W['3pm'], 1),
    )

def lineup_split(team_abbr: str):
    """Return (starters_list, bench_list) from TEAM_ROSTERS (top-5 starters, rest bench)."""
    all_players = TEAM_ROSTERS[team_abbr]
    starters_list = all_players[:5]
    bench_list = all_players[5:]
    return starters_list, bench_list

def build_game_proj(away: str, home: str,
                    market_total: Optional[float] = None,
                    series: str = "Playoffs",
                    game_time: str = "TBD") -> GameProjection:
    gl = game_line(away, home, market_total)
    away_starters, away_bench = lineup_split(away)
    home_starters, home_bench = lineup_split(home)

    return GameProjection(
        matchup=f"{TEAM_CITIES[away]} @ {TEAM_CITIES[home]}",
        away=away, home=home,
        series=series, game_time=game_time,
        market_total=market_total,
        tc_line=gl['tc_line'],
        edge=gl['edge'],
        signal=gl['signal'],
        raw_combined=gl.get('raw_combined', 0),
        tc_final=gl.get('tc_final', 0),
        away_tc=gl['away_tc'],
        home_tc=gl['home_tc'],
        cle_starters=[player_tc(p) for p in (away_starters if away == 'CLE' else home_starters)],
        det_starters=[player_tc(p) for p in (home_starters if home == 'DET' else away_starters)],
        cle_bench=[player_tc(p) for p in (away_bench if away == 'CLE' else home_bench)],
        det_bench=[player_tc(p) for p in (home_bench if home == 'DET' else away_bench)],
        formula=f"TC Line = (({gl['away_tc']} + {gl['home_tc']}) × {PLAYOFF_MULT}) × {LINE_FACTOR}",
    )

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "NBA TC Engine v8.1",
        "endpoints": [
            "GET /health",
            "GET /game/{away}@{home}?market_total=X",
            "GET /cle_det — CLE @ DET Game 7 full projection",
            "GET /props/{away}@{home}?stats=pts,reb,ast,3pm",
            "GET /backtest",
        ]
    }

@app.get("/health")
def health():
    return {"status": "ok", "version": "8.1", "model": "Triple Conservative"}

@app.get("/game/{away}@{home}")
def get_game(away: str, home: str, market_total: Optional[float] = None):
    """General game projection endpoint."""
    away = away.upper(); home = home.upper()
    return build_game_proj(away, home, market_total)

@app.get("/cle_det")
def cle_det_game7(market_total: Optional[float] = None):
    """
    CLE @ DET Game 7 full projection.
    Includes starters + bench for both rosters,
    TC breakdown per player, edge signal, and formula.
    """
    return build_game_proj("CLE", "DET", market_total, series="Playoffs Game 7", game_time="TBD")

@app.get("/props/{away}@{home}")
def get_props(away: str, home: str, stats: str = "pts"):
    """Generate player prop bets for a game."""
    away = away.upper(); home = home.upper()
    stat_filter = [s.strip() for s in stats.split(",")]
    props = generate_props(away, home, stat_filter=stat_filter)
    analyzed = [analyze_prop(p) for p in props]
    return {"matchup": f"{TEAM_CITIES[away]} @ {TEAM_CITIES[home]}", "props": analyzed}

@app.get("/backtest")
def get_backtest():
    from nba_tc_engine_v8 import run_backtest
    result = run_backtest()
    return result

if __name__ == "__main__":
    print("🏀 Starting NBA TC Engine v8.1 FastAPI server...")
    print("   Endpoints:")
    print("     GET /health          — health check")
    print("     GET /game/BOS@NYK?market_total=211  — general game")
    print("     GET /cle_det         — CLE @ DET Game 7 (this game)")
    print("     GET /props/CLE@DET   — prop bets")
    print("     GET /backtest        — backtest results")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8042, log_level="warning")