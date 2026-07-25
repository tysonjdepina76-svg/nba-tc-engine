"""
Action Network Free Adapter — v2 API
No API key required. Provides live game lines (moneyline, spread, total) for MLB + WNBA + NFL.
Player props are NOT available on the free public endpoint.
"""

import requests
import logging
from datetime import datetime, timezone

logger = logging.getLogger("action_network")

V2_URL = "https://api.actionnetwork.com/web/v2/scoreboard/{sport}?period=event"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"}

TEAM_ABBR_OVERRIDES = {
    "mlb": {"WSH": "WAS", "CWS": "CHW", "TB": "TBR", "SF": "SFG", "SD": "SDP", "KC": "KCR"},
    "wnba": {"Spoon": "Team Spoon", "Coop": "Team Coop", "LV": "LVA"},
    "nfl": {},
}


def _fetch_scoreboard(sport):
    """Fetch v2 scoreboard JSON for a sport."""
    try:
        r = requests.get(V2_URL.format(sport=sport), headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"[AN] Fetch failed for {sport}: {e}")
        return {"games": []}


def _normalize_team_abbr(sport, teams_list, team_id):
    """Map team_id from v2 API to standard abbreviation."""
    for t in teams_list:
        if t.get("id") == team_id:
            abbr = t.get("abbr", "")
            overrides = TEAM_ABBR_OVERRIDES.get(sport, {})
            return overrides.get(abbr, abbr)
    return ""


def get_game_lines(sport):
    """Return list of game dicts with moneyline, spread, total.
    
    Each game:
    {
      "game_id": int, "sport": str, "status": str, "start_time": ISO,
      "away": str, "home": str, "away_score": int, "home_score": int,
      "moneyline": {"away": int|None, "home": int|None},
      "spread": {"away": float|None, "home": float|None, "away_line": int|None, "home_line": int|None},
      "total": {"line": float|None, "over": int|None, "under": int|None}
    }
    """
    data = _fetch_scoreboard(sport)
    games = data.get("games", [])
    results = []

    for g in games:
        teams = g.get("teams", [])
        away_id = g.get("away_team_id")
        home_id = g.get("home_team_id")
        away_abbr = _normalize_team_abbr(sport, teams, away_id) if away_id else ""
        home_abbr = _normalize_team_abbr(sport, teams, home_id) if home_id else ""

        box = g.get("boxscore", {})
        away_score = box.get("away_score", box.get("away_team_score", 0)) or 0
        home_score = box.get("home_score", box.get("home_team_score", 0)) or 0

        markets = g.get("markets", {})
        first_book = list(markets.values())[0] if markets else None
        event = first_book.get("event", {}) if first_book else {}

        ml_data = event.get("moneyline", [])
        spread_data = event.get("spread", [])
        total_data = event.get("total", [])

        moneyline = {"away": None, "home": None}
        for m in ml_data:
            side = m.get("side", "")
            if side == "away":
                moneyline["away"] = m.get("odds")
            elif side == "home":
                moneyline["home"] = m.get("odds")

        spread = {"away": None, "home": None, "away_line": None, "home_line": None}
        for s in spread_data:
            side = s.get("side", "")
            if side == "away":
                spread["away"] = s.get("value")
                spread["away_line"] = s.get("odds")
            elif side == "home":
                spread["home"] = s.get("value")
                spread["home_line"] = s.get("odds")

        total = {"line": None, "over": None, "under": None}
        for t in total_data:
            side = t.get("side", "")
            if side == "over":
                total["line"] = t.get("value")
                total["over"] = t.get("odds")
            elif side == "under":
                total["under"] = t.get("odds")

        results.append({
            "game_id": g["id"],
            "sport": sport.upper(),
            "status": g.get("status", ""),
            "start_time": g.get("start_time", ""),
            "away": away_abbr,
            "home": home_abbr,
            "away_score": away_score,
            "home_score": home_score,
            "moneyline": moneyline,
            "spread": spread,
            "total": total,
        })

    return results


def get_live_odds_export():
    """Return all sports game lines as dict keyed by sport (lowercase)."""
    return {
        "mlb": get_game_lines("mlb"),
        "wnba": get_game_lines("wnba"),
        "nfl": get_game_lines("nfl"),
    }


def get_odds_for_pipeline(sport):
    """Pipeline-compatible: returns dict {player_lower: [{stat, line, book}, ...]}.
    
    Since player props aren't available on the free Action Network API,
    returns game-level spread/total as stat markers so daily_picks.py 
    can at least validate direction against real lines.
    """
    games = get_game_lines(sport)
    result = {}
    for g in games:
        away = g["away"]
        home = g["home"]
        matchup = f"{away}@{home}"
        total = g["total"]
        spread = g["spread"]

        if total.get("line"):
            key = f"game:{matchup}"
            result[key] = [{
                "stat": "TOTAL",
                "line": total["line"],
                "book": "ActionNetwork",
                "over_odds": total.get("over"),
                "under_odds": total.get("under"),
                "team": matchup,
            }]
    return result


def get_mlb_situations():
    """Fetch MLB live situation data (pitcher, count, runners, inning, outs)."""
    data = _fetch_scoreboard("mlb")
    results = []
    for g in data.get("games", []):
        if g.get("status") != "inprogress":
            continue

        teams = g.get("teams", [])
        box = g.get("boxscore", {})
        last_play = g.get("last_play", {}) or {}

        home_hits = [p for p in box.get("home_batting", []) if p.get("h", 0)]
        away_hits = [p for p in box.get("away_batting", []) if p.get("h", 0)]

        results.append({
            "game_id": g["id"],
            "away": _normalize_team_abbr("mlb", teams, g.get("away_team_id")),
            "home": _normalize_team_abbr("mlb", teams, g.get("home_team_id")),
            "away_score": box.get("away_score", 0) or 0,
            "home_score": box.get("home_score", 0) or 0,
            "inning": box.get("inning", 0) or 0,
            "inning_half": box.get("inning_half", ""),
            "outs": box.get("outs", 0) or 0,
            "balls": box.get("balls", 0) or 0,
            "strikes": box.get("strikes", 0) or 0,
            "on_first": bool(box.get("on_first")),
            "on_second": bool(box.get("on_second")),
            "on_third": bool(box.get("on_third")),
            "pitcher_name": box.get("pitcher", {}).get("full_name", "") if isinstance(box.get("pitcher"), dict) else "",
            "last_play": last_play.get("description", ""),
            "away_hitters": [p.get("full_name", "") for p in away_hits],
            "home_hitters": [p.get("full_name", "") for p in home_hits],
        })
    return results
