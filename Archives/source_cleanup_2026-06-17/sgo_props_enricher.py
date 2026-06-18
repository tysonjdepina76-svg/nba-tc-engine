#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
SGO Player Props Enricher — extracts DK player prop lines from SportsGameOdds data
and enriches the daily picks pipeline with live lines for NBA (WNBA unavailable at current tier).

Usage:
    from sgo_props_enricher import enrich_from_sgo
    result = enrich_from_sgo("NBA", "NYK", "SAS")
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
import requests

# Load secrets at module level
try:
    _sec = Path("/root/.zo/secrets.env")
    if _sec.exists():
        for _line in _sec.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except Exception:
    pass

SGO_API_KEY = os.environ.get("SPORTSGAMEODDS_API_KEY", "")
SGO_BASE = "https://api.sportsgameodds.com/v2"

STAT_MAP = {
    "points": "PTS",
    "rebounds": "REB",
    "assists": "AST",
    "steals": "STL",
    "blocks": "BLK",
    "threePointersMade": "3PM",
    "points+rebounds+assists": "PRA",
    "points+rebounds": "PR",
    "points+assists": "PA",
}

def _match_team(ev_team_short, our_code):
    """Fuzzy match SGO short codes to our 3-letter codes."""
    a = str(ev_team_short or "").upper().strip()
    b = str(our_code or "").upper().strip()
    aliases = {"SA": "SAS", "NY": "NYK", "NO": "NOP", "UTAH": "UTA", 
               "WASH": "WAS", "WS": "WSH", "LVA": "LV", "LAS": "LA", 
               "NYL": "NY", "GSW": "GS"}
    a = aliases.get(a, a)
    b = aliases.get(b, b)
    return a == b or a in b or b in a

def _find_sgo_event(sport, away, home):
    """Find the SGO event for a matchup."""
    if not SGO_API_KEY:
        return None
    league_map = {"NBA": "NBA", "WNBA": "WNBA"}
    league = league_map.get(sport.upper())
    if not league:
        return None
    
    try:
        r = requests.get(
            f"{SGO_BASE}/events",
            params={"leagueID": league},
            headers={"X-Api-Key": SGO_API_KEY, "Accept": "application/json"},
            timeout=15,
        )
        if not r.ok:
            return None
        
        events = r.json().get("data", [])
        for ev in events:
            ht = ev.get("teams", {}).get("home", {}).get("names", {}).get("short", "")
            at = ev.get("teams", {}).get("away", {}).get("names", {}).get("short", "")
            if _match_team(ht, home) and _match_team(at, away):
                return ev
        return None
    except Exception:
        return None

def _extract_player_props(event_data):
    """Extract player prop lines from SGO odds dictionary.
    
    SGO stores odds as keys like: points-JALEN_BRUNSON_1_NBA-game-ou-over
    Returns: { "Player Name": { "PTS": 13.5, "REB": 0.5, ... } }
    """
    odds = event_data.get("odds", {})
    players = {}
    
    for odd_key, odd_val in odds.items():
        if not isinstance(odd_val, dict):
            continue
        
        player_id = odd_val.get("playerID") or odd_val.get("statEntityID")
        if not player_id or player_id in ("away", "home", "all"):
            continue
        
        bet_type = odd_val.get("betTypeID", "")
        if bet_type != "ou":  # Only over/under lines
            continue
        
        stat_id = odd_val.get("statID", "")
        dk_stat = STAT_MAP.get(stat_id)
        if not dk_stat:
            continue
        
        line = odd_val.get("bookOverUnder")
        if line is None:
            continue
        
        odds_val = odd_val.get("bookOdds")
        
        # Normalize player name from SGO ID like JALEN_BRUNSON_1_NBA
        name = player_id.replace("_1_NBA", "").replace("_1_WNBA", "")
        name = name.replace("_", " ").title()
        # Fix common SGO capitalization issues
        name_fixes = {
            "Karlanthony Towns": "Karl-Anthony Towns",
            "Deaaron Fox": "De'Aaron Fox",
            "Og Anunoby": "OG Anunoby",
            "Mikal Bridges": "Mikal Bridges",
        }
        name = name_fixes.get(name, name)
        
        if name not in players:
            players[name] = {"_source": "SGO", "_book": "draftkings"}
        
        players[name][dk_stat] = float(line)
        if odds_val:
            players[name][f"{dk_stat}_odds"] = str(odds_val)
    
    return players

def _normalize_name(n):
    """Normalize a player name for fuzzy matching."""
    return str(n or "").lower().replace("-", "").replace("'", "").replace(".", "").replace(" ", "").strip()

def enrich_from_sgo(sport, away, home):
    """
    Main entry point. Returns dict with player_lines for matching against TC projections.
    
    Returns:
        { player_lines: { "Player Name": { "PTS": 13.5, ... } }, player_count: N, source: "sgo" }
        or { error: "...", player_lines: {}, source: "error" }
    """
    if sport.upper() == "WNBA":
        return {"error": "SGO WNBA unavailable at current tier", "player_lines": {}, "source": "sgo_wnba_unavailable"}
    
    if not SGO_API_KEY:
        return {"error": "SPORTSGAMEODDS_API_KEY not set", "player_lines": {}, "source": "sgo_no_key"}
    
    try:
        event = _find_sgo_event(sport, away, home)
        if not event:
            return {"error": f"No SGO event for {away}@{home}", "player_lines": {}, "source": "sgo_no_match"}
        
        player_lines = _extract_player_props(event)
        
        return {
            "player_lines": player_lines,
            "player_count": len(player_lines),
            "source": "sgo",
            "event_id": event.get("eventID"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "player_lines": {}, "source": "sgo_error"}


def match_line_to_pick(player_name, stat, player_lines):
    """Match a TC pick against SGO player props using fuzzy name matching.
    
    Args:
        player_name: Name from ESPN roster (e.g., "Jalen Brunson")
        stat: TC stat key (e.g., "PTS", "REB", "AST")
        player_lines: Dict from enrich_from_sgo
    
    Returns:
        (line_value, odds_value) or (None, None) if no match
    """
    if not player_lines:
        return None, None
    
    # Direct match
    if player_name in player_lines:
        pl = player_lines[player_name]
        return pl.get(stat), pl.get(f"{stat}_odds")
    
    # Fuzzy match
    norm_name = _normalize_name(player_name)
    for sgo_name, props in player_lines.items():
        norm_sgo = _normalize_name(sgo_name)
        if norm_name == norm_sgo or norm_name in norm_sgo or norm_sgo in norm_name:
            return props.get(stat), props.get(f"{stat}_odds")
    
    return None, None


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "NBA"
    away = sys.argv[2] if len(sys.argv) > 2 else "NYK"
    home = sys.argv[3] if len(sys.argv) > 3 else "SAS"
    
    result = enrich_from_sgo(sport, away, home)
    print(json.dumps(result, indent=2))
