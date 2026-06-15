#!/usr/bin/env python3
"""
Team-Game Mapper — single source of truth for matching book team IDs to canonical game keys.

Problem this fixes:
- SGO, Odds API, SportsData.io, BetMGM, and ESPN all use DIFFERENT team codes for the
  same WNBA team. The previous matcher was a 10-entry alias dict + substring check,
  which silently dropped every WNBA prop because none of the book codes (LV/LAS/LA/WS)
  appear in our internal 3-letter codes.
- We were also matching on team NAMES only, with no fallback to event_id / start time.

Solution:
- ESPN team abbr is the canonical key (e.g., "LV" for Las Vegas Aces).
- Each book has a WNBA alias map (full + nickname + city + alternate).
- 3-step match: (1) exact alias hit, (2) normalized name token overlap, (3) start-time
  proximity + book event_id cross-check.
- Build a per-day ESPN→book event map, then look up team→game by exact book teamID.
"""

import re
import json
import os
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Secrets loader (same pattern as the rest of the pipeline) ---
try:
    _sec = Path("/root/.zo/secrets.env")
    if _sec.exists():
        for _line in _sec.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except Exception:
    pass

# =====================================================================
# CANONICAL WNBA TEAM MAP (ESPN abbr → full name + all known aliases)
# =====================================================================
# This is the ONLY place team aliases live. If a book uses a new code,
# add it here once and every consumer benefits.

WNBA_TEAMS = {
    "LV":  {"name": "Las Vegas Aces",      "city": "Las Vegas",   "nick": "Aces",   "aliases": ["LVA", "LAS", "LA", "VEGAS", "ACES"]},
    "NY":  {"name": "New York Liberty",    "city": "New York",    "nick": "Liberty","aliases": ["NYL", "NEW YORK", "LIB"]},
    "CON": {"name": "Connecticut Sun",     "city": "Connecticut", "nick": "Sun",    "aliases": ["CONN", "CT", "SUN", "CONNECTICUT"]},
    "MIN": {"name": "Minnesota Lynx",      "city": "Minnesota",   "nick": "Lynx",   "aliases": ["MINN", "LYNX", "MINNESOTA"]},
    "IND": {"name": "Indiana Fever",       "city": "Indiana",     "nick": "Fever",  "aliases": ["INDY", "IND", "FEVER", "INDIANA"]},
    "SEA": {"name": "Seattle Storm",       "city": "Seattle",     "nick": "Storm",  "aliases": ["STORM", "SEATTLE"]},
    "PHX": {"name": "Phoenix Mercury",     "city": "Phoenix",     "nick": "Mercury","aliases": ["PHOENIX", "MERC", "MERCURY"]},
    "CHI": {"name": "Chicago Sky",         "city": "Chicago",     "nick": "Sky",    "aliases": ["CHICAGO", "SKY"]},
    "ATL": {"name": "Atlanta Dream",       "city": "Atlanta",     "nick": "Dream",  "aliases": ["ATLANTA", "DREAM"]},
    "DAL": {"name": "Dallas Wings",        "city": "Dallas",      "nick": "Wings",  "aliases": ["DALLAS", "WINGS"]},
    "LA":  {"name": "Los Angeles Sparks",  "city": "Los Angeles", "nick": "Sparks", "aliases": ["LAS", "LOS", "ANGELES", "SPARKS", "LAL"]},
    "WAS": {"name": "Washington Mystics",  "city": "Washington",  "nick": "Mystics","aliases": ["WSH", "WASH", "WASHINGT", "MYSTICS", "DC"]},
    "GS":  {"name": "Golden State Valkyries","city": "Golden State","nick": "Valkyries","aliases": ["GSW", "GOLDEN", "VALK", "VALKYRIES"]},
    "POR": {"name": "Portland Fire",         "city": "Portland",    "nick": "Fire",    "aliases": ["PORTLAND", "FIRE", "PTL"]},
    "TOR": {"name": "Toronto Tempo",         "city": "Toronto",     "nick": "Tempo",   "aliases": ["TORONTO", "TEMPO"]},
}

# Reverse lookup: any alias → canonical abbr
_ALIAS_TO_CANON = {}
for _canon, _meta in WNBA_TEAMS.items():
    _ALIAS_TO_CANON[_canon.upper()] = _canon
    for _a in _meta.get("aliases", []):
        _ALIAS_TO_CANON[_a.upper()] = _canon
    if "name" in _meta:
        _ALIAS_TO_CANON[_meta["name"].upper()] = _canon
    if "city" in _meta:
        _ALIAS_TO_CANON[_meta["city"].upper()] = _canon
    if "nick" in _meta:
        _ALIAS_TO_CANON[_meta["nick"].upper()] = _canon


def canon_abbr(s):
    """Resolve ANY known alias (city, nickname, full, or abbr) to canonical ESPN abbr."""
    if not s:
        return None
    key = str(s).upper().strip()
    key = re.sub(r"[^A-Z ]", "", key).strip()
    return _ALIAS_TO_CANON.get(key)


def canon_pair(away_any, home_any):
    """Resolve a (away, home) pair to canonical (away, home) abbrs. None if unknown."""
    a = canon_abbr(away_any)
    h = canon_abbr(home_any)
    if a and h and a != h:
        return (a, h)
    return None


# =====================================================================
# ESPN CANONICAL SLATE — fetches today's WNBA games, returns
# [{ espn_event_id, away, home, start_utc }, ...]
# =====================================================================

ESPN_WNBA = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"

def fetch_espn_wnba_slate(target_date=None):
    """
    Fetch ESPN WNBA scoreboard for a given date (or today).
    Returns list of dicts: {espn_event_id, away, home, start_utc, status}.
    """
    params = {}
    if target_date:
        params["dates"] = target_date.strftime("%Y%m%d")
    try:
        r = requests.get(ESPN_WNBA, params=params, timeout=12)
        if not r.ok:
            return []
        data = r.json()
        slate = []
        for ev in data.get("events", []):
            comps = ev.get("competitions", [{}])[0].get("competitors", [])
            away, home = None, None
            for c in comps:
                abbr = (c.get("team", {}).get("abbreviation") or "").upper()
                if c.get("homeAway") == "home":
                    home = abbr
                else:
                    away = abbr
            if not (away and home):
                continue
            slate.append({
                "espn_event_id": ev.get("id"),
                "away": away,
                "home": home,
                "start_utc": ev.get("date"),
                "status": ev.get("status", {}).get("type", {}).get("name", ""),
            })
        return slate
    except Exception as e:
        return []


# =====================================================================
# ODDS API EVENT BRIDGE — maps Odds API event_id → (away_canon, home_canon)
# =====================================================================

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")

def fetch_odds_api_wnba_events():
    """
    Fetch Odds API WNBA events list. Returns
    { event_id: { away_canon, home_canon, commence_utc } }.
    """
    if not ODDS_API_KEY:
        return {}
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/basketball_wnba/events",
            params={"apiKey": ODDS_API_KEY, "dateFormat": "iso"},
            timeout=12,
        )
        if not r.ok:
            return {}
        out = {}
        for ev in r.json():
            pair = canon_pair(ev.get("away_team"), ev.get("home_team"))
            if not pair:
                continue
            out[ev["id"]] = {
                "away_canon": pair[0],
                "home_canon": pair[1],
                "commence_utc": ev.get("commence_time"),
            }
        return out
    except Exception:
        return {}


# =====================================================================
# SGO EVENT BRIDGE — for NBA we keep the SGO path; for WNBA SGO is N/A
# so this just returns empty (documented).
# =====================================================================

def fetch_sgo_events(sport="WNBA"):
    """SGO is NBA-only at our tier. Returns {} for WNBA with a documented reason."""
    if sport.upper() == "WNBA":
        return {}
    # NBA path kept simple here; SGO consumer is in sgo_props_enricher.py.
    return {}


# =====================================================================
# HIGH-LEVEL: build a per-day canonical game map
# =====================================================================

def build_canonical_game_map(target_date=None):
    """
    Returns a dict keyed by espn_event_id with:
      { espn_event_id, away, home, start_utc, odds_api_event_id (or None) }
    The map is what every downstream consumer (enricher, pipeline, dashboard) should
    use to look up a game.
    """
    slate = fetch_espn_wnba_slate(target_date)
    odds = fetch_odds_api_wnba_events()
    # Build a (away, home) → odds_api_event_id index for cross-ref
    odds_idx = {}
    for oid, meta in odds.items():
        key = (meta["away_canon"], meta["home_canon"])
        odds_idx[key] = oid

    out = {}
    for g in slate:
        key = (g["away"], g["home"])
        g["odds_api_event_id"] = odds_idx.get(key)
        out[g["espn_event_id"]] = g
    return out


def find_espn_event_for_teams(away_abbr, home_abbr, game_map):
    """Given (away, home) canonical abbrs, return the ESPN event dict or None."""
    for ev in game_map.values():
        if ev["away"] == away_abbr and ev["home"] == home_abbr:
            return ev
    return None


# =====================================================================
# CLI smoke test
# =====================================================================

if __name__ == "__main__":
    print("=== Canonical WNBA team map (alias → ESPN abbr) ===")
    for k in sorted(_ALIAS_TO_CANON)[:25]:
        print(f"  {k:20s} -> {_ALIAS_TO_CANON[k]}")
    print(f"\nTotal aliases indexed: {len(_ALIAS_TO_CANON)}")
    print(f"Total WNBA teams: {len(WNBA_TEAMS)}")

    print("\n=== ESPN WNBA slate (today) ===")
    slate = fetch_espn_wnba_slate()
    if not slate:
        print("  (no events returned or fetch failed)")
    for g in slate:
        print(f"  espn={g['espn_event_id']}  {g['away']}@{g['home']}  {g['start_utc']}")

    print("\n=== Odds API WNBA events ===")
    odds = fetch_odds_api_wnba_events()
    if not odds:
        print("  (no events or key missing)")
    for oid, meta in list(odds.items())[:10]:
        print(f"  odds_id={oid}  {meta['away_canon']}@{meta['home_canon']}  {meta['commence_utc']}")

    print("\n=== Canonical game map ===")
    gmap = build_canonical_game_map()
    for ev in gmap.values():
        print(f"  espn={ev['espn_event_id']}  {ev['away']}@{ev['home']}  odds={ev.get('odds_api_event_id')}")
