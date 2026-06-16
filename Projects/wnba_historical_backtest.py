#!/usr/bin/env python3
"""WNBA Historical Backtest Pipeline — cross-reference TC vs closing lines + actuals"""

import sys, os, json, csv, requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path("/home/workspace")
LOG_DIR = WORKSPACE / "Daily_Log"
ET = timezone(timedelta(hours=-5))

_sec = Path("/root/.zo/secrets.env")
if _sec.exists():
    for _line in _sec.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
API_BASE = "https://api.the-odds-api.com/v4"


def fetch_hist_game_odds(date_str: str) -> list:
    """Fetch historical WNBA game odds for a specific date."""
    url = f"{API_BASE}/historical/sports/basketball_wnba/odds"
    params = {"apiKey": ODDS_KEY, "regions": "us", "markets": "h2h,spreads,totals",
              "oddsFormat": "american", "date": f"{date_str}T12:00:00Z"}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 200:
        return r.json().get("data", [])
    print(f"  Error fetching hist odds: {r.status_code}")
    return []


def fetch_hist_event_props(sport: str, event_id: str, date_str: str) -> dict:
    """Fetch historical player props for a specific event."""
    url = f"{API_BASE}/historical/sports/{sport}/events/{event_id}/odds"
    params = {"apiKey": ODDS_KEY, "regions": "us",
              "markets": "player_points,player_rebounds,player_assists",
              "oddsFormat": "american", "date": f"{date_str}T12:00:00Z"}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code == 200:
        return r.json()
    return {}


def fetch_espn_boxscore(game_id: str) -> dict:
    """Fetch ESPN WNBA boxscore for actual stats."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={game_id}"
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        return r.json()
    return {}


def parse_actuals(boxscore: dict) -> dict:
    """Extract per-player actual stats from ESPN WNBA boxscore."""
    actuals = {}
    players_list = boxscore.get("boxscore", {}).get("players", [])
    for pt in players_list:
        team = pt.get("team", {}).get("abbreviation", "")
        for sg in pt.get("statistics", []):
            for a in sg.get("athletes", []):
                if not isinstance(a, dict):
                    continue
                athlete = a.get("athlete", {})
                name = athlete.get("displayName") or athlete.get("fullName", "")
                if not name:
                    continue
                stats = a.get("stats", [])
                if not stats:
                    continue
                key = f"{name}|{team}"
                actuals[key] = {
                    "player": name, "team": team,
                    "PTS": float(stats[0]) if len(stats) > 0 and stats[0] else 0.0,
                    "REB": float(stats[1]) if len(stats) > 1 and stats[1] else 0.0,
                    "AST": float(stats[2]) if len(stats) > 2 and stats[2] else 0.0,
                    "3PM": float(stats[3]) if len(stats) > 3 and stats[3] else 0.0,
                    "STL": float(stats[4]) if len(stats) > 4 and stats[4] else 0.0,
                    "BLK": float(stats[5]) if len(stats) > 5 and stats[5] else 0.0,
                }
    return actuals


def parse_dk_lines(odds_data: dict) -> dict:
    """Extract DK player prop lines from historical odds."""
    lines = {}
    bookmakers = odds_data.get("bookmakers", [])
    for bk in bookmakers:
        if bk.get("key") != "draftkings":
            continue
        for market in bk.get("markets", []):
            mkey = market.get("key", "")
            stat_map = {"player_points": "PTS", "player_rebounds": "REB", "player_assists": "AST"}
            stat = stat_map.get(mkey)
            if not stat:
                continue
            for outcome in market.get("outcomes", []):
                name = outcome.get("description", "")
                point = outcome.get("point")
                price = outcome.get("price")
                over_under = "OVER" if outcome.get("name") == "Over" else "UNDER"
                key = f"{name}|{stat}|{over_under}"
                if key not in lines:
                    lines[key] = {"player": name, "stat": stat, "over_under": over_under,
                                  "line": point, "price": price}
    return lines


def run_backtest(days_back: int = 7):
    """Run WNBA historical backtest for the past N days."""
    results = []
    today = datetime.now(ET)

    for d in range(days_back, 0, -1):
        date_obj = today - timedelta(days=d)
        date_str = date_obj.strftime("%Y-%m-%d")
        print(f"\n=== {date_str} ===")

        games = fetch_hist_game_odds(date_str)
        if not games:
            print("  No games")
            continue

        for g in games[:8]:
            away = g.get("away_team", "")
            home = g.get("home_team", "")
            event_id = g.get("id", "")
            commence = g.get("commence_time", "")
            print(f"  {away} @ {home} ({event_id[:12]}...)")

            # Get historical lines
            props_data = fetch_hist_event_props("basketball_wnba", event_id, date_str)
            dk_lines = parse_dk_lines(props_data)
            if not dk_lines:
                print("    No DK lines")
                continue

            # Get actual stats from ESPN boxscore
            boxscore = fetch_espn_boxscore(event_id)
            actuals = parse_actuals(boxscore)
            if not actuals:
                print("    No boxscore data")
                continue

            # Compare
            hits = 0
            misses = 0
            pushes = 0
            for key, line_info in dk_lines.items():
                player = line_info["player"]
                stat = line_info["stat"]
                over_under = line_info["over_under"]
                line_val = line_info["line"]
                price = line_info["price"]

                # Find actual
                matched = None
                for ak, av in actuals.items():
                    if player.lower() in ak.lower() or ak.lower().startswith(player.lower()[:len(player) - 3]):
                        matched = av
                        break

                actual_val = matched[stat] if matched else None
                result = "NOT_FOUND"

                if actual_val is not None:
                    if over_under == "OVER":
                        if actual_val > line_val:
                            result = "HIT"
                            hits += 1
                        elif actual_val < line_val:
                            result = "MISS"
                            misses += 1
                        else:
                            result = "PUSH"
                            pushes += 1
                    else:
                        if actual_val < line_val:
                            result = "HIT"
                            hits += 1
                        elif actual_val > line_val:
                            result = "MISS"
                            misses += 1
                        else:
                            result = "PUSH"
                            pushes += 1

                results.append({
                    "date": date_str,
                    "matchup": f"{away}@{home}",
                    "player": player,
                    "stat": stat,
                    "over_under": over_under,
                    "line": line_val,
                    "price": price,
                    "actual": actual_val,
                    "result": result,
                })

            total = hits + misses + pushes
            pct = f"{(hits / total * 100):.1f}%" if total > 0 else "N/A"
            print(f"    H:{hits} M:{misses} P:{pushes} = {pct}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="WNBA Historical Backtest")
    parser.add_argument("--days", type=int, default=7, help="Days to backtest")
    parser.add_argument("--output", type=str, default=None, help="Output CSV path")
    args = parser.parse_args()

    results = run_backtest(args.days)

    date_str = datetime.now(ET).strftime("%Y-%m-%d")
    csv_path = args.output or str(LOG_DIR / f"{date_str}/wnba_hist_backtest.csv")
    Path(csv_path).parent.mkdir(exist_ok=True)

    if results:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

        total = len(results)
        hits = sum(1 for r in results if r["result"] == "HIT")
        misses = sum(1 for r in results if r["result"] == "MISS")
        pushes = sum(1 for r in results if r["result"] == "PUSH")
        nf = sum(1 for r in results if r["result"] == "NOT_FOUND")
        graded = hits + misses + pushes

        print(f"\n=== SUMMARY (WNBA Historical) ===")
        print(f"Total props: {total}")
        print(f"Hits: {hits} Misses: {misses} Pushes: {pushes} Not Found: {nf}")
        if graded > 0:
            print(f"Hit Rate (graded): {(hits / graded * 100):.1f}%")
        print(f"\nSaved to {csv_path}")

        # Per-stat breakdown
        by_stat = defaultdict(lambda: {"H": 0, "M": 0, "P": 0})
        for r in results:
            if r["result"] in ("HIT", "MISS", "PUSH"):
                by_stat[r["stat"]][r["result"][0]] += 1

        print(f"\n{'Stat':<6} {'H':>4} {'M':>4} {'P':>4} {'Rate':>7}")
        for stat, counts in sorted(by_stat.items()):
            t = counts["H"] + counts["M"] + counts["P"]
            rate = f"{(counts['H'] / t * 100):.1f}%" if t > 0 else "N/A"
            print(f"{stat:<6} {counts['H']:>4} {counts['M']:>4} {counts['P']:>4} {rate:>7}")
    else:
        print("No results.")


if __name__ == "__main__":
    main()
