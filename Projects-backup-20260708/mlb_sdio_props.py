#!/usr/bin/env python3
"""MLB SportsDataIO Player Props Fetcher
Fetches real DK-style player props from SportsDataIO (unlimited paid tier)
and maps them to ESPN team codes + player names for TC engine enrichment.

Usage:
  from mlb_sdio_props import fetch_mlb_props
  props = fetch_mlb_props()  # returns {matchup: {player_name: {stat: line}}}

Stat mapping:
  SDIO Description           → TC stat key         → Category
  ───────────────────────────────────────────────────────────
  Hits                        → hits                → BATTER
  Total Bases                 → total_bases         → BATTER
  Runs                        → runs                → BATTER
  Home Runs                   → hr                  → BATTER
  Runs Batted In              → rbi                 → BATTER
  Strikeouts                  → strikeouts          → PITCHER
  Pitching Hits               → hits_allowed        → PITCHER
  Pitching Runs               → earned_runs         → PITCHER
  Pitching Strikeouts         → strikeouts          → PITCHER
  Fantasy Points              → (skipped)           → N/A
"""

import json
import os
import urllib.request
from datetime import datetime
from typing import Dict, Optional

SDIO_BASE = "https://api.sportsdata.io/v3/mlb/odds/json"

STAT_MAP = {
    "Hits": "hits",
    "Total Bases": "total_bases",
    "Runs": "runs",
    "Home Runs": "hr",
    "Runs Batted In": "rbi",
    "Strikeouts": "strikeouts",
    "Pitching Hits": "hits_allowed",
    "Pitching Runs": "earned_runs",
    "Pitching Strikeouts": "strikeouts",
}

SDIO_KEY = None

def _get_key():
    global SDIO_KEY
    if SDIO_KEY is not None:
        return SDIO_KEY
    SDIO_KEY = os.environ.get("SPORTSDATAIO_API_KEY", "")
    if not SDIO_KEY:
        sp = os.path.expanduser("/root/.zo/secrets.env")
        if os.path.exists(sp):
            for line in open(sp):
                if "SPORTSDATAIO" in line and "=" in line:
                    SDIO_KEY = line.split("=", 1)[1].strip().strip('"').strip("'").strip("\n")
                    break
    return SDIO_KEY

def fetch_mlb_props(date_str: str = None) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Fetch player props for a date. Returns {matchup: {player_name: {stat: line}}}."""
    key = _get_key()
    if not key:
        return {}

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    url = f"{SDIO_BASE}/PlayerPropsByDate/{date_str}"
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": key})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_props = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  ⚠ SDIO props fetch failed: {e}")
        return {}

    props_by_matchup: Dict[str, Dict[str, Dict[str, float]]] = {}

    for prop in raw_props:
        desc = prop.get("Description", "")
        tc_stat = STAT_MAP.get(desc)
        if tc_stat is None:
            continue

        player_name = (prop.get("Name") or "").strip().lower()
        team_code = (prop.get("Team") or "").strip().upper()
        opponent = (prop.get("Opponent") or "").strip().upper()
        line_val = prop.get("OverUnder")

        if not player_name or not team_code or line_val is None:
            continue

        matchup = f"{team_code}@{opponent}" if team_code < opponent else f"{opponent}@{team_code}"

        try:
            line = float(line_val)
        except (ValueError, TypeError):
            continue

        if matchup not in props_by_matchup:
            props_by_matchup[matchup] = {}
        if player_name not in props_by_matchup[matchup]:
            props_by_matchup[matchup][player_name] = {}

        if tc_stat not in props_by_matchup[matchup][player_name]:
            props_by_matchup[matchup][player_name][tc_stat] = line

    return props_by_matchup

def enrich_player_lines(matchup: str, players: list) -> list:
    """Add SDIO market lines to player projections. Returns enriched players list."""
    props = fetch_mlb_props()
    matchup_lines = props.get(matchup, {})
    if not matchup_lines:
        return players

    for player in players:
        pid = player.get("id") or player.get("name", "").lower()
        pname = player.get("name", "").strip().lower()
        pteam = player.get("team", "").strip().upper()

        sdio_lines = matchup_lines.get(pname, {})
        if not sdio_lines:
            sdio_lines = matchup_lines.get(pid, {})

        for stat, line_val in sdio_lines.items():
            tc_key = f"tc_{stat}"
            line_key = f"line_{stat}"
            edge_key = f"edge_{stat}"

            if line_key in player:
                current_line = player.get(line_key)
                if current_line is None or (isinstance(current_line, (int, float)) and current_line == 0):
                    player[line_key] = line_val
                    tc_val = player.get(tc_key, 0)
                    if isinstance(tc_val, (int, float)):
                        player[edge_key] = round(tc_val - line_val, 1)

        player["_sdio_enriched"] = bool(sdio_lines)

    return players

if __name__ == "__main__":
    props = fetch_mlb_props()
    total_matches = len(props)
    total_players = sum(len(p) for p in props.values())
    total_lines = sum(sum(len(s) for s in p.values()) for p in props.values())
    print(f"SDIO MLB Props: {total_matches} games, {total_players} players, {total_lines} lines")
    for m, players in sorted(props.items()):
        print(f"  {m}: {len(players)} players, {sum(len(s) for s in players.values())} lines")
