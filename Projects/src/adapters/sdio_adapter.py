#!/usr/bin/env python3
"""SDIO (SportsDataIO) adapter for MLB player props."""

import os
import requests
import time
import json
from datetime import datetime

API_KEY = os.environ.get("SportsDataIo", "")
BASE = "https://api.sportsdata.io/v3/mlb/odds/json"

STAT_MAP = {
    "Hits": "H",
    "Home Runs": "HR",
    "Runs": "R",
    "Runs Batted In": "RBI",
    "Strikeouts": "SO",
    "Total Bases": "TB",
    "Fantasy Points": "FP",
    "Pitching Strikeouts": "P_SO",
    "Pitching Hits": "P_H",
    "Pitching Runs": "P_R",
}

def fetch_player_props(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE}/PlayerPropsByDate/{date_str}"
    try:
        r = requests.get(url, headers={"Ocp-Apim-Subscription-Key": API_KEY}, timeout=30)
        if r.status_code != 200:
            return {"error": f"SDIO returned {r.status_code}", "props": [], "source": "sdio"}
        raw = r.json()
    except Exception as e:
        return {"error": str(e), "props": [], "source": "sdio"}
    props = []
    for p in raw:
        stat_desc = p.get("Description", "")
        tc_stat = STAT_MAP.get(stat_desc)
        if not tc_stat:
            continue
        props.append({
            "player": p["Name"],
            "team": p["Team"],
            "opponent": p.get("Opponent", ""),
            "stat": tc_stat,
            "line": float(p.get("OverUnder", 0)),
            "over_payout": int(p.get("OverPayout", -999)),
            "under_payout": int(p.get("UnderPayout", -999)),
            "game_id": p.get("GameID"),
            "description": stat_desc,
        })
    return {"source": "sdio", "props": props, "count": len(props), "fetched_at": time.time()}

if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else None
    result = fetch_player_props(d)
    print(json.dumps(result, indent=2, default=str))
