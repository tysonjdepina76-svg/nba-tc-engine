#!/usr/bin/env python3
"""Generate WNBA projection files for daily_picks.py.

Fetches ESPN rosters + season combo stats, outputs the nested
projections format that load_projections() expects:
  {"player": "A'ja Wilson", "team": "IND", "projections": {"points": {tc_projection:..., line:0, edge:..., direction:"OVER"}, ...}}

Usage:
  python3 gen_wnba_projections.py                    # today's games
  python3 gen_wnba_projections.py --date 2026-07-19  # specific date
"""

import json
import os
import sys
import requests
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

# ── paths ──────────────────────────────────────────────────────────────
LOG_DIR = Path("/home/workspace/Daily_Log")
COMBOS = LOG_DIR / "wnba_combo_stats_2026-07-18.csv"

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"

# ── scraper helpers ────────────────────────────────────────────────────
def fetch_espn_games(target_date: str) -> list:
    """Return list of dicts: {home_team, away_team, home_abbr, away_abbr, game_id}"""
    url = f"{ESPN_SCOREBOARD}?dates={target_date.replace('-', '')}"
    resp = requests.get(url, timeout=15)
    data = resp.json()

    games = []
    for ev in data.get("events", []):
        comps = ev.get("competitions", [{}])
        if not comps:
            continue
        c = comps[0]
        teams = c.get("competitors", [])
        if len(teams) < 2:
            continue

        home = next((t for t in teams if t.get("homeAway") == "home"), None)
        away = next((t for t in teams if t.get("homeAway") == "away"), None)
        if not home or not away:
            continue

        games.append({
            "game_id": ev.get("id", ""),
            "home_team": home.get("team", {}).get("displayName", ""),
            "away_team": away.get("team", {}).get("displayName", ""),
            "home_abbr": home.get("team", {}).get("abbreviation", ""),
            "away_abbr": away.get("team", {}).get("abbreviation", ""),
        })
    return games


def fetch_espn_rosters(game_id: str) -> dict:
    """Return {home: [player_names], away: [player_names]} from summary."""
    url = f"{ESPN_SUMMARY}?event={game_id}"
    resp = requests.get(url, timeout=15)
    data = resp.json()

    rosters = {"home": [], "away": []}
    for team_data in data.get("boxscore", {}).get("teams", []):
        ha = team_data.get("homeAway", "")
        for stat_entry in team_data.get("statistics", []):
            names = stat_entry.get("names", [])
            athletes = stat_entry.get("athletes", [])
            for entry in athletes:
                name = entry.get("athlete", {}).get("displayName", "")
                if name:
                    rosters[ha].append(name)

    home_team = data.get("gamepackageJSON", {}).get("header", {}).get("competitions", [{}])[0].get("competitors", [])
    if not rosters["home"] and not rosters["away"]:
        # fallback: use header
        for c in home_team:
            ha = c.get("homeAway", "")
            for player_entry in c.get("roster", []):
                name = player_entry.get("athlete", {}).get("displayName", "")
                if name:
                    rosters[ha].append(name)

    return rosters


def normalize(n: str) -> str:
    """Normalize a player name for fuzzy matching."""
    return n.lower().strip().replace(".", "").replace("'", "").replace("-", " ").replace("  ", " ")


def load_combo_stats() -> dict:
    """Load combo stats CSV, return {normalized_name: {points, assists, total_rebounds, PRA, PR, PA, RA, team_abbr}}"""
    out = {}
    if not COMBOS.exists():
        print(f"⚠️  Combo stats not found: {COMBOS}")
        return out

    with open(COMBOS) as f:
        header = next(f).strip().split(",")

    col_map = {}
    for i, h in enumerate(header):
        col_map[h.strip().lower().replace(" ", "_")] = i

    pts_idx = col_map.get("pts")
    ast_idx = col_map.get("ast")
    reb_idx = col_map.get("reb")
    team_idx = col_map.get("team")
    name_idx = col_map.get("player")

    if None in (pts_idx, ast_idx, reb_idx, name_idx):
        print(f"⚠️  Missing required columns in combo stats")
        return out

    with open(COMBOS) as f:
        next(f)  # skip header
        for line in f:
            cols = line.strip().split(",")
            if len(cols) < max(pts_idx, ast_idx, reb_idx, name_idx) + 1:
                continue
            try:
                name = cols[name_idx].strip()
                pts = float(cols[pts_idx])
                ast = float(cols[ast_idx])
                reb = float(cols[reb_idx])
                team = cols[team_idx].strip() if team_idx is not None and team_idx < len(cols) else ""
            except (ValueError, IndexError):
                continue

            out[normalize(name)] = {
                "name": name,
                "team": team,
                "points": round(pts, 1),
                "assists": round(ast, 1),
                "total_rebounds": round(reb, 1),
                "PRA": round(pts + ast + reb, 1),
                "PR": round(pts + reb, 1),
                "PA": round(pts + ast, 1),
                "RA": round(ast + reb, 1),
            }

    return out


# ── main ───────────────────────────────────────────────────────────────
def main(target_date: str = None):
    if target_date is None:
        target_date = date.today().isoformat()

    log_dir = LOG_DIR / target_date
    log_dir.mkdir(parents=True, exist_ok=True)

    # 1. Get games
    print(f"📡 Fetching WNBA games for {target_date}...")
    games = fetch_espn_games(target_date)
    print(f"   Found {len(games)} games")

    if not games:
        print("❌ No WNBA games today")
        return

    # 2. Load combo stats
    print(f"📊 Loading combo stats...")
    combo_map = load_combo_stats()
    print(f"   {len(combo_map)} players in combo DB")

    all_players = []
    matchup_player_count = {}

    for g in games:
        home_abbr = g["home_abbr"]
        away_abbr = g["away_abbr"]
        matchup_key = f"{away_abbr}@{home_abbr}"
        print(f"\n🔍 {matchup_key}: {g['away_team']} @ {g['home_team']}")

        # 3. Fetch rosters
        rosters = fetch_espn_rosters(g["game_id"])
        home_players = rosters.get("home", [])
        away_players = rosters.get("away", [])

        if not home_players and not away_players:
            print(f"   ⚠️  No rosters found, falling back to combo stat players by team")
            # Fallback: use all combo players on these teams
            for norm_name, stats in combo_map.items():
                team_abbr = stats["team"].upper()
                if team_abbr in (home_abbr.upper(), away_abbr.upper()):
                    home_players.append(stats["name"]) if team_abbr == home_abbr.upper() else away_players.append(stats["name"])

        print(f"   Home roster ({home_abbr}): {len(home_players)} players")
        print(f"   Away roster ({away_abbr}): {len(away_players)} players")

        game_players = []

        for side, team_abbr in [(home_players, home_abbr), (away_players, away_abbr)]:
            for player_name in side:
                norm = normalize(player_name)
                stats = combo_map.get(norm)
                if not stats:
                    continue

                proj = {}
                for stat_key in ("points", "assists", "total_rebounds", "PRA", "PR", "PA", "RA"):
                    val = stats.get(stat_key, 0)
                    if val > 0:
                        proj[stat_key] = {
                            "tc_projection": val,
                            "line": 0,
                            "edge": round(val, 1),
                            "direction": "OVER",
                        }

                if proj:
                    game_players.append({
                        "player": stats["name"],
                        "team": team_abbr,
                        "projections": proj,
                    })

        print(f"   ✅ {len(game_players)} players matched")

        if game_players:
            proj_file = log_dir / f"proj_WNBA_{matchup_key}.json"
            with open(proj_file, "w") as f:
                json.dump({
                    "date": target_date,
                    "sport": "WNBA",
                    "matchup": matchup_key,
                    "away": g["away_team"],
                    "home": g["home_team"],
                    "players": game_players,
                }, f, indent=2)
            print(f"   📁 Saved → {proj_file}")
            all_players.extend(game_players)
            matchup_player_count[matchup_key] = len(game_players)

    # Combined file
    if all_players:
        combined = log_dir / "proj_WNBA_merged.json"
        with open(combined, "w") as f:
            json.dump({
                "date": target_date,
                "sport": "WNBA",
                "matchup": "merged",
                "players": all_players,
            }, f, indent=2)
        print(f"\n✅ Combined: {len(all_players)} total players → {combined}")
    else:
        print("\n❌ No WNBA projections generated")


if __name__ == "__main__":
    target = None
    if len(sys.argv) > 2 and sys.argv[1] == "--date":
        target = sys.argv[2]
    main(target)
