#!/usr/bin/env python3
"""SportsData.io NFL Daily Lines Puller — game odds + player props.
Saves to Daily_Log/YYYY-MM-DD/sportsdata_nfl_lines.json + sportsdata_nfl_props.json

Pulls PRE week 1 + REG week 1 using SPORTSDATAIO_API_KEY.
Auth: Ocp-Apim-Subscription-Key header (same as MLB endpoint).
"""
import json, os, requests, sys
from datetime import datetime
from pathlib import Path

SD = "https://api.sportsdata.io/v3/nfl/odds/json"

# Load key from secrets
SECRETS = Path("/root/.zo/secrets.env")
KEY = ""
if SECRETS.exists():
    for line in SECRETS.read_text().splitlines():
        line = line.strip()
        if line.startswith("SPORTSDATAIO_API_KEY="):
            KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not KEY:
    print("ERROR: SPORTSDATAIO_API_KEY not found in secrets")
    sys.exit(1)

HEADERS = {"Ocp-Apim-Subscription-Key": KEY}

today = datetime.now().strftime("%Y-%m-%d")
OUT_DIR = Path("/home/workspace") / "Daily_Log" / today
OUT_DIR.mkdir(parents=True, exist_ok=True)

def pull(season_type: str, week: int) -> dict:
    """Pull GameOdds + PlayerProps for a given week."""
    path = f"GameOddsByWeek/{season_type}/{week}"
    r = requests.get(f"{SD}/{path}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    games = r.json()

    ppath = f"PlayerPropsByWeek/{season_type}/{week}"
    r2 = requests.get(f"{SD}/{ppath}", headers=HEADERS, timeout=30)
    r2.raise_for_status()
    props = r2.json()

    return {"games": games, "props": props, "season": season_type, "week": week}

def summarize(data: dict) -> str:
    games = data.get("games", [])
    props = data.get("props", [])
    by_game = {}
    for p in props:
        sid = p.get("ScoreID", "?")
        by_game[sid] = by_game.get(sid, 0) + 1

    out = [
        f"=== SportsData.io NFL {data['season']} Week {data['week']} ===",
        f"Games: {len(games)}  |  Props: {len(props)}",
    ]

    for g in games[:6]:
        away = g.get("AwayTeamName", "?")
        home = g.get("HomeTeamName", "?")
        dt = g.get("DateTime", "?")
        odds = g.get("PregameOdds", [])
        if odds:
            o = odds[0]
            tot = o.get("OverUnder", "?")
            spr = o.get("HomePointSpread", "?")
            hml = o.get("HomeMoneyLine", "?")
            aml = o.get("AwayMoneyLine", "?")
            bk = o.get("Sportsbook", "?")
        else:
            tot = spr = hml = aml = bk = "?"
        scid = g.get("ScoreId", "?")
        out.append(f"  {away} @ {home}  |  {bk}  |  Spread {spr}  Total {tot}  ML {hml}/{aml}  |  {by_game.get(scid, 0)} props")

    return "\n".join(out)


# Pull PRE week 1 + REG week 1
all_games = []
all_props = []
sources = []

for stype, wk in [("2026PRE", 1), ("2026REG", 1)]:
    try:
        data = pull(stype, wk)
        all_games.extend(data["games"])
        all_props.extend(data["props"])
        sources.append(f"{stype} W{wk}")
        print(summarize(data))
    except Exception as e:
        print(f"  ⚠ {stype} W{wk}: {e}")

# Save lines.json (what /api/tc expects)
lines_out = {
    "pulled_at": datetime.now().isoformat(),
    "sources": sources,
    "games": all_games,
    "preseason_games": [g for g in all_games if g.get("SeasonType") == 1],
    "reg_season_games": [g for g in all_games if g.get("SeasonType") != 1],
    "total_games": len(all_games),
    "props": all_props,
    "total_props": len(all_props),
    "season": "2026",
    "weeks": [1],
}

lines_path = OUT_DIR / "sportsdata_nfl_lines.json"
lines_path.write_text(json.dumps(lines_out, indent=2, default=str))

# Save props.json separately for the dashboard
props_path = OUT_DIR / "sportsdata_nfl_props.json"
props_path.write_text(json.dumps({"pulled_at": datetime.now().isoformat(), "props": all_props, "total": len(all_props)}, indent=2, default=str))

print(f"\n=== SAVED ===")
print(f"  {lines_path}  ({len(all_games)} games, {len(all_props)} props)")
print(f"  {props_path}")
print(f"\n  All games: {len(all_games)} ({len([g for g in all_games if g.get('SeasonType')==1])} PRE, {len([g for g in all_games if g.get('SeasonType')!=1])} REG)")
