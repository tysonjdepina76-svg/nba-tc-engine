#!/usr/bin/env python3
"""Build 2025 NBA Finals backtest file from final box scores.

Calculates TC projections retroactively and reports hit rates.
"""
import json
from pathlib import Path
from collections import defaultdict

OUT = Path("/home/workspace/Daily_Log/2025-06-13")
data = json.load(open(OUT / "finals_2025_nba.json"))

# TC math
CONS = {"PTS": 0.85, "REB": 0.85, "AST": 0.85, "3PM": 0.85, "STL": 0.80, "BLK": 0.80}
LINE_FACTOR = 0.88

def tc_project(actual, cons):
    return round(actual * cons, 1)

def line_from_tc(tc):
    return int(max(0, tc) * LINE_FACTOR)

# Key: ESPN boxscore keys -> stat name
# From probe: keys order was minutes, PTS, FG, 3P, FT, REB, AST, STL, BLK, TO, PF, +/-, ...
KEY_MAP = {
    "PTS": "points",
    "REB": "rebounds",
    "AST": "assists",
    "STL": "steals",
    "BLK": "blocks",
    "3PM": "threePointFieldGoalsMade",  # 3-pointers made
}

report_games = []
all_picks = []

for game in data:
    g_label = game["label"]
    matchup = game["matchup"]
    g_date = game["date"]

    game_player_records = []
    for team in game["teams"]:
        for p in team["players"]:
            if p.get("dnp"):
                continue
            stats = p["stats"]
            try:
                pts = int(stats.get("points", 0) or 0)
                reb = int(stats.get("rebounds", 0) or 0)
                ast = int(stats.get("assists", 0) or 0)
                threes_raw = stats.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted", "0-0")
                threes = int(threes_raw.split("-")[0])
                if p["name"] in ("Pascal Siakam","Tyrese Haliburton","Scottie Barnes"):
                    print(f"DEBUG: {p['name']} 3PM = {threes}")
                stl = int(stats.get("steals", 0) or 0)
                blk = int(stats.get("blocks", 0) or 0)
            except (ValueError, TypeError):
                continue

            player_picks = []
            for stat, actual in [("PTS", pts), ("REB", reb), ("AST", ast), ("3PM", threes), ("STL", stl), ("BLK", blk)]:
                tc_val = tc_project(actual, CONS[stat])
                tc_line = line_from_tc(tc_val)
                # Edge: actual vs line (actual - line)
                edge = round(actual - tc_line, 1)
                hit = actual > tc_line  # OVER hit
                player_picks.append({
                    "stat": stat,
                    "actual": actual,
                    "tc_proj": tc_val,
                    "tc_line": tc_line,
                    "edge": edge,
                    "hit_over": hit,
                })
                all_picks.append({
                    "game": g_label, "matchup": matchup, "date": g_date,
                    "player": p["name"], "team": team["abbr"], "starter": p.get("starter", False),
                    **player_picks[-1],
                })

            game_player_records.append({
                "name": p["name"],
                "team": team["abbr"],
                "starter": p.get("starter", False),
                "actual": {"PTS": pts, "REB": reb, "AST": ast, "3PM": threes, "STL": stl, "BLK": blk},
                "tc_proj": {s: tc_project(a, CONS[s]) for s, a in [("PTS", pts), ("REB", reb), ("AST", ast), ("3PM", threes), ("STL", stl), ("BLK", blk)]},
            })

    report_games.append({
        "label": g_label,
        "matchup": matchup,
        "date": g_date,
        "teams": [
            {"team": t["team"], "abbr": t["abbr"], "n_players": len([p for p in t["players"] if not p.get("dnp")])}
            for t in game["teams"]
        ],
        "rosters": game_player_records,
    })

# Hit-rate aggregates
by_stat = defaultdict(lambda: {"hit": 0, "miss": 0})
by_team = defaultdict(lambda: {"hit": 0, "miss": 0})
by_player = defaultdict(lambda: {"hit": 0, "miss": 0, "stats": defaultdict(lambda: {"hit": 0, "miss": 0})})

for p in all_picks:
    s = p["stat"]
    if p["hit_over"]:
        by_stat[s]["hit"] += 1
        by_team[p["team"]]["hit"] += 1
        by_player[p["player"]]["hit"] += 1
        by_player[p["player"]]["stats"][s]["hit"] += 1
    else:
        by_stat[s]["miss"] += 1
        by_team[p["team"]]["miss"] += 1
        by_player[p["player"]]["miss"] += 1
        by_player[p["player"]]["stats"][s]["miss"] += 1

def rate(d):
    t = d["hit"] + d["miss"]
    return round(d["hit"] / t * 100, 1) if t else 0.0, d["hit"], d["miss"], t

stat_rates = {s: {"rate": rate(d)[0], "hit": rate(d)[1], "miss": rate(d)[2], "n": rate(d)[3]} for s, d in by_stat.items()}
team_rates = {t: {"rate": rate(d)[0], "hit": rate(d)[1], "miss": rate(d)[2], "n": rate(d)[3]} for t, d in by_team.items()}

player_rates = {}
for name, d in by_player.items():
    rate_pct, hit, miss, n = rate(d)
    player_rates[name] = {
        "rate": rate_pct, "hit": hit, "miss": miss, "n": n,
        "team": next((p["team"] for p in all_picks if p["player"] == name), None),
        "by_stat": {s: {"rate": rate(sd)[0], "hit": rate(sd)[1], "miss": rate(sd)[2], "n": rate(sd)[3]} for s, sd in d["stats"].items()},
    }

# Sort
sorted_stats = sorted(stat_rates.items(), key=lambda x: -x[1]["rate"])
sorted_teams = sorted(team_rates.items(), key=lambda x: -x[1]["rate"])
sorted_players = sorted(player_rates.items(), key=lambda x: -x[1]["rate"])[:30]

# Markdown report
md = []
md.append("# 2025 NBA Finals Backtest Report")
md.append(f"\n**Generated:** {Path(__file__).name}")
md.append(f"**Games:** {len(data)} | **Players:** {len(set(p['player'] for p in all_picks))} | **Picks:** {len(all_picks)}")
md.append(f"\n**Matchup:** Indiana Pacers vs Oklahoma City Thunder\n")
md.append("\n## Hit Rate by Stat")
md.append("| Stat | Hit Rate | Hit | Miss | N |")
md.append("|------|----------|-----|------|---|")
for s, d in sorted_stats:
    md.append(f"| {s} | {d['rate']}% | {d['hit']} | {d['miss']} | {d['n']} |")
md.append("\n## Hit Rate by Team")
md.append("| Team | Hit Rate | Hit | Miss | N |")
md.append("|------|----------|-----|------|---|")
for t, d in sorted_teams:
    md.append(f"| {t} | {d['rate']}% | {d['hit']} | {d['miss']} | {d['n']} |")
md.append("\n## Top 30 Players by Hit Rate")
md.append("| Player | Team | Hit Rate | Hit | Miss | N |")
md.append("|--------|------|----------|-----|------|---|")
for name, d in sorted_players:
    md.append(f"| {name} | {d['team']} | {d['rate']}% | {d['hit']} | {d['miss']} | {d['n']} |")

md.append("\n## Per-Game Summary")
for g in report_games:
    md.append(f"\n### {g['label']} — {g['matchup']} ({g['date']})")
    for t in g["teams"]:
        md.append(f"- **{t['team']} ({t['abbr']})** — {t['n_players']} players")

(OUT / "nba_finals_2025_backtest.json").write_text(json.dumps({
    "games": report_games,
    "stat_rates": stat_rates,
    "team_rates": team_rates,
    "player_rates": player_rates,
    "all_picks": all_picks,
}, indent=2))

(OUT / "nba_finals_2025_backtest.md").write_text("\n".join(md))

print(f"\n=== 2025 NBA Finals Backtest ===")
print(f"Games: {len(data)} | Picks: {len(all_picks)} | Players: {len(player_rates)}")
print(f"\nBy Stat:")
for s, d in sorted_stats:
    print(f"  {s}: {d['rate']}% ({d['hit']}/{d['n']})")
print(f"\nBy Team:")
for t, d in sorted_teams:
    print(f"  {t}: {d['rate']}% ({d['hit']}/{d['n']})")
print(f"\nTop 10 Players:")
for name, d in sorted_players[:10]:
    print(f"  {name} ({d['team']}): {d['rate']}% ({d['hit']}/{d['n']})")
print(f"\n→ {OUT}/nba_finals_2025_backtest.{{json,md}}")
