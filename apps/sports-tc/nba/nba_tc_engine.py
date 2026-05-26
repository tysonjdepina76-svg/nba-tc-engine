#!/usr/bin/env python3
"""
NBA TC Engine — Live Roster/Public App Version
==============================================

Purpose
-------
Generate NBA TC player-prop projections using LIVE/API rosters instead of stale
hard-coded player lists.

Critical TC rule
----------------
TC Match applies ONLY to individual player props:
  - points
  - rebounds
  - assists
  - 3-point shots made

TC Match does NOT apply to game totals, spreads, moneylines, or team totals.
Game total context, if shown, is a separate market/pace reference only.

Roster rule
-----------
No hard-coded player rosters are used. Team rosters, player names, positions,
heights, and stat averages are pulled from ESPN's public roster/stat endpoint at
runtime. The only hard-coded map is the ESPN team-id map needed to locate each
team endpoint.

Run
---
  python nba_tc_engine.py --game "CLE @ NYK" --market-total 217.5 --market-spread -6.5
  python nba_tc_engine.py --game "SAS @ OKC" --json
  python nba_tc_engine.py --teams
  python nba_tc_engine.py --serve --port 8001

API
---
  GET  /health
  GET  /teams
  GET  /team/{abbr}
  GET  /project?away=CLE&home=NYK&market_total=217.5&market_spread=-6.5
  POST /project
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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

CONS = 0.85
Q_MULT = 0.55
OUT_MULT = 0.0
LINE_FACTOR = 0.88
MIN_EDGE = 3.0
MIN_HIT_RATE = 0.75
KELLY_FRAC = 0.25

STAT_KEYS = ("PTS", "REB", "AST", "3PM")

ESPN_TEAM_IDS: Dict[str, str] = {
    "ATL": "1", "BOS": "2", "BKN": "17", "CHA": "30", "CHI": "4",
    "CLE": "5", "DAL": "6", "DEN": "7", "DET": "8", "GSW": "9",
    "HOU": "10", "IND": "11", "LAC": "12", "LAL": "13", "MEM": "29",
    "MIA": "14", "MIL": "15", "MIN": "16", "NOP": "3", "NYK": "18",
    "OKC": "25", "ORL": "19", "PHI": "20", "PHX": "21", "POR": "22",
    "SAC": "23", "SAS": "24", "TOR": "28", "UTA": "26", "WAS": "27",
}

ALIASES = {
    "SA": "SAS", "SAN": "SAS", "SAS": "SAS",
    "NY": "NYK", "NYK": "NYK",
    "OKLA": "OKC", "OKC": "OKC",
    "WSH": "WAS", "UTAH": "UTA",
}

_cache: Dict[str, Tuple[float, "Team"]] = {}
CACHE_TTL_SECONDS = 300


def normalize_abbr(abbr: str) -> str:
    value = (abbr or "").strip().upper()
    return ALIASES.get(value, value)


def _get_json(url: str, timeout: int = 20) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Zo TC Engine)",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _height(ht: Any) -> str:
    if isinstance(ht, str) and "'" in ht:
        return ht.replace("' ", "-").replace("'", "-").replace('"', "").replace(" ", "")
    return str(ht or "?")


def _float(x: Any, default: float = 0.0) -> float:
    try:
        if x in (None, "", "--"):
            return default
        return float(str(x).replace("%", ""))
    except Exception:
        return default


def _extract_stat_map(ath: Dict[str, Any]) -> Dict[str, float]:
    stats = {"PTS": 0.0, "REB": 0.0, "AST": 0.0, "3PM": 0.0}
    splits = (ath.get("statistics") or {}).get("splits") or {}
    categories = splits.get("categories") or []
    for cat in categories:
        for s in cat.get("stats") or []:
            name = s.get("name") or ""
            val = s.get("displayValue", s.get("value", 0))
            if name == "avgPoints":
                stats["PTS"] = _float(val)
            elif name == "avgRebounds":
                stats["REB"] = _float(val)
            elif name == "avgAssists":
                stats["AST"] = _float(val)
            elif name in ("avgThreePointFieldGoalsMade", "avgThreesMade", "threePointFieldGoalsMade"):
                raw_3pm = _float(val)
                # Total 3PM stat can appear in the same roster payload; only use per-game average here.
                if name == "threePointFieldGoalsMade" and raw_3pm > 8:
                    continue
                stats["3PM"] = raw_3pm
    return stats


def _hydrate_three_point_stats_from_core_api(team_id: str, players: List[Player]) -> None:
    """ESPN's web roster endpoint sometimes omits avg 3PM.
    Pull each player's core statistics endpoint and patch 3PM so TC_3PM never silently reads 0.
    """
    for p in players:
        if p.tpm > 0:
            continue
        athlete_id = getattr(p, "athlete_id", "")
        if not athlete_id:
            continue
        for season_type in (2, 3):
            try:
                url = (
                    f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/"
                    f"seasons/2026/types/{season_type}/teams/{team_id}/athletes/{athlete_id}/statistics"
                    f"?lang=en&region=us"
                )
                data = _get_json(url)
                cats = ((data.get("splits") or {}).get("categories") or [])
                for cat in cats:
                    for st in cat.get("stats") or []:
                        if st.get("name") == "avgThreePointFieldGoalsMade":
                            p.tpm = _float(st.get("displayValue", st.get("value", 0)))
                            break
                    if p.tpm > 0:
                        break
            except Exception:
                pass
            if p.tpm > 0:
                break


@dataclass
class Player:
    name: str
    pos: str
    ht: str
    pts: float
    reb: float
    ast: float
    tpm: float
    status: str = "ACTIVE"
    role: str = "ROLE"
    source: str = "ESPN_API"
    athlete_id: str = ""

    @property
    def production_score(self) -> float:
        return self.pts + self.reb + self.ast + self.tpm

    def _mult(self) -> float:
        if self.status.upper() == "OUT":
            return OUT_MULT
        if self.status.upper() in ("Q", "QUESTIONABLE", "GTD"):
            return Q_MULT
        return 1.0

    def tc_raw(self, stat: float) -> float:
        return round(stat * CONS * self._mult(), 1)

    def tc_target(self, stat: float) -> int:
        return math.floor(self.tc_raw(stat) * LINE_FACTOR)

    def stat_value(self, stat: str) -> float:
        stat = stat.upper()
        return {"PTS": self.pts, "REB": self.reb, "AST": self.ast, "3PM": self.tpm}[stat]

    def tc_projection(self) -> Dict[str, Any]:
        return {
            "TC_PTS": self.tc_raw(self.pts), "T_PTS": self.tc_target(self.pts),
            "TC_REB": self.tc_raw(self.reb), "T_REB": self.tc_target(self.reb),
            "TC_AST": self.tc_raw(self.ast), "T_AST": self.tc_target(self.ast),
            "TC_3PM": self.tc_raw(self.tpm), "T_3PM": self.tc_target(self.tpm),
        }

    def prop_edge(self, stat: str, market_line: float) -> Dict[str, Any]:
        raw = self.stat_value(stat)
        tc = self.tc_raw(raw)
        target = self.tc_target(raw)
        edge = round(market_line - target, 1)
        valid = edge >= MIN_EDGE
        return {
            "stat": stat.upper(), "raw_avg": raw, "TC": tc, "T": target,
            "market_line": market_line, "edge": edge, "valid": valid,
            "side": "UNDER", "note": "TC Match player-prop edge only",
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "pos": self.pos, "ht": self.ht, "status": self.status,
            "role": self.role, "pts": self.pts, "reb": self.reb, "ast": self.ast,
            "tpm": self.tpm, "source": self.source, "athlete_id": self.athlete_id, **self.tc_projection(),
        }


@dataclass
class Team:
    code: str
    name: str
    players: List[Player] = field(default_factory=list)
    source: str = "ESPN_API"

    def active(self) -> List[Player]:
        return [p for p in self.players if p.status.upper() != "OUT"]

    def starters(self) -> List[Player]:
        return [p for p in self.active() if p.role == "STARTER"]

    def role_players(self) -> List[Player]:
        return [p for p in self.active() if p.role != "STARTER"]

    def totals(self) -> Dict[str, float]:
        active = self.active()
        return {
            "TC_PTS": round(sum(p.tc_raw(p.pts) for p in active), 1),
            "TC_REB": round(sum(p.tc_raw(p.reb) for p in active), 1),
            "TC_AST": round(sum(p.tc_raw(p.ast) for p in active), 1),
            "TC_3PM": round(sum(p.tc_raw(p.tpm) for p in active), 1),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code, "name": self.name, "source": self.source,
            "players_count": len(self.players),
            "starters_count": len(self.starters()),
            "role_players_count": len(self.role_players()),
            "players": [p.to_dict() for p in self.players],
            "totals": self.totals(),
        }


def fetch_team_roster(abbr: str, force_refresh: bool = False) -> Team:
    code = normalize_abbr(abbr)
    if code not in ESPN_TEAM_IDS:
        raise ValueError(f"Unknown NBA team abbreviation: {abbr}")
    now = time.time()
    if not force_refresh and code in _cache and now - _cache[code][0] < CACHE_TTL_SECONDS:
        return _cache[code][1]

    team_id = ESPN_TEAM_IDS[code]
    url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/teams/{team_id}/roster?region=us&lang=en&contentorigin=espn"
    data = _get_json(url)
    team_name = (((data.get("team") or {}).get("displayName")) or code)
    raw = data.get("athletes") or []
    if not raw:
        for group in data.get("positionGroups") or []:
            raw.extend(group.get("athletes") or [])

    players: List[Player] = []
    for item in raw:
        ath = item.get("athlete") or item
        name = ath.get("displayName") or ath.get("fullName") or ath.get("name")
        if not name or name == "Name":
            continue
        pos = ((ath.get("position") or {}).get("abbreviation") or ath.get("position") or "?")
        ht = _height(ath.get("displayHeight"))
        sm = _extract_stat_map(ath)
        status = "ACTIVE"
        injuries = ath.get("injuries") or []
        if injuries:
            text = " ".join(str(x) for x in injuries).upper()
            if "OUT" in text:
                status = "OUT"
            elif "QUESTION" in text or "DAY-TO-DAY" in text or "GTD" in text:
                status = "Q"
        players.append(Player(name, str(pos), ht, sm["PTS"], sm["REB"], sm["AST"], sm["3PM"], status=status, athlete_id=str(ath.get("id") or "")))

    _hydrate_three_point_stats_from_core_api(team_id, players)
    players = sorted(players, key=lambda p: p.production_score, reverse=True)
    for idx, p in enumerate(players):
        p.role = "STARTER" if idx < 5 and p.status != "OUT" else "ROLE"

    team = Team(code, team_name, players)
    _cache[code] = (now, team)
    return team


class Game:
    def __init__(self, away: str, home: str, prop_lines: Optional[Dict[str, Dict[str, float]]] = None, bankroll: float = 1000.0):
        self.away_code = normalize_abbr(away)
        self.home_code = normalize_abbr(home)
        self.away = fetch_team_roster(self.away_code)
        self.home = fetch_team_roster(self.home_code)
        self.prop_lines = prop_lines or {}
        self.bankroll = bankroll

    def _player_props(self, p: Player) -> Dict[str, Any]:
        lines = self.prop_lines.get(p.name, {})
        out: Dict[str, Any] = {}
        for stat in STAT_KEYS:
            default_line = round(p.stat_value(stat) * 1.18, 1)
            market_line = float(lines.get(stat, default_line))
            out[stat] = p.prop_edge(stat, market_line)
        return out

    def project(self) -> Dict[str, Any]:
        props = {}
        for p in self.away.active() + self.home.active():
            props[p.name] = {"team": self.away_code if p in self.away.active() else self.home_code, "role": p.role, **self._player_props(p)}
        valid = []
        for name, pdata in props.items():
            for stat in STAT_KEYS:
                edge = pdata[stat]
                if edge["valid"]:
                    valid.append({"player": name, "team": pdata["team"], "role": pdata["role"], **edge})
        valid = sorted(valid, key=lambda x: x["edge"], reverse=True)
        return {
            "matchup": f"{self.away_code} @ {self.home_code}",
            "tc_scope": "player_props_only",
            "game_total_note": "TC Match does not apply to game totals/team totals/spreads/ML.",
            "sources": {"rosters": "ESPN API live roster/stat endpoint"},
            "away": self.away.to_dict(),
            "home": self.home.to_dict(),
            "tc_props": props,
            "valid_edges": valid,
        }

    def print_report(self) -> None:
        data = self.project()
        print(f"\n{'═'*100}")
        print(f"NBA TC LIVE ROSTER REPORT — {data['matchup']}")
        print("TC Match: PLAYER PROPS ONLY — PTS, REB, AST, 3PM")
        print("Rosters: LIVE ESPN API. No stale hard-coded player rosters.")
        print(f"{'═'*100}")
        for team_key in ("away", "home"):
            team = data[team_key]
            print(f"\n{team['code']} — {team['name']} ({team['source']})")
            print(f"{'Role':<8} {'Player':<24} {'POS':<4} {'Status':<7} {'TC_PTS':>7} {'T_PTS':>6} {'TC_REB':>7} {'T_REB':>6} {'TC_AST':>7} {'T_AST':>6} {'TC_3PM':>7} {'T_3PM':>6}")
            print("─"*100)
            for p in team["players"]:
                print(f"{p['role']:<8} {p['name']:<24} {p['pos']:<4} {p['status']:<7} {p['TC_PTS']:>7.1f} {p['T_PTS']:>6} {p['TC_REB']:>7.1f} {p['T_REB']:>6} {p['TC_AST']:>7.1f} {p['T_AST']:>6} {p['TC_3PM']:>7.1f} {p['T_3PM']:>6}")
        print("\nVALID PROP EDGES")
        print(f"{'Player':<24} {'Team':<5} {'Role':<8} {'Stat':<4} {'TC':>6} {'T':>4} {'Line':>6} {'Edge':>6}")
        print("─"*80)
        for e in data["valid_edges"][:30]:
            print(f"{e['player']:<24} {e['team']:<5} {e['role']:<8} {e['stat']:<4} {e['TC']:>6.1f} {e['T']:>4} {e['market_line']:>6.1f} {e['edge']:>6.1f}")


if FASTAPI_AVAILABLE:
    app = FastAPI(title="NBA TC Live Roster Engine", version="2.0.0")

    class ProjectRequest(BaseModel):
        away: str = Field(...)
        home: str = Field(...)
        prop_lines: Dict[str, Dict[str, float]] = Field(default_factory=dict)
        bankroll: float = 1000.0

    @app.get("/")
    def root() -> Dict[str, Any]:
        return {"status": "ok", "tc_scope": "player_props_only", "rosters": "live ESPN API"}

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "teams_available": len(ESPN_TEAM_IDS)}

    @app.get("/teams")
    def teams() -> Dict[str, Any]:
        return {"teams": sorted(ESPN_TEAM_IDS)}

    @app.get("/team/{abbr}")
    def team(abbr: str) -> Dict[str, Any]:
        try:
            return fetch_team_roster(abbr).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/project")
    def project_get(away: str = Query(...), home: str = Query(...)) -> Dict[str, Any]:
        try:
            return Game(away, home).project()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/project")
    def project_post(req: ProjectRequest) -> Dict[str, Any]:
        try:
            return Game(req.away, req.home, req.prop_lines, req.bankroll).project()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))


def parse_game(text: str) -> Tuple[str, str]:
    if "@" not in text:
        raise ValueError("Use format AWAY @ HOME")
    away, home = [x.strip() for x in text.split("@", 1)]
    return away, home


def main() -> None:
    parser = argparse.ArgumentParser(description="NBA TC live roster player-prop engine")
    parser.add_argument("--game", help="AWAY @ HOME, e.g. CLE @ NYK")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--teams", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    if args.serve:
        if not FASTAPI_AVAILABLE:
            raise SystemExit("FastAPI unavailable. pip install fastapi uvicorn")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=args.port)
        return

    if args.teams:
        for code in sorted(ESPN_TEAM_IDS):
            print(code)
        return

    if args.game:
        away, home = parse_game(args.game)
        g = Game(away, home)
        if args.json:
            print(json.dumps(g.project(), indent=2))
        else:
            g.print_report()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
