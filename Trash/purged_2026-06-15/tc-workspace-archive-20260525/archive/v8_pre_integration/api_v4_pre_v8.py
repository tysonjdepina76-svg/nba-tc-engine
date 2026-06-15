"""
Sports TC API — FastAPI Server
==============================
Endpoints for NBA + WNBA Triple Conservative projections.

Run:  python sports_tc/api.py
Docs: http://localhost:PORT/docs

Service mode (production):
    uvicorn sports_tc.api:app --host 0.0.0.0 --port PORT
"""

import sys, os, json, math
from datetime import datetime
from typing import Optional

# Ensure sports_tc package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("WARNING: fastapi not installed. Run: pip install fastapi uvicorn pydantic")

# ── Import core TC engine ──────────────────────────────────────────
from sports_tc.master_tc import (
    Game, CONS, Q_MULT, OUT_Z, LINE_FACTOR, MIN_EDGE,
    NBA_ROSTERS, WNBA_ROSTERS,
    NBA_BACKTEST, WNBA_BACKTEST,
    Player, Team,
)

# ── App setup ──────────────────────────────────────────────────────
app = FastAPI(
    title="Sports TC API",
    description="Triple Conservative NBA + WNBA betting projections",
    version="4.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ── Pydantic models ────────────────────────────────────────────────
class PlayerProj(BaseModel):
    name: str
    pos: str
    status: str
    pts: float
    tc_pts: float
    tc_reb: float
    tc_ast: float
    tc_3pm: float
    tc_total: float

class TeamProj(BaseModel):
    abbr: str
    name: str
    starters: list[PlayerProj]
    bench: list[PlayerProj]
    starters_totals: dict
    bench_totals: dict
    team_totals: dict
    injuries: list[str]

class GameProj(BaseModel):
    sport: str
    away_abbr: str
    home_abbr: str
    timestamp: str
    away: TeamProj
    home: TeamProj
    tc_combined: float
    tc_line: float
    edge: float
    signal: str
    market_total: Optional[float] = None
    market_diff: Optional[float] = None
    backtest_note: Optional[str] = None

class BacktestEntry(BaseModel):
    game: str
    date: str
    round: str
    tc: float
    line: float
    actual: int
    edge: float
    diff: float
    result: str
    hit: bool

class BacktestResult(BaseModel):
    sport: str
    games: list[BacktestEntry]
    hit_rate: float
    avg_diff: float
    avg_edge: float
    description: str

class RostersResponse(BaseModel):
    sport: str
    teams: dict[str, dict]

class SlateGame(BaseModel):
    away_abbr: str
    home_abbr: str
    tc_combined: float
    tc_line: float
    edge: float
    signal: str
    away_players: int
    home_players: int

class SlateResponse(BaseModel):
    sport: str
    timestamp: str
    games: list[SlateGame]

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# ── Helpers ────────────────────────────────────────────────────────
def player_to_model(p: Player) -> PlayerProj:
    proj = p.proj()
    return PlayerProj(
        name=p.name, pos=p.pos, status=p.status,
        pts=p.pts,
        tc_pts=proj["TC_PTS"],
        tc_reb=proj["TC_REB"],
        tc_ast=proj["TC_AST"],
        tc_3pm=proj["TC_3PM"],
        tc_total=p.tc_total(),
    )

def team_to_model(team: Team) -> TeamProj:
    starters = [player_to_model(p) for p in team.starters()]
    bench = [player_to_model(p) for p in team.bench()]
    injuries = [
        f"{p.name} ({p.status})"
        for p in team.players if p.status != "ACTIVE"
    ]
    return TeamProj(
        abbr=team.abbr, name=team.name,
        starters=starters, bench=bench,
        starters_totals=team.starters_totals(),
        bench_totals=team.bench_totals(),
        team_totals=team.team_totals_all(),
        injuries=injuries,
    )

# ── Routes ─────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        version="4.0.0",
    )

@app.get("/game/{sport}/{away_abbr}@{home_abbr}", response_model=GameProj, tags=["projections"])
def get_game_proj(
    sport: str,
    away_abbr: str,
    home_abbr: str,
    market_total: Optional[float] = Query(None, description="Market total line"),
):
    sport = sport.upper()
    if sport not in ("NBA", "WNBA"):
        raise HTTPException(400, f"Unknown sport: {sport}. Use NBA or WNBA.")
    try:
        g = Game(away_abbr.upper(), home_abbr.upper(), sport)
    except Exception:
        raise HTTPException(404, f"Teams not found: {away_abbr} or {home_abbr}")

    at = g.away.team_totals_all()
    ht = g.home.team_totals_all()
    tc_combined = round(at["TC_TOTAL"] + ht["TC_TOTAL"], 1)
    tc_line = round(tc_combined * LINE_FACTOR)
    edge = round(tc_combined - tc_line, 1)
    signal = "OVER" if edge > MIN_EDGE else ("UNDER" if edge < -MIN_EDGE else "NO EDGE")

    market_diff = None
    if market_total is not None:
        market_diff = round(tc_combined - market_total, 1)

    return GameProj(
        sport=sport,
        away_abbr=g.away_abbr,
        home_abbr=g.home_abbr,
        timestamp=datetime.utcnow().isoformat(),
        away=team_to_model(g.away),
        home=team_to_model(g.home),
        tc_combined=tc_combined,
        tc_line=tc_line,
        edge=edge,
        signal=signal,
        market_total=market_total,
        market_diff=market_diff,
        backtest_note="TC uses conservative point estimates. Compare TC_combined vs actual totals.",
    )

@app.get("/backtest/{sport}", response_model=BacktestResult, tags=["backtest"])
def get_backtest(sport: str):
    sport = sport.upper()
    if sport not in ("NBA", "WNBA"):
        raise HTTPException(400, f"Unknown sport: {sport}")

    suite = NBA_BACKTEST if sport == "NBA" else WNBA_BACKTEST
    roster = NBA_ROSTERS if sport == "NBA" else WNBA_ROSTERS

    entries = []
    total_diff = 0.0
    total_edge = 0.0

    for g in suite:
        away_p = roster.get(g["away"], [])
        home_p = roster.get(g["home"], [])
        ta = sum(p.tc(p.pts) for p in away_p if p.status != "OUT")
        th = sum(p.tc(p.pts) for p in home_p if p.status != "OUT")
        tc = round(ta + th, 1)
        line = round(tc * LINE_FACTOR)
        actual = g["actual_combined"]
        diff = round(tc - actual, 1)
        edge = round(tc - line, 1)
        result = "OVER" if diff > 0 else "UNDER"
        hit = (result == "OVER" and actual > tc) or (result == "UNDER" and actual < tc)
        total_diff += diff
        total_edge += edge
        entries.append(BacktestEntry(
            game=f"{g['away']}@{g['home']}", date=g["date"],
            round=g["round"], tc=tc, line=line, actual=actual,
            edge=edge, diff=diff, result=result, hit=hit,
        ))

    n = len(entries)
    return BacktestResult(
        sport=sport,
        games=entries,
        hit_rate=sum(e.hit for e in entries) / n,
        avg_diff=round(total_diff / n, 1),
        avg_edge=round(total_edge / n, 1),
        description=(
            f"TC = stat×{CONS} | Q={Q_MULT} | LINE=TC×{LINE_FACTOR}. "
            f"NOTE: 0% hit rate indicates systematic bias — actual totals run "
            f"{abs(total_diff/n):.1f} pts {'above' if total_diff < 0 else 'below'} TC. "
            "Recalibrate CONS factor or use raw TC_combined vs market total directly."
        ),
    )

@app.get("/rosters/{sport}", response_model=RostersResponse, tags=["rosters"])
def get_rosters(sport: str):
    sport = sport.upper()
    if sport not in ("NBA", "WNBA"):
        raise HTTPException(400, f"Unknown sport: {sport}")
    roster = NBA_ROSTERS if sport == "NBA" else WNBA_ROSTERS
    teams = {}
    for code, players in roster.items():
        teams[code] = {
            "active":   [p.name for p in players if p.status == "ACTIVE"],
            "questionable": [p.name for p in players if p.status == "Q"],
            "out":      [p.name for p in players if p.status == "OUT"],
        }
    return RostersResponse(sport=sport, teams=teams)

@app.get("/slate/{sport}", response_model=SlateResponse, tags=["slate"])
def get_slate(sport: str):
    sport = sport.upper()
    if sport not in ("NBA", "WNBA"):
        raise HTTPException(400, f"Unknown sport: {sport}")

    # Pre-configured matchups per sport
    NBA_SLATE = [
        ("PHI","NYK"), ("BOS","CLE"), ("OKC","MIN"),
        ("DEN","LAC"), ("DET","CHI"), ("LAL","GSW"),
        ("ORL","IND"), ("MIA","ATL"), ("MIL","TOR"),
        ("DAL","PHX"), ("HOU","SAC"), ("SAS","NOP"),
    ]
    WNBA_SLATE = [
        ("NYL","MIN"), ("LVA","IND"), ("CON","CHI"),
        ("SEA","ATL"), ("DAL","PHX"), ("LAS","POR"),
    ]

    matchups = NBA_SLATE if sport == "NBA" else WNBA_SLATE
    games = []
    for away, home in matchups:
        try:
            g = Game(away, home, sport)
        except Exception:
            continue
        at = g.away.team_totals_all()
        ht = g.home.team_totals_all()
        tc_combined = round(at["TC_TOTAL"] + ht["TC_TOTAL"], 1)
        tc_line = round(tc_combined * LINE_FACTOR)
        edge = round(tc_combined - tc_line, 1)
        signal = "OVER" if edge > MIN_EDGE else ("UNDER" if edge < -MIN_EDGE else "NO EDGE")
        active_a = sum(1 for p in g.away.players if p.status != "OUT")
        active_h = sum(1 for p in g.home.players if p.status != "OUT")
        games.append(SlateGame(
            away_abbr=away, home_abbr=home,
            tc_combined=tc_combined, tc_line=tc_line,
            edge=edge, signal=signal,
            away_players=active_a, home_players=active_h,
        ))

    return SlateResponse(
        sport=sport,
        timestamp=datetime.utcnow().isoformat(),
        games=games,
    )

@app.get("/explain/{sport}/{away_abbr}@{home_abbr}", tags=["explain"])
def explain_game(
    sport: str,
    away_abbr: str,
    home_abbr: str,
    market_total: Optional[float] = Query(None),
):
    """Human-readable text explanation of a game's TC projection."""
    sport = sport.upper()
    try:
        g = Game(away_abbr.upper(), home_abbr.upper(), sport)
    except Exception:
        raise HTTPException(404, "Teams not found")

    at = g.away.team_totals_all()
    ht = g.home.team_totals_all()
    tc_combined = round(at["TC_TOTAL"] + ht["TC_TOTAL"], 1)
    tc_line = round(tc_combined * LINE_FACTOR)
    edge = round(tc_combined - tc_line, 1)
    signal = "OVER" if edge > MIN_EDGE else ("UNDER" if edge < -MIN_EDGE else "NO EDGE")

    lines = [
        f"TC PROJECTION — {away_abbr.upper()} @ {home_abbr.upper()} ({sport})",
        f"=" * 56,
        f"  {away_abbr.upper()} TC Total:  {at['TC_TOTAL']:.1f}",
        f"    PTS: {at['TC_PTS']:.1f} | REB: {at['TC_REB']:.1f} | AST: {at['TC_AST']:.1f} | 3PM: {at['TC_3PM']:.1f}",
        f"  {home_abbr.upper()} TC Total:  {ht['TC_TOTAL']:.1f}",
        f"    PTS: {ht['TC_PTS']:.1f} | REB: {ht['TC_REB']:.1f} | AST: {ht['TC_AST']:.1f} | 3PM: {ht['TC_3PM']:.1f}",
        f"  {'─'*56}",
        f"  TC COMBINED: {tc_combined:.1f}",
        f"  TC LINE (×{LINE_FACTOR}): {tc_line}",
        f"  EDGE: {edge:+.1f} → {signal}",
    ]
    if market_total is not None:
        diff = round(tc_combined - market_total, 1)
        lines.append(f"  Market Total: {market_total} | Diff: {diff:+.1f} → {'OVER' if diff > 0 else 'UNDER'}")

    # Key injuries
    injured = [(t.abbr, p) for t in [g.away, g.home]
               for p in t.players if p.status != "ACTIVE"]
    if injured:
        lines.append(f"  {'─'*56}")
        lines.append(f"  KEY INJURIES:")
        for abbr, p in injured:
            lines.append(f"    {abbr} {p.name}: {p.status} (TC pts: {p.tc(p.pts):.1f})")

    return {"explanation": "\n".join(lines)}

# ── Run locally ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3456))
    print(f"Starting Sports TC API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)