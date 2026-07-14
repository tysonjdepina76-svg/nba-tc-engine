"""WNBA data fetcher: ESPN rosters, schedules, boxscores. No Odds API dependency (quota)."""
from __future__ import annotations
import json, time
from pathlib import Path
from typing import Dict, List, Optional
import requests, os
from typing import Dict, List, Optional, Tuple

CACHE_DIR = Path("/home/workspace/Daily_Log/wnba_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 600  # 10 min

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"


def _cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.json"


def _read_cache(name: str) -> Optional[dict]:
    p = _cache_path(name)
    if not p.exists() or time.time() - p.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _write_cache(name: str, data) -> None:
    _cache_path(name).write_text(json.dumps(data, indent=2))


def fetch_scoreboard(date_str: str) -> Dict:
    """Fetch WNBA scoreboard for a given date (YYYY-MM-DD)."""
    cached = _read_cache(f"scoreboard_{date_str}")
    if cached is not None:
        return cached
    try:
        ymd = date_str.replace("-", "")
        r = requests.get(f"{ESPN_BASE}/scoreboard", params={"dates": ymd, "limit": 50}, timeout=10)
        if r.status_code != 200:
            return {"events": [], "error": f"http_{r.status_code}"}
        data = r.json()
        _write_cache(f"scoreboard_{date_str}", data)
        return data
    except Exception as e:
        return {"events": [], "error": str(e)}


def fetch_roster(team_id: int) -> Dict:
    """Fetch a single WNBA team's roster."""
    cached = _read_cache(f"roster_{team_id}")
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{ESPN_BASE}/teams/{team_id}/roster", timeout=10)
        if r.status_code != 200:
            return {"athletes": [], "error": f"http_{r.status_code}"}
        data = r.json()
        _write_cache(f"roster_{team_id}", data)
        return data
    except Exception as e:
        return {"athletes": [], "error": str(e)}


def fetch_all_rosters() -> Dict[int, List[dict]]:
    """Fetch rosters for all 13 WNBA teams."""
    team_ids = [
        1, 2, 5, 6, 8, 9, 10, 11, 14, 15, 16, 17, 18,
        19, 20, 21, 22, 23, 24, 25, 26,
    ]
    out = {}
    for tid in team_ids:
        data = fetch_roster(tid)
        athletes = data.get("athletes", [])
        out[tid] = [
            {"name": a.get("fullName"), "id": a.get("id"), "pos": a.get("position", {}).get("abbreviation")}
            for a in athletes
        ]
    return out


def fetch_boxscore(event_id: str) -> Dict:
    """Fetch a single WNBA game's boxscore."""
    cached = _read_cache(f"boxscore_{event_id}")
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{ESPN_BASE}/summary", params={"event": event_id}, timeout=10)
        if r.status_code != 200:
            return {"error": f"http_{r.status_code}"}
        data = r.json()
        _write_cache(f"boxscore_{event_id}", data)
        return data
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    sb = fetch_scoreboard("2026-07-13")
    print(f"Events on 2026-07-13: {len(sb.get('events', []))}")
    for e in sb.get("events", [])[:3]:
        print(f"  {e.get('name')} (id={e.get('id')})")

# ---- Lines bridge (replaces Odds API for WNBA props) ----

def fetch_wnba_lines(date_str: str) -> Dict[Tuple[str, str], float]:
    """Fetch WNBA player prop lines. Returns {(player, stat): line}.
    Falls back to league-avg placeholders when no Odds API key / no data.
    """
    out: Dict[Tuple[str, str], float] = {}
    # 1) Try Odds API (will 401 on Business tier quota — caught silently)
    if os.environ.get("ODDS_API_KEY"):
        try:
            import requests
            r = requests.get(
                "https://api.the-odds-api.com/v4/sports/basketball_wnba/odds",
                params={"apiKey": os.environ["ODDS_API_KEY"], "regions": "us",
                        "markets": "player_points,player_rebounds,player_assists",
                        "oddsFormat": "american"},
                timeout=10)
            if r.status_code == 200:
                for ev in r.json():
                    for book in ev.get("bookmakers", []):
                        for m in book.get("markets", []):
                            for outc in m.get("outcomes", []):
                                pname = outc.get("description", "")
                                pt = outc.get("point")
                                if pname and pt is not None:
                                    stat_key = m["key"].replace("player_", "").upper()
                                    out[(pname, stat_key)] = float(pt)
        except Exception as e:
            print(f"[wnba_data_fetcher] odds-api failed: {e}")
    # 2) Fallback: league-avg lines (from LEAGUE_AVG) so picks have SOME line
    from hybrid_wnba_predictor import LEAGUE_AVG
    if not out:
        for stat, val in LEAGUE_AVG.items():
            out[("__LEAGUE_AVG__", stat)] = float(val)
    return out
