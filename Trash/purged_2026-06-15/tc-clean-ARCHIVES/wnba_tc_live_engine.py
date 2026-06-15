#!/usr/bin/env python3
"""
WNBA TC Live Engine — ESPN API + Backtest-Aware Prop Projections
================================================================

Purpose
-------
Generate WNBA pregame roster projections from live ESPN APIs.

Core rule
---------
TC math applies ONLY to individual player prop categories:
  - PTS  = points × 0.85
  - REB  = rebounds × 0.80
  - AST  = assists × 0.75
  - 3PM  = made threes × 0.70
  - Q    = multiply the TC result by 0.55
  - OUT  = 0

Team totals are informational only. Do NOT apply TC-match logic to game totals.

Data sources
------------
1. ESPN WNBA scoreboard API for today's games.
2. ESPN roster API for live active/inactive roster and injury status.
3. ESPN athlete statistics API for player averages.
4. Local backtest files remain the validation layer, not the roster source.

Run
---
  python3 wnba_tc_live_engine.py
  python3 wnba_tc_live_engine.py --date 20260520
  python3 wnba_tc_live_engine.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

CONS = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
Q_FACTOR = 0.55
OUT_FACTOR = 0.0

TEAM_ID_BY_ABBR = {
    "ATL": "20", "CHI": "19", "CON": "18", "DAL": "3", "GS": "21", "IND": "5",
    "LV": "17", "LVA": "17", "LA": "6", "LAS": "6", "MIN": "8", "NY": "9", "NYL": "9",
    "PHX": "11", "POR": "22", "SEA": "14", "TOR": "23", "WSH": "16",
}

ABBR_CANON = {"LVA": "LV", "LAS": "LA", "NYL": "NY"}

STAT_NAME_MAP = {
    "avgPoints": "pts",
    "avgRebounds": "reb",
    "avgAssists": "ast",
    "avgThreePointFieldGoalsMade": "tpm",
}

CACHE_DIR = Path("/home/workspace/live_sports_scrape")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def canon(abbr: str) -> str:
    value = (abbr or "").upper().strip()
    return ABBR_CANON.get(value, value)


def get_json(url: str, timeout: int = 12) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def height_to_text(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw)
    if "'" in s or "\"" in s:
        return s.replace(" ", "")
    try:
        inches = int(float(s))
        return f"{inches // 12}-{inches % 12}"
    except Exception:
        return s


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "--"):
            return default
        return float(value)
    except Exception:
        return default


def status_from_athlete(ath: Dict[str, Any]) -> str:
    status = ath.get("status") or {}
    text = " ".join(str(status.get(k, "")) for k in ("type", "name", "detail", "description", "abbreviation"))
    text = text.upper()
    if ath.get("injured") or "OUT" in text or "IR" in text:
        return "OUT"
    if "QUESTION" in text or text.strip() in {"Q", "DAY-TO-DAY", "DOUBTFUL"}:
        return "Q"
    return "ACTIVE"


def extract_stats_from_athlete_payload(data: Dict[str, Any]) -> Dict[str, float]:
    out = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}
    for cat in data.get("splits", {}).get("categories", []) or []:
        for stat in cat.get("stats", []) or []:
            name = stat.get("name")
            if name in STAT_NAME_MAP:
                out[STAT_NAME_MAP[name]] = to_float(stat.get("displayValue", stat.get("value")))
    return out


def fetch_athlete_stats(athlete_id: str) -> Dict[str, float]:
    if not athlete_id:
        return {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}
    urls = [
        f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/wnba/athletes/{athlete_id}/overview?region=us&lang=en&contentorigin=espn",
        f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/wnba/athletes/{athlete_id}/statistics?lang=en&region=us",
    ]
    for url in urls:
        try:
            data = get_json(url)
            stats = extract_stats_from_athlete_payload(data)
            if any(stats.values()):
                return stats
        except Exception:
            continue
    return {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}


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
    athlete_id: str = ""
    role: str = "BENCH"

    def _factor(self) -> float:
        if self.status == "OUT":
            return OUT_FACTOR
        if self.status == "Q":
            return Q_FACTOR
        return 1.0

    def tc(self) -> Dict[str, float]:
        f = self._factor()
        return {
            "PTS": round(self.pts * CONS["pts"] * f, 1),
            "REB": round(self.reb * CONS["reb"] * f, 1),
            "AST": round(self.ast * CONS["ast"] * f, 1),
            "3PM": round(self.tpm * CONS["tpm"] * f, 1),
        }

    def production_score(self) -> float:
        return self.pts + self.reb + self.ast + (self.tpm * 2)

    def row(self) -> Dict[str, Any]:
        t = self.tc()
        return {
            "role": self.role,
            "player": self.name,
            "pos": self.pos,
            "ht": self.ht,
            "status": self.status,
            "raw_pts": self.pts,
            "raw_reb": self.reb,
            "raw_ast": self.ast,
            "raw_3pm": self.tpm,
            "TC_PTS": t["PTS"],
            "TC_REB": t["REB"],
            "TC_AST": t["AST"],
            "TC_3PM": t["3PM"],
        }


def roster_url(abbr: str) -> str:
    code = canon(abbr).lower()
    special = {"lv": "lv", "la": "la", "ny": "ny", "gs": "gs", "por": "por", "tor": "tor"}
    code = special.get(code, code)
    return f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/{code}/roster"

def athlete_url_from_ref(ref: str) -> str:
    if ref.startswith("http"):
        return ref
    return ref


def fetch_roster(abbr: str) -> List[Player]:
    data = get_json(roster_url(abbr))
    raw_athletes = data.get("athletes", []) or []
    players: List[Player] = []
    for group in raw_athletes:
        if isinstance(group, dict) and "items" in group:
            items = group.get("items") or []
        else:
            items = [group]
        for ath in items:
            if not isinstance(ath, dict):
                continue
            name = ath.get("displayName") or ath.get("fullName") or ath.get("shortName") or "Unknown"
            if name.lower() in {"name", "unknown"}:
                continue
            athlete_id = str(ath.get("id") or "")
            pos = (ath.get("position") or {}).get("abbreviation") or (ath.get("position") or {}).get("name") or ath.get("position", "")
            ht = height_to_text(ath.get("displayHeight") or ath.get("height"))
            status = status_from_athlete(ath)
            stats = fetch_athlete_stats(athlete_id)
            players.append(Player(name=name, pos=str(pos), ht=ht, status=status, athlete_id=athlete_id, **stats))
    active_sorted = sorted([p for p in players if p.status != "OUT"], key=lambda p: p.production_score(), reverse=True)
    starter_names = {p.name for p in active_sorted[:5]}
    for p in players:
        p.role = "START" if p.name in starter_names else ("OUT" if p.status == "OUT" else "BENCH")
    return sorted(players, key=lambda p: (p.role != "START", p.role == "OUT", -p.production_score(), p.name))

def fetch_scoreboard(date: Optional[str] = None) -> Dict[str, Any]:
    base = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
    url = base if not date else f"{base}?dates={date}"
    return get_json(url)


def game_abbrs(event: Dict[str, Any]) -> tuple[str, str, str, str]:
    comps = event.get("competitions", [{}])[0].get("competitors", [])
    away = next((c for c in comps if c.get("homeAway") == "away"), {})
    home = next((c for c in comps if c.get("homeAway") == "home"), {})
    away_abbr = canon((away.get("team") or {}).get("abbreviation", ""))
    home_abbr = canon((home.get("team") or {}).get("abbreviation", ""))
    away_name = (away.get("team") or {}).get("displayName", away_abbr)
    home_name = (home.get("team") or {}).get("displayName", home_abbr)
    return away_abbr, home_abbr, away_name, home_name


def project_slate(date: Optional[str] = None) -> Dict[str, Any]:
    board = fetch_scoreboard(date)
    out = {"generated_at": datetime.utcnow().isoformat() + "Z", "date": date, "games": []}
    for event in board.get("events", []) or []:
        away_abbr, home_abbr, away_name, home_name = game_abbrs(event)
        if not away_abbr or not home_abbr:
            continue
        away_players = fetch_roster(away_abbr)
        home_players = fetch_roster(home_abbr)
        comp = event.get("competitions", [{}])[0]
        out["games"].append({
            "event_id": event.get("id"),
            "name": event.get("name") or f"{away_abbr} @ {home_abbr}",
            "date": event.get("date"),
            "status": (event.get("status") or {}).get("type", {}).get("description", ""),
            "away": {"abbr": away_abbr, "name": away_name, "players": [p.row() for p in away_players]},
            "home": {"abbr": home_abbr, "name": home_name, "players": [p.row() for p in home_players]},
            "note": "TC applies to player props only: PTS, REB, AST, 3PM. No TC game-total matching.",
        })
    return out


def print_report(data: Dict[str, Any]) -> None:
    print("# WNBA Live Pregame TC Roster Projections")
    print(f"Generated: {data['generated_at']}")
    print("TC: PTS×0.85 | REB×0.80 | AST×0.75 | 3PM×0.70 | Q×0.55 | OUT=0")
    print("IMPORTANT: TC match applies only to player props, not team/game totals.\n")
    for game in data["games"]:
        print(f"## {game['name']} — {game['status']} — {game['date']}")
        for side in ("away", "home"):
            team = game[side]
            print(f"\n### {side.upper()}: {team['abbr']} — {team['name']}")
            print("| Role | Player | POS | HT | Status | TC PTS | TC REB | TC AST | TC 3PM |")
            print("|---|---|---|---|---:|---:|---:|---:|---:|")
            for p in team["players"]:
                print(f"| {p['role']} | {p['player']} | {p['pos']} | {p['ht']} | {p['status']} | {p['TC_PTS']} | {p['TC_REB']} | {p['TC_AST']} | {p['TC_3PM']} |")
        print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="YYYYMMDD, defaults to ESPN current slate")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", default="/home/workspace/WNBA_Live_TC_Pregame_Report.md")
    args = parser.parse_args()
    data = project_slate(args.date)
    CACHE_DIR.joinpath(f"espn_wnba_live_{args.date or 'current'}.json").write_text(json.dumps(data, indent=2))
    if args.json:
        print(json.dumps(data, indent=2))
        return
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_report(data)
    text = buf.getvalue()
    Path(args.save).write_text(text)
    print(text)
    print(f"Saved: {args.save}")


if __name__ == "__main__":
    main()
