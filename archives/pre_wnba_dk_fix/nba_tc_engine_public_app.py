#!/usr/bin/env python3
"""
NBA TC Engine — Public App Wrapper
==================================

Purpose
-------
This is the public app / API wrapper for the workspace engine in
`nba_tc_engine.py`.

Core rule
---------
TC math is for INDIVIDUAL PLAYER PROP BETS ONLY:
  - points
  - rebounds
  - assists
  - 3-point shots made

Game totals are NOT TC-match bets. If exposed, they are labeled as a
separate pace estimate and must not be mixed with prop TC edges.

Run
---
  python nba_tc_engine_public_app.py --serve --port 8001
  python nba_tc_engine_public_app.py --game "SAS @ OKC" --market-total 218.5
  python nba_tc_engine_public_app.py --teams

API
---
  GET  /health
  GET  /teams
  GET  /team/{abbr}
  GET  /project?away=SAS&home=OKC&market_total=218.5
  POST /project
  GET  /backtest
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException, Query
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = Exception
    Query = None
    BaseModel = object
    Field = None

from nba_tc_engine import Game, NBA_TEAMS, run_backtest


APP_NAME = "NBA TC Engine Public App"
APP_VERSION = "1.0.0"
VALID_STATS = ("PTS", "REB", "AST", "3PM")


def normalize_abbr(abbr: str) -> str:
    if not abbr:
        raise ValueError("Missing team abbreviation")
    value = abbr.strip().upper()
    aliases = {
        "SA": "SAS",
        "SAN": "SAS",
        "SAS": "SAS",
        "NY": "NYK",
        "NYK": "NYK",
        "OKLA": "OKC",
        "OKC": "OKC",
    }
    return aliases.get(value, value)


def parse_game(game: str) -> tuple[str, str]:
    if "@" not in game:
        raise ValueError("Game must be formatted as 'AWAY @ HOME'")
    away, home = [normalize_abbr(x) for x in game.split("@", 1)]
    return away, home


def validate_team(abbr: str) -> str:
    code = normalize_abbr(abbr)
    if code not in NBA_TEAMS:
        raise ValueError(f"Unknown team: {abbr}. Available: {', '.join(sorted(NBA_TEAMS))}")
    return code


def project_game(
    away: str,
    home: str,
    market_total: Optional[float] = None,
    market_spread: Optional[float] = None,
    prop_lines: Optional[Dict[str, Dict[str, float]]] = None,
    bankroll: float = 1000.0,
    is_playoff: bool = True,
) -> Dict[str, Any]:
    away_code = validate_team(away)
    home_code = validate_team(home)
    game = Game(
        away_code,
        home_code,
        market_total=market_total,
        market_spread=market_spread,
        prop_lines=prop_lines or {},
        bankroll=bankroll,
        is_playoff=is_playoff,
    )
    data = game.to_dict()
    data["app"] = {
        "name": APP_NAME,
        "version": APP_VERSION,
        "tc_scope": "player_props_only",
        "prop_stats": list(VALID_STATS),
        "game_total_note": "Game totals use separate pace estimate; TC match does not apply to totals.",
    }
    return data


if FASTAPI_AVAILABLE:
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="Public API for NBA TC player prop projections. TC applies only to PTS/REB/AST/3PM props.",
    )

    class ProjectRequest(BaseModel):
        away: str = Field(..., description="Away team abbreviation, e.g. SAS")
        home: str = Field(..., description="Home team abbreviation, e.g. OKC")
        market_total: Optional[float] = None
        market_spread: Optional[float] = None
        prop_lines: Dict[str, Dict[str, float]] = Field(default_factory=dict)
        bankroll: float = 1000.0
        is_playoff: bool = True

    @app.get("/")
    def root() -> Dict[str, Any]:
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "status": "ok",
            "tc_scope": "player_props_only",
            "prop_stats": list(VALID_STATS),
            "endpoints": ["/health", "/teams", "/team/{abbr}", "/project", "/backtest"],
        }

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "teams_loaded": len(NBA_TEAMS)}

    @app.get("/teams")
    def teams() -> Dict[str, Any]:
        return {
            "count": len(NBA_TEAMS),
            "teams": [
                {"abbr": abbr, "name": team.name, "players": len(team.players)}
                for abbr, team in sorted(NBA_TEAMS.items())
            ],
        }

    @app.get("/team/{abbr}")
    def team(abbr: str) -> Dict[str, Any]:
        try:
            code = validate_team(abbr)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        t = NBA_TEAMS[code]
        return {
            "abbr": code,
            "name": t.name,
            "players": [
                {
                    "name": p.name,
                    "pos": p.pos,
                    "ht": p.ht,
                    "pts": p.pts,
                    "reb": p.reb,
                    "ast": p.ast,
                    "tpm": p.tpm,
                    "status": p.status,
                    "projection": p.proj(),
                }
                for p in t.players
            ],
        }

    @app.get("/project")
    def project_get(
        away: str = Query(...),
        home: str = Query(...),
        market_total: Optional[float] = None,
        market_spread: Optional[float] = None,
        bankroll: float = 1000.0,
        is_playoff: bool = True,
    ) -> Dict[str, Any]:
        try:
            return project_game(away, home, market_total, market_spread, {}, bankroll, is_playoff)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/project")
    def project_post(req: ProjectRequest) -> Dict[str, Any]:
        try:
            return project_game(
                req.away,
                req.home,
                req.market_total,
                req.market_spread,
                req.prop_lines,
                req.bankroll,
                req.is_playoff,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/backtest")
    def backtest() -> Dict[str, Any]:
        return run_backtest()
else:
    app = None


def print_projection(data: Dict[str, Any]) -> None:
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="NBA TC Engine Public App")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--game", help="Game format: 'AWAY @ HOME'")
    parser.add_argument("--market-total", type=float, default=None)
    parser.add_argument("--market-spread", type=float, default=None)
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--regular-season", action="store_true", help="Disable playoff pace flag")
    parser.add_argument("--teams", action="store_true", help="List teams")
    parser.add_argument("--backtest", action="store_true", help="Run backtest")
    args = parser.parse_args()

    if args.serve:
        if not FASTAPI_AVAILABLE:
            raise SystemExit("FastAPI is not installed. Run: pip install fastapi uvicorn")
        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port)
        return

    if args.teams:
        print(json.dumps({"teams": sorted(NBA_TEAMS.keys()), "count": len(NBA_TEAMS)}, indent=2))
        return

    if args.backtest:
        print(json.dumps(run_backtest(), indent=2))
        return

    if args.game:
        away, home = parse_game(args.game)
        data = project_game(
            away,
            home,
            market_total=args.market_total,
            market_spread=args.market_spread,
            bankroll=args.bankroll,
            is_playoff=not args.regular_season,
        )
        print_projection(data)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
