#!/usr/bin/env python3
"""
Grade WNBA picks using ESPN API boxscore data.
Fetches /summary for each game, extracts actual player stats,
compares against pick direction+projection to compute hit/miss.
"""
import csv, json, sys, os, urllib.request, urllib.error, argparse, re, time
from collections import defaultdict
from datetime import datetime

def add_combo_stats(boxscore):
    """Add PA, PR, PRA to boxscore dict for each player.
    Assumes boxscore has PTS, REB, AST for each player."""
    for player, stats in boxscore.items():
        pts = stats.get("PTS", 0) or 0
        reb = stats.get("REB", 0) or 0
        ast = stats.get("AST", 0) or 0
        stats["PA"] = pts + ast
        stats["PR"] = pts + reb
        stats["PRA"] = pts + reb + ast
    return boxscore


ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date}"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event={event_id}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TC-Grader/1.0)"}

def _name_key(name):
    """Normalize for matching: lowercase, strip punctuation, sort tokens."""
    n = re.sub(r"[^a-z]+", " ", name.lower()).strip()
    tokens = sorted(n.split())
    return " ".join(tokens)

def fetch_json(url, cache={}):
    if url in cache:
        return cache[url]
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        cache[url] = data
        return data
    except Exception as e:
        print(f"  FETCH ERROR: {url} -> {e}", file=sys.stderr)
        return None

def get_game_ids(date_str):
    """Get ESPN event IDs for WNBA games on a given date."""
    url = ESPN_SCOREBOARD.format(date=date_str.replace("-",""))
    data = fetch_json(url)
    if not data:
        return {}
    event_ids = {}
    for ev in data.get("events", []):
        comps = ev.get("competitions", [{}])
        if comps and len(comps[0].get("competitors", [])) >= 2:
            away = comps[0]["competitors"][1]["team"]["abbreviation"]
            home = comps[0]["competitors"][0]["team"]["abbreviation"]
            matchup = f"{away}_at_{home}"
            event_ids[matchup] = ev["id"]
    return event_ids

def get_boxscores(event_ids):
    """Fetch boxscore data for all game IDs. Returns dict of matchup -> {player_name_key: {stat: value}}."""
    boxes = {}
    for matchup, eid in event_ids.items():
        url = ESPN_SUMMARY.format(event_id=eid)
        data = fetch_json(url)
        if not data:
            continue
        player_stats = {}
        for team_data in data.get("boxscore", {}).get("players", []):
            for sg in team_data.get("statistics", []):
                stat_names = sg.get("names", [])
                for athlete in sg.get("athletes", []):
                    a = athlete.get("athlete", {})
                    if not a:
                        continue
                    name = a.get("displayName", "")
                    if not name:
                        continue
                    stats = athlete.get("stats", [])
                    nk = _name_key(name)
                    parsed = {}
                    for i, sn in enumerate(stat_names):
                        if i < len(stats):
                            try:
                                parsed[sn] = float(stats[i])
                            except (ValueError, TypeError):
                                parsed[sn] = None
                    if parsed:
                        player_stats[nk] = parsed
        boxes[matchup] = player_stats
        print(f"  {matchup}: {len(player_stats)} players with boxscores")
    return boxes

def grade_picks(picks_csv, date_str):
    """Grade all picks in the CSV against ESPN boxscores. Returns (hits, total, results_list, missing_list)."""
    game_ids = get_game_ids(date_str)
    if not game_ids:
        print("ERROR: No game IDs found for date", date_str)
        return 0, 0, [], []
    print(f"Found {len(game_ids)} games:", list(game_ids.keys()))
    boxes = get_boxscores(game_ids)
    if not boxes:
        print("ERROR: No boxscores fetched")
        return 0, 0, [], []

    picks = []
    with open(picks_csv) as f:
        for r in csv.DictReader(f):
            picks.append(r)
    print(f"Loaded {len(picks)} picks")

    # Normalize stat names + compute compound stats via add_combo_stats
    STAT_MAP = {"3PM": "3PT", "3PT": "3PT", "FG": "FG", "FT": "FT"}
    for matchup, players in boxes.items():
        for nk, stats in players.items():
            if "3PM" in stats:
                stats["3PT"] = stats.pop("3PM")
        boxes[matchup] = add_combo_stats(players)

    def _resolve_matchup(m, boxes):
        if m in boxes:
            return m
        parts = m.split("_at_")
        if len(parts) == 2:
            swapped = f"{parts[1]}_at_{parts[0]}"
            if swapped in boxes:
                return swapped
        return None

    hits = 0
    total = 0
    results = []
    missing = []
    for p in picks:
        matchup = p.get("matchup", "")
        stat = p.get("stat", "PTS")
        direction = p.get("direction", "OVER")
        try:
            projection = float(p.get("projection", 0))
            line = float(p.get("line", 0))
        except (ValueError, TypeError):
            missing.append(p)
            continue

        resolved = _resolve_matchup(matchup, boxes)
        if resolved is None:
            missing.append(p)
            continue

        nk = _name_key(p.get("name", ""))
        player_stats = boxes[resolved].get(nk)
        if not player_stats:
            missing.append(p)
            continue

        actual_str = player_stats.get(stat)
        if actual_str is None:
            missing.append(p)
            continue
        actual = float(actual_str)

        is_hit = (direction == "OVER" and actual > line) or (direction == "UNDER" and actual < line)
        total += 1
        if is_hit:
            hits += 1

        results.append({
            "name": p.get("name"),
            "stat": stat,
            "matchup": matchup,
            "direction": direction,
            "projection": projection,
            "line": line,
            "actual": actual,
            "edge": float(p.get("edge", 0)),
            "hit": is_hit,
        })
    return hits, total, results, missing

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--picks", required=True)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    print(f"Grading WNBA picks for {args.date} via ESPN...")
    hits, total, results, missing = grade_picks(args.picks, args.date)

    if total == 0:
        print(f"RESULTS: 0 graded, {len(missing)} missing (no player matches)")
        return

    rate = hits / total * 100
    print(f"\nRESULTS: {hits}/{total} = {rate:.1f}% ({len(missing)} missing)")

    print("By direction:")
    for d in ["OVER", "UNDER"]:
        subset = [r for r in results if r["direction"] == d]
        if not subset:
            continue
        h = sum(1 for r in subset if r["hit"])
        print(f"  {d}: {h}/{len(subset)} = {h/len(subset)*100:.1f}%")

    print("By stat:")
    by_stat = defaultdict(lambda: {"hits": 0, "total": 0})
    for r in results:
        by_stat[r["stat"]]["total"] += 1
        if r["hit"]:
            by_stat[r["stat"]]["hits"] += 1
    for s in sorted(by_stat, key=lambda x: by_stat[x]["hits"]/by_stat[x]["total"], reverse=True):
        d = by_stat[s]
        print(f"  {s}: {d['hits']}/{d['total']} = {d['hits']/d['total']*100:.1f}%")

    out = args.output or f"/home/workspace/data/picks/wnba_graded_{args.date.replace('-','')}.json"
    with open(out, "w") as f:
        json.dump({"date": args.date, "hits": hits, "total": total, "hit_rate": rate,
                   "missing_count": len(missing), "results": results}, f, indent=2)
    print(f"\nSaved: {out}")

if __name__ == "__main__":
    main()
