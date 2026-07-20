"""
ESPN API v2 Enricher — pulls live DK player prop lines (free, no key).
Maps to TC projections by player name + stat.
"""
from __future__ import annotations
import json, urllib.request, time, re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CACHE_DIR = Path("/home/workspace/Daily_Log/cache/espn_enrich")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 600

BASE = "http://sports.core.api.espn.com/v2/sports"

# Sport → (sport_path, league_path)
SPORT_MAP = {
    "wnba": ("basketball", "wnba"),
    "mlb": ("baseball", "mlb"),
    "wc": ("soccer", "fifa.world"),
}

# ESPN prop type name → TC stat
PROP_STAT_MAP = {
    "Points Milestones": "PTS",
    "Rebounds Milestones": "REB",
    "Assists Milestones": "AST",
    "3-Point Field Goals Milestones": "3PM",
    "Points + Assists Milestones": "P+A",
    "Points + Rebounds Milestones": "P+R",
    "Points + Assists + Rebounds Milestones": "P+A+R",
    "Total Hits": "H",
    "Total Singles Hit": "1B",
    "Total Doubles Hit": "2B",
    "Total Hits + Runs + RBIs": "H+R+RBI",
    "Total Bases": "TB",
    "Total Strikeouts": "SO",
    "Earned Runs Allowed": "ER",
    "Total Hits Allowed": "HA",
}


def _cache_get(key: str) -> Optional[dict]:
    p = CACHE_DIR / f"{key}.json"
    if p.exists() and time.time() - p.stat().st_mtime < CACHE_TTL:
        try:
            return json.loads(p.read_text())
        except:
            pass
    return None


def _cache_put(key: str, data: dict):
    try:
        (CACHE_DIR / f"{key}.json").write_text(json.dumps(data))
    except:
        pass


def _fetch(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e), "items": []}


def _fetch_all_pages(url: str) -> list:
    """Fetch paginated results."""
    all_items = []
    page = 1
    while True:
        sep = "&" if "?" in url else "?"
        paged = f"{url}{sep}page={page}&limit=100"
        data = _fetch(paged)
        if "error" in data:
            break
        items = data.get("items", [])
        if not items:
            break
        all_items.extend(items)
        if len(items) < 100:
            break
        page += 1
    return all_items


def fetch_espn_player_lines(sport: str) -> Dict[str, Dict[str, float]]:
    """
    Returns {(playername, stat): line_value} from ESPN DK prop bets.
    Example: {("Paige Bueckers", "PTS"): 20.0, ...}
    """
    today = datetime.now(ET).strftime("%Y%m%d")
    cache_key = f"{sport}_{today}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    if sport not in SPORT_MAP:
        return {}
    sport_path, league_path = SPORT_MAP[sport]

    # 1. Get today's events
    events_url = f"{BASE}/{sport_path}/leagues/{league_path}/events?dates={today}&lang=en&region=us"
    events_data = _fetch(events_url)
    event_refs = [item["$ref"] for item in events_data.get("items", [])]

    lines: Dict = {}

    # 2. For each event, get prop bets
    for ref in event_refs:
        try:
            event_id = ref.split("/events/")[1].split("?")[0] if "/events/" in ref else ""
            # Player prop bets
            props_url = f"{BASE}/{sport_path}/leagues/{league_path}/events/{event_id}/competitions/{event_id}/odds/100/propBets?lang=en&region=us"
            prop_items = _fetch_all_pages(props_url)

            for item in prop_items:
                athlete_ref = item.get("athlete", {}).get("$ref", "")
                if not athlete_ref:
                    continue
                athlete_id = athlete_ref.split("/athletes/")[-1].split("?")[0] if "/athletes/" in athlete_ref else ""
                prop_type = item.get("type", {}).get("name", "")
                stat = PROP_STAT_MAP.get(prop_type, prop_type)
                line_val = item.get("current", {}).get("target", {}).get("value") or item.get("odds", {}).get("total", {}).get("value", 0)
                if isinstance(line_val, str):
                    try:
                        line_val = float(line_val.replace("+", "").strip())
                    except:
                        continue
                if not line_val:
                    continue

                # Get athlete name
                name = _get_athlete_name(sport_path, league_path, athlete_id)
                if name:
                    key = (name, stat)
                    # Keep the lowest milestone line for each (player, stat)
                    if key not in lines or line_val < lines[key]:
                        lines[key] = line_val
        except Exception:
            continue

    _cache_put(cache_key, lines)
    return lines


def _get_athlete_name(sport: str, league: str, athlete_id: str) -> Optional[str]:
    """Cache athlete ID -> full name."""
    name_cache = CACHE_DIR / "athlete_names.json"
    cache: dict = {}
    if name_cache.exists():
        try:
            cache = json.loads(name_cache.read_text())
        except:
            pass
    if athlete_id in cache:
        return cache[athlete_id]

    url = f"{BASE}/{sport}/leagues/{league}/athletes/{athlete_id}?lang=en&region=us"
    data = _fetch(url)
    name = data.get("fullName") or data.get("displayName") or ""
    if name:
        cache[athlete_id] = name
        try:
            name_cache.write_text(json.dumps(cache))
        except:
            pass
    return name


def enrich_projection_lines(sport: str, projections: List[dict]) -> List[dict]:
    """
    Given TC projections, enrich with ESPN DK player prop lines.
    Matches on player name + stat. Returns updated projections.
    """
    espn_lines = fetch_espn_player_lines(sport)
    if not espn_lines:
        return projections

    enriched = 0
    for pick in projections:
        name = pick.get("name", "")
        stat = pick.get("stat", "")
        existing_line = pick.get("line", 0)

        # Only override if current line is 0 or self-edge
        if existing_line != 0 and pick.get("signal", "") != "SELF_EDGE":
            continue

        # Try exact match
        key = (name, stat)
        if key in espn_lines:
            new_line = espn_lines[key]
            pick["line"] = new_line
            pick["edge"] = pick["projection"] - new_line
            pick["direction"] = "OVER" if pick["edge"] > 0 else "UNDER"
            pick["signal"] = "ESPN"
            enriched += 1
        else:
            # Try partial name match (last name)
            for (pn, st), ln in espn_lines.items():
                if st == stat and (name.lower() in pn.lower() or pn.lower() in name.lower()):
                    pick["line"] = ln
                    pick["edge"] = pick["projection"] - ln
                    pick["direction"] = "OVER" if pick["edge"] > 0 else "UNDER"
                    pick["signal"] = "ESPN"
                    enriched += 1
                    break

    return projections


if __name__ == "__main__":
    import sys
    s = sys.argv[1] if len(sys.argv) > 1 else "wnba"
    lines = fetch_espn_player_lines(s)
    print(f"ESPN DK lines for {s}: {len(lines)} player-stat pairs")
    for k, v in sorted(lines.items())[:10]:
        print(f"  {k[0]:30s} {k[1]:6s} = {v}")
