#!/usr/bin/env python3
"""Pull today's NFL lines + props and save to Daily_Log for dashboard."""
import json, os, re, requests
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE = Path("/home/workspace")
LOG = WORKSPACE / "Daily_Log" / datetime.now().strftime("%Y-%m-%d")
LOG.mkdir(parents=True, exist_ok=True)

KEY = "2888700f9bce4c41ad074e26b505f9b3"
BASE = "https://api.sportsdata.io/v3/nfl"

def get(path, params=None):
    p = {"key": KEY}
    if params: p.update(params)
    r = requests.get(f"{BASE}{path}", params=p, timeout=20)
    if not r.ok:
        return None
    return r.json()

# Compute current NFL week: Sept start of REG. Today: 2026-06-13 → no REG yet.
# Use PRESEASON W1 as warmup, but season hasn't started — emit empty slate.
out = {
  "ts": datetime.now().isoformat() + "Z",
  "sport": "NFL",
  "endpoint": "/v3/nfl/odds/json/GameOddsByWeek/{season}{type}/{week}",
  "season": "2026REG",
  "week": 1,
  "games": [],
  "props": [],
  "status": "REG season starts 2026-09-10",
}

# Try REG W1 anyway (returns 0 games in June)
data = get("/odds/json/GameOddsByWeek/2026REG/1") or []
out["games"] = data

# PRESEASON W1 (Aug 2026, also future)
pre = get("/odds/json/GameOddsByWeek/2026PRE/1") or []

# REG W1 props (always 100+ props even before season)
props = get("/odds/json/PlayerPropsByWeek/2026REG/1") or []
out["props"] = props

out["preseason_games"] = pre
out["status"] = f"REG W1 has {len(data)} games, {len(props)} player props. Season opens Sept 10, 2026."

(LOG / "sportsdata_nfl_lines.json").write_text(json.dumps(out, indent=2, default=str))
print(f"NFL: {len(data)} REG W1 games, {len(props)} props, {len(pre)} PRES W1 games")
print(f"Saved → {LOG / 'sportsdata_nfl_lines.json'}")
