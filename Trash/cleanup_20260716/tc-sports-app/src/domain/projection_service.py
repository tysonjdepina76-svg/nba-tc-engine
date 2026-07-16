"""ProjectionService — unified projection engine for all sports.

Wraps the per-sport TC engines (WNBA, MLB, NFL, NBA, NHL, SOCCER) and exposes
a single `get_projections(sport, date)` API that returns a normalized
`{"projections": [...], "sport": ..., "date": ..., "source": ...}` payload.

Backed by:
- src.adapters.sportsdataio.{WNBAAdapter,NFLAdapter,MLBAdapter} for player data
- src.domain.market_line_provider.MarketLineProvider for market lines
- src.domain.tc_engine (per-sport TC implementations) for projections
- src.domain.fantasy_images / combo_optimizer for downstream consumers

Used by:
- src.domain.daily_picks (TC pipeline)
- src.dashboard.tc_dashboard (Streamlit panel)
- tests/test_projection_service.py
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.entities import Player, Projection, Sport, GameStatus
from src.domain.market_line_provider import MarketLineProvider

log = logging.getLogger(__name__)

WORKSPACE = Path("/home/workspace")
DAILY_LOG = WORKSPACE / "Daily_Log"
ET = timezone(timedelta(hours=-4))


class ProjectionService:
    """Single entry point for sport projections."""

    _VALID_SPORTS = ("WNBA", "NFL", "MLB", "NBA", "NHL", "SOCCER")

    def __init__(self, market_provider: Optional[MarketLineProvider] = None):
        self.market = market_provider  # per-sport, resolved in get_projections
        self._sport_to_engine: Dict[str, Any] = {}
        self._load_engines()

    def _load_engines(self) -> None:
        """Lazy-load TC engines for each sport (only sports that exist)."""
        try:
            from src.domain.tc_engine import (
                wnba_engine, mlb_engine, nfl_engine, nba_engine, nhl_engine, soccer_engine
            )
            self._sport_to_engine = {
                "WNBA": wnba_engine,
                "MLB": mlb_engine,
                "NFL": nfl_engine,
                "NBA": nba_engine,
                "NHL": nhl_engine,
                "SOCCER": soccer_engine,
            }
        except ImportError as e:
            log.warning("tc_engine not fully wired: %s — using stub engines", e)
            self._sport_to_engine = {}

    # ── Public API ─────────────────────────────────────────────────────

    def get_projections(
        self,
        sport: str,
        date: Optional[str] = None,
        team: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return projections for a sport/date.

        Args:
            sport: WNBA | NFL | MLB | NBA | NHL | SOCCER
            date: YYYY-MM-DD (defaults to today ET)
            team: optional team filter (e.g. "NY", "LAL")

        Returns:
            {
                "sport": str,
                "date": str,
                "source": "selfedge" | "sportsdataio" | "oddsapi" | "sportsgameodds" | "off_season",
                "projections": [
                    {"player": str, "team": str, "stat": str, "line": float,
                     "projection": float, "edge": float, "direction": "OVER"|"UNDER",
                     "confidence": float, "matchup": str, "source": str}
                ],
                "count": int,
                "errors": [str],
            }
        """
        sport = sport.upper()
        if sport not in self._VALID_SPORTS:
            return {
                "sport": sport,
                "date": date or "",
                "source": "invalid",
                "projections": [],
                "count": 0,
                "errors": [f"Invalid sport '{sport}'. Valid: {self._VALID_SPORTS}"],
            }

        if date is None:
            date = datetime.now(ET).strftime("%Y-%m-%d")

        # NBA + NHL are off-season mid-year — short-circuit cleanly
        if sport in ("NBA", "NHL"):
            today = datetime.now(ET)
            if today.month < 10:
                return {
                    "sport": sport,
                    "date": date,
                    "source": "off_season",
                    "projections": [],
                    "count": 0,
                    "errors": [f"{sport} is off-season (returns October)."],
                }

        # 1) Get market lines
        market = (self.market or MarketLineProvider(sport)).get_lines()
        source = market.get("source", "selfedge")

        # 2) Get players
        players = self._get_players(sport)

        # 3) Get TC projections
        engine = self._sport_to_engine.get(sport)
        projections: List[Dict[str, Any]] = []
        errors: List[str] = []

        if engine is None:
            errors.append(f"No TC engine for {sport} — returning empty projections")
        else:
            try:
                raw = engine.project(players, market_lines=market, date=date)
                for p in raw:
                    row = self._normalize(p, sport, source, date)
                    if team is None or row.get("team", "").upper() == team.upper():
                        projections.append(row)
            except Exception as e:  # noqa: BLE001
                errors.append(f"Engine error: {e}")

        return {
            "sport": sport,
            "date": date,
            "source": source,
            "projections": projections,
            "count": len(projections),
            "errors": errors,
        }

    # ── Helpers ────────────────────────────────────────────────────────

    def _get_players(self, sport: str) -> List[Player]:
        """Fetch players for a sport from the appropriate adapter.

        Falls back to empty list if the adapter is dead/off-season.
        """
        try:
            if sport == "WNBA":
                from src.adapters.sportsdataio.wnba import WNBAAdapter
                return WNBAAdapter().get_players()
            if sport == "NFL":
                from src.adapters.sportsdataio.nfl import NFLAdapter
                return NFLAdapter().get_players()
            if sport == "MLB":
                from src.adapters.sportsdataio.mlb import MLBAdapter
                return MLBAdapter().get_players()
        except Exception as e:  # noqa: BLE001
            log.warning("Player fetch failed for %s: %s", sport, e)
        return []

    def _normalize(self, p: Any, sport: str, source: str, date: str) -> Dict[str, Any]:
        """Normalize engine output into a flat dict."""
        if isinstance(p, dict):
            return {
                "player": p.get("player") or p.get("name", ""),
                "team": p.get("team", ""),
                "stat": p.get("stat", ""),
                "line": float(p.get("line", 0.0)),
                "projection": float(p.get("projection", p.get("proj", 0.0))),
                "edge": float(p.get("edge", 0.0)),
                "direction": p.get("direction", "OVER"),
                "confidence": float(p.get("confidence", 0.0)),
                "matchup": p.get("matchup", ""),
                "source": p.get("source", source),
            }
        if isinstance(p, Projection):
            d = asdict(p)
            return {
                "player": d.get("player_name", ""),
                "team": d.get("team", ""),
                "stat": d.get("stat", ""),
                "line": float(d.get("line", 0.0)),
                "projection": float(d.get("value", 0.0)),
                "edge": float(d.get("edge", 0.0)),
                "direction": d.get("direction", "OVER"),
                "confidence": float(d.get("confidence", 0.0)),
                "matchup": d.get("matchup", ""),
                "source": d.get("source", source),
            }
        return {
            "player": getattr(p, "name", str(p)),
            "team": getattr(p, "team", ""),
            "stat": "",
            "line": 0.0,
            "projection": 0.0,
            "edge": 0.0,
            "direction": "OVER",
            "confidence": 0.0,
            "matchup": "",
            "source": source,
        }


if __name__ == "__main__":
    import json
    svc = ProjectionService()
    for s in ("WNBA", "MLB", "NFL", "NBA", "NHL", "SOCCER"):
        out = svc.get_projections(s)
        print(f"{s:7s} source={out['source']:14s} count={out['count']}")
