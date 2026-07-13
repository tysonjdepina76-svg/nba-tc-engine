# TC — Triple Conservative — Trademark June 2026 — tysonjdepina76@gmail.com — All rights reserved.
#!/usr/bin/env python3
"""
Multi-Source Consensus Line Engine
====================================
Fetches player prop lines from ALL available books, builds a consensus
(average of the middle 60% of lines, clipping outliers), and provides
per-player, per-stat consensus values with individual book breakdowns.

Sport coverage: NBA, WNBA, NHL, MLB, Soccer (MLS/EPL/LaLiga/SerieA/Ligue1/Bundesliga)
Book priority (best lines first): DK > FD > BetMGM > Caesars > Fanatics > Bovada
Secondary feeds: PrizePicks, Underdog — stubbed for future API access

When DK is empty (common in WNBA), consensus falls back to FD → BetMGM → etc.

Usage:
  from consensus_engine import get_consensus_lines, merge_into_picks
  consensus = get_consensus_lines("WNBA", "event_id_here")
  # consensus.players["Arike Ogunbowale"]["points"] → {
  #   "consensus": 21.5, "dk": 21.5, "fd": 20.5, "best_book": "draftkings",
  #   "all_lines": [21.5, 20.5, 22.0], "source_count": 3
  # }
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Canonical team mapping (WNBA team names differ across books: LV vs LVA vs LAS vs LA, etc.)
try:
    from team_game_mapper import canon_abbr as canonicalize_team
except Exception:
    def canonicalize_team(s):
        return None

WNBA_TEAM_MAP = {
    "ATL": "atlanta dream", "CHI": "chicago sky", "CON": "connecticut sun",
    "DAL": "dallas wings", "GS": "golden state valkyries", "IND": "indiana fever",
    "LV": "las vegas aces", "LA": "los angeles sparks", "MIN": "minnesota lynx",
    "NY": "new york liberty", "PHX": "phoenix mercury", "POR": "portland fire",
    "SEA": "seattle storm", "TOR": "toronto tempo", "WSH": "washington mystics",
}

MLB_TEAM_MAP = {
    "ARI": "arizona diamondbacks",
    "ATL": "atlanta braves",
    "BAL": "baltimore orioles",
    "BOS": "boston red sox",
    "CHC": "chicago cubs",
    "CWS": "chicago white sox",
    "CLE": "cleveland guardians",
    "COL": "colorado rockies",
    "CIN": "cincinnati reds",
    "DET": "detroit tigers",
    "KC": "kansas city royals",
    "KCR": "kansas city royals",
    "LAA": "los angeles angels",
    "LAD": "los angeles dodgers",
    "MIA": "miami marlins",
    "MIL": "milwaukee brewers",
    "MIN": "minnesota twins",
    "NYM": "new york mets",
    "NYY": "new york yankees",
    "OAK": "oakland athletics",
    "PHI": "philadelphia phillies",
    "PIT": "pittsburgh pirates",
    "SD": "san diego padres",
    "SF": "san francisco giants",
    "SEA": "seattle mariners",
    "STL": "st. louis cardinals",
    "TEX": "dallas rangers",
    "TOR": "toronto blue jays",
    "TBD": "tampa bay rays",
    "TB": "tampa bay rays",
    "TBR": "tampa bay rays",
    "CHW": "chicago white sox",
    "WSH": "washington nationals",
}

# ── API Keys ──────────────────────────────────────────────

ODDS_KEY = os.environ.get("ODDS_API_KEY", "") 
SGO_KEY = os.environ.get("SGO_API_KEY", "") or os.environ.get("SPORTSGAMEODDS_API_KEY", "")
SECRETS_FILE = Path("/root/.zo/secrets.env")
if SECRETS_FILE.exists():
    for line in SECRETS_FILE.read_text().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k == "ODDS_API_KEY" and not ODDS_KEY:
            ODDS_KEY = v
            os.environ["ODDS_API_KEY"] = v
        elif k in ("SGO_API_KEY", "SPORTSGAMEODDS_API_KEY") and not SGO_KEY:
            SGO_KEY = v
            os.environ[k] = v

# ── Odds API Sport Mapping ────────────────────────────────
ODDS_SPORT_MAP = {
    "NBA": "basketball_nba",
    "WNBA": "basketball_wnba",
    "NHL": "icehockey_nhl",
    "MLB": "baseball_mlb",
    "MLS": "soccer_usa_mls",
    "EPL": "soccer_epl",
    "LALIGA": "soccer_spain_la_liga",
    "SERIEA": "soccer_italy_serie_a",
    "LIGUE1": "soccer_france_ligue_one",
    "BUNDESLIGA": "soccer_germany_bundesliga",
    "UCL": "soccer_uefa_champs_league",
    "UEL": "soccer_uefa_europa_league",
    "WORLD CUP": "soccer_fifa_world_cup",
    "SOCCER": "soccer_fifa_world_cup",
    "NFL": "americanfootball_nfl",
    "NCAAF": "americanfootball_ncaaf",
    "NCAAB": "basketball_ncaab",
}

# ── Book Priority ─────────────────────────────────────────
BOOK_PRIORITY = [
    "draftkings", "fanduel", "betmgm", "caesars",
    "fanatics", "bovada", "betonlineag", "betrivers",
    "lowvig", "pointsbet", "williamhill_us", "betus",
    "mybookieag", "superbook",
]

# ── Player Prop Market Mapping ────────────────────────────
PLAYER_MARKETS = [
    "player_points", "player_rebounds", "player_assists",
    "player_threes", "player_steals", "player_blocks",
]

ODDS_STAT_REVERSE = {
    "player_points": "points",
    "player_rebounds": "rebounds",
    "player_assists": "assists",
    "player_threes": "threes",
    "player_steals": "steals",
    "player_blocks": "blocks",
    "player_goals": "goals",
    "player_shots_on_target": "shots_on_target",
}

# ── PrizePicks / Underdog Stubs ───────────────────────────
# PrizePicks has a semi-public projections API at https://api.prizepicks.com/projections
# Underdog is app-only, no public API
# These are stubbed for future integration — see STUBS.md

PP_AVAILABLE = False  # Set True when PrizePicks API key is configured
UD_AVAILABLE = False  # Set True when Underdog API access is obtained

# ── Convenience sport map for external use ─────────────────
CONSENSUS_SPORT_MAP = ODDS_SPORT_MAP  # re-export

ODDS_BASE = "https://api.theoddsapi.com"

# ── SGO fallback helpers (for MLB, World Cup when Odds API is dead) ──
import time as _time

# In-memory cache to avoid 429 hammering on WNBA SGO rate-limited endpoints
_SGO_EVENTS_CACHE: dict[str, tuple[float, list]] = {}
_SGO_CACHE_TTL_SEC = 300  # 5 min cache per league
_SGO_RETRY_BACKOFF = (1.0, 2.5, 5.0)  # 3 retries on 429

def _sgo_fetch_events(league: str) -> list:
    """Fetch live/upcoming events from SGO with cache + 429 retry fallback."""
    if not SGO_KEY:
        return []
    # Cache hit?
    cached = _SGO_EVENTS_CACHE.get(league)
    if cached and (_time.time() - cached[0]) < _SGO_CACHE_TTL_SEC:
        return cached[1]
    last_err: Exception | None = None
    for attempt, delay in enumerate((0.0,) + _SGO_RETRY_BACKOFF):
        if delay:
            _time.sleep(delay)
        try:
            r = requests.get(
                "https://api.sportsgameodds.com/v2/events",
                params={"leagueID": league, "oddsAvailable": "true", "limit": "100"},
                headers={"x-api-key": SGO_KEY}, timeout=30)
            if r.status_code == 429:
                last_err = Exception(f"429 rate-limited (attempt {attempt+1})")
                continue
            r.raise_for_status()
            data = r.json().get("data", [])
            _SGO_EVENTS_CACHE[league] = (_time.time(), data)
            return data
        except Exception as e:
            last_err = e
            print(f"  [SGO] {league} events err: {e}")
    # All retries exhausted — return stale cache if we have one
    if cached:
        print(f"  [SGO] {league} returning stale cache after retries")
        return cached[1]
    print(f"  [SGO] {league} events failed: {last_err}")
    return []

def _sgo_normalize_to_bookmakers(event: dict, league: str) -> list:
    """Convert SGO event.odds into the bookmakers list shape _build_consensus_from_bookmakers expects.
    Only DK is taken — multi-book SGO parsing is complex and DK is the primary book.
    """
    odds = event.get("odds", {})
    if not odds:
        return []
    # Map SGO stat keys → ODDS_STAT_REVERSE keys
    sgo_stat_map = {
        "points": "points",
        "rebounds": "rebounds",
        "assists": "assists",
        "threes": "threes",
        "steals": "steals",
        "blocks": "blocks",
        "goals": "goals",
        "shots": "shots",
        "shots_on_target": "shots_on_target",
        "hits": "hits",
        "home_runs": "home_runs",
        "rbis": "rbis",
        "stolen_bases": "stolen_bases",
        "runs": "runs",
    }
    # Collect: market_key → list of (player_name, over_line)
    markets_out = {}
    for k, v in odds.items():
        dk = v.get("byBookmaker", {}).get("draftkings", {})
        if not dk or not dk.get("available"):
            continue
        # Player prop format: "points-PLAYERID-game-ou-over"
        m = re.match(r"^([a-z_]+)-([A-Z0-9_]+)-game-ou-over$", k)
        if not m:
            continue
        stat_raw, pid = m.group(1), m.group(2)
        stat = sgo_stat_map.get(stat_raw)
        if not stat:
            continue
        line = dk.get("overUnder")
        if line is None:
            continue
        try:
            line = float(line)
        except (TypeError, ValueError):
            continue
        # Convert player id → display name from teams
        player_name = pid.replace("_", " ").title()
        # Map back to a common id for matching
        markets_out.setdefault(stat, []).append({
            "name": player_name,
            "line": line,
            "over_odds": dk.get("odds"),
        })
    # Build bookmakers structure
    if not markets_out:
        return []
    bookmakers = [{
        "key": "draftkings",
        "markets": [
            {"key": f"player_{stat}", "outcomes": [
                {"name": "Over", "description": p["name"], "point": p["line"], "price": p["over_odds"]}
                for p in outcomes
            ]}
            for stat, outcomes in markets_out.items()
        ]
    }]
    return bookmakers

def _sgo_consensus_for_matchup(sport: str, away: str, home: str) -> dict:
    """Build consensus from SGO only (used when Odds API is dead)."""
    league_map = {"MLB": "MLB", "WNBA": "basketball_wnba", "WORLD CUP": "soccer_fifa_world_cup"}
    league = league_map.get(sport.upper())
    if not league:
        return {"players": {}, "available_books": [], "source": "none", "error": f"No SGO league for {sport}"}

    events = _sgo_fetch_events(league)
    if not events:
        return {"players": {}, "available_books": [], "source": "none", "error": "SGO events empty"}

    # Match by team names
    team_map = WNBA_TEAM_MAP if sport.upper() == "WNBA" else (MLB_TEAM_MAP if sport.upper() == "MLB" else {})
    away_full = team_map.get(away.upper(), "").lower()
    home_full = team_map.get(home.upper(), "").lower()

    matched_ev = None
    for ev in events:
        # SGO has teams array with names.short
        teams = ev.get("teams", {})
        home_n = teams.get("home", {}).get("names", {}).get("short", "").lower()
        away_n = teams.get("away", {}).get("names", {}).get("short", "").lower()
        if away.upper().lower() in away_n and home.upper().lower() in home_n:
            matched_ev = ev; break
        if away_full and home_full and away_full in teams.get("away", {}).get("names", {}).get("long", "").lower() and \
           home_full in teams.get("home", {}).get("names", {}).get("long", "").lower():
            matched_ev = ev; break

    if not matched_ev:
        return {"players": {}, "available_books": [], "source": "none", "error": f"No SGO event for {away}@{home}"}

    bookmakers = _sgo_normalize_to_bookmakers(matched_ev, league)
    if not bookmakers:
        return {"players": {}, "available_books": [], "source": "none", "error": "No DK lines in SGO"}
    result = _build_consensus_from_bookmakers(bookmakers)
    result["source"] = "sportsgameodds.com (fallback)"
    return result

# ── Response normalization: new api.theoddsapi.com format → old bookmakers format ──
def _normalize_odds_response(raw_data: dict) -> dict:
    """Convert new API response format into old bookmakers-style format.
    New: {data: [{event_id, books: [{book, market, outcomes}]}]}
    Old: {bookmakers: [{key, markets: [{key, outcomes}]}]}
    """
    # If already in old format (bookmakers key), return as-is
    if "bookmakers" in raw_data:
        return raw_data
    
    data = raw_data.get("data", [])
    if not data:
        return {"bookmakers": []}
    
    # If data is a list of games, we need a specific event_id to extract
    # For single-game lookups (event_id provided), filter to that game
    game = data[0] if len(data) == 1 else data
    
    # If game is a list, return empty — caller should filter by event_id
    if isinstance(game, list):
        return {"bookmakers": [], "_all_games": data}
    
    # Transform books array → bookmakers format
    bookmakers = []
    books_by_key = {}
    
    for b in game.get("books", []):
        bk = b.get("book", "")
        mkt = b.get("market", "")
        if bk not in books_by_key:
            books_by_key[bk] = {"key": bk, "markets": []}
        
        # Build market entry in old format
        market_entry = {
            "key": mkt,
            "outcomes": b.get("outcomes", [])
        }
        books_by_key[bk]["markets"].append(market_entry)
    
    result = {
        "bookmakers": list(books_by_key.values()),
        "_event_id": game.get("event_id"),
        "_away_team": game.get("away_team"),
        "_home_team": game.get("home_team"),
        "_start_time": game.get("start_time"),
    }
    return result

# ── Daily Cache (avoid double-counting API tokens) ────────
CACHE_DIR = Path("/home/workspace/Daily_Log")

def _cache_path(sport: str, event_id: str = None) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    d = CACHE_DIR / today
    d.mkdir(parents=True, exist_ok=True)
    if event_id:
        return d / f"consensus_{sport}_{event_id}.json"
    return d / f"consensus_slate_{sport}.json"

def _load_cache(sport: str, event_id: str) -> Optional[dict]:
    p = _cache_path(sport, event_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None

def _save_cache(sport: str, event_id: str, data: dict):
    p = _cache_path(sport, event_id)
    p.write_text(json.dumps(data, indent=2, default=str))

def get_consensus_lines_cached(
    sport: str,
    event_id: str,
    markets: Optional[List[str]] = None,
    force: bool = False,
) -> dict:
    """Fetch consensus lines with daily cache to avoid double-counting API tokens."""
    if not force:
        cached = _load_cache(sport, event_id)
        if cached:
            cached["_from_cache"] = True
            return cached

    result = get_consensus_lines(sport, event_id, markets)
    if result.get("source") not in ("error", "none"):
        _save_cache(sport, event_id, result)
    result["_from_cache"] = False
    return result

def fetch_sport_batch(sport: str, markets: Optional[List[str]] = None, force: bool = False) -> dict:
    """Fetch consensus for ALL upcoming games in a sport. One events-list call, cached per-event odds."""
    sport_key = ODDS_SPORT_MAP.get(sport.upper())
    if not sport_key:
        return {"events": {}, "error": f"No sport key for {sport}"}

    if not ODDS_KEY:
        return {"events": {}, "error": "ODDS_API_KEY not set"}

    today = datetime.now().strftime("%Y-%m-%d")
    batch_cache = _cache_path(sport, None).with_name(f"consensus_batch_{sport}_{today}.json")

    if batch_cache.exists() and not force:
        try:
            return json.loads(batch_cache.read_text())
        except Exception:
            import logging as _log
            _log.getLogger(__name__).debug("exception", exc_info=True)

    # Step 1: Get all events with odds (one API call)
    try:
        r = requests.get(
            f"{ODDS_BASE}/odds/",
            params={
                "sport_key": sport_key,
                "regions": "us",
                "apiKey": ODDS_KEY,
            },
            timeout=15
        )
        r.raise_for_status()
        ev_data = r.json()
        # New envelope: {success, source, data: [{event_id, books: [...]}]}
        if isinstance(ev_data, dict) and 'data' in ev_data and isinstance(ev_data['data'], list):
            events = ev_data['data']
        else:
            events = ev_data if isinstance(ev_data, list) else []
    except Exception as e:
        return {"events": {}, "error": f"events fetch: {e}"}

    # Step 2: For each event, normalize odds (no extra API calls needed — all odds in one response)
    results = {}
    total_api_calls = 1

    for ev in events:
        eid = ev.get("event_id")
        if not eid:
            continue
        away = ev.get("away_team", "???")
        home = ev.get("home_team", "???")
        commence = ev.get("start_time", "")

        # Normalize this single game into old format and run consensus
        normalized = _normalize_odds_response({"data": [ev]})
        consensus = _build_consensus_from_bookmakers(normalized.get("bookmakers", []))
        total_api_calls += 0  # No extra calls — all data from one request

        results[eid] = {
            "away": away, "home": home, "matchup": f"{away} @ {home}",
            "commence_time": commence,
            "player_count": consensus.get("player_count", 0),
            "available_books": consensus.get("available_books", []),
            "players": consensus.get("players", {}),
            "game_total": consensus.get("game_total"),
            "source": "api.theoddsapi.com",
            "from_cache": False,
        }

    batch = {
        "events": results,
        "total_events": len(results),
        "total_api_calls": total_api_calls,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sport": sport,
        "cached": True,
    }
    batch_cache.write_text(json.dumps(batch, indent=2, default=str))
    return batch

def fetch_consensus_for_matchup(sport: str, away: str, home: str, markets=None) -> dict:
    """Find an event by matchup and return consensus lines. One odds call for all games.

    Falls back to SGO (for MLB, World Cup) when Odds API returns no usable data.
    """
    sport_key = CONSENSUS_SPORT_MAP.get(sport.upper())
    if not sport_key:
        return {"players": {}, "available_books": [], "source": "none", "error": f"No sport key for {sport}"}
    if not ODDS_KEY:
        # No Odds API key — go straight to SGO
        sgo_res = _sgo_consensus_for_matchup(sport, away, home)
        if sgo_res.get("players"):
            return sgo_res
        return sgo_res

    try:
        mkt = markets or "player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks"
        r = requests.get(
            f"{ODDS_BASE}/odds/",
            params={
                "sport_key": sport_key,
                "regions": "us",
                "markets": mkt,
                "oddsFormat": "american",
                "apiKey": ODDS_KEY,
            },
            timeout=15
        )
        if r.status_code != 200:
            # Odds API dead — fall back to SGO for MLB/WC
            print(f"  [Odds API {r.status_code}] falling back to SGO for {sport}")
            sgo_res = _sgo_consensus_for_matchup(sport, away, home)
            if sgo_res.get("players"):
                return sgo_res
            return {"players": {}, "available_books": [], "source": "odds_dead_sgo_empty",
                    "odds_status": r.status_code, "odds_body": r.text[:200]}
        raw = r.json()
        events = raw.get("data", [])
    except Exception as e:
        # Network / parse failure — try SGO for MLB/WC
        print(f"  [Odds API err: {e}] falling back to SGO for {sport}")
        sgo_res = _sgo_consensus_for_matchup(sport, away, home)
        if sgo_res.get("players"):
            return sgo_res
        return {"players": {}, "available_books": [], "source": "odds_err_sgo_empty", "error": str(e)}

    ev = None
    a, h = away.upper(), home.upper()
    team_map = WNBA_TEAM_MAP if sport.upper() == "WNBA" else (MLB_TEAM_MAP if sport.upper() == "MLB" else {})
    away_full = team_map.get(a, "").lower()
    home_full = team_map.get(h, "").lower()

    for e in events:
        ea = (e.get("away_team") or "").lower()
        eh = (e.get("home_team") or "").lower()
        # Direct abbreviation substring match
        if a.lower() in ea and h.lower() in eh:
            ev = e; break
        # Full team name match via WNBA map
        if away_full and away_full in ea and home_full and home_full in eh:
            ev = e; break
        # Partial match
        if away_full and away_full in ea and h.lower() in eh:
            ev = e; break
        if home_full and home_full in eh and a.lower() in ea:
            ev = e; break
        # Reverse check with suffixes stripped
        ea_norm = ea.split()[-1] if ea else ""
        eh_norm = eh.split()[-1] if eh else ""
        if a.lower() in ea_norm and h.lower() in eh_norm:
            ev = e; break

    if not ev:
        return {"players": {}, "available_books": [], "source": "none", "error": f"No event for {away}@{home}"}

    # Normalize and build consensus
    normalized = _normalize_odds_response({"data": [ev]})
    result = _build_consensus_from_bookmakers(normalized.get("bookmakers", []))

    # If Odds API has the event but returned 0 player props (common when key
    # tier doesn't include player markets), fall back to SGO for MLB/WC.
    if not result.get("players") and sport.upper() in ("MLB", "WORLD CUP"):
        print(f"  [Odds API 0 players for {sport} {away}@{home}] falling back to SGO")
        sgo_res = _sgo_consensus_for_matchup(sport, away, home)
        if sgo_res.get("players"):
            return sgo_res
        return {"players": {}, "available_books": [], "source": "odds_zero_players_sgo_empty",
                "odds_books": result.get("all_books_seen", [])}

    result["_from_cache"] = False
    _save_cache(sport, ev.get("event_id", ""), result)
    return result

def _norm_name(name: str) -> str:
    """Normalize player name for cross-book matching."""
    return name.lower().replace("'", "").replace(",", "").replace(".", "").strip()

def _avg_trimmed(values: List[float], trim_pct: float = 0.2) -> Optional[float]:
    """Trimmed mean: drop top/bottom trim_pct%, average the middle."""
    if not values:
        return None
    if len(values) <= 2:
        return sum(values) / len(values)
    sv = sorted(values)
    trim_n = max(1, int(len(sv) * trim_pct))
    middle = sv[trim_n:-trim_n] if len(sv) > 2 * trim_n else sv
    return sum(middle) / len(middle)

def get_consensus_lines(
    sport: str,
    event_id: str,
    markets: Optional[List[str]] = None,
) -> dict:
    """
    Fetch player prop lines from ALL available books and build consensus.

    Returns:
      { players: { "Name": { "points": { consensus, dk, fd, ..., best_book, all_lines, source_count } } },
        game_total: ...,
        available_books: [...],
    """
    if not ODDS_KEY:
        return {"players": {}, "available_books": [], "source": "none", "error": "ODDS_API_KEY not set"}

    sport_key = ODDS_SPORT_MAP.get(sport.upper())
    if not sport_key:
        return {"players": {}, "available_books": [], "source": "none",
                "error": f"No sport key for {sport}"}

    try:
        r = requests.get(
            f"{ODDS_BASE}/odds/",
            params={
                "sport_key": sport_key,
                "regions": "us",
                "eventId": event_id,
                "apiKey": ODDS_KEY,
            },
            timeout=25,
        )
        r.raise_for_status()
        raw = r.json()
        # Normalize response format
        data = _normalize_odds_response(raw)
    except Exception as e:
        return {"players": {}, "available_books": [], "source": "error",
                "error": str(e)}

    return _build_consensus_from_bookmakers(data.get("bookmakers", []))

def _build_consensus_from_bookmakers(bookmakers: list) -> dict:
    """Build consensus from bookmakers list (old format). Extracted for reuse."""
    # ── Collect per-book, per-player, per-stat lines ──────
    all_books = set()
    # player_lines[book][norm_name][stat] = line_value
    player_lines: Dict[str, Dict[str, Dict[str, float]]] = {}
    game_total = None

    for bm in bookmakers:
        bk_key = bm.get("key", "")
        all_books.add(bk_key)
        if bk_key not in player_lines:
            player_lines[bk_key] = {}

        for market in bm.get("markets", []):
            mkey = market.get("key", "")
            stat = ODDS_STAT_REVERSE.get(mkey)
            if stat:
                for outcome in market.get("outcomes", []):
                    name = outcome.get("description") or outcome.get("name", "")
                    line = outcome.get("point")
                    if name and line is not None:
                        try: line = float(line)
                        except (TypeError, ValueError): continue
                        is_over = "Over" in outcome.get("name", "")
                        norm = _norm_name(name)
                        if is_over:
                            player_lines[bk_key].setdefault(norm, {})[stat] = line
            elif mkey == "totals":
                for outcome in market.get("outcomes", []):
                    if outcome.get("name") == "Over" and not game_total:
                        game_total = outcome.get("point")

    # ── Build consensus ───────────────────────────────────
    available_books = [b for b in BOOK_PRIORITY if b in all_books]

    # Collect all (player, stat) pairs across books
    all_entries: Dict[Tuple[str, str], Dict[str, float]] = {}
    for bk_key in all_books:
        for norm_name, stats in player_lines.get(bk_key, {}).items():
            for stat, line in stats.items():
                key = (norm_name, stat)
                if key not in all_entries:
                    all_entries[key] = {}
                all_entries[key][bk_key] = line

    players_out = {}
    for (norm_name, stat), book_lines in all_entries.items():
        # Best book (by priority, not by line magnitude)
        best_book = None
        for bk_key in available_books:
            if bk_key in book_lines:
                best_book = bk_key
                break

        all_vals = list(book_lines.values())
        consensus = _avg_trimmed(all_vals)

        entry = {
            "consensus": round(consensus, 1) if consensus else None,
            "all_lines": sorted(all_vals),
            "source_count": len(book_lines),
            "best_book": best_book,
        }
        # Per-book lines
        for bk_key in available_books:
            if bk_key in book_lines:
                entry[bk_key] = book_lines[bk_key]

        players_out.setdefault(norm_name, {})[stat] = entry

    # Best-effort display names (from any book's raw data)
    display_names = {}
    for bm in bookmakers:
        for market in bm.get("markets", []):
            stat = ODDS_STAT_REVERSE.get(market.get("key", ""))
            if not stat: continue
            for outcome in market.get("outcomes", []):
                desc = outcome.get("description") or outcome.get("name", "")
                if desc:
                    display_names[_norm_name(desc)] = desc

    # Add display names to output
    players_with_names = {}
    for norm_name, stats in players_out.items():
        display = display_names.get(norm_name, norm_name)
        players_with_names[display] = stats

    return {
        "players": players_with_names,
        "game_total": game_total,
        "available_books": available_books,
        "all_books_seen": sorted(all_books),
        "player_count": len(players_with_names),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

def get_best_line(
    consensus: dict,
    player_name: str,
    stat: str,
    prefer_book: str = "draftkings",
) -> Optional[float]:
    """Get the best available line for a player+stat. Falls back through books."""
    stat_map = {
        "PTS": "points", "REB": "rebounds", "AST": "assists",
        "3PM": "threes", "STL": "steals", "BLK": "blocks",
        "G": "goals", "A": "assists", "SOG": "shots_on_target",
    }
    stat_key = stat_map.get(stat, stat.lower())

    player_data = consensus.get("players", {}).get(player_name)
    if not player_data:
        # Try fuzzy match
        norm_target = _norm_name(player_name)
        for pname, pdata in consensus.get("players", {}).items():
            if _norm_name(pname) == norm_target:
                player_data = pdata
                break
        if not player_data:
            return None

    entry = player_data.get(stat_key)
    if not entry:
        return None

    # Prefer the requested book, fall back to consensus
    if prefer_book in entry and entry[prefer_book] is not None:
        return entry[prefer_book]
    return entry.get("consensus")

def merge_consensus_into_picks(
    picks: list,
    consensus: dict,
    prefer_book: str = "draftkings",
) -> list:
    """Enrich a list of pick dicts with consensus line data."""
    for p in picks:
        player = p.get("player", "")
        stat = p.get("stat", "")
        line = get_best_line(consensus, player, stat, prefer_book)
        if line is not None:
            p["consensus_line"] = line
            p["consensus_source"] = consensus.get("source", "unknown")
            p["consensus_books"] = len(consensus.get("available_books", []))
    return picks

# ── Batch Caching (token-efficient) ───

# ── CLI ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Source Consensus Line Engine")
    parser.add_argument("--sport", required=True, help="NBA, WNBA, NHL, MLB, MLS, etc.")
    parser.add_argument("--event-id", help="Odds API event ID")
    parser.add_argument("--matchup", help="Away@Home (finds event automatically)")
    parser.add_argument("--output", choices=["json", "table"], default="json")
    args = parser.parse_args()

    if args.event_id:
        result = get_consensus_lines(args.sport, args.event_id)
    elif args.matchup:
        sport_key = ODDS_SPORT_MAP.get(args.sport.upper())
        if not sport_key:
            print(json.dumps({"error": f"No sport key for {args.sport}"}))
            sys.exit(1)
        parts = args.matchup.split("@")
        if len(parts) != 2:
            print(json.dumps({"error": "Matchup must be Away@Home"}))
            sys.exit(1)
        away, home = parts

        # Find event via odds endpoint
        r = requests.get(
            f"{ODDS_BASE}/odds/",
            params={
                "sport_key": sport_key,
                "regions": "us",
                "apiKey": ODDS_KEY,
            },
            timeout=15
        )
        events_data = r.json()
        events = events_data.get("data", [])
        ev = None
        for e in events:
            if away.upper() in e.get("away_team", "").upper() and home.upper() in e.get("home_team", "").upper():
                ev = e; break
        if not ev:
            print(json.dumps({"error": f"No event for {args.matchup}"}))
            sys.exit(1)
        result = get_consensus_lines(args.sport, ev["event_id"])
    else:
        print(json.dumps({"error": "Need --event-id or --matchup"}))
        sys.exit(1)

    if args.output == "table":
        print(f"\n{'='*60}")
        print(f"Consensus Lines — {args.sport} | Books: {', '.join(result.get('available_books', []))}")
        print(f"{'='*60}")
        for name, stats in sorted(result.get("players", {}).items()):
            print(f"\n  {name}")
            for stat, entry in sorted(stats.items()):
                c = entry.get("consensus", "?")
                lines = ", ".join(f"{b}={entry.get(b,'?')}" for b in result.get("available_books", []) if b in entry)
                print(f"    {stat:12s}  consensus={c:5.1f}  sources={entry['source_count']}  [{lines}]")
    else:
        print(json.dumps(result, indent=2, default=str))

def list_sport_games(sport: str) -> dict:
    """List all upcoming games for a sport. Zero token cost — events list only, no odds."""
    sport_key = ODDS_SPORT_MAP.get(sport.upper())
    if not sport_key:
        return {"games": [], "error": f"No sport key for {sport}"}
    if not ODDS_KEY:
        return {"games": [], "error": "ODDS_API_KEY not set"}
    try:
        r = requests.get(
            params={"regions": "us", "dateFormat": "iso"}, timeout=15
        )
        r.raise_for_status()
        _d = r.json()
        events = _d["data"] if isinstance(_d, dict) and "data" in _d else _d

        ev = None
        for e in events:
            if away.upper() in e.get("away_team", "").upper() and home.upper() in e.get("home_team", "").upper():
                ev = e; break
        if not ev:
            print(json.dumps({"error": f"No event for {args.matchup}"}))
            sys.exit(1)
        result = get_consensus_lines(args.sport, ev["event_id"])
    except Exception as e:
        return {"games": [], "error": str(e)}
    games = []
    for ev in events:
        games.append({
            "id": ev.get("event_id"),
            "away": ev.get("away_team", "??"),
            "home": ev.get("home_team", "??"),
            "commence": ev.get("commence_time", ""),
        })
    return {"sport": sport, "game_count": len(games), "games": games}
