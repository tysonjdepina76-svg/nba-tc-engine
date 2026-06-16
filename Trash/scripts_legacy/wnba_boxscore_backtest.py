#!/usr/bin/env python3
"""
WNBA + NBA Boxscore Backtest — scrapes ESPN summary API for final boxscores,
reads picks.csv from Daily_Log, grades picks, produces graded report.

Usage:
  python3 /home/workspace/scripts/wnba_boxscore_backtest.py --dates 2026-06-13,2026-06-14
  python3 /home/workspace/scripts/wnba_boxscore_backtest.py --date 2026-06-13
"""

import argparse, csv, json, os, re, sys, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta

WORKSPACE = "/home/workspace"
LOG_DIR = f"{WORKSPACE}/Daily_Log"

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
TEAM_ABBR_MAP = {
    "NYK": "NY", "SAS": "SA",  # NBA
    "LAL": "LA", "LAC": "LA",  # NBA
    "GS": "GS", "GSW": "GS",
    "NOP": "NO", "NOH": "NO",
    "UTAH": "UT", "PHX": "PHX",
    "BKN": "BKN", "BRK": "BKN",
}

def normalize_team(abbr):
    return TEAM_ABBR_MAP.get(abbr, abbr)


STAT_MAP = {
    "points": "PTS", "rebounds": "REB", "assists": "AST",
    "steals": "STL", "blocks": "BLK",
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted": "3PM",
    "turnovers": "TO", "fouls": "PF",
    "plusMinus": "+/-",
}


def get_espn_games(sport_path, date_str):
    """Fetch all games from ESPN scoreboard for a given date."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard?dates={date_str}"
    req = urllib.request.Request(url, headers=HEADERS)
    data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    
    games = []
    for e in data.get("events", []):
        comps = e.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        away = competitors[0] if competitors[0].get("homeAway") == "away" else competitors[1]
        home = competitors[1] if competitors[1].get("homeAway") == "home" else competitors[0]

        away_team = away.get("team", {})
        home_team = home.get("team", {})
        status = comp.get("status", {}).get("type", {}).get("name", "UNKNOWN")

        games.append({
            "id": e["id"],
            "away": away_team.get("abbreviation", "???"),
            "home": home_team.get("abbreviation", "???"),
            "away_name": away_team.get("shortDisplayName", ""),
            "home_name": home_team.get("shortDisplayName", ""),
            "away_score": int(away.get("score", 0) or 0),
            "home_score": int(home.get("score", 0) or 0),
            "status": status,
        })
    return games


def scrape_espn_boxscore(game_id, sport_path, home_abbr):
    """Scrape ESPN summary API boxscore. Returns (away_dict, home_dict) where each dict is player_name -> stats_dict."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/summary?event={game_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    except Exception as e:
        print(f"    Boxscore fetch error (game {game_id}): {e}")
        return {}, {}

    players_data = data.get("boxscore", {}).get("players", [])
    away_dict = {}
    home_dict = {}

    for team_data in players_data:
        team_info = team_data.get("team", {})
        team_abbr = team_info.get("abbreviation", "UNK")
        is_away = team_abbr != home_abbr
        stats_list = team_data.get("statistics", [])

        for stats_entry in stats_list:
            keys = stats_entry.get("keys", [])
            athletes = stats_entry.get("athletes", [])

            for athlete_data in athletes:
                athlete_info = athlete_data.get("athlete", {})
                name = athlete_info.get("displayName", "Unknown")
                stats_arr = athlete_data.get("stats", [])

                if not stats_arr or all(str(s) in ("--", "", "DNP") for s in stats_arr):
                    continue

                player_stats = {"name": name, "team": team_abbr}

                for i, key in enumerate(keys):
                    if i >= len(stats_arr):
                        continue
                    val_str = str(stats_arr[i])

                    if val_str in ("--", "", "DNP") or val_str is None:
                        player_stats[key] = 0.0
                        continue

                    try:
                        if "-" in val_str and key in (
                            "fieldGoalsMade-fieldGoalsAttempted",
                            "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
                            "freeThrowsMade-freeThrowsAttempted",
                        ):
                            player_stats[key] = int(val_str.split("-")[0])
                        else:
                            player_stats[key] = float(val_str)
                    except (ValueError, IndexError):
                        player_stats[key] = 0.0

                if is_away:
                    away_dict[name] = player_stats
                else:
                    home_dict[name] = player_stats

    return away_dict, home_dict


def get_player_actual(player_name, boxscore_dict):
    """Find a player in boxscore by fuzzy name match. Returns stats dict or None."""
    player_name = player_name.strip().lower()
    for name, stats in boxscore_dict.items():
        if name.lower() == player_name:
            return stats
    for name, stats in boxscore_dict.items():
        if player_name in name.lower() or name.lower() in player_name:
            return stats
    for name, stats in boxscore_dict.items():
        parts = player_name.split()
        if len(parts) >= 2:
            if parts[0].lower() in name.lower() and parts[-1].lower() in name.lower():
                return stats
    return None


def grade_pick(pick, actual_value):
    """Grade a TC pick: H=hit, M=miss, P=push. Returns (result, actual)."""
    try:
        direction = pick.get("direction", "OVER").strip().upper()
        market_line = float(pick.get("market_line", 0) or 0)
    except (ValueError, TypeError):
        return "ERROR", actual_value

    if direction in ("OVER", "O"):
        if actual_value > market_line:
            return "H", actual_value
        elif actual_value == market_line:
            return "P", actual_value
        else:
            return "M", actual_value
    elif direction in ("UNDER", "U"):
        if actual_value < market_line:
            return "H", actual_value
        elif actual_value == market_line:
            return "P", actual_value
        else:
            return "M", actual_value
    return "UNKNOWN", actual_value


def parse_stat_from_boxscore(player_stats, stat_abbr):
    """Extract stat value from ESPN boxscore stats using STAT_MAP mapping."""
    for key, mapped in STAT_MAP.items():
        if mapped == stat_abbr:
            val = player_stats.get(key, 0.0)
            if isinstance(val, (int, float)):
                return float(val)
            break
    return 0.0


def main():
    parser = argparse.ArgumentParser(description="WNBA/NBA Boxscore Backtest")
    parser.add_argument("--date", help="Single date YYYY-MM-DD")
    parser.add_argument("--dates", help="Comma-separated dates YYYY-MM-DD,YYYY-MM-DD")
    args = parser.parse_args()

    dates = []
    if args.dates:
        dates = [d.strip() for d in args.dates.split(",")]
    elif args.date:
        dates = [args.date]
    else:
        now = datetime.now()
        dates = [(now - timedelta(days=1)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")]

    print(f"\n{'='*70}")
    print(f"  WNBA + NBA BOXSCORE BACKTEST — {', '.join(dates)}")
    print(f"{'='*70}\n")

    all_graded = []
    all_actuals = {}
    grand_totals = {"H": 0, "M": 0, "P": 0, "total": 0}

    for date_str in dates:
        print(f"━━━ {date_str} ━━━")

        espn_date = date_str.replace("-", "")
        wnba_games = get_espn_games("basketball/wnba", espn_date)
        nba_games = get_espn_games("basketball/nba", espn_date)

        all_games = [("WNBA", g) for g in wnba_games] + [("NBA", g) for g in nba_games]

        if not all_games:
            print(f"  No games found on {date_str}")
            continue

        for sport, g in all_games:
            matchup = f"{g['away']}@{g['home']}"
            sport_path = f"basketball/{sport.lower()}"
            print(f"\n  [{sport}] {matchup}: {g['away']} {g['away_score']} - {g['home_score']} {g['home']} ({g['status']})")

            if g["status"] not in ("STATUS_FINAL", "Final"):
                print(f"    Skipping — not final ({g['status']})")
                continue

            away_dict, home_dict = scrape_espn_boxscore(g["id"], sport_path, g["home"])
            all_boxscore = {**away_dict, **home_dict}
            print(f"    Players scraped: {len(all_boxscore)}")

            actual_key = f"{date_str}_{g['away']}_{g['home']}"
            all_actuals[actual_key] = {
                "date": date_str, "sport": sport, "matchup": matchup,
                "away": g["away"], "home": g["home"],
                "away_score": g["away_score"], "home_score": g["home_score"],
                "players": {},
            }
            for name, stats in all_boxscore.items():
                simple = {}
                for k, v in stats.items():
                    if k != "name":
                        simple[k] = v
                all_actuals[actual_key]["players"][name] = simple

            picks_file = f"{LOG_DIR}/{date_str}/picks.csv"
            if not os.path.exists(picks_file):
                print(f"    No picks.csv for {date_str}")
                continue

            picks = []
            with open(picks_file, "r", newline="") as f:
                first_line = f.readline()
                f.seek(0)
                COLUMNS = ["date", "league", "matchup", "team", "player", "role", "status",
                           "stat", "direction", "market_line", "tc_projection", "tc_target",
                           "edge", "threshold", "raw_average", "source", "actual", "result"]
                if first_line.startswith("date,league,matchup"):
                    reader = csv.DictReader(f)
                    for row in reader:
                        if not row.get("player"):
                            continue
                        row_matchup = row.get("matchup", "")
                        if row_matchup and row_matchup != matchup and row_matchup.replace("NYK","NY").replace("SAS","SA") != matchup:
                            continue
                        picks.append(row)
                else:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(",")
                        if len(parts) < 8:
                            continue
                        row = dict(zip(COLUMNS, parts))
                        row_matchup = row.get("matchup", "")
                        if row_matchup and row_matchup != matchup and row_matchup.replace("NYK","NY").replace("SAS","SA") != matchup:
                            continue
                        picks.append(row)

            if not picks:
                print(f"    No picks for {matchup}")
                continue

            graded_for_game = {"H": 0, "M": 0, "P": 0, "total": 0}

            for pick in picks:
                player_name = pick["player"].strip()
                stat = pick.get("stat", "").strip()
                team_abbr = pick.get("team", "").strip()

                team_boxscore = away_dict if normalize_team(team_abbr) == normalize_team(g["away"]) else home_dict

                player_stats = get_player_actual(player_name, team_boxscore)
                if not player_stats:
                    pick["actual"] = "N/A"
                    pick["result"] = "NOT_FOUND"
                    all_graded.append(dict(pick))
                    continue

                actual_val = parse_stat_from_boxscore(player_stats, stat)
                pick["actual"] = actual_val
                result, _ = grade_pick(pick, actual_val)
                pick["result"] = result

                all_graded.append(dict(pick))
                graded_for_game["total"] += 1
                if result in ("H", "M", "P"):
                    graded_for_game[result] += 1

            if graded_for_game["total"] > 0:
                total = graded_for_game["total"]
                hit_rate = graded_for_game["H"] / total * 100 if total else 0
                print(f"    Picks graded: {total} | H:{graded_for_game['H']} M:{graded_for_game['M']} P:{graded_for_game['P']} | Hit: {hit_rate:.1f}%")
                grand_totals["H"] += graded_for_game["H"]
                grand_totals["M"] += graded_for_game["M"]
                grand_totals["P"] += graded_for_game["P"]
                grand_totals["total"] += total

    print(f"\n{'='*70}")
    print(f"  OVERALL RESULTS")
    print(f"{'='*70}")

    total = grand_totals["total"]
    if total > 0:
        hit_rate = grand_totals["H"] / total * 100
        print(f"  Total picks graded: {total}")
        print(f"  H:{grand_totals['H']}  M:{grand_totals['M']}  P:{grand_totals['P']}")
        print(f"  Hit rate: {hit_rate:.1f}%")

        by_stat = defaultdict(lambda: {"H": 0, "M": 0, "P": 0})
        by_team = defaultdict(lambda: {"H": 0, "M": 0, "P": 0})
        by_date = defaultdict(lambda: {"H": 0, "M": 0, "P": 0})

        for g in all_graded:
            stat = g.get("stat", "?")
            team = g.get("team", "?")
            dt = g.get("date", "?")
            res = g.get("result", "?")
            if res in ("H", "M", "P"):
                by_stat[stat][res] += 1
                by_team[team][res] += 1
                by_date[dt][res] += 1

        print(f"\n  ── BY STAT ──")
        for stat in sorted(by_stat):
            d = by_stat[stat]
            t = d["H"] + d["M"] + d["P"]
            hr = d["H"] / t * 100 if t else 0
            print(f"  {stat:<4}: {t:>3} picks | H:{d['H']} M:{d['M']} P:{d['P']} | {hr:.1f}%")

        print(f"\n  ── BY TEAM ──")
        for team in sorted(by_team):
            d = by_team[team]
            t = d["H"] + d["M"] + d["P"]
            hr = d["H"] / t * 100 if t else 0
            print(f"  {team:<4}: {t:>3} picks | H:{d['H']} M:{d['M']} P:{d['P']} | {hr:.1f}%")

    summary = {
        "generated_at": datetime.now().isoformat(),
        "dates": dates,
        "games": [f"{k.split('_', 2)[2] if '_' in k else k} ({v['away_score']}-{v['home_score']})" for k, v in all_actuals.items()],
        "picks_graded": total,
        "hit_rate": round(hit_rate, 4) if total > 0 else 0,
        "by_stat": {s: {"H": d["H"], "M": d["M"], "P": d["P"], "rate": round(d["H"]/(d["H"]+d["M"]+d["P"]), 4) if (d["H"]+d["M"]+d["P"]) else 0} for s, d in by_stat.items()} if total > 0 else {},
        "by_team": {t: {"H": d["H"], "M": d["M"], "P": d["P"], "rate": round(d["H"]/(d["H"]+d["M"]+d["P"]), 4) if (d["H"]+d["M"]+d["P"]) else 0} for t, d in by_team.items()} if total > 0 else {},
    }

    for date_str in dates:
        out_dir = f"{LOG_DIR}/{date_str}"
        os.makedirs(out_dir, exist_ok=True)

        actuals_file = f"{out_dir}/boxscore_actuals.json"
        date_actuals = {k: v for k, v in all_actuals.items() if v["date"] == date_str}
        with open(actuals_file, "w") as f:
            json.dump(date_actuals, f, indent=2, default=str)
        print(f"\n  ✅ Actuals saved: {actuals_file}")

        date_graded = [g for g in all_graded if g.get("date") == date_str]
        if date_graded:
            graded_file = f"{out_dir}/boxscore_graded.json"
            with open(graded_file, "w") as f:
                json.dump(date_graded, f, indent=2, default=str)
            print(f"  ✅ Graded saved: {graded_file}")

            graded_csv = f"{out_dir}/boxscore_graded.csv"
            with open(graded_csv, "w", newline="") as f:
                if date_graded:
                    writer = csv.DictWriter(f, fieldnames=date_graded[0].keys())
                    writer.writeheader()
                    writer.writerows(date_graded)
            print(f"  ✅ Graded CSV saved: {graded_csv}")

    summary_file = f"{LOG_DIR}/boxscore_backtest_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  ✅ Summary saved: {summary_file}")

    return all_graded, all_actuals, summary


if __name__ == "__main__":
    main()
