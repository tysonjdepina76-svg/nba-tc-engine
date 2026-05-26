#!/usr/bin/env python3
"""
Sports TC API — FastAPI wrapper for sports_tc.py
Run: uvicorn sports_tc_api:app --port 8099 --host 0.0.0.0
"""
import sys
sys.path.insert(0, "/home/workspace")
from sports_tc.sports_tc import Game, BACKTEST_SUITE, NBA_TEAMS, WNBA_TEAMS

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Sports TC API", version="4.0",
              description="Triple Conservative betting engine — NBA & WNBA")

# ── Constants (mirrored from sports_tc) ───────────────────────
CONS = 0.85; Q_MULT = 0.65; LINE_FACT = 0.88
VAR_LOW = 0.76; VAR_HIGH = 0.82; PACE_ADJ = 8.0
MIN_EDGE = 3.0; KELLY_FRAC = 0.25; MIN_KELLY = 0.01

# ── Request model ─────────────────────────────────────────────
class GameQuery(BaseModel):
    away: str; home: str; sport: str = "NBA"
    market_total: Optional[float] = None
    market_spread: Optional[float] = None
    bankroll: float = 1000

# ── Helpers ────────────────────────────────────────────────────
def compute_game(q: GameQuery) -> dict:
    """Compute all TC values for a game query."""
    g = Game(q.away, q.home, sport=q.sport,
             market_total=q.market_total,
             market_spread=q.market_spread,
             bankroll=q.bankroll)

    away_tc = g.away.totals()["TC_PTS"]
    home_tc = g.home.totals()["TC_PTS"]
    raw = round(away_tc + home_tc, 1)

    # TC Final
    if q.market_spread is not None:
        factor = VAR_HIGH if abs(q.market_spread) >= 8 else VAR_LOW
        final = round(raw * factor, 1)
    else:
        factor = None
        final = round(raw + PACE_ADJ, 1)

    # TC Line
    line = round(final * LINE_FACT, 1)

    # Edge vs market
    edge = round(line - (q.market_total or 0), 1)
    signal = "UNDER" if edge > 0 else "OVER"

    # Kelly
    kelly_frac = 0.0
    if edge > 0 and q.market_total:
        odds = 110
        implied = odds / 100.0
        kelly_frac = round(KELLY_FRAC * abs(edge) / (implied - 1), 4)
        kelly_frac = max(kelly_frac, MIN_KELLY if abs(edge) >= MIN_EDGE else 0)

    kelly_amt = round(kelly_frac * q.bankroll, 2)

    # Backtest hit (if actual_total provided via market_total comparison)
    hit = None
    if q.market_total and hasattr(g, 'actual_total'):
        hit = (edge > 0 and g.actual_total < q.market_total) or \
              (edge < 0 and g.actual_total > q.market_total)

    return {
        "away_code": q.away, "home_code": q.home, "sport": q.sport,
        "away_tc_pts": round(away_tc, 1), "home_tc_pts": round(home_tc, 1),
        "raw_combined": raw,
        "factor": factor, "tc_final": final, "tc_line": line,
        "market_total": q.market_total, "market_spread": q.market_spread,
        "edge": edge, "signal": signal,
        "kelly_frac": kelly_frac, "kelly_stake": kelly_amt,
        "suggested_bet": f"{signal} {q.market_total or 'TOTAL'} (TC Line: {line})",
        "hit": hit
    }

# ── Routes ───────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "msg": "Sports TC API v4.0",
        "docs": "/docs",
        "endpoints": ["/health", "/projections", "/backtest", "/teams/{sport}"]
    }

@app.get("/health")
async def health():
    return {
        "status": "ok", "version": "4.0",
        "formula": {
            "CONS": CONS, "Q_MULT": Q_MULT, "LINE_FACT": LINE_FACT,
            "VAR_LOW": VAR_LOW, "VAR_HIGH": VAR_HIGH, "PACE_ADJ": PACE_ADJ,
            "MIN_EDGE": MIN_EDGE, "KELLY_FRAC": KELLY_FRAC
        },
        "sports": ["NBA", "WNBA"],
        "signal_logic": "edge > 0 → UNDER | edge < 0 → OVER"
    }

@app.post("/projections")
async def projections(q: GameQuery):
    try:
        return JSONResponse(content=compute_game(q))
    except KeyError as e:
        raise HTTPException(400, f"Unknown team: {e}. Use /teams/NBA to list codes.")

@app.get("/backtest")
async def backtest(sport: str = "NBA"):
    suite = [g for g in BACKTEST_SUITE if len(g) > 2 and g[2] == sport]
    if not suite:
        raise HTTPException(400, f"No backtest data for sport={sport}")

    results = []
    for game in suite:
        try:
            away, home, _, actual, market = game
            gq = GameQuery(away=away, home=home, sport=sport, market_total=market)
            result = compute_game(gq)
            result["actual_total"] = actual
            result["hit"] = (result["edge"] > 0 and actual < market) or \
                            (result["edge"] < 0 and actual > market)
            results.append(result)
        except Exception as e:
            results.append({"away": game[0], "home": game[1], "error": str(e)})

    hits = sum(1 for r in results if r.get("hit") in [True])
    total = len(results)
    rate = f"{hits}/{total} ({100*hits//total}%)" if total else "0/0"

    return {"sport": sport, "games": total, "hits": hits, "rate": rate, "results": results}

@app.get("/teams/{sport}")
async def teams(sport: str):
    if sport == "NBA":
        return {"sport": "NBA", "count": len(NBA_TEAMS), "teams": NBA_TEAMS}
    elif sport == "WNBA":
        return {"sport": "WNBA", "count": len(WNBA_TEAMS), "teams": WNBA_TEAMS}
    raise HTTPException(400, "Use sport=NBA or WNBA")

@app.get("/report/{away}/{home}")
async def report(away: str, home: str, sport: str = "NBA",
                 market_total: float = None, market_spread: float = None):
    try:
        q = GameQuery(away=away, home=home, sport=sport,
                       market_total=market_total, market_spread=market_spread)
        return JSONResponse(content=compute_game(q))
    except KeyError as e:
        raise HTTPException(400, f"Unknown team: {e}")

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8099)