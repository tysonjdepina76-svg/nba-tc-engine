"""Pull per-player last-N game logs and compute rolling averages.

For each WNBA team:
  1) Hit /schedule to get past event IDs
  2) Hit /summary?event= for each → box score
  3) Aggregate per-player rolling averages

Output: /home/workspace/Daily_Log/YYYY-MM-DD/gamelogs_<sport>_<team>.json
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("/home/workspace/Daily_Log")
SPORT = "wnba"
N_GAMES = 5

# ESPN team IDs (verified from /apis/site/v2/sports/basketball/wnba/teams)
WNBA_TEAM_IDS = {
    "ATL": "20", "CHI": "19", "DAL": "3", "MIN": "8", "PHX": "11", "GSV": "129689",
    "CON": "18", "IND": "5", "LV": "17", "LA": "6", "NY": "9", "SEA": "14",
    "WAS": "16", "POR": "132052", "TOR": "131935",
}


def fetch_team_schedule(team_id: str) -> list[str]:
    """Return list of past event IDs (most recent first) for a team."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{SPORT}/teams/{team_id}/schedule"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read())
    except Exception as e:
        print(f"  ! schedule err for team {team_id}: {e}")
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


def fetch_game_box(event_id: str) -> dict:
    """Fetch a single game's box score, return per-player {name_lower: {stat: val}}."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{SPORT}/summary?event={event_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read())
    except Exception as e:
        print(f"  ! box err for event {event_id}: {e}")
        return {}
    out = {}
    for t in d.get("boxscore", {}).get("players", []):
        for grp in t.get("statistics", []):
            keys = [k.lower() for k in grp.get("keys", [])]
            if not keys or "points" not in keys:
                continue
            idx = {k: i for i, k in enumerate(keys)}
            for a in grp.get("athletes", []):
                ath = a.get("athlete", {}) or {}
                name = ath.get("displayName") or ath.get("shortName") or ath.get("name", "")
                if not name:
                    continue
                vals = a.get("stats", [])
                row = {k: vals[i] if i < len(vals) else "" for k, i in idx.items()}
                for k_, v_ in row.items():
                    if "-" in str(v_) and k_.endswith("attempted"):
                        mk = k_.replace("attempted", "made")
                        if mk in row:
                            try:
                                row[k_.replace("fieldgoals", "fg").replace("threepointfieldgoals", "3p").replace("freethrows", "ft")] = int(row[mk])
                            except ValueError:
                                pass
                    else:
                        try:
                            row[k_] = int(v_)
                        except ValueError:
                            pass
                out[name.lower()] = row
            break
    return out


def fetch_team_logs(team_code: str, team_id: str) -> dict:
    """Aggregate rolling avgs for a team across last N_GAMES completed games."""
    sched = fetch_team_schedule(team_id)
    agg: dict[str, dict[str, list]] = {}
    games_used = 0
    for ev_id in sched:
        box = fetch_game_box(ev_id)
        if not box:
            continue
        games_used += 1
        for pname, stats in box.items():
            bucket = agg.setdefault(pname, {})
            for k, v in stats.items():
                if isinstance(v, int):
                    bucket.setdefault(k, []).append(v)
        if games_used >= N_GAMES:
            break
    rolling = {
        p: {k: round(sum(v) / len(v), 2) for k, v in stats.items()}
        for p, stats in agg.items()
    }
    return {
        "team": team_code,
        "team_id": team_id,
        "sport": SPORT.upper(),
        "games_used": games_used,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "players": rolling,
    }


def main(sport: str = "wnba"):
    global SPORT
    SPORT = sport.lower()
    team_ids = WNBA_TEAM_IDS if SPORT == "wnba" else {}
    if not team_ids:
        print(f"no team map for {sport}")
        return
    out_dir = LOG_DIR / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    for code, tid in team_ids.items():
        out = fetch_team_logs(code, tid)
        path = out_dir / f"gamelogs_{SPORT}_{code}.json"
        path.write_text(json.dumps(out, indent=2))
        print(f"  {code}: {out['games_used']} games, {len(out['players'])} players -> {path.name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "wnba")
