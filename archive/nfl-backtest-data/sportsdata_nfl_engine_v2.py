#!/usr/bin/env python3
"""SportsData.io NFL engine v2 — pulls ALL available endpoints for backtest enrichment.

Tier verified (2026-06-15): Gambling Basic
Working endpoints:
  ✅ GameOddsByWeek       -> spreads, totals, ML per game
  ✅ PlayerPropsByWeek    -> all player props across books
  ✅ LiveGameOddsByWeek   -> live in-game odds snapshot
  ✅ Teams                -> 32 teams with metadata
  ✅ Stadiums             -> 60 stadiums with capacity

NOT available (tier-locked or missing):
  🔒 Schedules, TeamSeasonStats, PlayerSeasonStats (401)
  ❌ Scores/Results, Injuries, Projections, LineMovement (404)

Auth: Ocp-Apim-Subscription-Key header
"""
import json, os, re, requests, sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

SD = "https://api.sportsdata.io/v3/nfl"
SECRETS = Path("/root/.zo/secrets.env")
KEY = re.search(r"^SPORTS_DATA_API_KEY=(\S+)", SECRETS.read_text(), re.MULTILINE).group(1)
HEADERS = {"Ocp-Apim-Subscription-Key": KEY}

def pull_full(season: str, week: int) -> dict:
    """Pull all available NFL data for a given week."""
    data = {"season": season, "week": week, "pulled_at": datetime.now(timezone.utc).isoformat()}

    def fetch(label, url):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            data[label] = r.json()
            print(f"  ✅ {label}: {len(data[label])} items")
        except Exception as e:
            data[label] = {"error": str(e)}
            print(f"  ❌ {label}: {e}")

    fetch("games",       f"{SD}/odds/json/GameOddsByWeek/{season}/{week}")
    fetch("props",       f"{SD}/odds/json/PlayerPropsByWeek/{season}/{week}")
    fetch("live_odds",   f"{SD}/odds/json/LiveGameOddsByWeek/{season}/{week}")
    fetch("teams",       f"{SD}/scores/json/Teams")
    fetch("stadiums",    f"{SD}/scores/json/Stadiums")

    return data


def summarize(data: dict) -> str:
    games = data.get("games", [])
    props = data.get("props", [])
    live = data.get("live_odds", [])
    teams = data.get("teams", [])
    stadiums = data.get("stadiums", [])

    lines = [
        f"=== SportsData NFL W{data['week']} {data['season']} === Full Pull ===",
        f"Games: {len(games)}  |  Props: {len(props)}  |  Live odds: {len(live)}",
        f"Teams: {len(teams)}  |  Stadiums: {len(stadiums)}",
        f"Pulled: {data['pulled_at']}",
        "",
    ]

    # Team → ScoreID mapping for enrichment
    team_map = {}
    for t in teams:
        team_map[t.get("Key", "")] = t.get("TeamID")

    # Game details
    for g in games[:8]:
        away = g.get("AwayTeamName", "?")
        home = g.get("HomeTeamName", "?")
        dt = g.get("DateTime", "?")
        sid = g.get("ScoreId")
        pregame = g.get("PregameOdds", [])
        if pregame:
            o = pregame[0]
            spr = f"H{o.get('HomePointSpread', '?')}"
            tot = o.get("OverUnder", "?")
        else:
            spr = tot = "?"
        prop_count = sum(1 for p in props if p.get("ScoreID") == sid)
        lines.append(f"  {away} @ {home}  {dt}  Spread {spr}  O/U {tot}  {prop_count} props")

    # Top prop markets
    if props:
        markets = Counter(p["Description"] for p in props)
        sorted_markets = sorted(markets.items(), key=lambda x: -x[1])[:8]
        lines.append(f"\n  Prop markets: {', '.join(f'{m}({c})' for m, c in sorted_markets)}")

    return "\n".join(lines)


if __name__ == "__main__":
    season = sys.argv[1] if len(sys.argv) > 1 else "2026REG"
    week = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    data = pull_full(season, week)

    out_dir = Path("/home/workspace/Daily_Log")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / today / f"sportsdata_nfl_{season}_W{week}_full.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, default=str))

    print(f"\n{summarize(data)}")
    print(f"\nSaved → {out_path}")
    print(f"Total pull size: {len(json.dumps(data)):,.0f} bytes")
