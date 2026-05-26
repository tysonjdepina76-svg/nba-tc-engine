#!/usr/bin/env python3
"""
Triple Conservative NBA Projections — v7 FINAL
================================================
TC Formula:
  TC pts    = pts × 0.85  (Q = ×0.55, OUT = 0)
  TC reb    = reb × 0.85  (Q = ×0.55, OUT = 0)
  TC ast    = ast × 0.85  (Q = ×0.55, OUT = 0)
  TC 3pm    = 3pm × 0.85  (Q = ×0.55, OUT = 0)
  TC Total  = sum(TC pts) + bench bonus
  Line      = TC_total × 0.88  (rounded to nearest whole)
  Edge      = TC pts − Line

ENHANCED: Now includes PTS / REB / AST / 3PM per player in every printout.

Usage:
  python triple_conservative_v7.py              # generate all games
  python triple_conservative_v7.py --game PHI@NY  # single game
  python triple_conservative_v7.py --game MIN@SA   # single game (OKC/PHX series)
"""

import json
from dataclasses import dataclass
from typing import Optional

# =====================================================================
# TEAM DATA — verified news/box scores
# Fields: pts, reb, ast, 3pm (3-point shots made per game)
# Status: A = Active, Q = Questionable, OUT = Out
# =====================================================================

TEAMS = {
    "PHI": {
        "name": "Philadelphia 76ers",
        "seed": 7,
        "rest": "Short (Game 7 vs BOS Apr 30)",
        "players": [
            {"name": "Joel Embiid",        "pos": "C",  "ht": "7-0",  "pts": 28.5, "reb": 10.5, "ast": 5.5, "3pm": 1.8, "status": "Q"},
            {"name": "Tyrese Maxey",       "pos": "G",  "ht": "6-2",  "pts": 24.5, "reb": 4.5,  "ast": 6.5, "3pm": 2.5, "status": "A"},
            {"name": "Paul George",        "pos": "F",  "ht": "6-8",  "pts": 22.0, "reb": 5.5,  "ast": 4.5, "3pm": 3.2, "status": "A"},
            {"name": "Kelly Oubre Jr",     "pos": "F",  "ht": "6-7",  "pts": 18.5, "reb": 5.0,  "ast": 1.5, "3pm": 2.1, "status": "A"},
            {"name": "VJ Edgecombe",       "pos": "G",  "ht": "6-5",  "pts": 15.0, "reb": 3.5,  "ast": 2.5, "3pm": 1.2, "status": "A"},
            {"name": "Justin Edwards",    "pos": "F",  "ht": "6-6",  "pts": 8.0,  "reb": 3.0,  "ast": 1.0, "3pm": 0.8, "status": "A"},
            {"name": "Jared McCain",       "pos": "G",  "ht": "6-3",  "pts": 9.5,  "reb": 2.5,  "ast": 2.0, "3pm": 1.0, "status": "A"},
            {"name": "Lamar Stevens",      "pos": "F",  "ht": "6-8",  "pts": 6.0,  "reb": 3.5,  "ast": 0.5, "3pm": 0.3, "status": "A"},
        ],
        "bench_total": 20,
        "note": "Embiid Q (right hip contusion) — limited to ~20 min",
    },
    "NY": {
        "name": "New York Knicks",
        "seed": 3,
        "rest": "Long (swept ATL Apr 25)",
        "players": [
            {"name": "Jalen Brunson",        "pos": "G",  "ht": "6-1",  "pts": 27.5, "reb": 4.0,  "ast": 7.5, "3pm": 2.5, "status": "A"},
            {"name": "Mikal Bridges",         "pos": "G",  "ht": "6-5",  "pts": 19.5, "reb": 4.5,  "ast": 3.5, "3pm": 2.0, "status": "A"},
            {"name": "OG Anunoby",            "pos": "F",  "ht": "6-7",  "pts": 17.0, "reb": 5.0,  "ast": 2.5, "3pm": 1.8, "status": "A"},
            {"name": "Karl-Anthony Towns",   "pos": "C",  "ht": "6-11", "pts": 20.0, "reb": 10.5, "ast": 3.0, "3pm": 1.5, "status": "A"},
            {"name": "Josh Hart",             "pos": "F",  "ht": "6-5",  "pts": 14.0, "reb": 6.5,  "ast": 4.5, "3pm": 1.2, "status": "A"},
            {"name": "Miles McBride",         "pos": "G",  "ht": "6-2",  "pts": 10.0, "reb": 2.5,  "ast": 3.0, "3pm": 1.5, "status": "A"},
            {"name": "Precious Achiuwa",      "pos": "F",  "ht": "6-8",  "pts": 7.5,  "reb": 5.5,  "ast": 1.0, "3pm": 0.5, "status": "A"},
            {"name": "Jeremy Sochan",         "pos": "F",  "ht": "6-8",  "pts": 6.0,  "reb": 3.5,  "ast": 1.5, "3pm": 0.4, "status": "Q"},
        ],
        "bench_total": 22,
        "note": "Sochan Q (left hamstring tightness) — limited if plays",
    },
    "MIN": {
        "name": "Minnesota Timberwolves",
        "seed": 6,
        "rest": "Moderate (beat DEN in 6, last game May 2)",
        "players": [
            {"name": "Anthony Edwards",          "pos": "G",  "ht": "6-4",  "pts": 29.0, "reb": 5.5,  "ast": 5.0, "3pm": 3.0, "status": "A"},
            {"name": "Julius Randle",            "pos": "F",  "ht": "6-8",  "pts": 22.0, "reb": 7.5,  "ast": 5.0, "3pm": 1.8, "status": "A"},
            {"name": "Rudy Gobert",               "pos": "C",  "ht": "7-1",  "pts": 16.5, "reb": 11.5, "ast": 1.5, "3pm": 0.0, "status": "A"},
            {"name": "Jaden McDaniels",          "pos": "F",  "ht": "6-9",  "pts": 13.5, "reb": 3.5,  "ast": 1.5, "3pm": 1.2, "status": "A"},
            {"name": "Nickeil Alexander-Walker", "pos": "G",  "ht": "6-5",  "pts": 12.0, "reb": 3.0,  "ast": 2.0, "3pm": 1.8, "status": "A"},
            {"name": "Donte DiVincenzo",          "pos": "G",  "ht": "6-4",  "pts": 10.5, "reb": 3.5,  "ast": 3.0, "3pm": 2.0, "status": "OUT"},
            {"name": "Ayo Dosunmu",              "pos": "G",  "ht": "6-5",  "pts": 9.5,  "reb": 3.0,  "ast": 3.5, "3pm": 0.8, "status": "Q"},
            {"name": "Naz Reid",                  "pos": "F",  "ht": "6-9",  "pts": 13.0, "reb": 5.0,  "ast": 1.5, "3pm": 1.5, "status": "A"},
        ],
        "bench_total": 25,
        "note": "Edwards A (healthy); DiVincenzo OUT (Achilles); Dosunmu Q (calf)",
    },
    "SA": {
        "name": "San Antonio Spurs",
        "seed": 2,
        "rest": "Long (swept POR Apr 28)",
        "players": [
            {"name": "Victor Wembanyama",   "pos": "C",  "ht": "7-4",  "pts": 30.0, "reb": 10.5, "ast": 4.5, "3pm": 3.5, "status": "A"},
            {"name": "Stephon Castle",       "pos": "G",  "ht": "6-5",  "pts": 21.0, "reb": 4.5,  "ast": 5.0, "3pm": 1.8, "status": "A"},
            {"name": "Julian Champagnie",   "pos": "F",  "ht": "6-8",  "pts": 16.5, "reb": 5.0,  "ast": 2.0, "3pm": 2.2, "status": "A"},
            {"name": "Harrison Barnes",      "pos": "F",  "ht": "6-8",  "pts": 14.0, "reb": 4.5,  "ast": 1.5, "3pm": 1.5, "status": "A"},
            {"name": "Chris Paul",           "pos": "G",  "ht": "6-0",  "pts": 12.0, "reb": 3.5,  "ast": 8.0, "3pm": 1.5, "status": "A"},
            {"name": "Keldon Johnson",       "pos": "F",  "ht": "6-5",  "pts": 11.5, "reb": 4.0,  "ast": 2.0, "3pm": 1.5, "status": "A"},
            {"name": "Devin Vassell",        "pos": "G",  "ht": "6-5",  "pts": 10.0, "reb": 3.5,  "ast": 2.0, "3pm": 1.5, "status": "A"},
            {"name": "Carter Bryant",        "pos": "F",  "ht": "6-7",  "pts": 7.5,  "reb": 3.0,  "ast": 0.5, "3pm": 0.5, "status": "Q"},
        ],
        "bench_total": 28,
        "note": "Carter Bryant Q (foot); David Jones Garcia out (ankle, season)",
    },
    "OKC": {
        "name": "Oklahoma City Thunder",
        "seed": 1,
        "rest": "Long (swept NOR Apr 28)",
        "players": [
            {"name": "Shai Gilgeous-Alexander", "pos": "G",  "ht": "6-6",  "pts": 32.0, "reb": 5.0,  "ast": 6.5, "3pm": 2.2, "status": "A"},
            {"name": "Jalen Williams",           "pos": "F",  "ht": "6-5",  "pts": 21.0, "reb": 5.5,  "ast": 4.5, "3pm": 1.5, "status": "A"},
            {"name": "Chet Holmgren",            "pos": "C",  "ht": "7-1",  "pts": 18.0, "reb": 7.5,  "ast": 2.5, "3pm": 1.8, "status": "A"},
            {"name": "Lu Dort",                  "pos": "G",  "ht": "6-4",  "pts": 12.0, "reb": 3.5,  "ast": 2.0, "3pm": 2.0, "status": "A"},
            {"name": "Josh Giddey",              "pos": "G",  "ht": "6-8",  "pts": 11.5, "reb": 6.5,  "ast": 5.5, "3pm": 1.2, "status": "A"},
            {"name": "Isaiah Hartenstein",      "pos": "C",  "ht": "7-0",  "pts": 10.0, "reb": 7.0,  "ast": 2.5, "3pm": 0.5, "status": "A"},
            {"name": "Jaylin Williams",          "pos": "F",  "ht": "6-10", "pts": 8.0,  "reb": 4.5,  "ast": 1.5, "3pm": 0.8, "status": "A"},
            {"name": "Cason Wallace",            "pos": "G",  "ht": "6-4",  "pts": 7.5,  "reb": 2.5,  "ast": 2.0, "3pm": 1.2, "status": "A"},
        ],
        "bench_total": 30,
        "note": "Fully healthy. OKC swept NOR in 4. Rest advantage.",
    },
    "PHX": {
        "name": "Phoenix Suns",
        "seed": 4,
        "rest": "Short (won Game 7 vs LAC Apr 30)",
        "players": [
            {"name": "Kevin Durant",          "pos": "F",  "ht": "6-10", "pts": 27.0, "reb": 6.5,  "ast": 4.5, "3pm": 2.2, "status": "A"},
            {"name": "Devin Booker",           "pos": "G",  "ht": "6-5",  "pts": 25.5, "reb": 4.5,  "ast": 7.0, "3pm": 2.5, "status": "A"},
            {"name": "Bradley Beal",            "pos": "G",  "ht": "6-5",  "pts": 20.0, "reb": 4.0,  "ast": 5.0, "3pm": 2.0, "status": "A"},
            {"name": "Nick Richards",           "pos": "C",  "ht": "7-0",  "pts": 14.0, "reb": 8.5,  "ast": 1.0, "3pm": 0.0, "status": "A"},
            {"name": "Royce O'Neale",           "pos": "F",  "ht": "6-5",  "pts": 9.5,  "reb": 5.5,  "ast": 3.5, "3pm": 1.8, "status": "A"},
            {"name": "Tyus Jones",              "pos": "G",  "ht": "6-0",  "pts": 9.0,  "reb": 2.5,  "ast": 5.5, "3pm": 1.5, "status": "A"},
            {"name": "Grayson Allen",           "pos": "G",  "ht": "6-4",  "pts": 8.5,  "reb": 3.0,  "ast": 2.0, "3pm": 1.5, "status": "A"},
            {"name": "Bol Bol",                 "pos": "C",  "ht": "7-2",  "pts": 8.0,  "reb": 5.0,  "ast": 1.0, "3pm": 0.8, "status": "A"},
        ],
        "bench_total": 22,
        "note": "Booker playing through ankle soreness (counted active). No new injuries.",
    },
}

# =====================================================================
# GAMES — Updated May 4, 2026
# =====================================================================

GAMES = [
    {
        "id": "PHI@NY",
        "date": "May 4, 2026",
        "time": "8:00 PM ET",
        "network": "NBC / Peacock",
        "series": "East Semifinals — Game 1",
        "matchup": "Philadelphia 76ers @ New York Knicks",
        "spread": {"favorite": "NY", "line": -7.5, "underdog": "PHI"},
        "total": {"line": 213.5},
        "ml": {"PHI": "+235", "NY": "-290"},
    },
    {
        "id": "MIN@SA",
        "date": "May 4, 2026",
        "time": "9:30 PM ET",
        "network": "NBCSN / Peacock",
        "series": "West Semifinals — Game 1",
        "matchup": "Minnesota Timberwolves @ San Antonio Spurs",
        "spread": {"favorite": "SA", "line": -13.0, "underdog": "MIN"},
        "total": {"line": 217.5},
        "ml": {"SA": "-650", "MIN": "+475"},
    },
    {
        "id": "OKC@PHX",
        "date": "May 4, 2026",
        "time": "10:30 PM ET",
        "network": "TNT",
        "series": "West Semifinals — Game 1",
        "matchup": "Oklahoma City Thunder @ Phoenix Suns",
        "spread": {"favorite": "OKC", "line": -5.5, "underdog": "PHX"},
        "total": {"line": 222.5},
        "ml": {"OKC": "-220", "PHX": "+185"},
    },
]

# =====================================================================
# TC PROJECTION ENGINE
# =====================================================================

MULTIPLIERS = {"A": 0.85, "Q": 0.55, "OUT": 0.0}

def tc_stat(val: float, status: str) -> float:
    return round(val * MULTIPLIERS.get(status, 0.85), 1)

def tc_proj_player(p: dict) -> dict:
    tc_pts  = tc_stat(p["pts"],  p["status"])
    tc_reb  = tc_stat(p["reb"],  p["status"])
    tc_ast  = tc_stat(p["ast"],  p["status"])
    tc_3pm  = tc_stat(p["3pm"], p["status"])
    tc_total = round(tc_pts + tc_reb + tc_ast + tc_3pm, 1)
    line    = round(tc_total * 0.88)
    edge    = round(tc_total - line, 1)
    flag    = {"A": "✅", "Q": "⚠️ Q", "OUT": "❌ OUT"}.get(p["status"], "")
    return {
        "name":    p["name"],
        "pos":     p["pos"],
        "ht":      p["ht"],
        "pts":     p["pts"],
        "reb":     p["reb"],
        "ast":     p["ast"],
        "3pm":     p["3pm"],
        "tc_pts":  tc_pts,
        "tc_reb":  tc_reb,
        "tc_ast":  tc_ast,
        "tc_3pm":  tc_3pm,
        "tc_total": tc_total,
        "line":    line,
        "edge":    edge,
        "status":  p["status"],
        "flag":    flag,
    }

def project_team(team_id: str, closeout: bool = False) -> dict:
    team = TEAMS[team_id]
    rows = []
    bench_tc_pts = 0.0
    bench_tc_reb = 0.0
    bench_tc_ast = 0.0
    bench_tc_3pm = 0.0

    for p in team["players"]:
        r = tc_proj_player(p)
        rows.append(r)
        if p["status"] in ("A", "Q"):
            bench_tc_pts += r["tc_pts"]
            bench_tc_reb += r["tc_reb"]
            bench_tc_ast += r["tc_ast"]
            bench_tc_3pm += r["tc_3pm"]

    closeout_mod = 8 if closeout else 0
    tc_team_total = round(
        bench_tc_pts + bench_tc_reb + bench_tc_ast + bench_tc_3pm
        + team["bench_total"] + closeout_mod, 1
    )

    return {
        "team_id":       team_id,
        "team_name":     team["name"],
        "seed":          team["seed"],
        "rest":          team["rest"],
        "players":       rows,
        "bench_tc_pts":  round(bench_tc_pts, 1),
        "bench_tc_reb":  round(bench_tc_reb, 1),
        "bench_tc_ast":  round(bench_tc_ast, 1),
        "bench_tc_3pm":  round(bench_tc_3pm, 1),
        "bench_total":   team["bench_total"],
        "tc_team_total": tc_team_total,
        "closeout_mod":  closeout_mod,
        "note":          team["note"],
    }

def project_game(game: dict, closeout: bool = False) -> dict:
    away_id, home_id = game["id"].split("@")
    away = project_team(away_id, closeout)
    home = project_team(home_id, closeout)

    tc_combined   = round(away["tc_team_total"] + home["tc_team_total"], 1)
    tc_spread_val = round(home["tc_team_total"] - away["tc_team_total"], 1)
    market_total  = game["total"]["line"]
    market_spread = game["spread"]["line"]
    spread_edge   = round(tc_spread_val - abs(market_spread), 1)
    total_edge    = round(tc_combined - market_total, 1)

    return {
        "game":         game,
        "away":         away,
        "home":         home,
        "tc_combined":  tc_combined,
        "tc_spread":    tc_spread_val,
        "market_total": market_total,
        "market_spread": market_spread,
        "spread_edge":  spread_edge,
        "total_edge":   total_edge,
        "closeout_mod": home["closeout_mod"],
    }

# =====================================================================
# REPORT GENERATOR — Full PTS / REB / AST / 3PM printout
# =====================================================================

def fmt_team_section(label: str, td: dict) -> str:
    rows = []
    rows.append(f"### {label}\n")
    rows.append(
        "| Player                  | POS | HT    | PTS  | REB  | AST  | 3PM  |"
        " TC PTS | TC REB | TC AST | TC 3PM | TC TOT | LINE | EDGE | STATUS |"
    )
    rows.append(
        "|------------------------|-----|-------|------|------|------|------|"
        "--------|--------|--------|--------|--------|------|------|--------|"
    )
    for p in td["players"]:
        flag = p["flag"]
        edge = f"+{p['edge']}" if p["edge"] >= 0 else str(p["edge"])
        rows.append(
            f"| {p['name']:<22} | {p['pos']}  | {p['ht']}  |"
            f" {p['pts']:>4.1f} | {p['reb']:>4.1f} | {p['ast']:>4.1f} | {p['3pm']:>3.1f} |"
            f" {p['tc_pts']:>6.1f} | {p['tc_reb']:>6.1f} | {p['tc_ast']:>6.1f} |"
            f" {p['tc_3pm']:>6.1f} | {p['tc_total']:>7.1f} | {p['line']:>4} |"
            f" {edge:>5} | {flag:<8} |"
        )

    rows.append(f"\n**Bench contribution:** TC PTS={td['bench_tc_pts']} | TC REB={td['bench_tc_reb']} | TC AST={td['bench_tc_ast']} | TC 3PM={td['bench_tc_3pm']} | bench bonus={td['bench_total']}")
    rows.append(f"**TC TEAM TOTAL: {td['tc_team_total']}**{f' (+{td["closeout_mod"]} closeout)' if td["closeout_mod"] else ''}")
    return "\n".join(rows)

def generate_report(g: dict) -> str:
    game = g["game"]
    total_edge  = g["total_edge"]
    spread_edge = g["spread_edge"]
    tc_combined = g["tc_combined"]
    tc_spread   = g["tc_spread"]
    market_tot  = g["market_total"]
    market_spr  = g["market_spread"]

    if total_edge > 10:   total_lean = "STRONG OVER"
    elif total_edge > 3:  total_lean = "OVER"
    elif total_edge < -10: total_lean = "STRONG UNDER"
    elif total_edge < -3:  total_lean = "UNDER"
    else:                  total_lean = "LEAN UNDER"

    conf_tot  = "HIGH" if abs(total_edge) > 8 else "MED" if abs(total_edge) > 4 else "LOW"
    conf_spr  = "HIGH" if abs(spread_edge) > 3 else "MED" if abs(spread_edge) > 1.5 else "LOW"
    favorite  = game["spread"]["favorite"]
    underdog  = game["spread"]["underdog"]

    report = f"""
# 🏀 TC Projections — {game['matchup']}
**Series:** {game['series']}  |  **Date:** {game['date']} — {game['time']}  |  **TV:** {game['network']}  |
**Market:** {favorite} {market_spr} / O/U {market_tot}

---

## Starting Lineups & TC Stats

{fmt_team_section(f"{TEAMS[game['id'].split('@')[0]]['name']} (Away)", g['away'])}

---

{fmt_team_section(f"{TEAMS[game['id'].split('@')[1]]['name']} (Home)", g['home'])}

---

## TC System Summary

| Metric | AWAY ({g['away']['team_name']}) | HOME ({g['home']['team_name']}) |
|--------|------|
| **TC Team Total** | {g['away']['tc_team_total']} | {g['home']['tc_team_total']} |
| **TC Combined Total** | **{tc_combined}** | |
| **Market Total (O/U)** | **{market_tot}** | |
| **Total Edge** | **{total_edge:+.1f}** → **{total_lean}** | |
| **TC Spread** | **{favorite} by {tc_spread}** | |
| **Market Spread** | **{favorite} {market_spr}** | |
| **Spread Edge** | **{spread_edge:+.1f}** → **{favorite} cover** | |

---

## Pick Candidates

| Pick Type | Market Line | TC Signal | Edge | Confidence |
|-----------|-------------|-----------|------|------------|
| **Total** | O/U {market_tot} | **{total_lean}** | {total_edge:+.1f} pts | {conf_tot} |
| **Spread** | {favorite} {market_spr} | **{favorite} cover** | {spread_edge:+.1f} pts | {conf_spr} |

**Recommended:** {"OVER" if "OVER" in total_lean else "UNDER"} {market_tot} | {favorite} {abs(tc_spread)} cover

---

## Key Notes

- **{g['away']['team_name']}:** {g['away']['note']}
- **{g['home']['team_name']}:** {g['home']['note']}
- **Rest context:** {g['away']['rest']} vs {g['home']['rest']}

---

*TC Formula: TC stat = stat × 0.85 (Q = ×0.55, OUT = 0) | Line = TC total × 0.88 | Edge = TC total − Line*  
*Columns: PTS = points | REB = rebounds | AST = assists | 3PM = 3-point shots made*
"""
    return report.strip()

# =====================================================================
# MAIN
# =====================================================================

def main():
    for game in GAMES:
        result = project_game(game)
        report = generate_report(result)
        filename = f"/home/workspace/{game['id']}_TC_Report.md"
        with open(filename, "w") as f:
            f.write(report)
        print(f"✅ Saved: {filename}")

        # Console summary
        print(f"\n{'='*60}")
        print(f"  {game['matchup']}")
        print(f"  TC: {result['tc_combined']} | Market O/U: {result['market_total']}")
        print(f"  Edge: {result['total_edge']:+.1f} → {result['away']['team_id']} vs {result['home']['team_id']}")
        print(f"{'='*60}\n")

    print("\n✅ triple_conservative_v7.py — All TC reports generated.")

if __name__ == "__main__":
    import sys
    if "--game" in sys.argv:
        target = sys.argv[sys.argv.index("--game") + 1]
        for game in GAMES:
            if game["id"] == target:
                print(generate_report(project_game(game)))
                break
    else:
        main()