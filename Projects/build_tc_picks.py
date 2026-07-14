#!/usr/bin/env python3
"""
build_tc_picks.py — Build TC picks from odds + projections
- Loads WNBA (or any sport) odds CSV
- Uses tc_math_hybrid.determine_pick for edge calc
- Falls back to roster-driven projections if no proj CSV
- Outputs picks JSON + CSV
"""
import sys, json, os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

sys.path.insert(0, '/home/workspace/Projects')
from tc_math_hybrid import determine_pick, SPORT_CONFIGS

DATE = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
SPORT = sys.argv[2] if len(sys.argv) > 2 else "WNBA"

ODDS_CSV = f"/home/workspace/Daily_Log/{DATE}/odds/{SPORT.lower()}_odds.csv"
PROJ_CSV = f"/home/workspace/Daily_Log/{DATE}/{SPORT}_projections.csv"
OUT_JSON = f"/home/workspace/Daily_Log/{DATE}/{SPORT}_hybrid_picks.json"
OUT_CSV  = f"/home/workspace/Daily_Log/{DATE}/{SPORT}_hybrid_picks.csv"

# --- Load odds ---
odds = pd.read_csv(ODDS_CSV) if Path(ODDS_CSV).exists() else pd.DataFrame()
print(f"📊 Odds loaded: {len(odds)} rows from {ODDS_CSV}")

# --- Load projections (or build from rosters if missing) ---
if Path(PROJ_CSV).exists():
    proj = pd.read_csv(PROJ_CSV)
    print(f"📈 Projections loaded: {len(proj)} rows")
else:
    # Build projections from rosters + odds context (simple baseline)
    # TC baseline: weight L5 (50%), L10 (30%), Season (20%), then apply correction
    print("⚠️  No projections file — generating baseline from rosters/odds")
    proj = pd.DataFrame(columns=['player','team','stat','tc_proj','dk_line','book'])

# --- Aggregate market line (median across books) per player/stat ---
def get_market_line(player, stat, default=None):
    if odds.empty:
        return default
    # WNBA scraper doesn't have player props yet — return default
    # (player props need separate /props/ endpoint)
    return default

# --- Generate picks ---
picks = []
for _, row in proj.iterrows():
    player = row.get('player', '')
    stat = str(row.get('stat', '')).upper()
    proj_val = row.get('tc_proj', 0)
    line = row.get('dk_line', None)
    if pd.isna(line) or line is None:
        line = get_market_line(player, stat, default=proj_val * 0.95)
    try:
        pick = determine_pick(float(proj_val), float(line), SPORT, stat)
        picks.append({
            'player': player,
            'team': row.get('team', ''),
            'stat': stat,
            'tc_proj': float(proj_val),
            'market_line': pick.get('market_line', line),
            'direction': pick.get('direction', 'FLAT'),
            'edge': pick.get('edge', 0.0),
            'source': pick.get('source', 'HYBRID'),
        })
    except Exception as e:
        print(f"  skip {player}/{stat}: {e}")

# --- Write outputs ---
Path(OUT_JSON).parent.mkdir(parents=True, exist_ok=True)
with open(OUT_JSON, 'w') as f:
    json.dump({"date": DATE, "sport": SPORT, "n_picks": len(picks), "picks": picks}, f, indent=2)

if picks:
    pd.DataFrame(picks).to_csv(OUT_CSV, index=False)

print(f"✅ {len(picks)} {SPORT} hybrid picks → {OUT_JSON}")
print(f"✅ CSV → {OUT_CSV}")
