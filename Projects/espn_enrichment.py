#!/usr/bin/env python3
"""ESPN line enrichment for daily_picks.py
Uses the ESPN v2 public API (free, no auth) to enrich projections with
real game-level market odds (spread, over/under, moneyline).

Truth: ESPN v2 public API provides game-level odds only through the
scoreboard and summary endpoints. Individual player milestone props
(PTS O/U, REB O/U, etc.) are NOT available through the public ESPN API —
those require sportsbook scraping or paid API access.

This module enriches projections with real game context, replacing
SELF_EDGE zero-lines with actual DraftKings spread/O/U where applicable.
"""

from __future__ import annotations

import json
import urllib.request
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CACHE_DIR = Path("/home/workspace/Daily_Log/cache/espn_odds")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports"

SPORT_PATHS = {
    "wnba": ("basketball", "wnba"),
    "mlb": ("baseball", "mlb"),
    "wc": ("soccer", "fifa.world"),
    "nba": ("basketball", "nba"),
}

PLAYER_NAME_NORMALIZE = str.maketrans("", "", ".-' JrSrIIIiiIV")


def normalize(name: str) -> str:
    """Strip punctuation and suffixes for fuzzy matching."""
    return name.lower().translate(PLAYER_NAME_NORMALIZE).replace(" ", "").strip()


def _espn_request(url: str, timeout: int = 8) -> Optional[Dict]:
    """GET JSON from ESPN API with error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _cache_path(sport: str, date_str: str) -> Path:
    sport_path, league = SPORT_PATHS.get(sport.lower(), (sport.lower(), sport.lower()))
    safe = f"{sport_path}_{league}_{date_str}"
    return CACHE_DIR / f"{safe}.json"


def _read_cache(path: Path, ttl_sec: int = 900) -> Optional[Dict]:
    if not path.exists():
        return None
    age = datetime.now().timestamp() - path.stat().st_mtime
    if age > ttl_sec:
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def fetch_espn_game_odds(sport: str, date_str: str = "") -> List[Dict]:
    """Fetch live game-level odds from ESPN public API for a sport/date.
    
    Returns list of {event_id, name, home_team, away_team, spread, over_under,
                      home_ml, away_ml, provider}
    """
    if not date_str:
        date_str = date.today().isoformat()

    sport_path, league = SPORT_PATHS.get(sport.lower(), (sport.lower(), sport.lower()))
    cache_file = _cache_path(sport, date_str)
    cached = _read_cache(cache_file)
    if cached is not None:
        return cached.get("events", [])

    espn_date = date_str.replace("-", "")
    url = f"{ESPN_SITE}/{sport_path}/{league}/scoreboard?dates={espn_date}"
    data = _espn_request(url)
    if not data:
        return []

    events_out = []
    for ev in data.get("events", []):
        comps = ev.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        competitors = comp.get("competitors", [])
        home_team = None
        away_team = None
        for c in competitors:
            team_data = c.get("team", {})
            abbrev = team_data.get("abbreviation", "")
            if c.get("homeAway") == "home":
                home_team = abbrev
            else:
                away_team = abbrev

        odds_list = comp.get("odds", [])
        ev_data = {
            "event_id": ev.get("id"),
            "name": ev.get("name"),
            "status": ev.get("status", {}).get("type", {}).get("name", ""),
            "home_team": home_team,
            "away_team": away_team,
            "spread": None,
            "over_under": None,
            "home_ml": None,
            "away_ml": None,
            "provider": None,
        }
        if odds_list:
            o = odds_list[0]
            ev_data["spread"] = o.get("spread")
            ev_data["over_under"] = o.get("overUnder")
            ev_data["provider"] = o.get("provider", {}).get("name")
            if o.get("homeTeamOdds"):
                ev_data["home_ml"] = o["homeTeamOdds"].get("moneyLine")
            if o.get("awayTeamOdds"):
                ev_data["away_ml"] = o["awayTeamOdds"].get("moneyLine")

        events_out.append(ev_data)

    cache_file.write_text(json.dumps({"events": events_out, "fetched_at": datetime.now(ET).isoformat()}))
    return events_out


def enrich_lines_via_espn(sport: str, projections: List[Dict]) -> List[Dict]:
    """Enrich TC projections with real ESPN game-level odds.
    
    For each projection, attaches game context (spread, O/U, ML) from ESPN.
    This gives the pipeline real market data for game-level analysis and
    replaces SELF_EDGE at the game-context level.
    
    Individual player prop lines (PTS O/U, REB O/U) require a separate
    source — ESPN v2 public API does not expose those.
    
    Returns modified projections list with 'espn_game_odds' key added
    and 'line_source' updated to 'ESPN' for game-context lines.
    """
    today = date.today().isoformat()
    game_odds = fetch_espn_game_odds(sport, today)

    if not game_odds:
        return projections

    enriched_count = 0

    for p in projections:
        matchup = p.get("matchup", "")
        team = p.get("team", "").upper()

        matched_event = None
        for ev in game_odds:
            ev_home = (ev.get("home_team") or "").upper()
            ev_away = (ev.get("away_team") or "").upper()
            ev_name = (ev.get("name") or "")

            if team and (team == ev_home or team == ev_away):
                matched_event = ev
                break
            if matchup and (ev_home in matchup or ev_away in matchup or matchup.replace("@", " @ ") in ev_name):
                matched_event = ev
                break

        if matched_event:
            p["game_odds"] = {
                "spread": matched_event.get("spread"),
                "over_under": matched_event.get("over_under"),
                "home_ml": matched_event.get("home_ml"),
                "away_ml": matched_event.get("away_ml"),
                "provider": matched_event.get("provider", "DraftKings"),
                "home_team": matched_event.get("home_team"),
                "away_team": matched_event.get("away_team"),
            }
            p["line_source"] = p.get("line_source", "SELF_EDGE") + "+ESPN_GAME"
            enriched_count += 1

    return projections


def get_espn_game_context(sport: str) -> List[Dict]:
    """Quick lookup: what games are live today with ESPN odds?"""
    return fetch_espn_game_odds(sport)


if __name__ == "__main__":
    import sys
    s = sys.argv[1] if len(sys.argv) > 1 else "wnba"
    odds = fetch_espn_game_odds(s)
    print(f"\nESPN Game Odds for {s.upper()} — {date.today().isoformat()}")
    print(f"Games with odds: {len(odds)}")
    for ev in odds:
        print(f"  {ev['name']} | Spread: {ev.get('spread')} | O/U: {ev.get('over_under')} | "
              f"Home ML: {ev.get('home_ml')} | Away ML: {ev.get('away_ml')} | Provider: {ev.get('provider')}")
