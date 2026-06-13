"""Pull per-player last-N game logs and compute rolling averages — NBA + WNBA.

Output: /home/workspace/Daily_Log/YYYY-MM-DD/gamelogs_cache_NBA.json
        /home/workspace/Daily_Log/YYYY-MM-DD/gamelogs_cache_WNBA.json

Cache format per sport:
  { "player_name_lower": {"pts": 22.5, "reb": 8.2, "ast": 5.1, "3pm": 3.0, "stl": 1.1, "blk": 0.8, "games": 5} }
"""
import json, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("/home/workspace/Daily_Log")
N_GAMES = 5

NBA_TEAM_IDS = {
    "ATL":"1","BOS":"2","BKN":"17","CHA":"30","CHI":"4","CLE":"5","DAL":"6","DEN":"7",
    "DET":"8","GSW":"9","HOU":"10","IND":"11","LAC":"12","LAL":"13","MEM":"29",
    "MIA":"14","MIL":"15","MIN":"16","NOP":"3","NYK":"18","OKC":"25","ORL":"19",
    "PHI":"20","PHX":"21","POR":"22","SAC":"23","SAS":"24","TOR":"28","UTA":"26","WAS":"27",
}

WNBA_TEAM_IDS = {
    "ATL":"20","CHI":"19","DAL":"3","MIN":"8","PHX":"11","GS":"129689",
    "CON":"18","IND":"5","LV":"17","LA":"6","NY":"9","SEA":"14",
    "WAS":"16","POR":"132052","TOR":"131935",
}

STAT_MAP = {
    "points": "pts","rebounds": "reb","assists": "ast",
    "threepointfieldgoalsmade": "3pm","steals": "stl","blocks": "blk",
}

def fetch_team_events(team_id, sport):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport}/teams/{team_id}/schedule"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            d = json.loads(r.read())
    except Exception as e:
        print(f"  ! schedule err team {team_id}: {e}")
        return []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    past = []
    for e in d.get("events", []):
        try:
            edate = datetime.fromisoformat(e["date"].replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            continue
        if edate < now:
            past.append((edate, e["id"]))
    past.sort(reverse=True)
    return [eid for _, eid in past[:N_GAMES * 2]]

def fetch_box(event_id, sport):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport}/summary?event={event_id}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            d = json.loads(r.read())
    except:
        return {}
    out = {}
    for t in d.get("boxscore", {}).get("players", []):
        for grp in t.get("statistics", []):
            keys = [k.lower() for k in grp.get("keys", [])]
            if not keys:
                continue
            idx = {k: i for i, k in enumerate(keys)}
            for a in grp.get("athletes", []):
                ath = a.get("athlete", {}) or {}
                name = (ath.get("displayName") or ath.get("shortName") or "").strip().lower()
                if not name:
                    continue
                vals = a.get("stats", [])
                row = {}
                for k, i in idx.items():
                    if i < len(vals):
                        raw = vals[i]
                        mapped = STAT_MAP.get(k)
                        if mapped:
                            try:
                                row[mapped] = int(raw)
                            except (ValueError, TypeError):
                                pass
                if row:
                    out[name] = row
            break
    return out

def build_cache(sport, team_ids):
    cache = {}
    total_players = 0
    for code, tid in team_ids.items():
        events = fetch_team_events(tid, sport)
        agg = {}
        games_used = 0
        for ev_id in events:
            box = fetch_box(ev_id, sport)
            if not box:
                continue
            games_used += 1
            for pname, stats in box.items():
                bucket = agg.setdefault(pname, {})
                for k, v in stats.items():
                    bucket.setdefault(k, []).append(v)
            if games_used >= N_GAMES:
                break
        for pname, stat_lists in agg.items():
            rolling = {k: round(sum(v) / len(v), 2) for k, v in stat_lists.items()}
            rolling["games"] = min(len(stat_lists.get("pts", [])), N_GAMES)
            rolling["team"] = code
            cache[pname] = rolling
            total_players += 1
        print(f"  {code}: {games_used} games, {len(agg)} players")

    out_dir = LOG_DIR / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"gamelogs_cache_{sport.upper()}.json"
    out_data = {
        "sport": sport.upper(),
        "teams_scanned": len(team_ids),
        "players_cached": total_players,
        "n_games": N_GAMES,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cache": cache,
    }
    out_path.write_text(json.dumps(out_data, indent=2))
    print(f"  → Wrote {out_path} ({total_players} players cached)\n")
    return out_path

def main():
    sports = [a.lower() for a in sys.argv[1:]] if len(sys.argv) > 1 else ["nba", "wnba"]
    for sport in sports:
        ids = NBA_TEAM_IDS if sport == "nba" else WNBA_TEAM_IDS if sport == "wnba" else None
        if not ids:
            print(f"Unknown sport: {sport}")
            continue
        print(f"\n=== {sport.upper()} ===")
        build_cache(sport, ids)

if __name__ == "__main__":
    main()
