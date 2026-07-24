#!/usr/bin/env python3
"""Build self-edge combos directly from picks.db — no external lines required.
Reads today's picks, groups by sport+player, builds 2-leg combos from stats with edges > 0.
Cap edge at 1.0 to prevent inflation from zero-line picks."""

import sqlite3, json, math
from pathlib import Path
from datetime import datetime

DB_PATH = Path("/home/workspace/Projects/data/picks.db")
TODAY = datetime.now().strftime("%Y-%m-%d")
OUT_DIR = Path(f"/home/workspace/Daily_Log/{TODAY}")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Combo definitions — which stat pairs make good combos
COMBO_DEFS = {
    "WNBA": [
        ("PTS", "REB"), ("PTS", "AST"), ("REB", "AST"),
        ("PRA", "3PM"), ("PTS", "3PM"), ("REB", "BLK"),
        ("AST", "STL"), ("3PM", "STL"), ("STL", "BLK"),
    ],
    "MLB": [
        ("H", "RBI"), ("H", "R"), ("R", "RBI"),
        ("HR", "RBI"), ("H", "HR"), ("R", "HR"),
        ("TB", "RBI"), ("K", "BB"),
    ],
    "WC": [
        ("passes", "shots"), ("passes", "tackles"),
        ("shots", "goals"), ("passes", "goals"),
    ],
}

def build_combos():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get today's picks
    c.execute("""
        SELECT league, player, team, stat, edge, tc_projection, market_line, direction, matchup
        FROM picks
        WHERE date = ? AND edge > 0
        ORDER BY league, player, stat
    """, (TODAY,))
    rows = c.fetchall()
    print(f"[combos] {len(rows)} picks with edge > 0 for {TODAY}")

    # Group by (sport, player)
    player_picks = {}
    for r in rows:
        sport = r["league"].lower()
        if sport == "wc":
            sport = "WC"
        else:
            sport = sport.upper()
        player = f"{r['player']}|{r['team']}|{r['matchup']}"
        if player not in player_picks:
            player_picks[player] = {"sport": sport, "stats": {}}
        player_picks[player]["stats"][r["stat"]] = dict(r)

    all_combos = []
    seen = set()

    for player, data in player_picks.items():
        sport = data["sport"]
        stats = data["stats"]
        combo_defs = COMBO_DEFS.get(sport, [])
        name, team, matchup = player.split("|", 2)

        for s1, s2 in combo_defs:
            if s1 not in stats or s2 not in stats:
                continue

            p1, p2 = stats[s1], stats[s2]
            direction = "Over-Over" if p1["direction"] == "OVER" and p2["direction"] == "OVER" else "Mixed"

            # Cap per-leg edge at 1.0 (100%) to prevent inflation
            e1 = min(abs(p1["edge"]), 1.0)
            e2 = min(abs(p2["edge"]), 1.0)
            combined_edge = math.sqrt(e1 * e2)

            combo_key = f"{player}|{s1}|{s2}"
            if combo_key in seen:
                continue
            seen.add(combo_key)

            combo = {
                "player": name,
                "team": team,
                "matchup": matchup,
                "sport": sport,
                "league": sport,
                "legs": [
                    {"stat": s1, "direction": p1["direction"], "edge": round(e1, 4), "projection": p1["tc_projection"]},
                    {"stat": s2, "direction": p2["direction"], "edge": round(e2, 4), "projection": p2["tc_projection"]},
                ],
                "combined_edge": round(combined_edge, 4),
                "label": f"{s1}+{s2}",
                "direction": direction,
                "source": "self_edge",
                "timestamp": datetime.now().isoformat(),
            }
            all_combos.append(combo)

    # Sort by edge descending
    all_combos.sort(key=lambda c: c["combined_edge"], reverse=True)

    # Output
    output = []
    for c in all_combos[:100]:  # Top 100
        output.append({
            "player": c["player"],
            "team": c["team"],
            "matchup": c["matchup"],
            "sport": c["sport"],
            "edge": f"+{c['combined_edge']*100:.1f}%",
            "edge_raw": c["combined_edge"],
            "label": c["label"],
            "direction": c["direction"],
            "legs": c["legs"],
            "source": c["source"],
        })

    out_path = OUT_DIR / "combos_daily.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"[combos] Wrote {len(output)} combos to {out_path}")

    # Stats
    for sport in ["WNBA", "MLB", "WC"]:
        count = sum(1 for c in output if c["sport"] == sport)
        if count:
            print(f"  {sport}: {count} combos")

    conn.close()
    return output

if __name__ == "__main__":
    build_combos()
