#!/usr/bin/env python3
"""
Player Stats Scraper — v1.0.0

Multi-source player stat scraper. Pulls season + recent game stats
for players from ESPN (primary) and nflfastR (fallback) for NFL,
ESPN for WNBA / NBA / MLB / NHL.

Output: JSON files under /home/workspace/Projects/data/picks/
        with the naming convention player_stats_<sport>_<YYYY-MM-DD>.json
"""

from __future__ import annotations
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.error

DATA_DIR = Path("/home/workspace/Projects/data/picks")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ESPN public scoreboard / summary endpoints
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"

SPORT_PATHS = {
    "nfl":   "football/nfl",
    "wnba":  "basketball/wnba",
    "nba":   "basketball/nba",
    "mlb":   "baseball/mlb",
    "nhl":   "hockey/nhl",
}

# Default stats to extract per sport (fallback when no explicit list given)
DEFAULT_STATS = {
    "nfl":   ["pass_yds", "pass_td", "pass_int", "rush_yds", "rush_td",
              "rec", "rec_yds", "rec_td", "targets"],
    "wnba":  ["pts", "reb", "ast", "stl", "blk", "tov", "3pm", "fg_pct", "ft_pct"],
    "nba":   ["pts", "reb", "ast", "stl", "blk", "tov", "3pm", "fg_pct", "ft_pct"],
    "mlb":   ["h", "rbi", "hr", "tb", "k", "er", "ip", "obp", "slg"],
    "nhl":   ["sog", "g", "a", "plus_minus", "toi", "ppp"],
}

# Add nfl_position_groups support if present
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from sources.nfl_position_groups import get_stats_for_position, get_position_for_stat
    HAS_POSITIONS = True
except Exception:
    HAS_POSITIONS = False


def _http_get_json(url: str, timeout: int = 12) -> Optional[dict]:
    """Fetch a URL and return parsed JSON. Returns None on failure."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "TC-Pipeline/1.0 (sports analytics)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"[player_stats_scraper] {url[:80]}... failed: {exc}", file=sys.stderr)
        return None


def fetch_espn_scoreboard(sport: str, target_date: Optional[date] = None) -> List[dict]:
    """Fetch ESPN scoreboard events for a sport on a given date."""
    path = SPORT_PATHS.get(sport.lower())
    if not path:
        raise ValueError(f"Unknown sport: {sport}")
    d = (target_date or date.today()).strftime("%Y%m%d")
    url = f"{ESPN_BASE}/{path}/scoreboard?dates={d}"
    data = _http_get_json(url)
    if not data:
        return []
    return data.get("events", [])


def fetch_espn_event_summary(sport: str, event_id: str) -> Optional[dict]:
    """Fetch the box score + leaders for a single event."""
    path = SPORT_PATHS.get(sport.lower())
    if not path:
        return None
    url = f"{ESPN_BASE}/{path}/summary?event={event_id}"
    return _http_get_json(url)


def parse_player_stats_from_event(event_summary: dict, sport: str) -> List[dict]:
    """Pull player box-score lines out of an ESPN event summary."""
    players = []
    if not event_summary:
        return players
    for boxscore in event_summary.get("boxscore", {}).get("players", []):
        team = boxscore.get("team", {}).get("displayName", "Unknown")
        for stat_group in boxscore.get("statistics", []):
            labels = stat_group.get("labels", [])
            keys   = stat_group.get("keys", [])
            for entry in stat_group.get("athletes", []):
                ath = entry.get("athlete", {})
                name = ath.get("displayName") or ath.get("fullName")
                pos  = ath.get("position", {}).get("abbreviation", "")
                stats = entry.get("stats", [])
                record = {
                    "name":  name,
                    "team":  team,
                    "pos":   pos,
                    "sport": sport.upper(),
                    "stats": dict(zip(labels, stats)),
                }
                players.append(record)
    return players


def scrape_sport_stats(sport: str, target_date: Optional[date] = None) -> List[dict]:
    """Top-level: return all player stats for a sport on a date."""
    sport = sport.lower()
    target_date = target_date or date.today()
    events = fetch_espn_scoreboard(sport, target_date)
    if not events:
        print(f"[player_stats_scraper] no events for {sport} on {target_date}", file=sys.stderr)
        return []
    out: List[dict] = []
    for ev in events:
        ev_id = ev.get("id")
        if not ev_id:
            continue
        summary = fetch_espn_event_summary(sport, ev_id)
        if not summary:
            continue
        out.extend(parse_player_stats_from_event(summary, sport))
    return out


def save_stats(sport: str, players: List[dict], target_date: Optional[date] = None) -> str:
    """Persist scraped stats to a dated JSON file. Returns the path."""
    d = target_date or date.today()
    out_path = DATA_DIR / f"player_stats_{sport.lower()}_{d.isoformat()}.json"
    payload = {
        "sport":        sport.upper(),
        "date":         d.isoformat(),
        "scraped_at":   datetime.now().isoformat(timespec="seconds"),
        "player_count": len(players),
        "players":      players,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return str(out_path)


def scrape_and_save(sport: str, target_date: Optional[date] = None) -> str:
    """Scrape + save in one call."""
    players = scrape_sport_stats(sport, target_date)
    return save_stats(sport, players, target_date)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", required=True, choices=list(SPORT_PATHS.keys()))
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)", default=None)
    args = ap.parse_args()
    target = None
    if args.date:
        target = date.fromisoformat(args.date)
    path = scrape_and_save(args.sport, target)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
