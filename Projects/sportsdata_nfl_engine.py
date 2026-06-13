#!/usr/bin/env python3
"""SportsData.io NFL engine — pulls pregame odds + player props.

Working endpoints (NFL only, gambling tier):
  GET /v3/nfl/odds/json/GameOddsByWeek/{season}{type}/{week}     -> [Game]
  GET /v3/nfl/odds/json/PlayerPropsByWeek/{season}{type}/{week}  -> [PlayerProp]

Auth: ?key={SPORTS_DATA_API_KEY} (query param, NOT header)
Season types: 1=PRE, 2=REG, 3=POST
Books available: FanDuel, BetMGM, Caesars, BetRivers, PlaySugarHouse, Parx, ESPN BET, etc.
"""
import json, os, re, requests, sys
from datetime import datetime
from pathlib import Path

SD = "https://api.sportsdata.io/v3/nfl/odds/json"
SECRETS = Path("/root/.zo/secrets.env")
KEY = re.search(r"^SPORTS_DATA_API_KEY=(\S+)", SECRETS.read_text(), re.MULTILINE).group(1)

OUT = Path("/home/workspace/Daily_Log/2026-06-13")
OUT.mkdir(parents=True, exist_ok=True)


def pull(season: str, week: int) -> dict:
    """Pull GameOdds + PlayerProps for a given week."""
    headers = {"Ocp-Apim-Subscription-Key": KEY}
    # Game odds
    go = requests.get(f"{SD}/GameOddsByWeek/{season}/{week}", headers=headers, timeout=20)
    go.raise_for_status()
    games = go.json()
    # Player props
    pp = requests.get(f"{SD}/PlayerPropsByWeek/{season}/{week}", headers=headers, timeout=20)
    pp.raise_for_status()
    props = pp.json()
    return {"games": games, "props": props, "season": season, "week": week}


def summarize(data: dict) -> str:
    games = data["games"]
    props = data["props"]
    by_game = {}
    for p in props:
        by_game.setdefault(p["ScoreID"], 0)
        by_game[p["ScoreID"]] += 1
    lines = [
        f"=== SportsData NFL W{data['week']} {data['season']} ===",
        f"Games: {len(games)}  |  Player props: {len(props)}",
        f"Props/game: {', '.join(str(v) for v in sorted(by_game.values(), reverse=True)[:5])}...",
        "",
    ]
    for g in games[:4]:
        score_id = g["ScoreId"]
        away = g["AwayTeamName"]
        home = g["HomeTeamName"]
        dt = g["DateTime"]
        pregame = g.get("PregameOdds", [])
        if pregame:
            o = pregame[0]
            spr = o.get("HomePointSpread", "n/a")
            tot = o.get("OverUnder", "n/a")
            hml = o.get("HomeMoneyLine", "n/a")
            aml = o.get("AwayMoneyLine", "n/a")
        else:
            spr = tot = hml = aml = "n/a"
        lines.append(
            f"{away} @ {home}  {dt}  |  Spread {spr}  Total {tot}  ML {hml}/{aml}  |  {by_game.get(score_id, 0)} props"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    season = sys.argv[1] if len(sys.argv) > 1 else "2026REG"
    week = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    data = pull(season, week)
    out = OUT / f"sportsdata_nfl_{season}_W{week}.json"
    out.write_text(json.dumps(data, indent=2, default=str))
    print(summarize(data))
    print(f"\nSaved → {out}")
