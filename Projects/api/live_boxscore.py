"""
ESPN Live Box Score Engine — Fetches full player stats for WNBA/MLB.
Writes per-game JSON to Daily_Log/boxscores/
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.api_cap_tracker import cap_check
sys.path.insert(0, "/home/workspace/Projects")
sys.path.insert(0, "/home/workspace/Projects/src")

DAILY_LOG = Path("/home/workspace/Daily_Log")
BOXSCORE_DIR = DAILY_LOG / "boxscores"
BOXSCORE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 30  # seconds for live games, longer for final

ESPN_CORE = "https://sports.core.api.espn.com/v2"
ESPN_SITE = "https://site.api.espn.com/apis/site/v2"

LEAGUE_CONFIG = {
    "wnba": {
        "site_path": "sports/basketball/wnba/scoreboard",
        "core_sport": "basketball",
        "core_league": "wnba",
        "use_summary": False,
    },
    "mlb": {
        "site_path": "sports/baseball/mlb/scoreboard",
        "core_sport": "baseball",
        "core_league": "mlb",
        "use_summary": True,
    },
    "wc": {
        "site_path": "sports/soccer/fifa.world/scoreboard",
        "core_sport": "soccer",
        "core_league": "fifa.world",
        "use_summary": True,
    },
}

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


def _get(url: str, ttl: int = 60) -> Optional[dict]:
    """Fetch JSON from ESPN with simple in-memory TTL cache."""
    domain = url.split('/')[2] if '://' in url else url
    if not cap_check(domain):
        return None
    try:
        r = session.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None


def fetch_wnba_live_events() -> List[dict]:
    """Get WNBA events from the public scoreboard endpoint."""
    url = f"{ESPN_SITE}/sports/basketball/wnba/scoreboard"
    data = _get(url)
    if not data:
        return []
    return data.get("events", [])


def fetch_mlb_live_events() -> List[dict]:
    """Get MLB events from the public scoreboard endpoint."""
    url = f"{ESPN_SITE}/sports/baseball/mlb/scoreboard"
    data = _get(url)
    if not data:
        return []
    return data.get("events", [])


def fetch_wc_live_events() -> List[dict]:
    """Fetch live WC (FIFA World Cup) events from ESPN."""
    cfg = LEAGUE_CONFIG["wc"]
    url = f"{ESPN_SITE}/{cfg['site_path']}"
    data = _get(url, ttl=30)
    if not data:
        return []
    events = []
    for evt in data.get("events", []):
        status = evt.get("status", {}).get("type", {}).get("name", "pre")
        if status in ("STATUS_IN_PROGRESS", "STATUS_FINAL", "STATUS_SCHEDULED"):
            competitions = evt.get("competitions", [])
            if not competitions:
                continue
            comp = competitions[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = None
            away = None
            for c in competitors:
                if c.get("homeAway") == "home":
                    home = c
                else:
                    away = c
            if not home or not away:
                home, away = competitors[0], competitors[1]
            events.append({
                "event_id": evt["id"],
                "status": status,
                "shortName": f"{away['team']['abbreviation']} @ {home['team']['abbreviation']}",
                "away": {"name": away["team"]["displayName"], "abbrev": away["team"]["abbreviation"], "score": away.get("score", "0")},
                "home": {"name": home["team"]["displayName"], "abbrev": home["team"]["abbreviation"], "score": home.get("score", "0")},
                "period": comp.get("period", 0),
                "clock": comp.get("status", {}).get("displayClock", ""),
                "raw_data": evt,
            })
    return events


def _athlete_name(athlete_ref: str) -> dict:
    """Resolve athlete reference to {fullName, displayName, shortName}."""
    d = _get(athlete_ref)
    if not d:
        return {"fullName": "Unknown", "displayName": "??", "shortName": "??"}
    return {
        "fullName": d.get("fullName", "Unknown"),
        "displayName": d.get("displayName", d.get("shortName", "??")),
        "shortName": d.get("shortName", "??"),
    }


def _position_name(pos_ref: str) -> str:
    """Resolve position reference to abbreviation."""
    d = _get(pos_ref)
    if not d:
        return "N/A"
    return d.get("abbreviation", d.get("name", "N/A"))


def _player_stats(stats_ref: str) -> dict:
    """Fetch individual player game stats from ESPN core API."""
    data = _get(stats_ref)
    if not data:
        return {}
    result = {}
    splits = data.get("splits", {})
    for cat in splits.get("categories", []):
        for stat in cat.get("stats", []):
            result[stat["name"]] = stat.get("value", 0)
    return result


def _clean_wnba_stats(raw_stats: dict) -> dict:
    """Map ESPN raw stat names to short display names for WNBA."""
    MAP = {
        "minutes": "MIN",
        "points": "PTS",
        "totalRebounds": "REB",
        "rebounds": "REB",
        "assists": "AST",
        "threePointFieldGoalsMade": "3PM",
        "steals": "STL",
        "blocks": "BLK",
        "fouls": "PF",
        "fieldGoalsMade": "FGM",
        "fieldGoalsAttempted": "FGA",
        "threePointFieldGoalsAttempted": "3PA",
        "freeThrowsMade": "FTM",
        "freeThrowsAttempted": "FTA",
        "offensiveRebounds": "OREB",
        "defensiveRebounds": "DREB",
        "turnovers": "TO",
        "totalTurnovers": "TO",
        "plusMinus": "+/-",
    }
    cleaned = {}
    for k, v in raw_stats.items():
        if k in MAP:
            val = v
            if isinstance(val, float) and val == int(val):
                val = int(val)
            cleaned[MAP[k]] = val
    if "PTS" in cleaned and "REB" in cleaned and "AST" in cleaned:
        cleaned["PRA"] = cleaned["PTS"] + cleaned["REB"] + cleaned["AST"]
    return cleaned


def _clean_mlb_stats(raw_stats: dict) -> dict:
    """Map ESPN raw stat names to short display names for MLB."""
    MAP = {
        "atBats": "AB",
        "runs": "R",
        "hits": "H",
        "rbi": "RBI",
        "baseOnBalls": "BB",
        "strikeOuts": "K",
        "homeRuns": "HR",
        "stolenBases": "SB",
        "totalBases": "TB",
        "avg": "AVG",
        "obp": "OBP",
        "slg": "SLG",
        "ops": "OPS",
        "inningsPitched": "IP",
        "earnedRuns": "ER",
        "pitchesThrown": "PIT",
        "strikes": "STR",
        "battersFaced": "BF",
        "outs": "OUTS",
    }
    cleaned = {}
    for k, v in raw_stats.items():
        if k in MAP:
            val = v
            if isinstance(val, float) and val == int(val):
                val = int(val)
            cleaned[MAP[k]] = val
    return cleaned


def _parse_wnba_player(entry: dict) -> dict:
    """Parse a WNBA roster entry into {name, pos, jersey, starter, stats, injury_status, alt_lines}."""
    status_type = (entry.get("status", {}) or {}).get("type", {})
    injury_detail = status_type.get("description", "") or ""
    is_injured = bool(injury_detail) and "healthy" not in injury_detail.lower()
    
    player = {
        "name": "Unknown",
        "pos": "N/A",
        "jersey": entry.get("jersey", "\u2014"),
        "starter": entry.get("starter", False),
        "dnp": not entry.get("active", True),
        "injury_status": injury_detail if is_injured else ("DNP" if not entry.get("active", True) else ""),
        "stats": {},
        "display": {},
        "display_stats": {},
        "alt_lines": {},
    }

    athlete_ref = entry.get("athlete", {}).get("$ref", "")
    if athlete_ref:
        name_info = _athlete_name(athlete_ref)
        player["name"] = name_info["displayName"] or name_info["shortName"] or "Unknown"

    pos_ref = entry.get("position", {}).get("$ref", "")
    if pos_ref:
        player["pos"] = _position_name(pos_ref)

    stats_ref = entry.get("statistics", {}).get("$ref", "")
    if stats_ref:
        player["stats"] = _player_stats(stats_ref)
        player["display"] = _clean_wnba_stats(player["stats"])
        player["display_stats"] = player["display"]

    return player


def _parse_mlb_player(entry: dict) -> dict:
    """Parse an MLB roster entry with batting stats."""
    athlete_ref = entry.get("athlete", {}).get("$ref", "")
    name_info = _athlete_name(athlete_ref) if athlete_ref else {"fullName": "Unknown", "displayName": "??"}
    pos_ref = entry.get("position", {}).get("$ref", "")
    pos = _position_name(pos_ref) if pos_ref else "N/A"

    stats = {}
    stats_ref = entry.get("statistics", {}).get("$ref", "")
    if stats_ref:
        stats = _player_stats(stats_ref)

    status_info = entry.get("status", {}) or {}
    injury = status_info.get("type", {}).get("name") if isinstance(status_info, dict) else None
    result = {
        "name": name_info.get("displayName", name_info.get("shortName", "Unknown")),
        "pos": pos,
        "jersey": entry.get("jersey", "—"),
        "starter": entry.get("starter", False),
        "dnp": not entry.get("active", True),
        "injury": injury,
        "battingOrder": entry.get("battingOrder", 99),
        "stats": stats,
        "display": {},
    }

    if stats:
        result["display"] = _clean_mlb_stats(stats)
        result["display_stats"] = dict(result["display"])
        result["display_stats"] = result["display"]
    return result


def _parse_wc_player(player_json: dict, team_name: str) -> dict:
    """Parse WC player stats from ESPN summary endpoint."""
    stats_list = player_json.get("statistics", [])
    ds: Dict[str, float] = {}
    stat_map = {
        "goals": "goals", "assists": "assists",
        "totalShots": "shots", "shotsOnTarget": "shots_on_target",
        "totalPasses": "passes", "totalTackles": "tackles",
        "saves": "saves", "yellowCards": "yellow_cards",
        "minutesPlayed": "minutes",
    }
    for s in stats_list:
        for k, v in (s.items() if isinstance(s, dict) else []):
            if k in stat_map:
                try:
                    ds[stat_map[k]] = float(v) if v else 0.0
                except (ValueError, TypeError):
                    ds[stat_map[k]] = 0.0
    jersey = str(player_json.get("jersey", "")) or ""
    pos = str(player_json.get("position", {}).get("abbreviation", "")) or ""
    return {
        "name": player_json.get("athlete", {}).get("displayName", "Unknown"),
        "pos": pos,
        "jersey": jersey,
        "starter": player_json.get("starter", False),
        "stats": ds,
        "display_stats": ds,
        "tc_picks": [],
    }


def fetch_wnba_boxscore(event: dict) -> dict:
    """Fetch full box score for a WNBA event using ESPN core API."""
    event_id = event.get("id", "")
    short_name = event.get("shortName", "? @ ?")
    comps = event.get("competitions", [{}])[0]
    status = comps.get("status", {})
    competitors = comps.get("competitors", [])

    # Extract team IDs from the site API
    home_team = None
    away_team = None
    for c in competitors:
        side = c.get("homeAway", "")
        team_info = c.get("team", {})
        if side == "home":
            home_team = {
                "name": team_info.get("displayName", team_info.get("shortDisplayName", "HOME")),
                "abbrev": team_info.get("abbreviation", "H"),
                "score": c.get("score", "0"),
                "id": team_info.get("id", ""),
            }
        else:
            away_team = {
                "name": team_info.get("displayName", team_info.get("shortDisplayName", "AWAY")),
                "abbrev": team_info.get("abbreviation", "A"),
                "score": c.get("score", "0"),
                "id": team_info.get("id", ""),
            }

    if not home_team or not away_team:
        return event

    # Fetch rosters via ESPN core API
    def fetch_roster_players(team_id: str) -> list:
        url = f"{ESPN_CORE}/sports/basketball/leagues/wnba/events/{event_id}/competitions/{event_id}/competitors/{team_id}/roster?lang=en&region=us"
        data = _get(url)
        if not data:
            return []
        entries = data.get("entries", [])
        # Filter to active players first
        active = [e for e in entries if e.get("active")]
        inactive = [e for e in entries if not e.get("active")]
        return active + inactive

    home_players_raw = fetch_roster_players(home_team["id"])
    away_players_raw = fetch_roster_players(away_team["id"])

    # Parse with ThreadPoolExecutor for speed
    home_players = []
    away_players = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_parse_wnba_player, p): ("home", p) for p in home_players_raw}
        futures.update({ex.submit(_parse_wnba_player, p): ("away", p) for p in away_players_raw})
        for f in as_completed(futures):
            side, _ = futures[f]
            player_data = f.result()
            if side == "home":
                home_players.append(player_data)
            else:
                away_players.append(player_data)

    return {
        "event_id": event_id,
        "shortName": short_name,
        "sport": "WNBA",
        "status": status.get("type", {}).get("name", "UNKNOWN"),
        "period": status.get("period", 0),
        "clock": status.get("displayClock", "0:00"),
        "home": {**home_team, "players": home_players},
        "away": {**away_team, "players": away_players},
    }


def fetch_mlb_boxscore(event: dict) -> dict:
    """Fetch full box score for an MLB event using ESPN site API boxscore."""
    event_id = event.get("id", "")
    short_name = event.get("shortName", "? @ ?")
    comps = event.get("competitions", [{}])[0]
    status = comps.get("status", {})
    competitors = comps.get("competitors", [])

    home_team = {}
    away_team = {}
    for c in competitors:
        side = c.get("homeAway", "")
        team_info = c.get("team", {})
        t = {
            "name": team_info.get("displayName", team_info.get("shortDisplayName", "??")),
            "abbrev": team_info.get("abbreviation", "?"),
            "score": c.get("score", "0"),
            "hits": c.get("hits", 0),
            "errors": c.get("errors", 0),
            "id": team_info.get("id", ""),
            "players": [],
        }
        if side == "home":
            home_team = t
        else:
            away_team = t

    # Use ESPN boxscore endpoint for batting stats
    boxscore_url = f"{ESPN_SITE}/sports/baseball/mlb/summary?event={event_id}"
    box_data = _get(boxscore_url)

    if box_data:
        bso = box_data.get("boxscore", {}) or {}
        bs_teams = bso.get("teams", [])
        for bst in bs_teams:
            team_info = bst.get("team", {})
            team_abbr = team_info.get("abbreviation", "")
            # Find matching team
            target = home_team if team_abbr == home_team.get("abbrev", "") else away_team

            for pl in bst.get("statistics", []):
                if pl.get("name") == "batting":
                    for stat in pl.get("stats", []):
                        target["batting_stats"] = stat

    # Also try core API for detailed lineup
    def fetch_roster(team_id: str) -> list:
        url = f"{ESPN_CORE}/sports/baseball/leagues/mlb/events/{event_id}/competitions/{event_id}/competitors/{team_id}/roster?lang=en&region=us"
        data = _get(url)
        if not data:
            return []
        return data.get("entries", [])

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(fetch_roster, home_team.get("id", "")): "home",
            ex.submit(fetch_roster, away_team.get("id", "")): "away",
        }
        for f in as_completed(futures):
            side = futures[f]
            players = []
            for entry in f.result():
                players.append(_parse_mlb_player(entry))
            if side == "home":
                home_team["players"] = sorted(players, key=lambda p: p.get("battingOrder", 99))
            else:
                away_team["players"] = sorted(players, key=lambda p: p.get("battingOrder", 99))

    return {
        "event_id": event_id,
        "shortName": short_name,
        "sport": "MLB",
        "status": status.get("type", {}).get("name", "UNKNOWN"),
        "period": status.get("period", 0),
        "clock": status.get("displayClock", "0:00"),
        "home": home_team,
        "away": away_team,
    }


def fetch_wc_boxscore(event: dict) -> dict:
    """Fetch full WC box score for a single event."""
    event_id = event["event_id"]
    cfg = LEAGUE_CONFIG["wc"]
    # Use ESPN summary endpoint for rosters
    summary_url = f"{ESPN_SITE}/sports/{cfg['core_sport']}/{cfg['core_league']}/summary"
    params = {"event": event_id}
    summary_resp = _get(f"{summary_url}?event={event_id}", ttl=30)
    
    players_by_team: Dict[str, List[dict]] = {"away": [], "home": []}
    
    if summary_resp:
        for slot in summary_resp.get("rostersByTeam", {}).get("home", {}).get("roster", []):
            players_by_team["home"].append(_parse_wc_player(slot, event["home"]["name"]))
        for slot in summary_resp.get("rostersByTeam", {}).get("away", {}).get("roster", []):
            players_by_team["away"].append(_parse_wc_player(slot, event["away"]["name"]))
    
    return {
        "event_id": event_id,
        "shortName": event["shortName"],
        "sport": "WC",
        "status": event["status"],
        "period": event.get("period", 0),
        "clock": event.get("clock", ""),
        "home": {
            "name": event["home"]["name"],
            "abbrev": event["home"]["abbrev"],
            "score": event["home"]["score"],
            "players": players_by_team["home"],
        },
        "away": {
            "name": event["away"]["name"],
            "abbrev": event["away"]["abbrev"],
            "score": event["away"]["score"],
            "players": players_by_team["away"],
        },
    }


def merge_tc_picks(boxscore: dict, picks_db: str) -> dict:
    """Merge TC picks from the database onto the box score players."""
    import sqlite3

    try:
        conn = sqlite3.connect(picks_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT date FROM picks ORDER BY date DESC LIMIT 1")
        latest_date = cursor.fetchone()
        today = latest_date["date"] if latest_date else datetime.now().strftime("%Y-%m-%d")

        cursor.execute(
            "SELECT player, stat, tc_projection, edge, direction, team FROM picks WHERE date = ?",
            (today,),
        )
        all_picks = cursor.fetchall()
        conn.close()
    except Exception:
        return boxscore

    # Build lookup: player_name -> {stat: pick_info}
    picks_by_player = {}
    for row in all_picks:
        name = row["player"]
        if name not in picks_by_player:
            picks_by_player[name] = []
        picks_by_player[name].append({
            "stat": row["stat"],
            "projection": row["tc_projection"],
            "edge": row["edge"],
            "direction": row["direction"],
            "team": row["team"],
        })

    for side_key in ["home", "away"]:
        for player in boxscore.get(side_key, {}).get("players", []):
            pname = player.get("name", "")
            player["tc_picks"] = picks_by_player.get(pname, [])
            alt_lines = {}
            for pick in player["tc_picks"]:
                proj = pick.get("projection", 0) or 0
                base_line = proj * 0.85 if proj else 0
                alt_lines[pick["stat"]] = [
                    {"label": "LOW", "line": round(base_line * 0.85, 1)},
                    {"label": "BASE", "line": round(base_line, 1)},
                    {"label": "HIGH", "line": round(base_line * 1.15, 1)},
                    {"label": "MAX", "line": round(base_line * 1.30, 1)},
                ]
            player["alt_lines"] = alt_lines

    return boxscore


def fetch_all_boxscores(sport: str = "all") -> dict:
    """Fetch box scores for all live/final events and cache."""
    cache_key = f"boxscore_{sport}_{datetime.now().strftime('%Y%m%d')}.json"
    cache_path = BOXSCORE_DIR / cache_key

    # Use cache if fresh (< 30s)
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL:
            with open(cache_path) as f:
                return json.load(f)

    result = {"sports": {}, "timestamp": datetime.now().isoformat()}

    if sport in ("all", "wnba"):
        wnba_events = fetch_wnba_live_events()
        wnba_boxes = []
        for event in wnba_events:
            box = fetch_wnba_boxscore(event)
            box = merge_tc_picks(box, str(Path("/home/workspace/Projects/data/picks.db")))
            wnba_boxes.append(box)
        result["sports"]["WNBA"] = {"game_count": len(wnba_boxes), "games": wnba_boxes}

    if sport in ("all", "mlb"):
        mlb_events = fetch_mlb_live_events()
        mlb_boxes = []
        for event in mlb_events[:8]:  # Limit to 8 for performance
            box = fetch_mlb_boxscore(event)
            box = merge_tc_picks(box, str(Path("/home/workspace/Projects/data/picks.db")))
            mlb_boxes.append(box)
        result["sports"]["MLB"] = {"game_count": len(mlb_boxes), "games": mlb_boxes}

    if sport in ("all", "wc"):
        wc_events = fetch_wc_live_events()
        wc_boxes = []
        for event in wc_events:
            box = fetch_wc_boxscore(event)
            wc_boxes.append(box)
        result["sports"]["WC"] = {"game_count": len(wc_boxes), "games": wc_boxes}

    # Cache
    with open(cache_path, "w") as f:
        json.dump(result, f, default=str)

    return result


if __name__ == "__main__":
    data = fetch_all_boxscores("all")
    print(json.dumps(data, indent=2, default=str)[:5000])
