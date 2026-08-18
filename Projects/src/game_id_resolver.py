#!/usr/bin/env python3
"""
game_id_resolver.py - Unified Game ID resolver for all sports.
Uses team IDs from statsapi for MLB, ESPN API for WNBA, nfl_data_py for NFL.
Caches mappings to avoid repeated API calls.
"""

import sqlite3
import requests
import statsapi
import nfl_data_py as nfl
from pathlib import Path
from datetime import datetime
from src.name_resolver import resolve_team
from src.time_utils import today_et

PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DB = PROJECT_ROOT / "data" / "cache" / "game_ids.db"
CACHE_DB.parent.mkdir(parents=True, exist_ok=True)

_MLB_ID_TO_ABBREV = {}
_MLB_NAME_TO_ABBREV = {}
_MLB_LOADED = False

def _load_mlb_teams():
    global _MLB_ID_TO_ABBREV, _MLB_NAME_TO_ABBREV, _MLB_LOADED
    if _MLB_LOADED:
        return
    try:
        teams = statsapi.get('teams', {'sportIds': 1})['teams']
        for t in teams:
            _MLB_ID_TO_ABBREV[t['id']] = t['abbreviation']
            _MLB_NAME_TO_ABBREV[t['name']] = t['abbreviation']
            _MLB_NAME_TO_ABBREV[t['teamName']] = t['abbreviation']
        _MLB_LOADED = True
    except Exception as e:
        print(f"[game_id_resolver] WARN: Could not load MLB teams: {e}")

def init_cache():
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_id_cache (
            league TEXT,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            game_id TEXT,
            PRIMARY KEY (league, date, home_team, away_team)
        )
    """)
    conn.commit()
    conn.close()

def _get_cached(league: str, date: str, home_team: str, away_team: str) -> str:
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT game_id FROM game_id_cache
        WHERE league = ? AND date = ? AND home_team = ? AND away_team = ?
    """, (league, date, home_team, away_team))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def _set_cached(league: str, date: str, home_team: str, away_team: str, game_id: str):
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO game_id_cache (league, date, home_team, away_team, game_id)
        VALUES (?, ?, ?, ?, ?)
    """, (league, date, home_team, away_team, game_id))
    conn.commit()
    conn.close()

def resolve_game_id(league: str, date: str, home_team: str, away_team: str) -> str:
    """
    Resolve game_id for a given league, date, and teams.
    Returns game_id (string) or None if not found.
    Auto-swaps home/away if first attempt misses.
    """
    home = resolve_team(home_team, league) or home_team
    away = resolve_team(away_team, league) or away_team

    # Check cache first
    cached = _get_cached(league, date, home, away)
    if cached:
        return cached

    # Try swapped cache
    cached_swapped = _get_cached(league, date, away, home)
    if cached_swapped:
        return cached_swapped

    # Resolve based on league (with auto-swap fallback)
    game_id = None
    league_lower = league.lower()
    if league_lower == 'mlb':
        game_id = _resolve_mlb(date, home, away)
        if not game_id:
            game_id = _resolve_mlb(date, away, home)
    elif league_lower == 'wnba':
        game_id = _resolve_wnba(date, home, away)
        if not game_id:
            game_id = _resolve_wnba(date, away, home)
    elif league_lower == 'nfl':
        game_id = _resolve_nfl(date, home, away)
        if not game_id:
            game_id = _resolve_nfl(date, away, home)

    if game_id:
        _set_cached(league, date, home, away, game_id)
    return game_id

def _resolve_mlb(date: str, home_abbrev: str, away_abbrev: str) -> str:
    """Use statsapi to get game_id. Matches by team abbreviation via ID lookup."""
    _load_mlb_teams()
    try:
        schedule = statsapi.schedule(date=date)
    except Exception as e:
        print(f"[game_id_resolver] MLB schedule error: {e}")
        return None

    for game in schedule:
        home_game_id = game.get('home_id')
        away_game_id = game.get('away_id')
        home_game_abbrev = _MLB_ID_TO_ABBREV.get(home_game_id, '')
        away_game_abbrev = _MLB_ID_TO_ABBREV.get(away_game_id, '')
        # Match either exact abbreviation OR full name via _MLB_NAME_TO_ABBREV
        if home_game_abbrev == home_abbrev and away_game_abbrev == away_abbrev:
            return str(game.get('game_id'))
        # Also try matching full names (fallback for when resolve_team returns full name)
        home_game_name = game.get('home_name', '')
        away_game_name = game.get('away_name', '')
        if home_game_name == home_abbrev and away_game_name == away_abbrev:
            return str(game.get('game_id'))
    return None

def _resolve_wnba(date: str, home_abbrev: str, away_abbrev: str) -> str:
    """Use ESPN scoreboard to get game_id. Matches by team abbreviation."""
    try:
        date_espn = datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')
    except ValueError:
        return None
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={date_espn}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for event in data.get('events', []):
                comp = event.get('competitions', [{}])[0]
                competitors = comp.get('competitors', [])
                if len(competitors) < 2:
                    continue
                home_espn = None
                away_espn = None
                for c in competitors:
                    abbr = c.get('team', {}).get('abbreviation', '')
                    if c.get('homeAway') == 'home':
                        home_espn = abbr
                    else:
                        away_espn = abbr
                if home_espn == home_abbrev and away_espn == away_abbrev:
                    return str(event.get('id'))
    except Exception as e:
        print(f"[game_id_resolver] WNBA ESPN error: {e}")
    return None

def _resolve_nfl(date: str, home_abbrev: str, away_abbrev: str) -> str:
    """Use nfl_data_py schedule + ESPN fallback to get game_id."""
    try:
        year = int(date[:4])
        schedule = nfl.import_schedules([year])
        if not schedule.empty:
            matched = schedule[
                (schedule['gameday'] == date) &
                (schedule['home_team'] == home_abbrev) &
                (schedule['away_team'] == away_abbrev)
            ]
            if not matched.empty:
                return str(matched.iloc[0]['game_id'])
    except Exception as e:
        print(f"[game_id_resolver] NFL nfl_data_py error: {e}")
    try:
        date_espn = date.replace('-', '')
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date_espn}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for event in data.get('events', []):
                comp = event.get('competitions', [{}])[0]
                competitors = comp.get('competitors', [])
                if len(competitors) < 2:
                    continue
                espn_home = None
                espn_away = None
                for c in competitors:
                    if c.get('homeAway') == 'home':
                        espn_home = c.get('team', {}).get('abbreviation')
                    else:
                        espn_away = c.get('team', {}).get('abbreviation')
                if espn_home == home_abbrev and espn_away == away_abbrev:
                    return event.get('id')
    except Exception as e:
        print(f"[game_id_resolver] NFL ESPN error: {e}")
    return None

init_cache()
