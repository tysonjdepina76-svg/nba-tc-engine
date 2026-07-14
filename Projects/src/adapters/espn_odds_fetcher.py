"""ESPN v2 odds/metrics fetcher with caching and fallback."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

CACHE_DIR = Path("/home/workspace/Daily_Log/cache/espn_odds")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL_SEC = 900  # 15 minutes
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"


def _cache_path(key: str) -> Path:
    safe = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.json"


def _read_cache(key: str) -> Optional[Dict]:
    p = _cache_path(key)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL_SEC:
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(key: str, data: Dict) -> None:
    try:
        with open(_cache_path(key), "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def fetch_scoreboard(sport: str, league: str, date_str: str) -> Dict:
    """Fetch ESPN v2 scoreboard. sport e.g. 'basketball', league e.g. 'wnba'."""
    key = f"{sport}/{league}/{date_str}"
    cached = _read_cache(key)
    if cached is not None:
        return cached
    try:
        import urllib.request
        url = f"{ESPN_BASE}/{sport}/{league}/scoreboard?dates={date_str.replace('-','')}"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        _write_cache(key, data)
        return data
    except Exception as e:
        return {"error": str(e), "events": []}


def extract_odds(events: List[Dict]) -> List[Dict]:
    """Pull best odds (spread, total, moneyline) from ESPN event dicts."""
    out = []
    for ev in events:
        comps = ev.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        odds_list = comp.get("odds", [])
        if not odds_list:
            continue
        o = odds_list[0]
        out.append({
            "event_id": ev.get("id"),
            "name": ev.get("name"),
            "spread": o.get("spread"),
            "over_under": o.get("overUnder"),
            "favorite": o.get("favorite", {}).get("abbreviation") if o.get("favorite") else None,
            "provider": o.get("provider", {}).get("name"),
        })
    return out


if __name__ == "__main__":
    import sys
    sport = sys.argv[1] if len(sys.argv) > 1 else "basketball"
    league = sys.argv[2] if len(sys.argv) > 2 else "wnba"
    date = sys.argv[3] if len(sys.argv) > 3 else "20260713"
    sb = fetch_scoreboard(sport, league, date)
    print(f"events: {len(sb.get('events', []))}")
    print(json.dumps(extract_odds(sb.get("events", [])), indent=2)[:500])


def fetch_espn_odds_cached(sport: str, date_str: str, league: Optional[str] = None) -> Dict:
    """Return odds keyed by (player, stat) -> line. sport e.g. 'wnba', 'mlb'. Returns {} if no events."""
    if not league:
        sport_l = (sport or "").lower()
        if "wnba" in sport_l:
            league = "basketball/wnba"
        elif "nba" in sport_l:
            league = "basketball/nba"
        elif "mlb" in sport_l:
            league = "baseball/mlb"
        elif "nfl" in sport_l:
            league = "football/nfl"
        elif "nhl" in sport_l:
            league = "hockey/nhl"
        else:
            league = sport
    parts = league.split("/")
    sport_path = parts[0] if parts else sport
    league_path = parts[1] if len(parts) > 1 else league
    sb = fetch_scoreboard(sport_path, league_path, date_str)
    events = sb.get("events", []) if isinstance(sb, dict) else []
    odds_list = extract_odds(events)
    out: Dict = {}
    for ev in odds_list:
        out[ev.get("name", "")] = {
            "spread": ev.get("spread"),
            "over_under": ev.get("over_under"),
            "favorite": ev.get("favorite"),
        }
    return out
