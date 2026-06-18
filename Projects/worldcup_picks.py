#!/usr/bin/env python3

# TC — Triple Conservative — Trademark June 2026 — All rights reserved.
"""
World Cup 2026 Daily Pick Scraper — completely standalone, zero impact on basketball pipeline.

Pulls:
  - Match schedule + live scores from ESPN (free)
  - DK player props (goals, assists, shots_on_target, shots) from The Odds API (free tier)

Writes:
  - Daily_Log/worldcup/YYYY-MM-DD/matches.json   — raw match data
  - Daily_Log/worldcup/YYYY-MM-DD/props.json     — player props by match
  - Daily_Log/worldcup/YYYY-MM-DD/picks.csv      — flat prop table
  - Daily_Log/worldcup/last_run.json             — summary

Usage:
  python3 /home/workspace/Projects/worldcup_picks.py
  python3 /home/workspace/Projects/worldcup_picks.py --date 2026-06-14
"""

import os, sys, json, csv, argparse, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Secrets ---
WORKSPACE = Path("/home/workspace")
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

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_BASE = "https://api.the-odds-api.com/v4"
SPORT_KEY = "soccer_fifa_world_cup"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

LOG_DIR = WORKSPACE / "Daily_Log" / "worldcup"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# DK player prop markets available for World Cup on the free tier
PROP_MARKETS = [
    "player_goals",
    "player_assists",
    "player_shots_on_target",
    "player_shots",
    "player_tackles",
    "player_fouls",
]
# Books to try in priority order
BOOK_PRIORITY = ["fanduel", "draftkings", "betmgm", "caesars", "fanatics"]


def fetch_espn_matches(date_str=None):
    """Fetch World Cup matches from ESPN for a given date (YYYYMMDD)."""
    url = ESPN_SCOREBOARD
    if date_str:
        url += f"?dates={date_str}"
    try:
        r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
        events = data.get("events", [])
        matches = []
        for e in events:
            status = e.get("status", {}).get("type", {})
            comps = e.get("competitions", [])
            teams = []
            for c in comps:
                for co in c.get("competitors", []):
                    team = co.get("team", {})
                    teams.append({
                        "name": team.get("displayName", ""),
                        "abbrev": team.get("abbreviation", ""),
                        "score": co.get("score", "0"),
                        "homeAway": co.get("homeAway", ""),
                    })
            matches.append({
                "espn_id": e.get("id", ""),
                "name": e.get("name", ""),
                "short_name": e.get("shortName", ""),
                "date": e.get("date", ""),
                "status": status.get("description", ""),
                "status_detail": status.get("shortDetail", ""),
                "completed": status.get("completed", False),
                "period": status.get("period", 0),
                "teams": teams,
            })
        return matches
    except Exception as exc:
        print(f"ESPN error: {exc}")
        return []


def norm_team_name(name):
    """Normalize team names for cross-matching ESPN ↔ Odds API."""
    if not name:
        return ""
    n = name.lower().strip()
    repl = {"&": "and", "bosnia & herzegovina": "bosnia and herzegovina"}
    for k, v in repl.items():
        n = n.replace(k, v)
    return n


def fetch_odds_games():
    """Get all active World Cup games from Odds API with their IDs."""
    if not ODDS_API_KEY:
        print("No ODDS_API_KEY — skipping odds fetch")
        return []
    try:
        url = f"{ODDS_BASE}/sports/{SPORT_KEY}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "commenceTimeFrom": (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commenceTimeTo": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"Odds API error: {exc}")
        return []


def fetch_player_props(game_id):
    """Fetch player props for a specific game from Odds API."""
    if not ODDS_API_KEY:
        return {"bookmakers": []}
    try:
        url = f"{ODDS_BASE}/sports/{SPORT_KEY}/events/{game_id}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": ",".join(PROP_MARKETS),
            "oddsFormat": "american",
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"Props fetch error for {game_id}: {exc}")
        return {"bookmakers": []}


def match_espn_to_odds(espn_match, odds_games):
    """Cross-reference ESPN match to Odds API game by team names."""
    espn_teams = [t["name"] for t in espn_match.get("teams", [])]
    if len(espn_teams) < 2:
        return None
    n_away, n_home = norm_team_name(espn_teams[0]), norm_team_name(espn_teams[1])
    for g in odds_games:
        o_away = norm_team_name(g.get("away_team", ""))
        o_home = norm_team_name(g.get("home_team", ""))
        if n_away == o_away and n_home == o_home:
            return g
        if (n_away in o_away or o_away in n_away) and (n_home in o_home or o_home in n_home):
            return g
    # Try reverse (ESPN might list home first)
    for g in odds_games:
        o_away = norm_team_name(g.get("away_team", ""))
        o_home = norm_team_name(g.get("home_team", ""))
        if n_home == o_away and n_away == o_home:
            return g
    return None


def extract_props(prop_data, preferred_book="draftkings"):
    """Extract player props from Odds API response for a specific book.
    Returns { player_name: { stat: { line, over_price } } }
    """
    props = {}
    stat_map = {
        "player_goals": "goals",
        "player_assists": "assists",
        "player_shots_on_target": "shots_on_target",
        "player_shots": "shots",
        "player_tackles": "tackles",
        "player_fouls": "fouls",
    }
    for bk in prop_data.get("bookmakers", []):
        if bk.get("key") != preferred_book:
            continue
        for m in bk.get("markets", []):
            stat = stat_map.get(m.get("key", ""))
            if not stat:
                continue
            for o in m.get("outcomes", []):
                name = o.get("description", o.get("name", ""))
                if o.get("name") == "Over":
                    props.setdefault(name, {})[stat] = {
                        "line": o.get("point"),
                        "over_price": o.get("price"),
                    }
    return props


def build_csv_rows(matches_with_props):
    """Flatten matches + props into rows for CSV."""
    rows = []
    for m in matches_with_props:
        matchup_short = m.get("short_name", m.get("name", "?"))
        status = m.get("status", "?")
        teams_list = m.get("teams", [])
        home = teams_list[1]["name"] if len(teams_list) > 1 else "?"
        away = teams_list[0]["name"] if len(teams_list) > 0 else "?"
        book = m.get("book", "none")
        props = m.get("player_props", {})
        if not props:
            rows.append({
                "matchup": matchup_short,
                "status": status,
                "home": home,
                "away": away,
                "book": book,
                "player": "",
                "stat": "",
                "line": "",
                "over_price": "",
                "fetched_at": m.get("fetched_at", ""),
            })
        for player_name, stats in props.items():
            for stat, info in stats.items():
                rows.append({
                    "matchup": matchup_short,
                    "status": status,
                    "home": home,
                    "away": away,
                    "book": book,
                    "player": player_name,
                    "stat": stat,
                    "line": info.get("line", ""),
                    "over_price": info.get("over_price", ""),
                    "fetched_at": m.get("fetched_at", ""),
                })
    return rows


def run(date_str=None):
    """Main entry point."""
    now = datetime.now(timezone.utc)
    if not date_str:
        date_str = now.strftime("%Y%m%d")
    day_dir = LOG_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== World Cup Picks — {date_str} ===")

    # Step 1: Get matches from ESPN
    espn_matches = fetch_espn_matches(date_str)
    print(f"ESPN matches: {len(espn_matches)}")
    for m in espn_matches:
        print(f"  {m['name']}: {m['status']}")

    # Step 2: Get game IDs from Odds API
    odds_games = fetch_odds_games()
    print(f"Odds API games: {len(odds_games)}")

    # Step 3: For each upcoming match, fetch player props
    results = []
    for em in espn_matches:
        if em.get("completed"):
            print(f"  Skipping completed: {em['name']}")
            result = {
                **em,
                "player_props": {},
                "book": "none",
                "fetched_at": now.isoformat(),
            }
            results.append(result)
            continue

        og = match_espn_to_odds(em, odds_games)
        if not og:
            print(f"  No Odds API match for: {em['name']}")
            result = {
                **em,
                "player_props": {},
                "book": "none",
                "fetched_at": now.isoformat(),
            }
            results.append(result)
            continue

        # Try books in priority order
        game_id = og["id"]
        props = {}
        book_used = "none"
        prop_data = fetch_player_props(game_id)

        for bk in BOOK_PRIORITY:
            props = extract_props(prop_data, bk)
            if props:
                book_used = bk
                break

        if not props:
            print(f"  No {', '.join(BOOK_PRIORITY)} props for: {em['name']}")

        print(f"  {em['name']}: {len(props)} players, {sum(len(v) for v in props.values())} props [{book_used}]")

        result = {
            **em,
            "odds_game_id": game_id,
            "player_props": props,
            "book": book_used,
            "fetched_at": now.isoformat(),
        }
        results.append(result)

    # Step 4: Write outputs
    # matches.json
    with open(day_dir / "matches.json", "w") as f:
        json.dump({"date": date_str, "fetched_at": now.isoformat(), "matches": results}, f, indent=2, default=str)

    # props.json (full detail)
    with open(day_dir / "props.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # picks.csv
    csv_rows = build_csv_rows(results)
    csv_path = day_dir / "picks.csv"
    with open(csv_path, "w", newline="") as f:
        if csv_rows:
            w = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            w.writeheader()
            w.writerows(csv_rows)
        else:
            f.write("matchup,status,home,away,book,player,stat,line,over_price,fetched_at\n")

    # last_run.json
    summary = {
        "timestamp": now.isoformat(),
        "date": date_str,
        "matches_total": len(results),
        "matches_upcoming": sum(1 for r in results if not r.get("completed")),
        "matches_with_props": sum(1 for r in results if r.get("player_props")),
        "total_players": sum(len(r.get("player_props", {})) for r in results),
        "total_props": sum(sum(len(v) for v in r.get("player_props", {}).values()) for r in results),
        "books_used": list(set(r.get("book", "none") for r in results)),
    }
    with open(LOG_DIR / "last_run.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nDone. {summary['total_players']} players, {summary['total_props']} props")
    print(f"Output: {day_dir}/")
    print(f"  {day_dir}/matches.json")
    print(f"  {day_dir}/props.json")
    print(f"  {csv_path}")
    print(f"  {LOG_DIR}/last_run.json")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="World Cup 2026 Daily Pick Scraper")
    parser.add_argument("--date", default=None, help="Date in YYYYMMDD format (default: today UTC)")
    args = parser.parse_args()
    run(args.date)
