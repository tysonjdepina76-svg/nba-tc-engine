"""
Hardwired schedule fetcher — reads from schedules_master.json.
One source of truth for all 6 sports schedules.
"""
import json, os, datetime
from pathlib import Path

MASTER_FILE = Path("/home/workspace/data/schedules/schedules_master.json")


def _load_master():
    if not MASTER_FILE.exists():
        return {"sports": {}}
    with open(MASTER_FILE) as f:
        return json.load(f)


def get_schedule(sport: str) -> dict:
    sport = sport.lower()
    master = _load_master()
    sdata = master.get("sports", {}).get(sport, {})
    sdata["sport"] = sport
    sdata["generated_at"] = master.get("generated", "")
    sdata["generated_et"] = master.get("generated_et", "")
    return sdata


def get_all_schedules() -> dict:

    master = _load_master()
    out = {"generated": master.get("generated", ""), "generated_et": master.get("generated_et", ""),
           "today": master.get("today", ""), "active_sports": master.get("active_sports", []),
           "offseason_sports": master.get("offseason_sports", []),
           "preseason_sports": master.get("preseason_sports", []),
           "ended_sports": master.get("ended_sports", []),
           "total_games_today": master.get("total_games_today", 0)}
    out["sports"] = {s: get_schedule(s) for s in ["mlb", "wnba", "nba", "nfl", "nhl", "wc"]}
    return out


def has_games_today(sport: str) -> bool:
    sdata = get_schedule(sport)
    return sdata.get("today_game_count", 0) > 0


def get_active_sports() -> list:
    master = _load_master()
    return master.get("active_sports", [])
