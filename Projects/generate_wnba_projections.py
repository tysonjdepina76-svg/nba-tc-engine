#!/usr/bin/env python3
"""ESPN-native WNBA projection generator — no Odds API needed.
Fetches rosters + season stats (from ESPN + wnba_stats.db + combo stats),
generates TC projections, saves proj_WNBA_*.json files for daily_picks.py."""

import json
import os
import sys
from datetime import date
from pathlib import Path
import httpx
import duckdb

DAILY_LOG = Path("/home/workspace/Daily_Log")
WOMENS_DB = Path("/home/workspace/wnba_stats.db")
COMBO_CSV = Path("/home/workspace/Daily_Log/wnba_combo_stats_full_2026-07-18.csv")

ESPN_SCOREBARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
ESPN_SUMMARY  = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"

# WNBA season average stats per team (from ESPN / DB — fallback for missing)
SEASON_DEFAULTS = {
    "PTS": 10.5, "AST": 2.5, "REB": 3.5, "STL": 0.8, "BLK": 0.4,
    "TO": 1.5, "3PM": 1.2, "FGM": 4.0, "FGA": 9.0, "FTM": 1.5, "FTA": 2.0
}

def load_player_combo_db():
    """Load player combo stats from CSV + DB."""
    players = {}

    # Try DuckDB first
    if WOMENS_DB.exists():
        try:
            db = duckdb.connect(str(WOMENS_DB), read_only=True)
            rows = db.execute("""
                SELECT DISTINCT name, team, ppg, apg, rpg, bpg, spg, tpg, threes_pg, fg_pct, ft_pct, mpg
                FROM player_games
                ORDER BY name
            """).fetchall()
            for r in rows:
                name, team, pts, ast, reb, blk, stl, tov, threes, fgp, ftp, minutes = r
                players[name.lower()] = {
                    "name": name, "team": team,
                    "PTS": float(pts or 0), "AST": float(ast or 0),
                    "REB": float(reb or 0), "BLK": float(blk or 0),
                    "STL": float(stl or 0), "TO": float(tov or 0),
                    "3PM": float(threes or 0), "fg_pct": float(fgp or 0),
                    "ft_pct": float(ftp or 0), "MIN": float(minutes or 0),
                }
            db.close()
        except Exception:
            pass

    # Try combo stats CSV
    if COMBO_CSV.exists():
        try:
            with open(COMBO_CSV) as f:
                header = f.readline().strip().split(",")
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) < 6:
                        continue
                    name = parts[0].strip()
                    team = parts[1].strip() if len(parts) > 1 else ""
                    ppg = float(parts[2]) if len(parts) > 2 else 0
                    apg = float(parts[3]) if len(parts) > 3 else 0
                    rpg = float(parts[4]) if len(parts) > 4 else 0
                    key = name.lower()
                    if key not in players:
                        players[key] = {"name": name, "team": team}
                    players[key]["PTS"] = max(players[key].get("PTS", 0), ppg)
                    players[key]["AST"] = max(players[key].get("AST", 0), apg)
                    players[key]["REB"] = max(players[key].get("REB", 0), rpg)
        except Exception:
            pass

    return players


def fetch_roster(event_id):
    """Fetch roster from ESPN summary endpoint."""
    url = f"{ESPN_SUMMARY}?event={event_id}"
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        data = resp.json()
        roster = []
        for team_key in ("boxscore",):
            bs = data.get(team_key, {})
            players_data = bs.get("players", [])
            for team_entry in players_data:
                team_info = team_entry.get("team", {})
                team_abbr = team_info.get("abbreviation", "")
                for stat_entry in team_entry.get("statistics", []):
                    for athlete in stat_entry.get("athletes", []):
                        ath = athlete.get("athlete", {})
                        stats_list = athlete.get("stats", [])
                        name = ath.get("displayName", "")
                        stats_map = {}
                        for s in stats_list:
                            stats_map[s.get("name", "")] = s.get("value", 0) or 0
                        if name and team_abbr:
                            roster.append({
                                "name": name,
                                "team": team_abbr,
                                "PTS": float(stats_map.get("pointsPerGame", 0)),
                                "AST": float(stats_map.get("assistsPerGame", 0)),
                                "REB": float(stats_map.get("reboundsPerGame", 0)),
                                "STL": float(stats_map.get("stealsPerGame", 0)),
                                "BLK": float(stats_map.get("blocksPerGame", 0)),
                                "TO": float(stats_map.get("turnoversPerGame", 0)),
                                "3PM": float(stats_map.get("threePointersPerGame", 0)),
                                "FGM": float(stats_map.get("fieldGoalsPerGame", 0)),
                                "FGA": float(stats_map.get("fieldGoalsAttemptedPerGame", 0)),
                                "MIN": float(stats_map.get("minutesPerGame", 0)),
                            })
        return roster
    except Exception as e:
        print(f"  ⚠️ Failed roster fetch: {e}")
        return []


def generate_projections(roster, combo_db):
    """Generate TC projections with self-edge lines."""
    projections = []
    for player in roster:
        name = player["name"]
        team = player["team"]
        key = name.lower()

        # Merge with combo DB
        db_entry = combo_db.get(key, {})
        stats = {**SEASON_DEFAULTS}
        for stat in ["PTS", "AST", "REB", "STL", "BLK", "TO", "3PM", "MIN"]:
            v = player.get(stat, 0) or 0
            if v <= 0:
                v = db_entry.get(stat, 0) or 0
            if v <= 0:
                v = SEASON_DEFAULTS.get(stat, 0)
            stats[stat] = max(v, SEASON_DEFAULTS.get(stat, 0))

        # Generate combo projections
        pts = stats["PTS"]
        ast = stats["AST"]
        reb = stats["REB"]
        stl = stats["STL"]
        blk = stats["BLK"]
        tov = stats["TO"]
        threes = stats["3PM"]
        minutes = stats.get("MIN", 25)

        # Apply TC adjustments (conservative 90% of season avg)
        tc_adj = 0.90

        entries = []
        # PTS
        proj_pts = round(pts * tc_adj, 1)
        entries.append({"stat": "PTS", "projection": proj_pts, "line": round(pts * 0.95, 1)})
        # AST
        proj_ast = round(ast * tc_adj, 1)
        entries.append({"stat": "AST", "projection": proj_ast, "line": round(ast * 0.95, 1)})
        # REB
        proj_reb = round(reb * tc_adj, 1)
        entries.append({"stat": "REB", "projection": proj_reb, "line": round(reb * 0.95, 1)})
        # P+A
        proj_pa = round((pts + ast) * tc_adj, 1)
        entries.append({"stat": "P+A", "projection": proj_pa, "line": round((pts + ast) * 0.95, 1)})
        # P+R
        proj_pr = round((pts + reb) * tc_adj, 1)
        entries.append({"stat": "P+R", "projection": proj_pr, "line": round((pts + reb) * 0.95, 1)})
        # R+A
        proj_ra = round((reb + ast) * tc_adj, 1)
        entries.append({"stat": "R+A", "projection": proj_ra, "line": round((reb + ast) * 0.95, 1)})
        # P+R+A
        proj_pra = round((pts + reb + ast) * tc_adj, 1)
        entries.append({"stat": "P+R+A", "projection": proj_pra, "line": round((pts + reb + ast) * 0.95, 1)})
        # STL
        proj_stl = round(stl * tc_adj, 1)
        entries.append({"stat": "STL", "projection": proj_stl, "line": round(stl * 0.90, 1)})
        # BLK
        proj_blk = round(blk * tc_adj, 1)
        entries.append({"stat": "BLK", "projection": proj_blk, "line": round(blk * 0.90, 1)})
        # 3PM
        proj_3pm = round(threes * tc_adj, 1)
        entries.append({"stat": "3PM", "projection": proj_3pm, "line": round(threes * 0.90, 1)})

        projections.append({
            "name": name,
            "team": team,
            "entries": entries,
            "season_avg": {
                "PTS": pts, "AST": ast, "REB": reb, "STL": stl,
                "BLK": blk, "TO": tov, "3PM": threes, "MIN": minutes
            }
        })

    return projections


def fetch_games(game_date=None):
    """Fetch WNBA games from ESPN scoreboard."""
    if game_date is None:
        game_date = date.today().isoformat().replace("-", "")
    url = f"{ESPN_SCOREBARD}?dates={game_date}"
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        data = resp.json()
        games = []
        for event in data.get("events", []):
            comps = event.get("competitions", [])
            if comps:
                c = comps[0]
                away = c["competitors"][1]
                home = c["competitors"][0]
                games.append({
                    "event_id": event["id"],
                    "away": away["team"]["abbreviation"],
                    "home": home["team"]["abbreviation"],
                    "matchup": f"{away['team']['abbreviation']}@{home['team']['abbreviation']}",
                    "status": c.get("status", {}).get("type", {}).get("name", "UNKNOWN"),
                })
        return games
    except Exception as e:
        print(f"⚠️ Failed fetch games: {e}")
        return []


def generate_wnba(game_date=None):
    """Main entry point — generate WNBA projections."""
    if game_date is None:
        game_date = date.today().isoformat()
        date_str = game_date.replace("-", "")
    else:
        date_str = game_date.replace("-", "")

    print(f"\n{'='*60}")
    print(f"WNBA PROJECTIONS: {game_date}")
    print(f"{'='*60}")

    games = fetch_games(date_str)
    if not games:
        print("❌ No games found")
        return []

    print(f"  Found {len(games)} games: {[g['matchup'] for g in games]}")

    combo_db = load_player_combo_db()
    print(f"  Loaded {len(combo_db)} players from stat DB")

    date_dir = DAILY_LOG / game_date
    date_dir.mkdir(parents=True, exist_ok=True)

    all_projections = []
    for game in games:
        print(f"  Game: {game['matchup']} (ID: {game['event_id']})")
        roster = fetch_roster(game["event_id"])
        print(f"    Fetched {len(roster)} players from ESPN roster")

        if not roster:
            # Fallback: use combo DB for these teams
            away_team = game["away"]
            home_team = game["home"]
            roster = []
            for key, entry in combo_db.items():
                if entry.get("team", "") in (away_team, home_team):
                    roster.append({
                        "name": entry["name"],
                        "team": entry.get("team", ""),
                        "PTS": entry.get("PTS", 0),
                        "AST": entry.get("AST", 0),
                        "REB": entry.get("REB", 0),
                        "STL": entry.get("STL", 0),
                        "BLK": entry.get("BLK", 0),
                        "TO": entry.get("TO", 0),
                        "3PM": entry.get("3PM", 0),
                        "MIN": entry.get("MIN", 0),
                    })
            print(f"    Used combo DB fallback — {len(roster)} players")

            if not roster:
                WNBA_STAR_FALLBACK = [
                    ("A'ja Wilson", "LV"), ("Breanna Stewart", "NY"), ("Sabrina Ionescu", "NY"),
                    ("Caitlin Clark", "IND"), ("Arike Ogunbowale", "DAL"), ("Napheesa Collier", "MIN"),
                    ("Kahleah Copper", "PHX"), ("Jewell Loyd", "LV"), ("Kelsey Plum", "LA"),
                    ("Brittney Griner", "PHX"), ("Nneka Ogwumike", "SEA"), ("Skylar Diggins-Smith", "DAL"),
                    ("Dearica Hamby", "LA"), ("Jackie Young", "LV"), ("Chelsea Gray", "LV"),
                    ("Jonquel Jones", "NY"), ("Courtney Vandersloot", "NY"), ("Betnijah Laney", "NY"),
                    ("Allisha Gray", "ATL"), ("Marina Mabrey", "CON"), ("DeWanna Bonner", "CON"),
                    ("Aliyah Boston", "IND"), ("Kelsey Mitchell", "IND"), ("Erica Wheeler", "IND"),
                    ("Rhyne Howard", "ATL"), ("Cheyenne Parker", "ATL"), ("Ezi Magbegor", "SEA"),
                    ("Satou Sabally", "DAL"), ("Teaira McCowan", "DAL"), ("Elena Delle Donne", "WSH"),
                    ("Shakira Austin", "WSH"), ("Ariel Atkins", "WSH"), ("Diana Taurasi", "PHX"),
                    ("Alyssa Thomas", "CON"), ("Brionna Jones", "CON"), ("Natasha Howard", "DAL"),
                    ("Kayla McBride", "MIN"), ("Diamond DeShields", "CHI"), ("Candace Parker", "LV"),
                    ("Azura Stevens", "LA"), ("Lexie Brown", "LA"), ("Jordin Canada", "LA"),
                ]
                for name, team_abbr in WNBA_STAR_FALLBACK:
                    if team_abbr in (away_team, home_team):
                        key = name.lower()
                        entry = combo_db.get(key, {})
                        roster.append({
                            "name": name, "team": team_abbr,
                            "PTS": entry.get("PTS", 15),
                            "AST": entry.get("AST", 3),
                            "REB": entry.get("REB", 5),
                            "STL": entry.get("STL", 1),
                            "BLK": entry.get("BLK", 0.5),
                            "TO": entry.get("TO", 2),
                            "3PM": entry.get("3PM", 1),
                            "MIN": entry.get("MIN", 30),
                        })
                print(f"    Used hardcoded star fallback — {len(roster)} players")

        projs = generate_projections(roster, combo_db)
        all_projections.extend(projs)

        matchup_key = game["matchup"]
        output = {"game": game, "projections": projs, "generated_at": game_date}
        outpath = date_dir / f"proj_WNBA_{matchup_key}.json"
        with open(outpath, "w") as f:
            json.dump(output, f, indent=2)
        print(f"    ✅ Saved {outpath} ({len(projs)} players)")

    # Combined file
    combined_path = date_dir / f"proj_WNBA_{game_date}.json"
    all_output = {"games": games, "projections": all_projections, "generated_at": game_date}
    with open(combined_path, "w") as f:
        json.dump(all_output, f, indent=2)
    print(f"  ✅ Combined: {combined_path} ({len(all_projections)} total players)")

    return all_projections


if __name__ == "__main__":
    dt = sys.argv[1] if len(sys.argv) > 1 else None
    generate_wnba(dt)
