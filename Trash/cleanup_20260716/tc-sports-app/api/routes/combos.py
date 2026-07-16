from fastapi import APIRouter
import json
import os
from datetime import datetime

router = APIRouter()

@router.get("/combos")
def get_combos(sport: str, date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    try:
        path = os.path.expanduser(f"~/workspace/data/picks/{sport}_{date}.csv")
        with open(path) as f:
            lines = f.readlines()
        players = []
        headers = lines[0].strip().split(",")
        for line in lines[1:]:
            vals = line.strip().split(",")
            players.append(dict(zip(headers, vals)))
        combos = []
        for i in range(len(players)):
            for j in range(i+1, min(i+4, len(players))):
                e1 = float(players[i].get("edge", 0) or 0)
                e2 = float(players[j].get("edge", 0) or 0)
                if e1 > 0.5 and e2 > 0.5:
                    combos.append({
                        "legs": f"{players[i]['player']} + {players[j]['player']}",
                        "sport": sport,
                        "total_edge": round(e1 + e2, 2),
                        "leg_count": 2
                    })
        return combos[:20]
    except Exception as e:
        return [{"legs": "Live combos unavailable", "sport": sport, "total_edge": 0, "leg_count": 0, "error": str(e)}]
